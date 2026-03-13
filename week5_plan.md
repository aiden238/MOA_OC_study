# Week 5 Plan — Router + Judge/Rewrite + 조건부 분기

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 5주차 |
| **상태** | ✅ 완료 |
| **시작일** | 2026-03-13 |
| **완료일** | 2026-03-13 |

---

## 이전 주차 산출물 요약

> 4주차에서 완성된 핵심 결과물:

| 산출물 | 검증 상태 | 설명 |
|--------|----------|------|
| `app/agents/draft_agent.py` | ✅ | 3종 Draft Agent (analytical/creative/structured), async 병렬 |
| `app/agents/critic_agent.py` | ✅ | 3개 draft 비교 분석, 구조화 JSON 출력 |
| `app/orchestrator/synthesizer.py` | ✅ | Critic 피드백 + drafts → 최종 결과 조합 |
| `app/orchestrator/executor.py` | ✅ | Draft → Critic → Synthesizer 파이프라인 엔진 |
| `scripts/run_moa.py` | ✅ | MOA 실행 스크립트 (12건 실행, trace 저장) |
| `tests/test_pipeline_moa.py` | ✅ | MOA 통합 테스트 통과 |

---

## 이번 주차 목표

> **Router로 경로를 자동 선택하고, Judge가 품질을 판정하여 조건부 Rewrite를 수행하고, cost_tracker로 비용을 집계하는 완전한 파이프라인을 만든다.**

이번 주 이후 `run_full.py`로 입력만 넣으면 Router → 자동 분기 → 결과까지 end-to-end로 실행된다.

---

## 커밋 계획

### C5-1: Judge Agent + Rewrite Agent 구현 (Day 1~2)

**작업:** 최종 품질 판정(pass/rewrite/escalate)과 피드백 기반 재작성

**산출물:**
- `app/agents/judge_agent.py`
- `app/agents/rewrite_agent.py`
- `tests/test_judge.py`

**커밋 메시지:** `feat(agents): implement judge and rewrite agents with quality gate`

### C5-2: Router + Retry Policy 구현 (Day 3~5)

**작업:** Rule-based + LLM hybrid 라우팅, 재시도/폴백 정책

**산출물:**
- `app/orchestrator/router.py`
- `app/orchestrator/retry_policy.py`
- `tests/test_router.py`
- `docs/04_routing_rules.md`

**커밋 메시지:** `feat(orchestrator): implement hybrid router and retry policy`

### C5-3: cost_tracker + run_full.py 통합 (Day 6~7)

**작업:** 토큰·비용 집계 모듈, end-to-end 실행 스크립트

**산출물:**
- `app/core/cost_tracker.py`
- `scripts/run_full.py`

**커밋 메시지:** `feat(core): add cost tracker and full pipeline run script`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `app/agents/judge_agent.py` | Judge Agent (pass/rewrite/escalate) | C5-1 |
| `app/agents/rewrite_agent.py` | Rewrite Agent (피드백 기반 개선) | C5-1 |
| `app/orchestrator/router.py` | 2단계 하이브리드 Router | C5-2 |
| `app/orchestrator/retry_policy.py` | 재시도/폴백 정책 | C5-2 |
| `tests/test_router.py` | Router 단위/통합 테스트 | C5-2 |
| `docs/04_routing_rules.md` | 라우팅 규칙 명세 문서 | C5-2 |
| `app/core/cost_tracker.py` | 토큰·비용 집계 | C5-3 |
| `scripts/run_full.py` | end-to-end 통합 실행 스크립트 | C5-3 |

---

## 완료 기준 (DoD)

- [x] Router가 입력을 분석하여 single/moa 경로를 자동 선택
- [x] Rule-based 1차 필터가 명확한 케이스를 LLM 호출 없이 판별
- [x] LLM 2차 판별이 애매한 케이스에서 작동
- [x] Judge가 "pass/rewrite/escalate" 판정을 JSON으로 반환
- [x] rewrite 시 Rewrite Agent가 Judge 피드백을 반영하여 개선
- [x] rewrite 루프가 최대 2회로 제한됨
- [x] `run_full.py`가 Router → 자동 분기 → 결과 저장까지 end-to-end 실행
- [x] cost_tracker가 총 토큰, 추정 비용, 경로별 비용을 집계
- [x] `tests/test_router.py` 통과
- [x] `docs/04_routing_rules.md`에 라우팅 규칙이 문서화

---

## 다음 주차 의존성

> 6주차가 의존하는 5주차 산출물:

| 산출물 | 6주차에서의 용도 |
|--------|-----------------|
| `app/orchestrator/router.py` | `requires_rag`, `requires_mcp` 플래그 활성화하여 RAG/MCP 분기 추가 |
| `app/orchestrator/executor.py` | RAG context injection, MCP tool result injection 포인트 추가 |
| `app/orchestrator/retry_policy.py` | RAG/MCP 실패 시 폴백 정책 재사용 |
| `app/core/cost_tracker.py` | RAG/MCP 경로의 비용도 동일 트래커로 집계 |
| `scripts/run_full.py` | 4경로(single/moa/moa+rag/moa+mcp) 실행의 기반 |
| Router의 `RoutingDecision` 스키마 | `requires_rag`, `requires_mcp` 필드가 이미 정의됨 (6주차 활성화) |
