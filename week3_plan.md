# Week 3 Plan — Baseline (Single Path) 파이프라인

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 3주차 |
| **상태** | 🔲 대기 |
| **시작일** | — |
| **완료일** | — |

---

## 이전 주차 산출물 요약

> 2주차에서 완성된 핵심 결과물:

| 산출물 | 검증 상태 | 설명 |
|--------|----------|------|
| `app/schemas/task.py` | ✅ | TaskRequest, TaskPlan 스키마 (validation 테스트 통과) |
| `app/schemas/agent_io.py` | ✅ | AgentInput, AgentOutput 스키마 |
| `app/schemas/trace.py` | ✅ | TraceRecord, RunSummary 스키마 |
| `app/agents/base_agent.py` | ✅ | httpx 기반 LLM API 호출 래퍼 (실제 API 호출 검증) |
| `app/prompts/*.md` (8개) | ✅ | 역할별 시스템 프롬프트 파일 |
| `docs/03_agent_roles.md` | ✅ | 에이전트 역할 명세 |

---

## 이번 주차 목표

> **벤치마크 입력 데이터를 작성하고, 단일 호출 baseline 파이프라인을 구현하고, 평가 루브릭을 만든다.**

이번 주차의 결과물(baseline 점수)은 4주차 MOA 파이프라인과 직접 비교되는 **기준선**이다.

---

## 커밋 계획

### C3-1: 벤치마크 입력 데이터 v1 작성 (Day 1~2)

**작업:** 4종 × 3건 = 12건의 벤치마크 데이터 + 평가 지표 문서

**산출물:**
- `data/benchmarks/v1.json`
- `docs/05_eval_metrics.md`

**커밋 메시지:** `docs(eval): add benchmark v1 data and evaluation metrics document`

### C3-2: `run_single.py` 구현 (Day 3~4)

**작업:** 벤치마크 입력 → 단일 LLM 호출 → trace 저장 + 결과 출력

**산출물:**
- `scripts/run_single.py`
- `tests/test_pipeline_single.py`

**커밋 메시지:** `feat(scripts): implement single path baseline pipeline`

### C3-3: 평가 루브릭 구현 (Day 5~7)

**작업:** LLM Judge 기반 자동 채점 + 수동 교차 검증 프레임워크

**산출물:**
- `app/eval/rubric.py`
- `app/eval/metrics.py`

**커밋 메시지:** `feat(eval): implement rubric-based LLM evaluation and metrics`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `data/benchmarks/v1.json` | 벤치마크 입력 데이터 12건 | C3-1 |
| `docs/05_eval_metrics.md` | 평가 지표 명세 문서 | C3-1 |
| `scripts/run_single.py` | baseline 단일 호출 실행 스크립트 | C3-2 |
| `tests/test_pipeline_single.py` | single 파이프라인 통합 테스트 | C3-2 |
| `app/eval/rubric.py` | 루브릭 기반 LLM Judge 채점 | C3-3 |
| `app/eval/metrics.py` | 시스템 지표 자동 계산 | C3-3 |

---

## 완료 기준 (DoD)

- [ ] `data/benchmarks/v1.json`에 4종 × 3건 = 12건의 벤치마크 데이터 존재
- [ ] `python scripts/run_single.py` 실행 시 12건 입력에 대한 결과가 `data/outputs/`에 저장
- [ ] 각 실행의 trace가 `data/traces/`에 JSON으로 저장
- [ ] trace JSON의 필드가 `TraceRecord` 스키마와 일치
- [ ] 루브릭이 clarity / structure / constraint_following / usefulness 4항목을 1~5점으로 채점
- [ ] `app/eval/metrics.py`가 total_tokens, total_cost, total_latency를 정상 계산
- [ ] `tests/test_pipeline_single.py` 통과
- [ ] 수동 채점 5건 완료, LLM Judge와의 상관관계 확인

---

## 다음 주차 의존성

> 4주차가 의존하는 3주차 산출물:

| 산출물 | 4주차에서의 용도 |
|--------|-----------------|
| `data/benchmarks/v1.json` | 동일 입력으로 MOA 파이프라인 실행 (single vs moa 비교) |
| `data/outputs/single_*.json` | MOA 결과와 나란히 비교하기 위한 baseline 결과 |
| `data/traces/` (single 실행분) | baseline 비용·시간 기준선 |
| `app/eval/rubric.py` | MOA 결과도 동일 루브릭으로 채점 |
| `app/eval/metrics.py` | MOA 결과의 시스템 지표도 동일 도구로 계산 |
| `scripts/run_single.py` | `run_moa.py`의 템플릿으로 참조 |
