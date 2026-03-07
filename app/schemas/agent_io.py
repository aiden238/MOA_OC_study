"""에이전트 입출력 스키마 — AgentInput, AgentOutput."""

from typing import Any

from pydantic import BaseModel


class AgentInput(BaseModel):
    agent_name: str
    system_prompt: str
    user_message: str
    temperature: float = 0.7
    max_tokens: int = 1024


class AgentOutput(BaseModel):
    agent_name: str
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float = 0.0
    raw_response: dict[str, Any] = {}
