"""프로젝트 전역 설정 — .env 파일 로딩 및 환경변수 관리.

모든 모듈이 공유하는 설정값(API 키, 모델, 경로 등)을
.env 파일에서 읽어와 상수로 노출한다.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트 경로 (이 파일 기준 3단계 상위 = 워크스페이스 루트)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
# .env 파일을 읽어 환경변수로 등록
load_dotenv(PROJECT_ROOT / ".env")


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    """환경변수를 가져오는 헬퍼. required=True일 때 값이 없으면 예외 발생."""
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"환경변수 '{key}'가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return value or ""


# ── LLM API 키 ──
OPENAI_API_KEY: str = _get_env("OPENAI_API_KEY")
ANTHROPIC_API_KEY: str = _get_env("ANTHROPIC_API_KEY")

# ── 모델 기본 설정 ──
DEFAULT_MODEL: str = _get_env("DEFAULT_MODEL", "gpt-4o-mini")       # 사용할 LLM 모델명
DEFAULT_TEMPERATURE: float = float(_get_env("DEFAULT_TEMPERATURE", "0.7"))  # 생성 온도
MAX_TOKENS: int = int(_get_env("MAX_TOKENS", "1024"))                # 최대 생성 토큰 수
MAX_RETRIES: int = int(_get_env("MAX_RETRIES", "3"))                 # API 재시도 횟수

# ── 데이터 저장 경로 ──
TRACE_DIR: Path = PROJECT_ROOT / _get_env("TRACE_DIR", "data/traces")          # 실행 추적 로그 저장
OUTPUT_DIR: Path = PROJECT_ROOT / _get_env("OUTPUT_DIR", "data/outputs")       # 실행 결과 저장
BENCHMARK_DIR: Path = PROJECT_ROOT / _get_env("BENCHMARK_DIR", "data/benchmarks")  # 벤치마크 데이터
