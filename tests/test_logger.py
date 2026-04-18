"""TraceLogger + config + timer 단위 테스트."""

import json
import time
from pathlib import Path

from app.core.config import DEFAULT_MODEL, TRACE_DIR
from app.core.logger import TraceLogger, generate_run_id
from app.core.timer import measure_time


class TestConfig:
    def test_default_model_has_value(self):
        assert DEFAULT_MODEL, "DEFAULT_MODEL은 비어 있으면 안 됨"

    def test_trace_dir_is_path(self):
        assert isinstance(TRACE_DIR, Path)


class TestTraceLogger:
    def test_generate_run_id_unique(self):
        ids = {generate_run_id() for _ in range(100)}
        assert len(ids) == 100

    def test_log_creates_record(self):
        logger = TraceLogger(run_id="test-run-001")
        record = logger.log(
            agent_name="test_agent",
            model="gpt-4o-mini",
            input_prompt="Hello",
            output_text="World",
            prompt_tokens=5,
            completion_tokens=3,
            latency_ms=123.456,
            cost_estimate=0.0001,
            path="single",
        )
        assert record["run_id"] == "test-run-001"
        assert record["agent_name"] == "test_agent"
        assert record["latency_ms"] == 123.46
        assert len(logger) == 1

    def test_log_multiple_records(self):
        logger = TraceLogger()
        for i in range(3):
            logger.log(
                agent_name=f"agent_{i}",
                model="gpt-4o-mini",
                input_prompt=f"prompt_{i}",
                output_text=f"output_{i}",
                prompt_tokens=10,
                completion_tokens=10,
                latency_ms=100.0,
            )
        assert len(logger) == 3

    def test_save_creates_json_file(self, tmp_path: Path):
        trace_dir = tmp_path / "traces"
        logger = TraceLogger(run_id="save-test", trace_dir=trace_dir)
        logger.log(
            agent_name="test_agent",
            model="gpt-4o-mini",
            input_prompt="test input",
            output_text="test output",
            prompt_tokens=5,
            completion_tokens=5,
            latency_ms=50.0,
        )
        saved_path = logger.save()

        assert saved_path.exists()
        assert saved_path.name == "save-test.json"

        with open(saved_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["run_id"] == "save-test"
        assert len(data["records"]) == 1
        assert data["records"][0]["agent_name"] == "test_agent"
        assert "timestamp" in data["records"][0]

    def test_save_creates_directory_if_missing(self, tmp_path: Path):
        nested_dir = tmp_path / "a" / "b" / "c"
        logger = TraceLogger(run_id="nested-test", trace_dir=nested_dir)
        logger.log(
            agent_name="x",
            model="m",
            input_prompt="p",
            output_text="o",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1.0,
        )
        saved_path = logger.save()
        assert saved_path.exists()

    def test_record_fields_match_spec(self, tmp_path: Path):
        logger = TraceLogger(run_id="field-test", trace_dir=tmp_path)
        logger.log(
            agent_name="agent",
            model="gpt-4o-mini",
            input_prompt="prompt",
            output_text="output",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=200.5,
            cost_estimate=0.001,
            path="moa",
        )
        saved_path = logger.save()

        with open(saved_path, encoding="utf-8") as f:
            data = json.load(f)

        record = data["records"][0]
        required_fields = {
            "run_id", "agent_name", "model", "input_prompt", "output_text",
            "prompt_tokens", "completion_tokens", "latency_ms",
            "cost_estimate", "timestamp", "path", "operation_type", "metadata",
        }
        assert required_fields.issubset(record.keys())

    def test_log_supports_operation_type_and_metadata(self):
        logger = TraceLogger(run_id="op-test")
        record = logger.log(
            agent_name="retriever",
            model="gpt-4o-mini",
            input_prompt="query",
            output_text="context",
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=5.0,
            cost_estimate=0.0,
            path="moa+rag",
            operation_type="rag",
            metadata={"stage": "retrieval", "hits": 3},
        )
        assert record["operation_type"] == "rag"
        assert record["metadata"]["stage"] == "retrieval"


class TestTimer:
    def test_sync_measure_time(self):
        @measure_time
        def slow_fn():
            time.sleep(0.01)
            return 42

        result, latency_ms = slow_fn()
        assert result == 42
        assert latency_ms >= 10  # 최소 10ms

    def test_async_measure_time(self):
        import asyncio

        @measure_time
        async def async_fn():
            await asyncio.sleep(0.01)
            return "done"

        result, latency_ms = asyncio.run(async_fn())
        assert result == "done"
        assert latency_ms >= 10
