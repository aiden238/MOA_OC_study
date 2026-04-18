"""Router — 2단계 하이브리드 라우팅 (Rule-based + LLM 판별).

입력 태스크를 분석하여 single 또는 moa 경로를 자동 선택한다.
기본적으로 `selected_path`는 "single" 또는 "moa"이고,
추가 boolean 플래그로 `requires_rag`/`requires_mcp`를 반환하여
실행기에서 적절히 컨텍스트 주입을 할 수 있도록 설계되어 있다.
"""

import json

from pydantic import BaseModel, Field
from typing import Literal

from app.agents.base_agent import BaseAgent
from app.schemas.task import TaskRequest


class RoutingDecision(BaseModel):
    """라우팅 판정 결과 — 어떤 경로로 태스크를 처리할지 결정.

    `selected_path`는 기본 실행 경로를 의미하고, 추가 플래그로
    `requires_rag` / `requires_mcp`를 사용해 런타임에 RAG/MCP 주입을 제어한다.
    """
    selected_path: Literal["single", "moa"]  # 선택된 실행 경로 (기본)
    reason: str                                # 판정 사유
    confidence: float = Field(ge=0.0, le=1.0)  # 판정 확신도 (0.0~1.0)
    requires_rag: bool = False                 # RAG 컨텍스트 주입 여부
    requires_mcp: bool = False                 # MCP 도구 호출 여부
    rag_query_hint: str | None = None          # RAG 질의 힌트
    mcp_intent: str | None = None              # MCP 호출 의도
    preferred_server: str | None = None        # 선호 MCP 서버
    preferred_tool: str | None = None          # 선호 MCP 도구


def rule_based_route(task: TaskRequest) -> RoutingDecision | None:
    """1단계: Rule-based 필터 — 명확한 케이스만 처리, 애매하면 None 반환.

    LLM 호출 없이 태스크 속성만으로 경로를 결정한다.
    확실한 패턴만 처리하고, 나머지는 2단계 LLM 판별로 넘긴다.
    """
    # 단순 요약 + 낮은 난이도 → single 경로
    if task.task_type == "summarize":
        difficulty = task.constraints.get("difficulty") or task.metadata.get("difficulty", "")
        if difficulty == "low":
            return RoutingDecision(
                selected_path="single",
                reason="단순 요약 + 낮은 난이도 → 단일 호출 충분",
                confidence=0.9,
            )

    # 아이디어 생성 → moa 경로 (다중 관점 필요)
    if task.task_type == "ideate":
        return RoutingDecision(
            selected_path="moa",
            reason="창의적 과제 → 다중 관점 필요",
            confidence=0.85,
        )

    # 비평+재작성 → moa 경로 (Judge/Rewrite 활용)
    if task.task_type == "critique_rewrite":
        return RoutingDecision(
            selected_path="moa",
            reason="비평+재작성 → MOA 파이프라인 필요",
            confidence=0.9,
        )

    # 긴 프롬프트 → moa 경로 (복합 과제 가능성)
    if len(task.prompt) > 500:
        return RoutingDecision(
            selected_path="moa",
            reason="긴 프롬프트 → 복합 과제 가능성",
            confidence=0.7,
        )

    # novelty 제약 → moa 경로 (다양성 필요)
    if "novelty" in str(task.constraints):
        return RoutingDecision(
            selected_path="moa",
            reason="novelty 요구 → 다양성 필요",
            confidence=0.8,
        )

    # RAG 필요성: constraints에 source:rag_docs가 있으면 RAG 플래그 설정
    if isinstance(task.constraints, dict) and task.constraints.get("source") == "rag_docs":
        return RoutingDecision(
            selected_path="moa",
            reason="constraints에 source:rag_docs 포함 → RAG 필요",
            confidence=0.95,
            requires_rag=True,
            rag_query_hint=task.prompt,
        )

    # MCP 필요성: 외부 도구 필요 키워드(파일 목록, 웹 검색, 현재 날씨 등)
    mcp_keywords = ["현재 날씨", "파일 목록", "웹 검색", "파일", "시스템 정보", "os 목록"]
    if any(k in task.prompt for k in mcp_keywords):
        return RoutingDecision(
            selected_path="moa",
            reason="프롬프트에 외부 도구 필요 키워드 포함 → MCP 필요",
            confidence=0.9,
            requires_mcp=True,
            mcp_intent="filesystem_lookup",
            preferred_server="filesystem",
            preferred_tool="list_files",
        )

    # 애매한 경우 → None (2단계 LLM 판별 필요)
    return None


# LLM 라우터용 시스템 프롬프트
_ROUTER_SYSTEM_PROMPT = """당신은 태스크 라우팅 전문가입니다.
주어진 요청을 분석하여, 단일 LLM 호출(single)로 충분한지 또는 다중 관점 파이프라인(moa)이 필요한지 판단하세요.

아울러 요청에 RAG(문서 검색)이나 MCP(외부 도구 호출)가 필요한지 여부도 판별해 주십시오.

반드시 아래 JSON 형식으로만 응답하세요:
{"selected_path": "single|moa", "reason": "판단 근거", "confidence": 0.0~1.0, "requires_rag": false, "requires_mcp": false, "rag_query_hint": null, "mcp_intent": null, "preferred_server": null, "preferred_tool": null}
"""


async def llm_route(task: TaskRequest) -> RoutingDecision:
    """2단계: LLM 판별 — 1단계에서 결정 못 한 애매한 케이스를 LLM으로 판정."""
    agent = BaseAgent(agent_name="router", system_prompt=_ROUTER_SYSTEM_PROMPT)

    message = f"""[태스크 유형] {task.task_type}
[프롬프트] {task.prompt[:300]}
[제약 조건] {json.dumps(task.constraints, ensure_ascii=False) if task.constraints else "없음"}

이 요청은 단일 LLM 호출(single)로 충분한가요, 다중 관점 파이프라인(moa)이 필요한가요? 추가로 RAG나 MCP가 필요한지 여부도 알려주세요."""

    result = await agent.run(message, temperature=0.2)

    # JSON 파싱
    try:
        text = result.content.strip()
        if text.startswith("``"):
            lines = text.split("\n")
            json_lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(json_lines)
        data = json.loads(text)
        return RoutingDecision(
            selected_path=data.get("selected_path", "single"),
            reason=data.get("reason", "LLM 판별"),
            confidence=float(data.get("confidence", 0.5)),
            requires_rag=bool(data.get("requires_rag", False)),
            requires_mcp=bool(data.get("requires_mcp", False)),
            rag_query_hint=data.get("rag_query_hint"),
            mcp_intent=data.get("mcp_intent"),
            preferred_server=data.get("preferred_server"),
            preferred_tool=data.get("preferred_tool"),
        )
    except (json.JSONDecodeError, KeyError):
        # 파싱 실패 시 안전한 기본값 — moa 경로 (더 안전한 선택)
        return RoutingDecision(
            selected_path="moa",
            reason="LLM 라우팅 응답 파싱 실패 → 안전하게 moa 선택",
            confidence=0.5,
            requires_rag=False,
            requires_mcp=False,
            rag_query_hint=None,
            mcp_intent=None,
            preferred_server=None,
            preferred_tool=None,
        )


class Router:
    """2단계 하이브리드 라우터 — Rule-based 우선, 실패 시 LLM 판별."""

    async def route(self, task: TaskRequest) -> RoutingDecision:
        """태스크를 분석하여 single 또는 moa 경로를 결정.

        1단계 rule_based_route()가 결정하면 즉시 반환 (LLM 비용 절약).
        결정 못 하면 2단계 llm_route()로 LLM을 호출하여 판정.
        """
        # 1단계: Rule-based 필터
        decision = rule_based_route(task)
        if decision is not None:
            return decision

        # 2단계: LLM 판별 (비용 발생)
        return await llm_route(task)
