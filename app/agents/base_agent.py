"""BaseAgent — httpx + pydantic 기반 LLM API 호출 래퍼.

모든 에이전트(Draft, Critic, Synthesizer 등)의 부모 클래스.
OpenAI Chat Completions API를 httpx로 호출하고
AgentOutput 스키마로 정형화된 결과를 반환한다.
"""

from pathlib import Path

import httpx

from app.core.config import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    MAX_TOKENS,
    OPENAI_API_KEY,
    PROJECT_ROOT,
)
from app.core.timer import measure_time
from app.schemas.agent_io import AgentInput, AgentOutput


class BaseAgent:
    """모든 에이전트의 기반 클래스. httpx로 LLM API를 호출하고 AgentOutput을 반환."""

    # 역할별 시스템 프롬프트 마크다운 파일이 위치한 디렉토리
    PROMPTS_DIR = PROJECT_ROOT / "app" / "prompts"

    def __init__(self, agent_name: str, system_prompt: str | None = None):
        self.agent_name = agent_name          # 에이전트 식별 이름
        self.system_prompt = system_prompt or ""  # LLM에 전달할 시스템 프롬프트

    async def run(self, user_message: str, **kwargs) -> AgentOutput:
        """사용자 메시지를 받아 LLM을 호출하고 AgentOutput을 반환."""
        # 입력 스키마 구성
        agent_input = AgentInput(
            agent_name=self.agent_name,
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=kwargs.get("temperature", DEFAULT_TEMPERATURE),
            max_tokens=kwargs.get("max_tokens", MAX_TOKENS),
        )
        # LLM 호출 (measure_time 데코레이터가 지연시간도 함께 반환)
        output, latency_ms = await self._call_llm(agent_input)
        # 결과를 AgentOutput 스키마로 변환
        return AgentOutput(
            agent_name=self.agent_name,
            content=output["content"],
            model=output["model"],
            prompt_tokens=output["prompt_tokens"],
            completion_tokens=output["completion_tokens"],
            latency_ms=latency_ms,
            cost_estimate=self._estimate_cost(
                output["prompt_tokens"], output["completion_tokens"], output["model"]
            ),
            raw_response=output.get("raw", {}),
        )

    @measure_time
    async def _call_llm(self, agent_input: AgentInput) -> dict:
        """OpenAI Chat Completions API를 호출하고 응답을 딕셔너리로 반환."""
        model = DEFAULT_MODEL
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": agent_input.system_prompt},
                {"role": "user", "content": agent_input.user_message},
            ],
            "temperature": agent_input.temperature,
            "max_tokens": agent_input.max_tokens,
        }

        # httpx 비동기 클라이언트로 API 호출
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()  # 4xx/5xx 에러 시 예외 발생
            data = resp.json()

        # 응답에서 필요한 필드 추출
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "content": choice,
            "model": data.get("model", model),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "raw": data,
        }

    @staticmethod
    def _estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """모델별 토큰 단가를 기반으로 API 호출 비용을 추정 (USD)."""
        pricing = {
            # (입력 단가/토큰, 출력 단가/토큰) — 2024년 기준 공식 가격
            "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
            "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        }
        input_rate, output_rate = pricing.get(model, (0.0, 0.0))
        return round(prompt_tokens * input_rate + completion_tokens * output_rate, 6)

    @classmethod
    def load_prompt(cls, prompt_name: str) -> str:
        """app/prompts/{prompt_name}.md 파일을 읽어 시스템 프롬프트 텍스트로 반환."""
        prompt_path = cls.PROMPTS_DIR / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
