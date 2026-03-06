"""JSON trace 로거 — 모든 LLM 호출을 run 단위 JSON 파일로 기록."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import TRACE_DIR


def generate_run_id() -> str:
    return uuid.uuid4().hex[:12]


class TraceLogger:
    """run_id 단위로 LLM 호출 기록을 수집하고 JSON 파일로 저장."""

    def __init__(self, run_id: str | None = None, trace_dir: Path | None = None):
        self.run_id = run_id or generate_run_id()
        self.trace_dir = trace_dir or TRACE_DIR
        self.records: list[dict[str, Any]] = []

    def log(
        self,
        *,
        agent_name: str,
        model: str,
        input_prompt: str,
        output_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cost_estimate: float = 0.0,
        path: str = "single",
    ) -> dict[str, Any]:
        record = {
            "run_id": self.run_id,
            "agent_name": agent_name,
            "model": model,
            "input_prompt": input_prompt,
            "output_text": output_text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "cost_estimate": round(cost_estimate, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
        }
        self.records.append(record)
        return record

    def save(self) -> Path:
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.trace_dir / f"{self.run_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                {"run_id": self.run_id, "records": self.records},
                f,
                ensure_ascii=False,
                indent=2,
            )
        return file_path

    def __len__(self) -> int:
        return len(self.records)
