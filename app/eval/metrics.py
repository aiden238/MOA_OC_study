"""시스템 지표 자동 계산 — trace 데이터에서 비용·토큰·지연 시간 집계.

RunSummary나 TraceRecord 리스트로부터 총 토큰, 비용, 지연시간 등을 계산.
baseline(single)과 실험(moa) 지표를 비교하는 유틸리티도 제공.
"""

from app.schemas.trace import RunSummary, TraceRecord


def compute_metrics(summary: RunSummary) -> dict:
    """RunSummary에서 시스템 지표를 계산하여 딕셔너리로 반환."""
    return {
        "run_id": summary.run_id,
        "task_id": summary.task_id,
        "path": summary.path,
        "total_tokens": summary.total_tokens,
        "total_cost_estimate": round(summary.total_cost, 6),
        "total_latency_ms": round(summary.total_latency_ms, 2),
        "agent_count": summary.agent_count,
        "trace_count": len(summary.traces),
    }


def compute_metrics_from_traces(traces: list[TraceRecord]) -> dict:
    """TraceRecord 리스트에서 직접 시스템 지표를 계산."""
    total_prompt = sum(t.prompt_tokens for t in traces)       # 총 입력 토큰
    total_completion = sum(t.completion_tokens for t in traces)  # 총 출력 토큰
    total_cost = sum(t.cost_estimate for t in traces)          # 총 비용
    total_latency = sum(t.latency_ms for t in traces)          # 총 지연시간
    agents = {t.agent_name for t in traces}                    # 고유 에이전트 집합

    return {
        "total_tokens": total_prompt + total_completion,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_cost_estimate": round(total_cost, 6),
        "total_latency_ms": round(total_latency, 2),
        "agent_count": len(agents),
        "trace_count": len(traces),
    }


def compare_metrics(baseline: dict, experiment: dict) -> dict:
    """두 실행의 지표를 비교하여 비율과 차이를 계산. single vs moa 비교용."""
    def safe_ratio(a: float, b: float) -> float | None:
        """분모가 0이면 None 반환하는 안전한 비율 계산."""
        return round(a / b, 4) if b != 0 else None

    return {
        "token_ratio": safe_ratio(
            experiment.get("total_tokens", 0),
            baseline.get("total_tokens", 1),
        ),
        "cost_ratio": safe_ratio(
            experiment.get("total_cost_estimate", 0),
            baseline.get("total_cost_estimate", 1),
        ),
        "latency_ratio": safe_ratio(
            experiment.get("total_latency_ms", 0),
            baseline.get("total_latency_ms", 1),
        ),
        "token_diff": experiment.get("total_tokens", 0) - baseline.get("total_tokens", 0),
        "cost_diff": round(
            experiment.get("total_cost_estimate", 0) - baseline.get("total_cost_estimate", 0), 6
        ),
        "latency_diff": round(
            experiment.get("total_latency_ms", 0) - baseline.get("total_latency_ms", 0), 2
        ),
    }
