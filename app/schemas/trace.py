"""트레이스 스키마 — TraceRecord, CaseResult, RunSummary.

TraceRecord: 개별 에이전트 호출 1건의 추적 기록
CaseResult: 개별 벤치마크 케이스 결과 저장 모델
RunSummary:  한 번의 실행(run) 전체를 요약하는 집계 모델
"""

from typing import Any

from pydantic import BaseModel, Field


class TraceRecord(BaseModel):
    """에이전트 호출 1건의 추적 기록."""
    run_id: str             # 실행 식별자
    agent_name: str         # 호출된 에이전트 이름
    model: str              # 사용된 LLM 모델
    input_prompt: str       # 입력 프롬프트
    output_text: str        # LLM 응답 텍스트
    prompt_tokens: int      # 입력 토큰 수
    completion_tokens: int  # 출력 토큰 수
    latency_ms: float       # 응답 지연 시간 (ms)
    cost_estimate: float    # 추정 비용 (USD)
    timestamp: str          # 호출 시각 (ISO 형식)
    path: str               # 실행 경로 ("single" | "moa" | "full")
    operation_type: str = "llm_completion"  # 연산 유형
    metadata: dict[str, Any] = Field(default_factory=dict)  # 추가 메타데이터


class CaseResult(BaseModel):
    """개별 케이스 결과 저장 모델."""

    case_id: str
    task_type: str
    prompt: str
    output: str
    path: str = "moa"
    routing_reason: str = ""
    routing_confidence: float = 0.0
    agent_count: int = 0
    agents: list[str] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    constraints: dict[str, Any] = Field(default_factory=dict)
    evaluation: dict[str, Any] = Field(default_factory=dict)
    evaluation_context: dict[str, Any] = Field(default_factory=dict)
    context_metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    """한 번의 실행(run) 전체 요약."""
    run_id: str                    # 실행 식별자
    task_id: str                   # 태스크 식별자
    path: str                      # 실행 경로
    total_tokens: int              # 총 토큰 수
    total_cost: float              # 총 비용 (USD)
    total_latency_ms: float        # 총 지연 시간 (ms)
    agent_count: int               # 호출된 에이전트 수
    traces: list[TraceRecord]      # 개별 호출 기록 리스트
    final_output: str              # 최종 출력 텍스트
