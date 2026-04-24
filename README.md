# MOA Orchestration Lab

단일 LLM 호출, Multi-Agent Orchestration, RAG, MCP를 단계적으로 비교 검증하는 실험 프로젝트입니다.

핵심 질문:
`멀티 에이전트 오케스트레이션이 단일 호출보다 실제로 나은가?`

---

## 현재 기준

- 기본 LLM provider: `OpenAI`
- 기본 모델 source of truth: `.env`의 `DEFAULT_MODEL`
- 기본 embedding: `text-embedding-3-small`
- 선택 확장 provider: `Gemini`, `Z.AI`
- 레거시 alias: `xAI`, `Grok`, `Zhipu`, `GLM` 입력은 내부 정규화에서 처리
- CLI 비교 실험은 유지하고, Week 10부터 `FastAPI + 정적 웹 UI`를 추가 지원

문서 우선순위:
`AGENTS.md -> refs/tech_stack.md -> 현재 주차 문서`

---

## 빠른 시작

### 1. 환경 준비

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy env.example .env
```

### 2. 최소 `.env`

```text
LLM_API_PROVIDER=openai
DEFAULT_MODEL=gpt-4o-mini
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1

EMBEDDING_API_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=
EMBEDDING_API_BASE_URL=https://api.openai.com/v1
```

### 3. 선택 provider 예시

```text
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai

ZAI_API_KEY=
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
```

### 4. 에이전트별 override 예시

```text
DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_ANALYTICAL_MODEL=gemini-2.5-flash

DRAFT_CREATIVE_MODEL_PROVIDER=zai
DRAFT_CREATIVE_MODEL=glm-4.7-flash

CRITIC_MODEL_PROVIDER=openai
CRITIC_MODEL=gpt-4o-mini
```

---

## CLI 실행

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

### RAG 검증

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
```

### MCP 검증

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

## Web UI

Week 10부터 웹 챗봇 UI를 지원합니다.

실행:

```bash
uvicorn app.web.server:app --reload
```

접속:

- `/`
- `/health`
- `/api/models`
- `/api/sessions`
- `/api/chat`

지원 기능:

- 세션형 대화
- `auto / single / moa` 경로 선택
- 글로벌 모델 선택
- agent별 override
- preset 기반 다중 모델 조합
- trace path / output path / routing metadata 반환

현재 웹 레이어는 메모리 세션 저장소를 사용합니다. 영속 세션 저장은 후속 확장 범위입니다.

---

## 벤치마크

- `data/benchmarks/v1.json`: baseline 12건
- `data/benchmarks/v1_rag_mcp.json`: RAG/MCP smoke 및 validation

---

## 주요 구조

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
  services/
  web/
scripts/
data/
docs/
refs/
```

---

## 변경 기록

### 2026-04-25

- Week 10 C10-1 ~ C10-4 구현을 반영했다.
- `app/services/chat_service.py` 기반 공용 chat runtime을 추가했다.
- `FastAPI` 웹 서버와 정적 챗 UI를 추가했다.
- 글로벌 모델 선택, agent override, preset 기반 다중 모델 선택을 추가했다.
- `scripts/run_full.py`를 service-layer wrapper 구조로 정리했다.
- 신규 테스트를 포함해 전체 `pytest` 통과 상태를 확인했다.

### 2026-04-20

- OpenRouter + Gemma 기준을 철회하고 OpenAI 기본 런타임으로 복구했다.
- Gemini와 Z.AI를 선택 확장 provider로 재정리했다.
