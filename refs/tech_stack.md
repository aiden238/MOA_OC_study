# 기술 스택 제약

## 라이선스 원칙

MIT 또는 Apache 2.0만 허용한다. GPL 계열은 사용하지 않는다.

---

## 허용 의존성

| 패키지 | 용도 | 라이선스 | 도입 시점 |
|--------|------|----------|-----------|
| `pydantic` | 스키마와 검증 | MIT | 1주차 |
| `httpx` | API 호출 | BSD-3 | 1주차 |
| `python-dotenv` | 환경 변수 로드 | BSD-3 | 1주차 |
| `pytest` | 테스트 | MIT | 1주차 |
| `pytest-asyncio` | async 테스트 | MIT | 4주차 |
| `tenacity` | 재시도 로직 | Apache 2.0 | 3주차 |
| `tiktoken` | 토큰 추정 | MIT | 3주차 |
| `chromadb` | 로컬 persistent vector store | Apache 2.0 | 6주차 |
| `mcp` | MCP Python SDK | MIT | 6주차 |

---

## 사용 금지

| 패키지/도구 | 이유 |
|-------------|------|
| LangChain / LangGraph | 오케스트레이션 로직을 직접 검증하기 어렵다 |
| CrewAI / AutoGen | black-box 추상화가 과하다 |
| Streamlit / Gradio | 현재 산출물은 CLI + JSON 로그가 기준이다 |
| 대형 ORM/에이전트 프레임워크 | 현재 범위에서는 직접 구현으로 충분하다 |

---

## LLM / Embedding 정책

### 기본 정책

- 기본 런타임 provider는 `OpenAI`다.
- 기본 모델은 `.env`의 `DEFAULT_MODEL`이다.
- 기본 임베딩 provider는 `OpenAI`다.
- 기본 임베딩 모델은 `text-embedding-3-small`이다.

### 선택 확장

- `Gemini`와 `Grok(xAI)`는 OpenAI-compatible endpoint로 선택 확장할 수 있다.
- 에이전트별 env override를 통해 같은 run 안에서 provider를 섞을 수 있다.

### provider별 기준 env

기본:

- `LLM_API_PROVIDER`
- `DEFAULT_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `EMBEDDING_API_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_BASE_URL`

선택:

- `GEMINI_API_KEY`
- `GEMINI_BASE_URL`
- `XAI_API_KEY`
- `XAI_BASE_URL`

에이전트별 override:

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

사용 예:

```text
LLM_API_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini

DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_ANALYTICAL_MODEL=gemini-2.5-flash

DRAFT_CREATIVE_MODEL_PROVIDER=xai
DRAFT_CREATIVE_MODEL=grok-4
```

### 문서 해석 규칙

- OpenRouter, Gemma 기준 문구는 현재 정책이 아니다.
- 과거 문서에 남아 있어도 current runtime 해석에 사용하지 않는다.

---

## CLI / 벤치마크 정책

- `run_single.py`, `run_moa.py`, `run_full.py`는 `--benchmark`를 사용한다.
- `run_full.py --output-tag`로 결과 파일을 분리 저장한다.
- `data/benchmarks/v1.json`은 baseline이다.
- `data/benchmarks/v1_rag_mcp.json`은 RAG/MCP validation용이다.

---

## 변경 기록

### 2026-04-20

- OpenAI 기본 정책으로 복구했다.
- Gemini/Grok 혼합 사용을 위한 env 규칙을 추가했다.
- OpenRouter + Gemma 기준 문구를 현재 정책에서 제거했다.
