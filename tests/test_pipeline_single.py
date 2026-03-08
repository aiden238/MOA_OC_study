"""run_single.py 파이프라인 통합 테스트 — mock 기반 (API 키 불필요)."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from scripts.run_single import (
    build_run_summary,
    case_to_task,
    load_benchmark,
    run_pipeline,
    run_single_case,
    save_case_output,
)
from app.core.logger import TraceLogger
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary


@pytest.fixture
def sample_cases():
    return [
        {
            "id": "test-001",
            "type": "summarize",
            "prompt": "테스트 프롬프트입니다.",
            "constraints": {"max_sentences": 3},
            "difficulty": "low",
            "expected_moa_advantage": "minimal",
        },
        {
            "id": "test-002",
            "type": "explain",
            "prompt": "테스트 설명 프롬프트입니다.",
            "constraints": {"audience": "middle_school"},
            "difficulty": "medium",
            "expected_moa_advantage": "planner_helps",
        },
    ]


@pytest.fixture
def benchmark_file(tmp_path, sample_cases):
    path = tmp_path / "v1.json"
    data = {"version": "v1", "cases": sample_cases}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


@pytest.fixture
def mock_openai_response():
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Mock LLM output"}}
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "total_tokens": 80,
        },
    }


class TestLoadBenchmark:
    def test_load_valid_file(self, benchmark_file):
        cases = load_benchmark(benchmark_file)
        assert len(cases) == 2
        assert cases[0]["id"] == "test-001"

    def test_load_real_v1(self):
        """실제 v1.json이 12건인지 확인."""
        cases = load_benchmark()
        assert len(cases) == 12
        types = {c["type"] for c in cases}
        assert types == {"summarize", "explain", "ideate", "critique_rewrite"}


class TestCaseToTask:
    def test_conversion(self, sample_cases):
        task = case_to_task(sample_cases[0])
        assert isinstance(task, TaskRequest)
        assert task.task_id == "test-001"
        assert task.task_type == "summarize"
        assert task.prompt == "테스트 프롬프트입니다."
        assert task.constraints == {"max_sentences": 3}

    def test_metadata_mapping(self, sample_cases):
        task = case_to_task(sample_cases[1])
        assert task.metadata["difficulty"] == "medium"
        assert task.metadata["expected_moa_advantage"] == "planner_helps"


class TestSaveCaseOutput:
    def test_save_creates_file(self, tmp_path):
        result = {
            "case_id": "test-001",
            "task_type": "summarize",
            "prompt": "test",
            "output": "result",
            "model": "gpt-4o-mini",
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "latency_ms": 100.0,
            "cost_estimate": 0.001,
        }
        path = save_case_output(result, tmp_path)
        assert path.exists()
        assert path.name == "single_test-001.json"

        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["case_id"] == "test-001"
        assert saved["output"] == "result"


class TestBuildRunSummary:
    def test_summary_aggregation(self):
        logger = TraceLogger(run_id="summary-test")
        logger.log(
            agent_name="single_baseline",
            model="gpt-4o-mini",
            input_prompt="p1",
            output_text="o1",
            prompt_tokens=50,
            completion_tokens=30,
            latency_ms=200.0,
            cost_estimate=0.001,
            path="single",
        )
        logger.log(
            agent_name="single_baseline",
            model="gpt-4o-mini",
            input_prompt="p2",
            output_text="o2",
            prompt_tokens=40,
            completion_tokens=20,
            latency_ms=150.0,
            cost_estimate=0.0005,
            path="single",
        )

        results = [
            {"prompt_tokens": 50, "completion_tokens": 30, "latency_ms": 200.0, "cost_estimate": 0.001, "output": "o1"},
            {"prompt_tokens": 40, "completion_tokens": 20, "latency_ms": 150.0, "cost_estimate": 0.0005, "output": "o2"},
        ]

        summary = build_run_summary("summary-test", results, logger)
        assert isinstance(summary, RunSummary)
        assert summary.run_id == "summary-test"
        assert summary.total_tokens == 140  # (50+30) + (40+20)
        assert summary.total_cost == 0.0015
        assert summary.total_latency_ms == 350.0
        assert summary.agent_count == 1
        assert len(summary.traces) == 2
        assert summary.final_output == "o2"


class TestRunSingleCase:
    @pytest.mark.asyncio
    async def test_run_with_mock(self, mock_openai_response):
        task = TaskRequest(
            task_id="mock-001",
            prompt="Test prompt",
            task_type="summarize",
        )
        logger = TraceLogger(run_id="mock-run")

        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_response
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await run_single_case(task, logger)

        assert result["case_id"] == "mock-001"
        assert result["output"] == "Mock LLM output"
        assert result["prompt_tokens"] == 50
        assert result["completion_tokens"] == 30
        assert len(logger) == 1


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_with_mock(self, sample_cases, tmp_path, mock_openai_response):
        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_response
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            summaries = await run_pipeline(
                sample_cases, output_dir=tmp_path
            )

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.path == "single"
        assert len(summary.traces) == 2

        # output 파일 확인
        out_files = list(tmp_path.glob("single_*.json"))
        assert len(out_files) == 2

    @pytest.mark.asyncio
    async def test_pipeline_case_filter(self, sample_cases, tmp_path, mock_openai_response):
        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_response
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            summaries = await run_pipeline(
                sample_cases, case_id="test-001", output_dir=tmp_path
            )

        assert len(summaries[0].traces) == 1

    @pytest.mark.asyncio
    async def test_pipeline_invalid_case_id(self, sample_cases, tmp_path):
        summaries = await run_pipeline(
            sample_cases, case_id="nonexistent", output_dir=tmp_path
        )
        assert summaries == []
