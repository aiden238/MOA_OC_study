"""Router + RetryPolicy 단위/통합 테스트.

- Rule-based 라우팅 검증 (summarize/low → single, ideate → moa 등)
- LLM 라우팅 Mock 테스트
- Router 2단계 통합 테스트
- RetryPolicy 로직 테스트
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.orchestrator.router import (
    Router,
    RoutingDecision,
    llm_route,
    rule_based_route,
)
from app.orchestrator.retry_policy import RetryPolicy
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest


# ── Rule-based 라우팅 테스트 ──

class TestRuleBasedRoute:

    def test_summarize_low_returns_single(self):
        """summarize + difficulty=low → single 경로."""
        task = TaskRequest(
            prompt="이 글을 요약해 주세요.",
            task_type="summarize",
            constraints={"difficulty": "low"},
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "single"
        assert decision.confidence >= 0.8

    def test_ideate_returns_moa(self):
        """ideate → moa 경로 (다중 관점 필요)."""
        task = TaskRequest(
            prompt="AI 활용 아이디어를 제안하세요.",
            task_type="ideate",
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"

    def test_critique_rewrite_returns_moa(self):
        """critique_rewrite → moa 경로."""
        task = TaskRequest(
            prompt="이 에세이를 비평하고 개선하세요.",
            task_type="critique_rewrite",
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"

    def test_long_prompt_returns_moa(self):
        """500자 초과 프롬프트 → moa 경로."""
        task = TaskRequest(
            prompt="A" * 501,
            task_type="explain",
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"

    def test_novelty_constraint_returns_moa(self):
        """novelty 제약 → moa 경로."""
        task = TaskRequest(
            prompt="새로운 접근법을 제시하세요.",
            task_type="explain",
            constraints={"novelty": "high"},
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"

    def test_ambiguous_returns_none(self):
        """애매한 케이스 → None (2단계로 위임)."""
        task = TaskRequest(
            prompt="짧은 설명 요청",
            task_type="explain",
        )
        decision = rule_based_route(task)
        assert decision is None

    def test_summarize_without_low_difficulty_returns_none(self):
        """summarize이지만 difficulty가 low가 아니면 → None."""
        task = TaskRequest(
            prompt="복잡한 논문을 요약해 주세요.",
            task_type="summarize",
            constraints={"difficulty": "high"},
        )
        decision = rule_based_route(task)
        assert decision is None

    def test_use_mcp_constraint_returns_mcp_decision(self):
        """use_mcp constraint가 있으면 MCP 경로를 우선 선택한다."""
        task = TaskRequest(
            prompt="문서 목록을 보여줘",
            task_type="explain",
            constraints={"use_mcp": True},
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"
        assert decision.requires_mcp is True
        assert decision.mcp_intent == "user_forced"


# ── LLM 라우팅 테스트 ──

class TestLLMRoute:

    @pytest.mark.asyncio
    async def test_llm_route_parses_response(self):
        """LLM 응답을 정상 파싱하는 경우."""
        llm_response = json.dumps({
            "selected_path": "moa",
            "reason": "복합 과제",
            "confidence": 0.75,
            "requires_rag": True,
            "rag_query_hint": "문서 기반 검색 질의",
            "mcp_intent": "filesystem_lookup",
            "preferred_server": "filesystem",
            "preferred_tool": "list_files",
        })
        mock_output = AgentOutput(
            agent_name="router",
            content=llm_response,
            model="gpt-4o-mini",
            prompt_tokens=50,
            completion_tokens=30,
            latency_ms=100.0,
        )

        with patch("app.orchestrator.router.BaseAgent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_output
            task = TaskRequest(prompt="테스트", task_type="explain")
            decision = await llm_route(task)

        assert decision.selected_path == "moa"
        assert decision.confidence == 0.75
        assert decision.requires_rag is True
        assert decision.rag_query_hint == "문서 기반 검색 질의"
        assert decision.mcp_intent == "filesystem_lookup"
        assert decision.preferred_server == "filesystem"
        assert decision.preferred_tool == "list_files"

    @pytest.mark.asyncio
    async def test_llm_route_parse_failure_defaults_to_moa(self):
        """LLM 응답 파싱 실패 시 moa로 안전하게 폴백."""
        mock_output = AgentOutput(
            agent_name="router",
            content="파싱 불가능한 텍스트",
            model="gpt-4o-mini",
            prompt_tokens=50,
            completion_tokens=30,
            latency_ms=100.0,
        )

        with patch("app.orchestrator.router.BaseAgent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_output
            task = TaskRequest(prompt="테스트", task_type="explain")
            decision = await llm_route(task)

        assert decision.selected_path == "moa"
        assert "파싱 실패" in decision.reason
        assert decision.rag_query_hint is None
        assert decision.preferred_tool is None


# ── Router 통합 테스트 ──

class TestRouter:

    @pytest.mark.asyncio
    async def test_route_uses_rule_based_first(self):
        """Router가 rule-based를 먼저 시도하는지 확인."""
        router = Router()
        task = TaskRequest(prompt="아이디어", task_type="ideate")
        decision = await router.route(task)
        # ideate는 rule-based에서 처리됨
        assert decision.selected_path == "moa"

    @pytest.mark.asyncio
    async def test_route_falls_back_to_llm(self):
        """Rule-based가 None이면 LLM 판별로 폴백."""
        llm_response = json.dumps({
            "selected_path": "single",
            "reason": "단순 질문",
            "confidence": 0.8,
        })
        mock_output = AgentOutput(
            agent_name="router",
            content=llm_response,
            model="gpt-4o-mini",
            prompt_tokens=50,
            completion_tokens=30,
            latency_ms=100.0,
        )

        with patch("app.orchestrator.router.BaseAgent.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_output
            router = Router()
            task = TaskRequest(prompt="짧은 질문", task_type="explain")
            decision = await router.route(task)

        assert decision.selected_path == "single"


# ── RoutingDecision 스키마 테스트 ──

class TestRoutingDecision:

    def test_valid_creation(self):
        """정상 RoutingDecision 생성."""
        d = RoutingDecision(
            selected_path="moa",
            reason="복합 과제",
            confidence=0.8,
        )
        assert d.selected_path == "moa"
        assert d.requires_rag is False
        assert d.requires_mcp is False
        assert d.rag_query_hint is None
        assert d.preferred_server is None

    def test_confidence_bounds(self):
        """confidence 범위 위반 시 ValidationError."""
        with pytest.raises(Exception):
            RoutingDecision(selected_path="single", reason="테스트", confidence=1.5)


# ── RetryPolicy 테스트 ──

class TestRetryPolicy:

    def test_default_values(self):
        """기본값 확인."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.backoff_base == 1.0
        assert policy.backoff_max == 30.0

    def test_should_retry_within_limit(self):
        """재시도 횟수 내에서는 True 반환."""
        policy = RetryPolicy(max_retries=3)
        # HTTPStatusError 가정
        error = type("HTTPStatusError", (Exception,), {})()
        assert policy.should_retry(error, attempt=1) is True
        assert policy.should_retry(error, attempt=2) is True

    def test_should_retry_exceeds_limit(self):
        """최대 횟수 초과 시 False 반환."""
        policy = RetryPolicy(max_retries=3)
        error = type("HTTPStatusError", (Exception,), {})()
        assert policy.should_retry(error, attempt=3) is False

    def test_should_retry_non_retryable_error(self):
        """재시도 불가능한 에러 유형은 False."""
        policy = RetryPolicy()
        error = ValueError("잘못된 입력")
        assert policy.should_retry(error, attempt=1) is False

    def test_get_delay_exponential(self):
        """지수 백오프 대기 시간 계산."""
        policy = RetryPolicy(backoff_base=1.0, backoff_max=30.0)
        assert policy.get_delay(0) == 1.0   # 1.0 * 2^0 = 1.0
        assert policy.get_delay(1) == 2.0   # 1.0 * 2^1 = 2.0
        assert policy.get_delay(2) == 4.0   # 1.0 * 2^2 = 4.0
        assert policy.get_delay(5) == 30.0  # 1.0 * 2^5 = 32 → cap at 30

    def test_on_final_failure_logs(self):
        """최종 실패 시 로그에 기록."""
        policy = RetryPolicy()
        error = RuntimeError("네트워크 오류")
        policy.on_final_failure(error, {"agent": "draft", "attempt": 3})
        assert len(policy.failure_log) == 1
        assert policy.failure_log[0]["error_type"] == "RuntimeError"

    def test_reset_clears_log(self):
        """reset()으로 실패 이력 초기화."""
        policy = RetryPolicy()
        policy.on_final_failure(RuntimeError("에러"), {})
        policy.reset()
        assert len(policy.failure_log) == 0
