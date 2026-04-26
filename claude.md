# Claude Reference Guide

이 문서는 `AGENTS.md`의 실행 기준을 빠르게 다시 확인하기 위한 요약본이다.

- 충돌 시 `AGENTS.md`를 우선한다.
- 해석 순서는 `AGENTS.md -> refs/tech_stack.md -> 현재 주차 문서`다.

---

## 현재 런타임

- 기본 provider: `OpenAI`
- 기본 모델: `.env`의 `DEFAULT_MODEL`
- 기본 embedding: `text-embedding-3-small`
- 선택 확장: `Gemini`, `Z.AI`
- 레거시 alias: `xai`, `grok`, `zhipu`, `glm`
- agent-level env override와 request-level override를 모두 지원

---

## Week 10 추가 사항

추가 완료:

- 공용 service-layer runtime
- `FastAPI` 웹 서버
- 정적 웹 챗 UI
- 메모리 세션 저장소
- 글로벌 모델 선택
- agent override
- preset 기반 다중 모델 선택
- `/api/models`, `/api/sessions`, `/api/chat` API

웹 서버 실행:

```bash
uvicorn app.web.server:app --reload
```

---

## CLI 기준

- `run_single.py`, `run_moa.py`, `run_full.py`는 `--benchmark`를 사용한다.
- `run_full.py`는 `--output-tag`를 지원한다.

---

## 벤치마크 기준

- `data/benchmarks/v1.json`: baseline
- `data/benchmarks/v1_rag_mcp.json`: RAG/MCP smoke validation

---

## 현재 상태 요약

기준일: 2026-04-26

- OpenAI 기본 런타임 복구 상태 유지
- Gemini/Z.AI mixed-provider 구성 지원
- RAG, MCP, path-aware evaluation 유지
- Week 10 웹 챗봇 레이어 구현 완료 (한국어 UI 리디자인 포함)
- Synthesizer → gpt-5.4-mini 적용 (.env + model_registry)
- 글로벌 모델 "에이전트별 기본값" 옵션 추가 (env 기본값 우선)
- Week 11 지침 작성 완료 (RAG·MCP 프론트엔드 연동)
- 전체 테스트 통과: `155 passed`

---

## 자주 쓰는 override prefix

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

예시:

```text
DRAFT_ANALYTICAL_MODEL_PROVIDER=gemini
DRAFT_CREATIVE_MODEL_PROVIDER=zai
EVAL_MODEL_PROVIDER=openai
```

---

## 변경 기록

### 2026-04-25

- Week 10 웹 UI, 세션 챗, 모델 선택 런타임을 반영했다.
- `scripts/run_full.py`의 service-layer wrapper 구조를 반영했다.
- 테스트 통과 상태를 현재 기준으로 갱신했다.

### 2026-04-20

- OpenAI 기본 런타임 복구와 mixed-provider 정책을 반영했다.
