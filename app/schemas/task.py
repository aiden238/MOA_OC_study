"""태스크 관련 스키마 — TaskRequest, TaskPlan.

TaskRequest: 사용자 입력을 정형화하는 요청 모델
TaskPlan: Router/Planner가 결정한 실행 계획 모델
"""

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """사용자의 태스크 요청을 표현하는 스키마."""
    task_id: str = Field(default_factory=lambda: uuid4().hex[:12])  # 고유 식별자 (자동 생성)
    prompt: str                                                      # 사용자 프롬프트
    task_type: Literal["summarize", "explain", "ideate", "critique_rewrite"] = "explain"  # 태스크 유형
    constraints: dict[str, Any] = {}   # 제약 조건 (예: max_sentences, audience)
    metadata: dict[str, Any] = {}      # 부가 메타데이터


class TaskPlan(BaseModel):
    """Router/Planner가 결정한 실행 계획."""
    original_request: TaskRequest       # 원본 요청
    subtasks: list[str] = []            # 분해된 하위 태스크 목록
    selected_path: Literal["single", "moa"] = "single"  # 실행 경로 선택
    requires_rag: bool = False          # RAG 필요 여부 (6주차)
    requires_mcp: bool = False          # MCP 필요 여부 (6주차)
