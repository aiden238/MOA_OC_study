"""C7-1 compare_runs / comparator 테스트."""

import json

from app.eval.comparator import Comparator
from app.schemas.trace import CaseResult
from scripts.compare_runs import load_case_results


class TestComparator:
    def test_compare_groups(self):
        comparator = Comparator()
        runs = {
            "single": [
                CaseResult(
                    case_id="case-001",
                    task_type="explain",
                    prompt="prompt",
                    output="single",
                    path="single",
                    prompt_tokens=50,
                    completion_tokens=20,
                    latency_ms=100.0,
                    cost_estimate=0.001,
                    evaluation={"avg_score": 3.5},
                )
            ],
            "moa": [
                CaseResult(
                    case_id="case-001",
                    task_type="explain",
                    prompt="prompt",
                    output="moa",
                    path="moa",
                    prompt_tokens=80,
                    completion_tokens=40,
                    latency_ms=180.0,
                    cost_estimate=0.003,
                    evaluation={"avg_score": 4.2},
                )
            ],
            "moa+rag": [
                CaseResult(
                    case_id="case-001",
                    task_type="explain",
                    prompt="prompt",
                    output="moa+rag",
                    path="moa+rag",
                    prompt_tokens=90,
                    completion_tokens=45,
                    latency_ms=200.0,
                    cost_estimate=0.0035,
                    evaluation={"avg_score": 4.4, "groundedness": 5},
                )
            ],
        }

        table = comparator.compare(runs)
        groups = {row["group"]: row for row in table}

        assert groups["baseline"]["left_path"] == "single"
        assert groups["baseline"]["right_path"] == "moa"
        assert groups["baseline"]["avg_score_delta"] == 0.7
        assert groups["rag"]["left_path"] == "moa"
        assert groups["rag"]["right_path"] == "moa+rag"


class TestLoadCaseResults:
    def test_load_case_results_infers_path(self, tmp_path):
        single_path = tmp_path / "single_case-001.json"
        single_payload = {
            "case_id": "case-001",
            "task_type": "summarize",
            "prompt": "prompt",
            "output": "result",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "latency_ms": 20.0,
            "cost_estimate": 0.0001,
        }
        single_path.write_text(json.dumps(single_payload, ensure_ascii=False), encoding="utf-8")

        runs = load_case_results(tmp_path)
        assert "single" in runs
        assert runs["single"][0].case_id == "case-001"
