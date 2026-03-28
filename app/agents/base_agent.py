"""Base agent backed by a provider-configurable chat completions API."""

import asyncio

import httpx

from app.core.config import (
    DEFAULT_TEMPERATURE,
    MAX_RETRIES,
    MAX_TOKENS,
    PROJECT_ROOT,
    resolve_llm_settings,
)
from app.core.timer import measure_time
from app.schemas.agent_io import AgentInput, AgentOutput


class BaseAgent:
    """Base class used by the orchestration agents."""

    PROMPTS_DIR = PROJECT_ROOT / "app" / "prompts"

    def __init__(
        self,
        agent_name: str,
        system_prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.agent_name = agent_name
        self.system_prompt = system_prompt or ""
        self.model_override = model
        self.provider_override = provider
        self.api_key_override = api_key
        self.base_url_override = base_url

    @staticmethod
    def _retryable_status(status_code: int) -> bool:
        if not isinstance(status_code, int):
            return False
        return status_code == 429 or 500 <= status_code < 600

    @staticmethod
    def _uses_max_completion_tokens(provider: str, model: str) -> bool:
        if provider != "openai":
            return False
        return model.startswith("gpt-5") or model.startswith("o1") or model.startswith("o3")

    @staticmethod
    def _supports_custom_temperature(provider: str, model: str) -> bool:
        if provider != "openai":
            return True
        return not model.startswith("gpt-5")

    @staticmethod
    def _default_reasoning_effort(provider: str, model: str) -> str | None:
        if provider == "openai" and model.startswith("gpt-5"):
            return "minimal"
        return None

    @staticmethod
    def _retry_delay_seconds(attempt_index: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(1.0, float(retry_after))
                except ValueError:
                    pass
        return min(8.0, float(2 ** attempt_index))

    async def run(self, user_message: str, **kwargs) -> AgentOutput:
        agent_input = AgentInput(
            agent_name=self.agent_name,
            system_prompt=self.system_prompt,
            user_message=user_message,
            temperature=kwargs.get("temperature", DEFAULT_TEMPERATURE),
            max_tokens=kwargs.get("max_tokens", MAX_TOKENS),
        )
        output, latency_ms = await self._call_llm(
            agent_input,
            response_format=kwargs.get("response_format"),
            reasoning_effort=kwargs.get("reasoning_effort"),
        )
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
    async def _call_llm(
        self,
        agent_input: AgentInput,
        response_format: dict | None = None,
        reasoning_effort: str | None = None,
    ) -> dict:
        settings = resolve_llm_settings(
            agent_name=self.agent_name,
            provider=self.provider_override,
            model=self.model_override,
            api_key=self.api_key_override,
            base_url=self.base_url_override,
        )
        model = settings["model"]
        provider = settings["provider"]
        api_key = settings["api_key"]
        base_url = settings["base_url"]

        if not api_key:
            raise RuntimeError(f"{provider} API key is not configured. Check .env.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": agent_input.system_prompt},
                {"role": "user", "content": agent_input.user_message},
            ],
        }
        if self._supports_custom_temperature(provider, model):
            payload["temperature"] = agent_input.temperature
        if self._uses_max_completion_tokens(provider, model):
            payload["max_completion_tokens"] = agent_input.max_tokens
            resolved_reasoning_effort = reasoning_effort or self._default_reasoning_effort(
                provider, model
            )
            if resolved_reasoning_effort:
                payload["reasoning_effort"] = resolved_reasoning_effort
        else:
            payload["max_tokens"] = agent_input.max_tokens
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            attempts = max(1, MAX_RETRIES)
            last_exc: Exception | None = None

            for attempt in range(attempts):
                try:
                    resp = await client.post(
                        f"{base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    if self._retryable_status(resp.status_code) and attempt < attempts - 1:
                        await asyncio.sleep(self._retry_delay_seconds(attempt, resp))
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if (
                        exc.response is not None
                        and self._retryable_status(exc.response.status_code)
                        and attempt < attempts - 1
                    ):
                        await asyncio.sleep(self._retry_delay_seconds(attempt, exc.response))
                        continue
                    raise
                except httpx.RequestError as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        await asyncio.sleep(self._retry_delay_seconds(attempt))
                        continue
                    raise
            else:
                raise RuntimeError("Chat completion request failed without a response") from last_exc

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
        pricing = {
            "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
            "gpt-4o": (2.50 / 1_000_000, 10.00 / 1_000_000),
        }
        input_rate, output_rate = pricing.get(model, (0.0, 0.0))
        return round(prompt_tokens * input_rate + completion_tokens * output_rate, 6)

    @classmethod
    def load_prompt(cls, prompt_name: str) -> str:
        prompt_path = cls.PROMPTS_DIR / f"{prompt_name}.md"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
