# Week 7 C7-1 Implement Guide

## 목표

Week 7의 첫 단계로 실행선과 평가 스캐폴딩을 정리한다.

- Router가 만든 `RoutingDecision`이 실제 executor까지 전달되도록 연결
- trace / cost / evaluation / comparison 스키마를 Week 7 기준으로 확장
- 이후 `moa+rag`, `moa+mcp` 실험을 받을 수 있는 저장 포맷을 먼저 고정

## 범위

- `app/orchestrator/router.py`
- `scripts/run_full.py`
- `app/orchestrator/executor.py`
- `app/schemas/trace.py`
- `app/core/logger.py`
- `app/core/cost_tracker.py`
- `app/eval/rubric.py`
- `app/eval/comparator.py`
- `scripts/compare_runs.py`
- 관련 테스트 파일

## 선행 조건

- `AGENTS.md`, `week7_plan.md`, `week7_implement.md`를 기준 문서로 사용한다.
- 기존 회귀 기준은 전체 `116 passed` 상태다.
- C7-1에서는 새 의존성을 추가하지 않는다.

## 핵심 결정

### 1. RoutingDecision 확장

기존 필드에 아래 4개를 추가한다.

- `rag_query_hint: str | None`
- `mcp_intent: str | None`
- `preferred_server: str | None`
- `preferred_tool: str | None`

### 2. LLM router 동시 수정

`RoutingDecision` 필드만 늘리면 안 된다. 아래 둘을 반드시 같이 바꾼다.

- `_ROUTER_SYSTEM_PROMPT`
- `llm_route()` JSON parser

LLM 라우팅 응답 JSON이 새 필드를 포함하도록 만들고, 누락 시에는 안전하게 `None`으로 처리한다.

### 3. operation_type 단순화

trace / cost 집계용 `operation_type`는 아래 3개만 사용한다.

- `llm_completion`
- `rag`
- `mcp_tool`

RAG 세부 단계는 `metadata.stage`로 구분한다.

- `indexing`
- `embedding`
- `retrieval`
- `context_build`

### 4. per-case result 확장

`run_full.py`가 저장하는 결과 dict에 아래 필드를 추가한다.

- `evaluation`
- `evaluation_context`
- `context_metadata`

이 구조가 먼저 생겨야 `avg_score_delta`를 계산할 수 있다.

### 5. 평가 함수 이름 유지

기존 `rubric.py`의 `evaluate_single()` 이름은 유지한다.

권장 시그니처:

```python
async def evaluate_single(
    prompt: str,
    output: str,
    constraints: dict | None = None,
    path: str = "single",
    evaluation_context: dict | None = None,
) -> dict:
```

`evaluate_batch()`는 이 컨텍스트를 그대로 전달하는 래퍼로 확장한다.

## 구현 상세

### A. Routing 계층

- `RoutingDecision` 필드 확장
- `_ROUTER_SYSTEM_PROMPT`가 새 필드를 포함한 JSON만 요구하도록 수정
- `llm_route()`가 새 필드를 파싱하도록 수정
- rule-based 경로는 새 필드가 비어 있어도 동작 유지

### B. 실행선 연결

- `run_full.py`에서 `decision`을 `run_moa_path(..., routing=decision)`로 전달
- `run_moa_path()`에서 `MOAExecutor.execute(..., routing=decision)`로 전달
- 이 단계 완료 후 routing 정보가 executor에서 실제로 살아 있어야 한다

### C. Trace / Cost 확장

- `TraceRecord`에 `operation_type`, `metadata` 추가
- `TraceLogger.log()`에 같은 필드 추가
- `CostTracker.add()`가 `path`, `operation_type`, `metadata`, `cost_override`를 받도록 확장
- summary는 최소 아래 집계를 제공해야 한다
  - `by_path`
  - `by_operation_type`

### D. per-case result 확장

`run_full.py` 결과 저장 구조에 최소 아래 필드를 유지한다.

- `case_id`
- `task_type`
- `prompt`
- `output`
- `path`
- `routing_reason`
- `routing_confidence`
- `agent_count`
- `agents`
- `prompt_tokens`
- `completion_tokens`
- `latency_ms`
- `cost_estimate`
- `evaluation`
- `evaluation_context`
- `context_metadata`

### E. 평가 계층 확장

경로별 평가 입력은 아래 원칙을 따른다.

- `single`, `moa`: 기존 입력 사용
- `moa+rag`: 기존 입력 + retrieval context + chunk metadata + citation label
- `moa+mcp`: 기존 입력 + tool trace + normalized tool summary

trace 부족 시 path-specific metric은 `0`이 아니라 `not_evaluable`로 저장한다.

### F. 비교 계층 확장

`Comparator`와 `compare_runs.py`는 아래 그룹 비교를 지원해야 한다.

- `baseline`: `single` vs `moa`
- `rag`: `moa` vs `moa+rag`
- `mcp`: `moa` vs `moa+mcp`

최소 출력 필드:

- `group`
- `left_path`
- `right_path`
- `count`
- `avg_score_delta`
- `avg_cost_delta`
- `avg_latency_delta`
- `avg_tokens_delta`

## 테스트 계획

### 섹션별 확인

1. Routing 계층 완료 후
- router 단위 테스트
- `llm_route()` 새 필드 파싱 테스트
- `run_full.py` routing 전달 테스트

2. 실행선 연결 완료 후
- `run_full.py` / executor 연동 테스트
- 기존 `test_run_full.py` 회귀 확인

3. Trace / Cost 확장 완료 후
- logger 테스트
- cost tracker 테스트
- trace schema 테스트

4. per-case result 확장 완료 후
- 저장 결과 구조 테스트
- `evaluation`, `evaluation_context`, `context_metadata` 존재 확인

5. 평가 계층 완료 후
- rubric 단위 테스트
- path-aware `evaluation_context` 테스트

6. 비교 계층 완료 후
- comparator 테스트
- `compare_runs.py` baseline / rag / mcp 그룹 출력 테스트

7. 마감 전
- 전체 테스트 실행

## DoD

- 기존 116개 테스트 통과
- C7-1 신규 테스트 통과
- routing 확장 필드가 rule-based / llm-based 양쪽에서 깨지지 않음
- `run_full.py` routing이 executor까지 전달됨
- per-case result dict에 `evaluation`, `evaluation_context`, `context_metadata`가 저장됨
- `TraceRecord`, `TraceLogger`, `CostTracker`가 새 구조를 지원함
- `rubric.py`가 path-aware evaluation을 수행함
- `Comparator`, `compare_runs.py`가 baseline / rag / mcp 그룹 비교를 지원함

## 중단 조건

- `RoutingDecision` 확장으로 기존 fixture와 호환 방향을 안전하게 정할 수 없을 때
- per-case result 저장 구조를 기존 output JSON 확장으로 둘 수 없을 때
- `evaluate_single()` / `evaluate_batch()` 호환성을 유지한 채 rubric 확장이 불가능할 때
- 전체 테스트 회귀가 설계 충돌 수준으로 발생할 때

## 권장 커밋 메시지

```text
feat(eval): implement c7-1 routing trace and comparison scaffolding
```
