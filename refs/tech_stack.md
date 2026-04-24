# 기술 스택 요약

## 라이선스 원칙

- 새 의존성은 `MIT` 또는 `Apache 2.0`만 허용한다.
- GPL 계열 의존성은 도입하지 않는다.

---

## 사용 의존성

| 패키지 | 용도 | 라이선스 | 도입 시점 |
|--------|------|----------|-----------|
| `pydantic` | 스키마 검증 | MIT | Week 1 |
| `httpx` | LLM API 호출 | BSD-3 | Week 1 |
| `python-dotenv` | 환경 변수 로드 | BSD-3 | Week 1 |
| `pytest` | 테스트 | MIT | Week 1 |
| `pytest-asyncio` | async 테스트 | MIT | Week 4 |
| `tenacity` | retry 로직 | Apache 2.0 | Week 3 |
| `tiktoken` | 토큰 추정 | MIT | Week 3 |
| `chromadb` | 로컬 vector store | Apache 2.0 | Week 6 |
| `mcp` | MCP Python SDK | MIT | Week 6 |
| `fastapi` | 웹 API 서버 | MIT | Week 10 |
| `uvicorn` | ASGI 서버 | BSD-3 | Week 10 |

---

## 사용 금지 또는 비채택

| 도구/패키지 | 이유 |
|------------|------|
| `LangChain`, `LangGraph` | 오케스트레이션 로직을 직접 검증하는 현재 실험 목적과 맞지 않음 |
| `CrewAI`, `AutoGen` | black-box 추상화가 과함 |
| `Streamlit`, `Gradio` | 이번 구현은 `FastAPI + static UI`로 충분하고, CLI 우선 원칙을 유지함 |
| 대형 ORM/agent framework | 현재 범위에서는 직접 구현이 더 단순하고 검증 가능함 |

---

## LLM / Embedding 정책

### 기본 런타임

- 기본 provider는 `OpenAI`
- 기본 모델은 `.env`의 `DEFAULT_MODEL`
- 기본 embedding provider는 `OpenAI`
- 기본 embedding 모델은 `text-embedding-3-small`

### 선택 확장

- `Gemini`, `Z.AI`를 선택 확장 provider로 지원
- 한 run 안에서 agent별 env override 또는 request-level override로 provider를 섞어 쓸 수 있음
- 레거시 alias `xai`, `grok`, `zhipu`, `glm`은 내부 정규화에서 허용

### 기본 env

- `LLM_API_PROVIDER`
- `DEFAULT_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `EMBEDDING_API_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_BASE_URL`

### 선택 provider env

- `GEMINI_API_KEY`
- `GEMINI_BASE_URL`
- `ZAI_API_KEY`
- `ZAI_BASE_URL`
- 레거시 호환 alias: `XAI_API_KEY`, `XAI_BASE_URL`, `ZHIPU_API_KEY`, `ZHIPU_BASE_URL`

### 에이전트별 override env

- `SINGLE_*`
- `ROUTER_*`
- `DRAFT_ANALYTICAL_*`
- `DRAFT_CREATIVE_*`
- `DRAFT_STRUCTURED_*`
- `CRITIC_*`
- `SYNTH_*` 또는 `SYNTHESIZER_*`
- `JUDGE_*`
- `REWRITE_*`
- `EVAL_*` 또는 `RUBRIC_JUDGE_*`

예시:

```text
LLM_API_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini

DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_ANALYTICAL_MODEL=gemini-2.5-flash

DRAFT_CREATIVE_MODEL_PROVIDER=zai
DRAFT_CREATIVE_MODEL=glm-4.7-flash
```

---

## Week 10 웹 런타임

추가된 구성:

- `app/services/chat_service.py`
- `app/core/model_registry.py`
- `app/web/server.py`
- `app/web/session_store.py`
- `app/web/static/*`

지원 기능:

- 세션형 챗 요청/응답
- `auto`, `single`, `moa` 경로 선택
- request-level 글로벌 모델 선택
- agent override
- preset 기반 mixed-provider 조합
- trace/output metadata에 선택 모델 기록

현재 세션 저장은 메모리 기반이다.

---

## CLI / 벤치마크 기준

- `scripts/run_single.py`, `scripts/run_moa.py`, `scripts/run_full.py`는 `--benchmark`를 사용한다.
- `scripts/run_full.py`는 `--output-tag`를 지원한다.
- `data/benchmarks/v1.json`은 baseline이다.
- `data/benchmarks/v1_rag_mcp.json`은 RAG/MCP validation이다.

---

## 변경 기록

### 2026-04-25

- Week 10 웹 UI 의존성 `fastapi`, `uvicorn`을 추가했다.
- 공용 chat runtime과 model registry를 문서 기준에 반영했다.
- Z.AI 중심 표기를 유지하되 xAI/Grok/Zhipu alias 호환을 명시했다.

### 2026-04-20

- OpenAI 기본 런타임으로 복구했다.
- OpenRouter + Gemma 표기를 현재 기준에서 제외했다.
