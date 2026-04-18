"""CostTracker — 실행 비용을 토큰·달러로 집계하는 트래커.

모든 LLM 호출의 토큰 사용량과 비용을 실시간으로 누적하여
경로별(single/moa) 비용 분석을 지원한다.
"""

from typing import Any


class CostTracker:
    """LLM 호출 비용을 모델·경로별로 집계하는 트래커."""

    # 모델별 토큰 단가 (USD per token) — 2024년 공식 가격 기준
    PRICING: dict[str, dict[str, float]] = {
        "gpt-4o-mini": {
            "prompt": 0.15 / 1_000_000,      # $0.15 / 1M tokens
            "completion": 0.60 / 1_000_000,   # $0.60 / 1M tokens
        },
        "gpt-4o": {
            "prompt": 2.50 / 1_000_000,      # $2.50 / 1M tokens
            "completion": 10.00 / 1_000_000,  # $10.00 / 1M tokens
        },
    }

    def __init__(self):
        self._records: list[dict] = []     # 개별 호출 기록
        self._total_prompt: int = 0        # 누적 입력 토큰
        self._total_completion: int = 0    # 누적 출력 토큰
        self._total_cost: float = 0.0      # 누적 비용 (USD)

    def add(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        path: str = "unknown",
        agent_name: str = "",
        operation_type: str = "llm_completion",
        metadata: dict[str, Any] | None = None,
        cost_override: float | None = None,
    ) -> float:
        """호출 1건의 비용을 집계하고 추정 비용을 반환.

        Args:
            model: 사용된 모델명
            prompt_tokens: 입력 토큰 수
            completion_tokens: 출력 토큰 수
            path: 실행 경로 (single/moa)
            agent_name: 호출한 에이전트 이름

        Returns:
            해당 호출의 추정 비용 (USD)
        """
        pricing = self.PRICING.get(model, {"prompt": 0.0, "completion": 0.0})
        if cost_override is None:
            cost = (prompt_tokens * pricing["prompt"]
                    + completion_tokens * pricing["completion"])
            cost = round(cost, 6)
        else:
            cost = round(cost_override, 6)

        self._records.append({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "path": path,
            "agent_name": agent_name,
            "operation_type": operation_type,
            "metadata": metadata or {},
        })

        self._total_prompt += prompt_tokens
        self._total_completion += completion_tokens
        self._total_cost += cost

        return cost

    def summary(self) -> dict:
        """총 토큰·비용·경로별 집계를 반환."""
        # 경로별 비용 집계
        path_costs: dict[str, float] = {}
        path_tokens: dict[str, int] = {}
        operation_costs: dict[str, float] = {}
        operation_tokens: dict[str, int] = {}
        for r in self._records:
            p = r["path"]
            path_costs[p] = path_costs.get(p, 0.0) + r["cost"]
            path_tokens[p] = (path_tokens.get(p, 0)
                              + r["prompt_tokens"] + r["completion_tokens"])
            op = r["operation_type"]
            operation_costs[op] = operation_costs.get(op, 0.0) + r["cost"]
            operation_tokens[op] = (
                operation_tokens.get(op, 0)
                + r["prompt_tokens"] + r["completion_tokens"]
            )

        return {
            "total_prompt_tokens": self._total_prompt,
            "total_completion_tokens": self._total_completion,
            "total_tokens": self._total_prompt + self._total_completion,
            "total_cost": round(self._total_cost, 6),
            "call_count": len(self._records),
            "by_path": {
                path: {
                    "tokens": path_tokens[path],
                    "cost": round(path_costs[path], 6),
                }
                for path in path_costs
            },
            "by_operation_type": {
                operation_type: {
                    "tokens": operation_tokens[operation_type],
                    "cost": round(operation_costs[operation_type], 6),
                }
                for operation_type in operation_costs
            },
        }

    @property
    def total_cost(self) -> float:
        """누적 총 비용."""
        return round(self._total_cost, 6)

    @property
    def total_tokens(self) -> int:
        """누적 총 토큰."""
        return self._total_prompt + self._total_completion

    def __len__(self) -> int:
        """기록된 호출 건수."""
        return len(self._records)
