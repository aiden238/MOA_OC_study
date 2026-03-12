# Week 4 Plan — MOA 파이프라인 (Draft + Critic + Trace)

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 4주차 |
| **상태** | ✅ 완료 |
| **시작일** | 2026-03-09 |
| **완료일** | 2026-03-12 |

---

## 이전 주차 산출물 요약

> 3주차에서 완성된 핵심 결과물:

| 산출물 | 검증 상태 | 설명 |
|--------|----------|------|
| `data/benchmarks/v1.json` | ✅ | 4종 × 3건 = 12건 벤치마크 데이터 |
| `scripts/run_single.py` | ✅ | baseline 단일 호출 → trace/output 저장 |
| `data/outputs/single_*.json` | ✅ | 12건 baseline 결과 |
| `data/traces/` (single 분) | ✅ | baseline trace (비용·시간 기준선) |
| `app/eval/rubric.py` | ✅ | LLM Judge 기반 1~5점 채점 (4항목) |
| `app/eval/metrics.py` | ✅ | 시스템 지표 자동 계산 |
| `tests/test_pipeline_single.py` | ✅ | single 파이프라인 통합 테스트 통과 |

---

## 이번 주차 목표

> **Draft Agent 3종을 비동기 병렬로 실행하고, Critic이 비교 분석하고, Synthesizer가 최종 조합하는 MOA 파이프라인을 완성한다.**

이번 주는 Judge/Rewrite 없이 **Draft → Critic → Synthesizer**까지만 구현한다.

---

## 커밋 계획

### C4-1: Draft Agent 3종 구현 + 다양성 테스트 (Day 1~2)

**작업:** 3가지 관점의 Draft Agent (analytical, creative, structured)를 async 병렬로 실행

**산출물:**
- `app/agents/draft_agent.py`
- `tests/test_draft_diversity.py`

**커밋 메시지:** `feat(agents): implement three draft agents with async parallel execution`

### C4-2: Critic Agent + Synthesizer 구현 (Day 3~5)

**작업:** 3개 draft를 비교 분석하는 Critic과, 최종 조합하는 Synthesizer 구현

**산출물:**
- `app/agents/critic_agent.py`
- `app/orchestrator/synthesizer.py`
- `tests/test_critic.py`
- `tests/test_synthesizer.py`

**커밋 메시지:** `feat(agents): implement critic agent and synthesizer`

### C4-3: MOA 실행 스크립트 + trace 통합 + 첫 비교 (Day 6~7)

**작업:** end-to-end MOA 파이프라인 실행, single vs moa 첫 비교

**산출물:**
- `scripts/run_moa.py`
- `app/orchestrator/executor.py`
- `tests/test_pipeline_moa.py`

**커밋 메시지:** `feat(orchestrator): implement MOA pipeline executor and run script`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `app/agents/draft_agent.py` | Draft Agent 3종 (비동기 병렬) | C4-1 |
| `tests/test_draft_diversity.py` | draft 다양성 검증 테스트 | C4-1 |
| `app/agents/critic_agent.py` | Critic Agent (비교 분석) | C4-2 |
| `app/orchestrator/synthesizer.py` | Synthesizer Agent (최종 조합) | C4-2 |
| `tests/test_critic.py` | Critic 단위 테스트 | C4-2 |
| `tests/test_synthesizer.py` | Synthesizer 단위 테스트 | C4-2 |
| `scripts/run_moa.py` | MOA 실행 스크립트 | C4-3 |
| `app/orchestrator/executor.py` | 파이프라인 실행 엔진 | C4-3 |
| `tests/test_pipeline_moa.py` | MOA 파이프라인 통합 테스트 | C4-3 |

---

## 완료 기준 (DoD)

- [x] `python scripts/run_moa.py` 실행 시 3개 draft가 생성됨
- [x] 3개 draft가 **비동기 병렬**로 실행됨 (`asyncio.gather`)
- [x] Critic이 3개 draft의 강점/약점을 구조화된 JSON으로 분석
- [x] Synthesizer가 critic 피드백 + drafts로 최종 결과 생성
- [x] trace에 각 에이전트별(draft×3, critic, synthesizer) 호출 정보가 모두 기록
- [x] 동일 입력에 대해 single vs moa 결과가 나란히 비교 가능
- [x] `tests/test_draft_diversity.py` 통과 (유사도 ≤ 0.7)
- [x] `tests/test_pipeline_moa.py` 통과
- [x] API 429 에러 시 재시도 로직이 동작 (tenacity)

---

## 다음 주차 의존성

> 5주차가 의존하는 4주차 산출물:

| 산출물 | 5주차에서의 용도 |
|--------|-----------------|
| `app/agents/draft_agent.py` | Judge/Rewrite가 draft 결과를 평가·개선 |
| `app/agents/critic_agent.py` | 기존 Critic 구조 위에 Judge 판정 추가 |
| `app/orchestrator/executor.py` | Router가 executor를 호출하는 구조로 확장 |
| `app/orchestrator/synthesizer.py` | Judge → pass 시 synthesizer 결과를 최종 출력으로 확정 |
| `scripts/run_moa.py` | `run_full.py`의 템플릿으로 참조 |
| MOA trace/output 데이터 | single vs moa 비교 기준선 |
