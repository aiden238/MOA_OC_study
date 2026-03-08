"""평가 모듈 테스트 — rubric 파싱 + metrics 계산."""

import pytest

from app.eval.metrics import compare_metrics, compute_metrics, compute_metrics_from_traces
from app.eval.rubric import (
    RUBRIC_DIMENSIONS,
    build_judge_message,
    parse_judge_response,
)
from app.schemas.trace import RunSummary, TraceRecord


class TestBuildJudgeMessage:
    def test_basic_message(self):
        msg = build_judge_message("요약하세요", "요약 결과입니다")
        assert "[원래 요청]" in msg
        assert "요약하세요" in msg
        assert "[생성된 결과]" in msg
        assert "요약 결과입니다" in msg

    def test_message_with_constraints(self):
        msg = build_judge_message("요약하세요", "결과", {"max_sentences": 3})
        assert "[제약 조건]" in msg
        assert "max_sentences" in msg


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = '{"clarity": 4, "structure": 5, "constraint_following": 3, "usefulness": 4, "reasoning": "잘함"}'
        scores = parse_judge_response(response)
        assert scores["clarity"] == 4
        assert scores["structure"] == 5
        assert scores["constraint_following"] == 3
        assert scores["usefulness"] == 4
        assert scores["reasoning"] == "잘함"
        assert scores["avg_score"] == 4.0

    def test_code_block_json(self):
        response = '```json\n{"clarity": 3, "structure": 3, "constraint_following": 3, "usefulness": 3, "reasoning": "보통"}\n```'
        scores = parse_judge_response(response)
        assert scores["clarity"] == 3
        assert scores["avg_score"] == 3.0

    def test_missing_dimension_raises(self):
        response = '{"clarity": 4, "structure": 5, "usefulness": 4}'
        with pytest.raises(ValueError, match="constraint_following"):
            parse_judge_response(response)

    def test_out_of_range_raises(self):
        response = '{"clarity": 7, "structure": 5, "constraint_following": 3, "usefulness": 4}'
        with pytest.raises(ValueError, match="범위"):
            parse_judge_response(response)

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_judge_response("이것은 JSON이 아닙니다")

    def test_float_scores_converted_to_int(self):
        response = '{"clarity": 4.0, "structure": 5.0, "constraint_following": 3.0, "usefulness": 4.0}'
        scores = parse_judge_response(response)
        assert scores["clarity"] == 4
        assert isinstance(scores["clarity"], int)


class TestComputeMetrics:
    def test_from_summary(self):
        summary = RunSummary(
            run_id="test-run",
            task_id="t1",
            path="single",
            total_tokens=100,
            total_cost=0.001,
            total_latency_ms=500.0,
            agent_count=1,
            traces=[],
            final_output="output",
        )
        metrics = compute_metrics(summary)
        assert metrics["total_tokens"] == 100
        assert metrics["total_cost_estimate"] == 0.001
        assert metrics["total_latency_ms"] == 500.0
        assert metrics["agent_count"] == 1

    def test_from_traces(self):
        traces = [
            TraceRecord(
                run_id="r1", agent_name="a1", model="gpt-4o-mini",
                input_prompt="p", output_text="o",
                prompt_tokens=50, completion_tokens=30,
                latency_ms=200.0, cost_estimate=0.001,
                timestamp="2026-01-01T00:00:00Z", path="single",
            ),
            TraceRecord(
                run_id="r1", agent_name="a1", model="gpt-4o-mini",
                input_prompt="p2", output_text="o2",
                prompt_tokens=40, completion_tokens=20,
                latency_ms=150.0, cost_estimate=0.0005,
                timestamp="2026-01-01T00:00:01Z", path="single",
            ),
        ]
        metrics = compute_metrics_from_traces(traces)
        assert metrics["total_tokens"] == 140
        assert metrics["prompt_tokens"] == 90
        assert metrics["completion_tokens"] == 50
        assert metrics["total_cost_estimate"] == 0.0015
        assert metrics["total_latency_ms"] == 350.0
        assert metrics["agent_count"] == 1  # 같은 에이전트


class TestCompareMetrics:
    def test_comparison(self):
        baseline = {"total_tokens": 100, "total_cost_estimate": 0.001, "total_latency_ms": 500.0}
        experiment = {"total_tokens": 300, "total_cost_estimate": 0.003, "total_latency_ms": 1500.0}
        diff = compare_metrics(baseline, experiment)
        assert diff["token_ratio"] == 3.0
        assert diff["cost_ratio"] == 3.0
        assert diff["latency_ratio"] == 3.0
        assert diff["token_diff"] == 200
        assert diff["cost_diff"] == 0.002
        assert diff["latency_diff"] == 1000.0

    def test_zero_baseline(self):
        baseline = {"total_tokens": 0, "total_cost_estimate": 0, "total_latency_ms": 0}
        experiment = {"total_tokens": 100, "total_cost_estimate": 0.001, "total_latency_ms": 500.0}
        diff = compare_metrics(baseline, experiment)
        assert diff["token_ratio"] is None
        assert diff["cost_ratio"] is None
