"""JSON trace 로거 — 모든 LLM 호출을 run 단위 JSON 파일로 기록.

각 실행(run)마다 고유 run_id를 부여하고, 호출되는 모든 에이전트의
입출력·토큰·비용·지연시간을 records 리스트에 수집한 뒤
data/traces/{run_id}.json 으로 저장한다.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import TRACE_DIR


def generate_run_id() -> str:
    """UUID 기반 12자리 고유 실행 ID 생성."""
    return uuid.uuid4().hex[:12]


class TraceLogger:
    """run_id 단위로 LLM 호출 기록을 수집하고 JSON 파일로 저장."""

    def __init__(self, run_id: str | None = None, trace_dir: Path | None = None):
        self.run_id = run_id or generate_run_id()    # 실행 식별자
        self.trace_dir = trace_dir or TRACE_DIR       # 저장 디렉토리
        self.records: list[dict[str, Any]] = []       # 호출 기록 리스트

    def log(
        self,
        *,
        agent_name: str,       # 호출된 에이전트 이름
        model: str,            # 사용된 LLM 모델
        input_prompt: str,     # 입력 프롬프트
        output_text: str,      # LLM 응답 텍스트
        prompt_tokens: int,    # 입력 토큰 수
        completion_tokens: int,  # 출력 토큰 수
        latency_ms: float,     # 응답 지연 시간 (ms)
        cost_estimate: float = 0.0,  # 추정 비용 (USD)
        path: str = "single",  # 실행 경로 (single/moa/full)
    ) -> dict[str, Any]:
        """에이전트 호출 1건을 기록에 추가하고 해당 기록을 반환."""
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
        """수집된 기록을 JSON 파일로 저장. 디렉토리가 없으면 자동 생성."""
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
