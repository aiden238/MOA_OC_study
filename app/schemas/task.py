"""태스크 관련 스키마 — TaskRequest, TaskPlan."""

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    prompt: str
    task_type: Literal["summarize", "explain", "ideate", "critique_rewrite"] = "explain"
    constraints: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class TaskPlan(BaseModel):
    original_request: TaskRequest
    subtasks: list[str] = []
    selected_path: Literal["single", "moa"] = "single"
    requires_rag: bool = False
    requires_mcp: bool = False
