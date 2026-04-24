"""Tests for the run_full CLI wrappers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger
from app.orchestrator.router import RoutingDecision
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest
from scripts.run_full import run_moa_path, run_pipeline, run_single_path, save_full_output


def _mock_output(name: str, content: str = "mock") -> AgentOutput:
    return AgentOutput(
        agent_name=name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
        cost_estimate=0.001,
    )


class TestRunFullWrappers:
    @pytest.mark.asyncio
    async def test_run_single_path_delegates_to_service(self):
        expected = ("single result", [_mock_output("single_baseline", "single result")])

        with patch("scripts.run_full.run_single_task", new=AsyncMock(return_value=expected)) as mock_run:
            task = TaskRequest(prompt="simple summary", task_type="summarize")
            logger = TraceLogger(run_id="test-single")
            tracker = CostTracker()

            result = await run_single_path(task, logger, tracker)

        assert result == expected
        mock_run.assert_awaited_once_with(task, logger, tracker)

    @pytest.mark.asyncio
    async def test_run_moa_path_delegates_routing_to_service(self):
        routing = RoutingDecision(
            selected_path="moa",
            reason="route hint",
            confidence=0.9,
            requires_rag=True,
            rag_query_hint="test query",
        )
        expected = ("moa result", [_mock_output("synthesizer", "moa result")])

        with patch("scripts.run_full.run_moa_task", new=AsyncMock(return_value=expected)) as mock_run:
            task = TaskRequest(prompt="document grounded answer", task_type="explain")
            logger = TraceLogger(run_id="test-moa")
            tracker = CostTracker()

            result = await run_moa_path(task, logger, tracker, routing=routing)

        assert result == expected
        mock_run.assert_awaited_once_with(task, logger, tracker, routing=routing)

    def test_save_full_output_persists_case_result(self, tmp_path: Path):
        result = {
            "case_id": "test-001",
            "task_type": "summarize",
            "prompt": "Prompt",
            "output": "Result",
            "path": "single",
            "routing_reason": "test",
            "routing_confidence": 0.9,
            "agent_count": 1,
            "agents": ["single_baseline"],
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "latency_ms": 100.0,
            "cost_estimate": 0.001,
        }

        path = save_full_output(result, output_dir=tmp_path, output_tag="demo tag")

        assert path.exists()
        assert path.name == "full_test-001__demo-tag.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["case_id"] == "test-001"
        assert payload["output"] == "Result"
        assert payload["evaluation"] == {}
        assert payload["context_metadata"] == {}

    @pytest.mark.asyncio
    async def test_run_pipeline_delegates_to_benchmark_service(self):
        cases = [{"id": "sum-001", "prompt": "Summarize", "type": "summarize"}]
        expected = [{"case_id": "sum-001", "path": "single"}]
        output_dir = Path(".")

        with patch(
            "scripts.run_full.run_benchmark_pipeline",
            new=AsyncMock(return_value=expected),
        ) as mock_run:
            result = await run_pipeline(
                cases,
                case_id="sum-001",
                force_path="single",
                cost_report=True,
                evaluate=True,
                output_dir=output_dir,
                output_tag="week10",
            )

        assert result == expected
        mock_run.assert_awaited_once_with(
            cases,
            case_id="sum-001",
            force_path="single",
            cost_report=True,
            evaluate=True,
            output_dir=output_dir,
            output_tag="week10",
        )

    @pytest.mark.asyncio
    async def test_run_pipeline_returns_empty_list_on_value_error(self):
        with patch(
            "scripts.run_full.run_benchmark_pipeline",
            new=AsyncMock(side_effect=ValueError("missing case")),
        ):
            result = await run_pipeline([])

        assert result == []
