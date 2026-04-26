"""CostTracker — execution cost and token accounting."""

from typing import Any


MODEL_PRICING: tuple[tuple[str, float, float], ...] = (
    # OpenAI
    ("gpt-5-nano",   0.05 / 1_000_000,  0.40 / 1_000_000),
    ("gpt-5-mini",   0.25 / 1_000_000,  2.00 / 1_000_000),
    ("gpt-5",        1.25 / 1_000_000, 10.00 / 1_000_000),
    ("gpt-4o-mini", 0.15 / 1_000_000, 0.60 / 1_000_000),
    ("gpt-4o", 2.50 / 1_000_000, 10.00 / 1_000_000),
    # Google Gemini  (approx. — Flash-tier pricing)
    ("gemini-3", 0.075 / 1_000_000, 0.30 / 1_000_000),   # Gemini 3.x Flash/Pro preview
    ("gemini-2", 0.075 / 1_000_000, 0.30 / 1_000_000),   # Gemini 2.x Flash
    ("gemini-1", 0.075 / 1_000_000, 0.30 / 1_000_000),   # Gemini 1.5 Flash
    # Zhipu AI GLM  (approx. — Flash-tier pricing)
    ("glm-4", 0.07 / 1_000_000, 0.07 / 1_000_000),       # GLM-4.7-Flash and variants
    ("glm-", 0.07 / 1_000_000, 0.07 / 1_000_000),        # other GLM models fallback
    # Cerebras  (free tier — no token-level charge)
    ("qwen-3-235b", 0.0, 0.0),                            # Qwen3-235B on Cerebras free tier
)


def resolve_model_pricing(model: str) -> dict[str, float]:
    normalized = (model or "").strip().lower()
    for prefix, prompt_rate, completion_rate in MODEL_PRICING:
        if normalized.startswith(prefix):
            return {
                "prompt": prompt_rate,
                "completion": completion_rate,
            }
    return {"prompt": 0.0, "completion": 0.0}


def estimate_token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = resolve_model_pricing(model)
    cost = prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]
    return round(cost, 6)


class CostTracker:
    """Aggregate LLM costs by path and operation type."""

    def __init__(self):
        self._records: list[dict] = []
        self._total_prompt: int = 0
        self._total_completion: int = 0
        self._total_cost: float = 0.0

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
        """Record a single invocation and return its cost."""
        if cost_override is None:
            cost = estimate_token_cost(model, prompt_tokens, completion_tokens)
        else:
            cost = round(cost_override, 6)

        self._records.append(
            {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
                "path": path,
                "agent_name": agent_name,
                "operation_type": operation_type,
                "metadata": metadata or {},
            }
        )

        self._total_prompt += prompt_tokens
        self._total_completion += completion_tokens
        self._total_cost += cost

        return cost

    def summary(self) -> dict:
        """Return cumulative token and cost accounting."""
        path_costs: dict[str, float] = {}
        path_tokens: dict[str, int] = {}
        operation_costs: dict[str, float] = {}
        operation_tokens: dict[str, int] = {}

        for record in self._records:
            path = record["path"]
            path_costs[path] = path_costs.get(path, 0.0) + record["cost"]
            path_tokens[path] = (
                path_tokens.get(path, 0) + record["prompt_tokens"] + record["completion_tokens"]
            )

            operation = record["operation_type"]
            operation_costs[operation] = operation_costs.get(operation, 0.0) + record["cost"]
            operation_tokens[operation] = (
                operation_tokens.get(operation, 0)
                + record["prompt_tokens"]
                + record["completion_tokens"]
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
                operation: {
                    "tokens": operation_tokens[operation],
                    "cost": round(operation_costs[operation], 6),
                }
                for operation in operation_costs
            },
        }

    @property
    def total_cost(self) -> float:
        return round(self._total_cost, 6)

    @property
    def total_tokens(self) -> int:
        return self._total_prompt + self._total_completion

    def __len__(self) -> int:
        return len(self._records)
