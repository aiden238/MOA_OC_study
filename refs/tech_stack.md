# 기술 스택 제약

## 라이선스 원칙

> **MIT 또는 Apache 2.0 라이선스만 사용한다. GPL 계열은 사용하지 않는다.**

## 허용 의존성

| 패키지 | 용도 | 라이선스 | 도입 시점 |
|--------|------|----------|-----------|
| `pydantic` (v2) | 스키마 유효성 검증 | MIT | 1주차~ |
| `httpx` | LLM API 호출 (async) | BSD-3 | 1주차~ |
| `python-dotenv` | 환경변수 관리 | BSD-3 | 1주차~ |
| `pytest` | 테스트 프레임워크 | MIT | 1주차~ |
| `pytest-asyncio` | async 테스트 | MIT | 4주차~ |
| `tenacity` | 재시도 로직 | Apache 2.0 | 3주차~ |
| `tiktoken` | 토큰 수 추정 | MIT | 3주차~ |
| `chromadb` | 벡터 DB (RAG) | Apache 2.0 | 6주차 |
| `mcp` (Python SDK) | MCP 서버 연동 | MIT | 6주차 |

## 사용 금지

| 패키지 | 이유 |
|--------|------|
| LangChain / LangGraph | 내부 동작을 이해하지 못한 채 의존 → 학습 목적 상실 |
| CrewAI / AutoGen | 같은 이유 |
| Streamlit / Gradio | 6주 내 UI 불필요 |
| SQLAlchemy | JSON/SQLite 직접 사용으로 충분 |

## LLM 모델 정책

- **1~5주차:** 단일 모델 고정 (예: `gpt-4o-mini` 또는 `claude-3-5-haiku`)
  - 모델 차이 vs 구조 차이를 분리하기 위해
- **6주차:** 멀티 모델 실험 도입 (Router가 모델도 선택)
