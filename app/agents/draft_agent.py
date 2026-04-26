"""Draft Agent — 3가지 관점(분석적/창의적/구조적)의 초안을 생성하는 에이전트.

동일한 입력에 대해 서로 다른 temperature와 시스템 프롬프트를 사용하여
다양한 관점의 초안을 생성한다. asyncio.gather()로 병렬 실행하여
응답 시간을 최소화한다.
"""

import asyncio

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest


# Draft 변형별 설정: 프롬프트 파일명과 생성 temperature
DRAFT_VARIANTS = {
    "analytical": {"prompt": "draft_analytical", "temperature": 0.4},  # 분석적: 낮은 온도
    "creative": {"prompt": "draft_creative", "temperature": 0.9},      # 창의적: 높은 온도
    "structured": {"prompt": "draft_structured", "temperature": 0.6},  # 구조적: 중간 온도
}

# API 동시 호출 수 제한 (rate limit 방지)
_semaphore = asyncio.Semaphore(3)


class DraftAgent(BaseAgent):
    """특정 관점의 초안을 생성하는 에이전트. BaseAgent를 상속."""

    def __init__(self, variant: str, model_settings: dict[str, str] | None = None):
        """variant: 'analytical' | 'creative' | 'structured'"""
        if variant not in DRAFT_VARIANTS:
            raise ValueError(f"알 수 없는 Draft 변형: {variant}. 허용: {list(DRAFT_VARIANTS.keys())}")
        config = DRAFT_VARIANTS[variant]
        # 역할별 프롬프트 파일 로딩
        prompt = self.load_prompt(config["prompt"])
        settings = model_settings or {}
        super().__init__(
            agent_name=f"draft_{variant}",
            system_prompt=prompt,
            provider=settings.get("provider"),
            model=settings.get("model"),
            api_key=settings.get("api_key"),
            base_url=settings.get("base_url"),
        )
        self.variant = variant
        self.temperature = config["temperature"]  # 변형별 고유 temperature

    async def run(self, user_message: str, **kwargs) -> AgentOutput:
        """temperature를 변형별 값으로 오버라이드하여 LLM 호출."""
        kwargs.setdefault("temperature", self.temperature)
        return await super().run(user_message, **kwargs)


@retry(
    stop=stop_after_attempt(3),                        # 최대 3회 재시도
    wait=wait_exponential(multiplier=1, min=1, max=10),  # 1→2→4초 지수 백오프
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),  # HTTP 에러 시 재시도
    reraise=True,
)
async def _call_with_retry(agent: DraftAgent, user_message: str) -> AgentOutput:
    """API rate limit(429) 등 HTTP 에러 시 지수 백오프로 재시도."""
    async with _semaphore:  # 동시 호출 수 제한
        return await agent.run(user_message)


async def run_all_drafts(
    task: TaskRequest,
    model_overrides: dict[str, dict[str, str]] | None = None,
) -> tuple[list[AgentOutput], list[dict]]:
    """3개 Draft Agent를 asyncio.gather()로 비동기 병렬 실행.

    하나의 draft가 실패해도 나머지 결과는 반환 (graceful degradation).

    Returns:
        (성공한 AgentOutput 목록, 실패 정보 목록)
        실패 정보: {"agent_name": str, "reason": str}
    """
    model_overrides = model_overrides or {}
    agents = [
        DraftAgent(v, model_settings=model_overrides.get(f"draft_{v}"))
        for v in DRAFT_VARIANTS
    ]
    # 각 에이전트를 병렬로 호출하되, 개별 실패는 예외로 수집
    tasks = [_call_with_retry(agent, task.prompt) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 성공/실패 분리
    outputs: list[AgentOutput] = []
    failures: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            variant = list(DRAFT_VARIANTS.keys())[i]
            agent_name = f"draft_{variant}"
            reason = str(result)
            print(f"  [WARNING] {agent_name} 실패: {reason}")
            failures.append({"agent_name": agent_name, "reason": reason})
        else:
            outputs.append(result)

    if not outputs:
        raise RuntimeError("모든 Draft Agent가 실패했습니다.")

    return outputs, failures
