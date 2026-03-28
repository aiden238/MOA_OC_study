# Claude Reference Guide

이 파일은 `AGENTS.md`의 요약 미러다.

- 충돌 시 `AGENTS.md`를 우선한다.
- Claude는 현재 기준을 `AGENTS.md`, `refs/tech_stack.md`, 현재 주차 문서 순서로 해석한다.

---

## 현재 해석 규칙

### 1. 런타임 기준

- 기본 프로바이더는 `OpenAI`다.
- 기본 모델은 `.env`의 `DEFAULT_MODEL`이다.
- 기본 임베딩은 `text-embedding-3-small`이다.
- `Gemini`, `Grok(xAI)`는 선택 확장이다.
- 에이전트별 env override로 혼합 사용이 가능하다.

### 2. OpenRouter 해석

- OpenRouter + Gemma 전환 시도는 철회됐다.
- 과거 문서의 OpenRouter 관련 표기는 stale wording으로 처리한다.

### 3. 실행 기준

- `run_single.py`, `run_moa.py`, `run_full.py`는 `--benchmark`를 사용한다.
- `run_full.py --output-tag`로 결과 파일 덮어쓰기를 피한다.

### 4. 벤치마크 기준

- `v1.json`: baseline
- `v1_rag_mcp.json`: RAG/MCP smoke validation

### 5. Planner 해석

- `Planner`는 현재 코드에서 독립 런타임 모듈이 아니라 planning stage 개념이다.

---

## 현재 진행 스냅샷

기준 시각: 2026-04-20

- OpenAI 기본 런타임 복구는 완료됐다.
- Gemini/Grok 혼합 사용을 위한 agent-level override도 반영됐다.
- Week 8 실주행 4건은 완료됐다.
- GPT-5 계열 chat completions 호환성 수정도 반영됐다.
- `data/outputs/`에는 RAG 1건, MCP 1건, plain MOA 2건이 저장돼 있다.
- Claude는 이 상태를 current progress로 인식해야 한다.

실주행 재개 조건:

- 현재 기준으로는 실주행 재개 조건이 아니라 결과 검토 및 후속 실험 확장 단계다.

현재 확보 결과:

- `rag-001` path=`moa+rag`, avg_score=`4.0`
- `mcp-001` path=`moa+mcp`, avg_score=`4.0`
- rag delta: `+2.25`
- mcp delta: `+0.25`

추가 상태 해석:

- 위 결과는 "실주행 완료" 상태다. 단순 구현 완료가 아니다.
- mixed-provider는 아직 실행되지 않았다.
- GPT-5 cost estimation은 미반영 상태라 비용 숫자는 신뢰 기준이 아니다.
- `data/outputs`, `data/traces` evidence는 로컬 기준이며 기본 git 추적 대상은 아니다.

---

## Claude용 선택지

Claude는 현재 다음 분기 중 하나를 후속 작업으로 인식한다.

1. OpenAI 기준 Week 8 snapshot 유지
2. Gemini/Grok를 `draft_*`에 분배해 mixed-provider 확장 실험
3. 운영 보강
   - GPT-5 pricing 반영
   - evidence commit 정책 정리
   - 추가 benchmark 확장

금지 해석:

- "RAG/MCP는 아직 구현 전"으로 읽지 말 것
- "OpenRouter가 현재 기본값"으로 읽지 말 것

---

## 에이전트별 override 힌트

자주 쓰는 prefix:

- `SINGLE_*`
- `ROUTER_*`
- `DRAFT_ANALYTICAL_*`
- `DRAFT_CREATIVE_*`
- `DRAFT_STRUCTURED_*`
- `CRITIC_*`
- `SYNTH_*`
- `JUDGE_*`
- `REWRITE_*`
- `EVAL_*`

예:

- `DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini`
- `DRAFT_CREATIVE_MODEL_PROVIDER=xai`
- `EVAL_MODEL_PROVIDER=openai`

---

## 변경 기록

### 2026-04-20

- OpenAI 기본 복구와 Gemini/Grok 혼합 사용 규칙을 반영했다.
- OpenRouter 문구를 현재 기준에서 제외했다.
- Week 8 실주행 완료 상태와 비교 결과를 반영했다.
- 현재 선택지와 미완료 항목 해석 규칙을 추가했다.
