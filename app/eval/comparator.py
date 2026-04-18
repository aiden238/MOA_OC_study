"""경로별 per-case result를 그룹 단위로 비교하는 비교기."""

from typing import Dict, List

from app.schemas.trace import CaseResult


class Comparator:
    """여러 경로의 실행 결과를 baseline/rag/mcp 그룹으로 비교."""

    GROUPS = {
        "baseline": ("single", "moa"),
        "rag": ("moa", "moa+rag"),
        "mcp": ("moa", "moa+mcp"),
    }
    PATH_SPECIFIC_METRICS = (
        "groundedness",
        "citation_traceability",
        "tool_use_correctness",
        "tool_result_faithfulness",
    )

    def _pair_results(
        self,
        left_results: List[CaseResult],
        right_results: List[CaseResult],
    ) -> list[tuple[CaseResult, CaseResult]]:
        left_by_case = {result.case_id: result for result in left_results}
        right_by_case = {result.case_id: result for result in right_results}
        common_ids = sorted(set(left_by_case) & set(right_by_case))
        return [(left_by_case[case_id], right_by_case[case_id]) for case_id in common_ids]

    @staticmethod
    def _avg(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 6)

    @staticmethod
    def _evaluation_score(result: CaseResult, metric: str = "avg_score") -> float | None:
        value = result.evaluation.get(metric)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def compare(self, runs: Dict[str, List[CaseResult]]) -> List[dict]:
        table = []
        for group, (left_path, right_path) in self.GROUPS.items():
            pairs = self._pair_results(runs.get(left_path, []), runs.get(right_path, []))
            if not pairs:
                continue

            token_deltas = []
            cost_deltas = []
            latency_deltas = []
            score_deltas = []
            extra_deltas: dict[str, list[float]] = {
                metric: [] for metric in self.PATH_SPECIFIC_METRICS
            }

            for left, right in pairs:
                left_tokens = left.prompt_tokens + left.completion_tokens
                right_tokens = right.prompt_tokens + right.completion_tokens
                token_deltas.append(right_tokens - left_tokens)
                cost_deltas.append(right.cost_estimate - left.cost_estimate)
                latency_deltas.append(right.latency_ms - left.latency_ms)

                left_score = self._evaluation_score(left)
                right_score = self._evaluation_score(right)
                if left_score is not None and right_score is not None:
                    score_deltas.append(right_score - left_score)

                for metric in self.PATH_SPECIFIC_METRICS:
                    left_metric = self._evaluation_score(left, metric)
                    right_metric = self._evaluation_score(right, metric)
                    if left_metric is not None and right_metric is not None:
                        extra_deltas[metric].append(right_metric - left_metric)

            row = {
                "group": group,
                "left_path": left_path,
                "right_path": right_path,
                "count": len(pairs),
                "avg_score_delta": self._avg(score_deltas),
                "avg_cost_delta": self._avg(cost_deltas),
                "avg_latency_delta": self._avg(latency_deltas),
                "avg_tokens_delta": self._avg(token_deltas),
            }

            for metric, values in extra_deltas.items():
                if values:
                    row[f"avg_{metric}_delta"] = self._avg(values)

            table.append(row)

        return table
