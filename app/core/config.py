"""프로젝트 전역 설정 — .env 파일 로딩 및 환경변수 관리."""

import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 기준으로 .env 로딩
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"환경변수 '{key}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return value or ""


# LLM API
OPENAI_API_KEY: str = _get_env("OPENAI_API_KEY")
ANTHROPIC_API_KEY: str = _get_env("ANTHROPIC_API_KEY")

# 모델 설정
DEFAULT_MODEL: str = _get_env("DEFAULT_MODEL", "gpt-4o-mini")
DEFAULT_TEMPERATURE: float = float(_get_env("DEFAULT_TEMPERATURE", "0.7"))
MAX_TOKENS: int = int(_get_env("MAX_TOKENS", "1024"))
MAX_RETRIES: int = int(_get_env("MAX_RETRIES", "3"))

# 경로 설정
TRACE_DIR: Path = PROJECT_ROOT / _get_env("TRACE_DIR", "data/traces")
OUTPUT_DIR: Path = PROJECT_ROOT / _get_env("OUTPUT_DIR", "data/outputs")
BENCHMARK_DIR: Path = PROJECT_ROOT / _get_env("BENCHMARK_DIR", "data/benchmarks")
