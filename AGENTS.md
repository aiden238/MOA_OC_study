# MOA Orchestration Lab - AI Agent Instructions

> 항상 이 파일을 첨부한다.  
> 주차 작업 시 현재 주차의 `weekN_plan.md`와 `weekN_implement.md`를 함께 본다.

---

## 프로젝트 정체성

한 줄 정의: 단일 LLM 호출, Multi-Agent Orchestration, RAG, MCP를 단계적으로 비교 검증하는 실험 프로젝트

핵심 질문: "멀티 에이전트 오케스트레이션이 단일 호출보다 실제로 나은가?"

최종 아키텍처: `Input -> Router -> Planning Stage -> [RAG/MCP] -> Draft x3 -> Critic -> Judge -> (Rewrite) -> Synthesizer -> Output + Trace`

---

## 가드레일

| # | 제약 조건 |
|---|----------|
| 1 | LangChain / CrewAI / AutoGen 사용 금지 |
| 2 | 1~5주차 동안 모델 단일화 유지 |
| 3 | UI보다 CLI + JSON 로그를 우선한다 |
| 4 | 범용 벤치마크를 우선하고 도메인 데이터는 지양한다 |
| 5 | RAG와 MCP는 6주차 이후 범위에서만 도입한다 |
| 6 | 주간 커밋 횟수 제한 없음 |
| 7 | 새 의존성은 MIT 또는 Apache 2.0만 허용한다 |
| 8 | 문서 없이 코드만 커밋하지 않는다 |

---

## 현재 런타임 기준

기준일: 2026-04-20

- 기본 LLM 프로바이더는 `OpenAI`다.
- 기본 호출 형식은 chat completions 기반 OpenAI-compatible API다.
- 실제 기본 모델명은 `.env`의 `DEFAULT_MODEL`을 source of truth로 본다.
- 기본 임베딩 경로는 `OpenAI`의 `text-embedding-3-small`이다.
- `Gemini`와 `Grok(xAI)`는 기본값이 아니라 선택 확장이다.
- 에이전트별 env override를 통해 한 파이프라인 안에서 OpenAI, Gemini, Grok를 혼합 사용할 수 있다.
- 2026-04-20의 OpenRouter + Gemma 전환 시도는 철회됐다. 그 표기는 현재 기준이 아니다.

### 환경 변수 기준

기본 런타임:

- `LLM_API_PROVIDER`
- `DEFAULT_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `EMBEDDING_API_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_API_BASE_URL`

선택 프로바이더:

- `GEMINI_API_KEY`
- `GEMINI_BASE_URL`
- `XAI_API_KEY`
- `XAI_BASE_URL`

에이전트별 override:

- `SINGLE_MODEL_PROVIDER`, `SINGLE_MODEL`
- `ROUTER_MODEL_PROVIDER`, `ROUTER_MODEL`
- `DRAFT_ANALYTICAL_MODEL_PROVIDER`, `DRAFT_ANALYTICAL_MODEL`
- `DRAFT_CREATIVE_MODEL_PROVIDER`, `DRAFT_CREATIVE_MODEL`
- `DRAFT_STRUCTURED_MODEL_PROVIDER`, `DRAFT_STRUCTURED_MODEL`
- `CRITIC_MODEL_PROVIDER`, `CRITIC_MODEL`
- `SYNTH_MODEL_PROVIDER`, `SYNTH_MODEL`
- `JUDGE_MODEL_PROVIDER`, `JUDGE_MODEL`
- `REWRITE_MODEL_PROVIDER`, `REWRITE_MODEL`
- `EVAL_MODEL_PROVIDER`, `EVAL_MODEL`

설명:

- `SYNTHESIZER_*`, `SINGLE_BASELINE_*`, `RUBRIC_JUDGE_*`도 같은 의미의 alias로 허용된다.
- provider를 지정하면 API key와 base URL은 해당 provider의 기본값을 따른다.
- 더 세밀한 제어가 필요하면 `<PREFIX>_API_KEY`, `<PREFIX>_API_BASE_URL`로 개별 override 할 수 있다.

### CLI 기준

- `scripts/run_single.py`, `scripts/run_moa.py`, `scripts/run_full.py`는 `--benchmark`를 사용한다.
- `scripts/run_full.py`는 `--output-tag`를 지원한다.
- 문서에 `--input`이 남아 있으면 구버전 표기로 본다.

### 벤치마크 기준

- `data/benchmarks/v1.json`: baseline 12건
- `data/benchmarks/v1_rag_mcp.json`: RAG/MCP smoke 및 validation

---

## 문서 우선순위

문서가 충돌하면 아래 순서로 해석한다.

1. `AGENTS.md`
2. `refs/tech_stack.md`
3. 현재 주차 문서
4. 이전 주차 문서와 초기 기획 문서

과거 문서에 `OpenRouter`, `Gemma`, `OPENROUTER_API_KEY`가 남아 있어도 현재 기준 문서와 충돌하면 현재 기준 문서를 따른다.

---

## 문서 동기화 규칙

프로바이더, 모델 정책, 임베딩 경로, CLI 인터페이스, 벤치마크 구성이 바뀌면 다음 문서를 같이 갱신한다.

- `AGENTS.md`
- `claude.md`
- `refs/tech_stack.md`
- `README.md`
- 현재 주차의 `weekN_plan.md`
- 현재 주차의 `weekN_implement.md`
- 필요 시 `docs/06_experiment_log.md`

모든 기준 변경에는 날짜가 있는 변경 기록을 남긴다.

---

## 현재 구현 체크포인트

기준 시각: 2026-04-20

완료:

- OpenAI 기본 런타임 복구
- Gemini/Grok agent-level override 지원
- GPT-5 chat completions 호환 패치
- `v1_rag_mcp.json` 준비
- `rag-001` 실주행 완료
- `mcp-001` 실주행 완료
- plain `moa` 비교 2건 완료
- `compare_runs.py` 비교 실행 완료
- Claude 참조 문서 정렬 완료

현 시점에서 "구현은 됐지만 아직 실주행하지 않음"으로 보면 안 되는 항목:

- RAG 경로
- MCP 경로
- path-aware evaluation
- compare_runs 기반 비교

아직 남은 것:

- mixed-provider 실험은 구성만 가능하고 아직 실주행하지 않음
- GPT-5 계열 pricing table은 아직 코드에 반영되지 않아 `cost_estimate`가 `0.0`일 수 있음
- 실주행 evidence 파일은 로컬에 있으나 `data/outputs`, `data/traces`는 gitignored 상태

로컬 evidence:

- `data/outputs/full_rag-001__rag.json`
- `data/outputs/full_mcp-001__mcp.json`
- `data/outputs/full_rag-001__rag_plain.json`
- `data/outputs/full_mcp-001__mcp_plain.json`

---

## 현재 선택지

Claude는 현재 상태를 아래 셋 중 하나의 분기점으로 이해한다.

1. 현재 OpenAI 기준 Week 8 결과를 baseline snapshot으로 유지하고 문서/커밋 정리
2. `draft_*` 계열에 Gemini/Grok override를 적용해 mixed-provider 실험 추가
3. GPT-5 cost estimation, evidence commit policy 같은 운영 보강 진행

주의:

- mixed-provider는 "지원됨"이지 "이미 실행됨"이 아니다.
- OpenRouter 기준으로 되돌아가거나, OpenRouter를 현재 기본값으로 가정하면 안 된다.

---

## 커밋 컨벤션

```text
<type>(<scope>): <subject>

type: docs | feat | test | fix | refactor | chore
scope: core | schemas | agents | orchestrator | eval | rag | mcp | scripts
```

---

## 진행 상태 추적

| 주차 | 상태 | 핵심 산출물 | 완료일 |
|------|------|------------|--------|
| 1주차 | 완료 | logger, config, timer, docs/00~02 | 2026-04-17 |
| 2주차 | 완료 | 스키마 3종, BaseAgent, 프롬프트 파일 | 2026-04-18 |
| 3주차 | 완료 | benchmark v1, run_single.py, rubric | 2026-03-08 |
| 4주차 | 완료 | Draft x3, Critic, Synthesizer, run_moa.py | 2026-03-12 |
| 5주차 | 완료 | Router, Judge/Rewrite, CostTracker, run_full.py | 2026-03-13 |
| 6주차 | 완료 | RAG, MCP, compare_runs.py, 회고 | 2026-03-14 |
| 7주차 | 진행 중 | C7-1 스캐폴딩, C7-2 Chroma RAG, C7-3 Filesystem MCP | - |
| 8주차 | 진행 중 | 실주행 검증, 평가 보강, 문서 정합성 보정 | - |

---

## 참조 문서

| 파일 | 내용 |
|------|------|
| `refs/tech_stack.md` | 허용 의존성, 프로바이더 정책, env 규칙 |
| `refs/folder_structure.md` | 디렉토리 구조와 역할 |
| `refs/eval_framework.md` | 평가 지표, 비교 축, 프로토콜 |

---

## 사용 안내

1. 항상 `AGENTS.md`를 먼저 본다.
2. 현재 주차의 `weekN_plan.md`와 `weekN_implement.md`를 함께 본다.
3. 과거 문서는 historical snapshot으로 읽고, 현재 기준과 충돌하면 현재 기준을 따른다.
4. 작업 완료 후 진행 상태와 변경 기록을 갱신한다.

---

## 변경 기록

### 2026-04-20

- OpenRouter + Gemma 기준을 철회하고 OpenAI 기본 런타임으로 복구했다.
- Gemini와 Grok를 에이전트별 env override로 혼합 사용할 수 있게 기준을 재정의했다.
- OpenRouter 관련 문구를 현재 기준에서 제외하고 stale wording으로 명시했다.
- 현재 구현 체크포인트와 Claude용 후속 선택지를 추가했다.
