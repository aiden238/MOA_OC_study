# MOA Orchestration Lab

단일 LLM 호출, Multi-Agent Orchestration, RAG, MCP 경로를 비교하는 실험 저장소다.

---

## 현재 기준

- 기본 프로바이더: `OpenAI`
- 기본 모델: `.env`의 `DEFAULT_MODEL`
- 기본 임베딩: `text-embedding-3-small`
- 선택 확장: `Gemini`, `Grok(xAI)`
- 실행 기준 문서: `README.md`, `AGENTS.md`, `refs/tech_stack.md`

주의:

- 2026-04-20에 시도했던 OpenRouter + Gemma 기준은 철회됐다.
- 과거 문서에 남아 있는 OpenRouter 관련 표기는 현재 기준이 아니다.

---

## 빠른 시작

### 1. 환경 준비

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy env.example .env
```

### 2. `.env` 설정

최소 설정:

```text
LLM_API_PROVIDER=openai
OPENAI_API_KEY=
DEFAULT_MODEL=gpt-4o-mini
EMBEDDING_API_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

혼합 프로바이더 예시:

```text
DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_ANALYTICAL_MODEL=gemini-2.5-flash

DRAFT_CREATIVE_MODEL_PROVIDER=xai
DRAFT_CREATIVE_MODEL=grok-4

CRITIC_MODEL_PROVIDER=openai
CRITIC_MODEL=gpt-4o-mini
```

---

## 실행

### Baseline

```bash
python scripts/run_single.py --benchmark v1.json
```

### MOA

```bash
python scripts/run_moa.py --benchmark v1.json
```

### Full Pipeline

```bash
python scripts/run_full.py --benchmark v1.json
```

### RAG 실주행

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
```

### MCP 실주행

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --evaluate --output-tag mcp
```

### Plain MOA 비교

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --force-path moa --evaluate --output-tag rag_plain
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --force-path moa --evaluate --output-tag mcp_plain
```

### 결과 비교

```bash
python scripts/compare_runs.py --dir data/outputs --format table
```

---

## 벤치마크

- `data/benchmarks/v1.json`: baseline 12건
- `data/benchmarks/v1_rag_mcp.json`: RAG/MCP smoke validation

---

## 주요 디렉토리

```text
app/
  agents/
  core/
  eval/
  mcp_client/
  orchestrator/
  prompts/
  rag/
  schemas/
scripts/
data/
docs/
refs/
```

---

## 문서 해석 규칙

- 현재 기준은 `AGENTS.md -> refs/tech_stack.md -> 현재 주차 문서` 순서로 읽는다.
- OpenRouter 중심 문구는 historical snapshot 또는 철회된 시도로 본다.
- `Planner`는 현재 코드에서 독립 모듈이라기보다 planning stage 개념으로 읽는다.

---

## 변경 기록

### 2026-04-20

- 기본 런타임을 OpenAI로 복구했다.
- Gemini와 Grok를 agent-level override로 동시에 사용할 수 있게 README 예시를 바꿨다.
- OpenRouter + Gemma 기준 예시를 제거했다.
