"""Chat service and web-layer schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelSelection(BaseModel):
    """Request-scoped model selection."""

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


class SelectedModelInfo(BaseModel):
    """Resolved model info returned to callers and persisted in metadata."""

    provider: str
    model: str
    base_url: str = ""
    source: str = "env"
    available: bool = True
    api_key_configured: bool = True
    active: bool = False


class ChatMetrics(BaseModel):
    """Aggregated metrics for a single chat turn."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0


class ChatSessionMessage(BaseModel):
    """Stored chat session message."""

    role: Literal["system", "user", "assistant"]
    content: str
    created_at: str = Field(default_factory=_utc_now_iso)
    run_id: str | None = None
    path: str | None = None
    trace_path: str | None = None


class ChatTurnRequest(BaseModel):
    """Single chat turn request."""

    prompt: str
    session_id: str | None = None
    force_path: Literal["auto", "single", "moa"] = "auto"
    evaluate: bool = False
    task_type: Literal["summarize", "explain", "ideate", "critique_rewrite"] = "explain"
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[ChatSessionMessage] = Field(default_factory=list)
    global_model: ModelSelection | None = None
    agent_overrides: dict[str, ModelSelection] = Field(default_factory=dict)
    preset_id: str | None = None
    save_output: bool = False
    output_tag: str | None = None


class ChatTurnResponse(BaseModel):
    """Single chat turn response."""

    session_id: str | None = None
    run_id: str
    prompt: str
    reply: str
    path: str
    routing_reason: str = ""
    routing_confidence: float = 0.0
    metrics: ChatMetrics = Field(default_factory=ChatMetrics)
    trace_path: str = ""
    output_path: str = ""
    agent_count: int = 0
    agents: list[str] = Field(default_factory=list)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    evaluation_context: dict[str, Any] = Field(default_factory=dict)
    context_metadata: dict[str, Any] = Field(default_factory=dict)
    selected_models: dict[str, SelectedModelInfo] = Field(default_factory=dict)
    resolved_provider_map: dict[str, str] = Field(default_factory=dict)
    fallback_reasons: dict[str, str | None] = Field(default_factory=dict)
    preset_id: str | None = None
