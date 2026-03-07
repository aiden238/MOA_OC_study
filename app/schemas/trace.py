"""트레이스 스키마 — TraceRecord, RunSummary."""

from pydantic import BaseModel


class TraceRecord(BaseModel):
    run_id: str
    agent_name: str
    model: str
    input_prompt: str
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float
    timestamp: str
    path: str  # "single" | "moa" | "rag" | "mcp"


class RunSummary(BaseModel):
    run_id: str
    task_id: str
    path: str
    total_tokens: int
    total_cost: float
    total_latency_ms: float
    agent_count: int
    traces: list[TraceRecord]
    final_output: str
