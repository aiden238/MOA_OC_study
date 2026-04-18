"""Pydantic 스키마 validation 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AgentInput,
    AgentOutput,
    CaseResult,
    RunSummary,
    TaskPlan,
    TaskRequest,
    TraceRecord,
)


class TestTaskRequest:
    def test_minimal_creation(self):
        req = TaskRequest(prompt="test prompt")
        assert req.prompt == "test prompt"
        assert req.task_type == "explain"
        assert len(req.task_id) == 12

    def test_full_creation(self):
        req = TaskRequest(
            prompt="summarize this",
            task_type="summarize",
            constraints={"max_length": 100},
            metadata={"source": "benchmark"},
        )
        assert req.task_type == "summarize"
        assert req.constraints["max_length"] == 100

    def test_invalid_task_type_raises(self):
        with pytest.raises(ValidationError):
            TaskRequest(prompt="test", task_type="invalid_type")

    def test_missing_prompt_raises(self):
        with pytest.raises(ValidationError):
            TaskRequest()


class TestTaskPlan:
    def test_creation_with_request(self):
        req = TaskRequest(prompt="test")
        plan = TaskPlan(original_request=req)
        assert plan.selected_path == "single"
        assert plan.requires_rag is False

    def test_moa_path(self):
        req = TaskRequest(prompt="complex task")
        plan = TaskPlan(
            original_request=req,
            subtasks=["step1", "step2"],
            selected_path="moa",
        )
        assert plan.selected_path == "moa"
        assert len(plan.subtasks) == 2


class TestAgentInput:
    def test_minimal_creation(self):
        inp = AgentInput(
            agent_name="test",
            system_prompt="You are helpful.",
            user_message="Hello",
        )
        assert inp.temperature == 0.7
        assert inp.max_tokens == 1024

    def test_missing_fields_raises(self):
        with pytest.raises(ValidationError):
            AgentInput(agent_name="test")


class TestAgentOutput:
    def test_full_creation(self):
        out = AgentOutput(
            agent_name="draft",
            content="result text",
            model="gpt-4o-mini",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=150.5,
        )
        assert out.cost_estimate == 0.0
        assert out.raw_response == {}

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            AgentOutput(agent_name="draft", content="text")


class TestTraceRecord:
    def test_full_creation(self):
        rec = TraceRecord(
            run_id="abc123",
            agent_name="critic",
            model="gpt-4o-mini",
            input_prompt="analyze this",
            output_text="analysis result",
            prompt_tokens=15,
            completion_tokens=25,
            latency_ms=200.0,
            cost_estimate=0.001,
            timestamp="2026-04-18T00:00:00Z",
            path="moa",
        )
        assert rec.path == "moa"
        assert rec.operation_type == "llm_completion"
        assert rec.metadata == {}

    def test_missing_fields_raises(self):
        with pytest.raises(ValidationError):
            TraceRecord(run_id="abc", agent_name="x")


class TestRunSummary:
    def test_full_creation(self):
        trace = TraceRecord(
            run_id="run1",
            agent_name="draft",
            model="gpt-4o-mini",
            input_prompt="p",
            output_text="o",
            prompt_tokens=5,
            completion_tokens=10,
            latency_ms=100.0,
            cost_estimate=0.0005,
            timestamp="2026-04-18T00:00:00Z",
            path="single",
        )
        summary = RunSummary(
            run_id="run1",
            task_id="task1",
            path="single",
            total_tokens=15,
            total_cost=0.0005,
            total_latency_ms=100.0,
            agent_count=1,
            traces=[trace],
            final_output="final result",
        )
        assert summary.agent_count == 1
        assert len(summary.traces) == 1


class TestCaseResult:
    def test_defaults(self):
        result = CaseResult(
            case_id="case-001",
            task_type="explain",
            prompt="prompt",
            output="output",
        )
        assert result.path == "moa"
        assert result.evaluation == {}
        assert result.evaluation_context == {}
        assert result.context_metadata == {}
