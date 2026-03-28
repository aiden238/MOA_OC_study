# 02. Architecture

## 실행 경로

### Path A: Single

```text
Input -> Single LLM -> Output + Trace
```

### Path B: MOA

```text
Input
  -> Draft x3
  -> Critic
  -> Synthesizer
  -> Judge
  -> (Rewrite)
  -> Output + Trace
```

### Path C: Full

```text
Input
  -> Router
  -> Planning Stage
  -> [RAG Retrieval]
  -> [MCP Tool Call]
  -> MOA Pipeline
  -> Output + Trace
```

---

## 구현 해석

- Router는 `selected_path`, `requires_rag`, `requires_mcp`와 enrichment hint를 반환한다.
- Executor는 Router 결정을 받아 RAG/MCP context를 prompt enrichment로 주입한다.
- 문서의 `Planner`는 현재 코드에서 별도 필수 모듈이 아니라 planning stage 개념이다.

---

## 모델 / 프로바이더 기준

- 기본 provider는 `OpenAI`다.
- 실제 기본 모델은 `.env`의 `DEFAULT_MODEL`이다.
- Gemini와 Grok는 에이전트별 env override로 선택 사용한다.
- BaseAgent는 agent name을 기준으로 provider/model override를 읽는다.
- 기본 임베딩은 OpenAI `text-embedding-3-small`이다.

예:

```text
DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_ANALYTICAL_MODEL=gemini-2.5-flash

DRAFT_CREATIVE_MODEL_PROVIDER=xai
DRAFT_CREATIVE_MODEL=grok-4
```

---

## 주요 모듈

| 모듈 | 역할 | 위치 |
|------|------|------|
| `core` | config, logger, timer, cost tracking | `app/core/` |
| `schemas` | Pydantic 입출력 모델 | `app/schemas/` |
| `agents` | LLM 호출 단위 | `app/agents/` |
| `orchestrator` | Router, Executor, Synthesizer, retry policy | `app/orchestrator/` |
| `eval` | rubric, comparator, metrics | `app/eval/` |
| `rag` | chunking, embedding, retrieval | `app/rag/` |
| `mcp_client` | MCP session and tool wrapper | `app/mcp_client/` |

---

## 변경 기록

### 2026-04-20

- OpenAI 기본, Gemini/Grok 선택 확장 기준으로 런타임 설명을 갱신했다.
- OpenRouter 기반 설명을 철회했다.
