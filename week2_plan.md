# Week 2 Plan — 스키마 + 에이전트 기반 + 프롬프트 분리

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 2주차 |
| **상태** | ✅ 완료 |
| **시작일** | 2026-04-18 |
| **완료일** | 2026-04-18 |

---

## 이전 주차 산출물 요약

> 1주차에서 완성된 핵심 결과물:

| 산출물 | 검증 상태 | 설명 |
|--------|----------|------|
| `app/core/config.py` | ✅ | dotenv 기반 전역 설정 로딩 |
| `app/core/logger.py` | ✅ | JSON trace 로거 (`data/traces/{run_id}.json` 생성) |
| `app/core/timer.py` | ✅ | 밀리초 단위 레이턴시 측정 데코레이터 |
| `docs/00~02.md` | ✅ | 프로젝트 목표, 범위, 아키텍처 명세 |
| 디렉토리 구조 | ✅ | 기획서 Section 2 기준 전체 폴더 생성 완료 |
| `tests/test_logger.py` | ✅ | 로거 단위 테스트 통과 |

---

## 이번 주차 목표

> **Pydantic 스키마 3종을 정의하고, Base Agent 클래스를 구현하고, 역할별 프롬프트를 .md 파일로 분리한다.**

이번 주차 이후 모든 에이전트는 `BaseAgent`를 상속하고, 모든 입출력은 Pydantic 스키마를 거치며, 모든 프롬프트는 `.md` 파일에서 로딩된다.

---

## 커밋 계획

### C2-1: Pydantic 스키마 3종 정의 + validation 테스트 (Day 1~2)

**작업:** TaskRequest/TaskPlan, AgentInput/AgentOutput, TraceRecord/RunSummary 스키마 정의

**산출물:**
- `app/schemas/__init__.py` (re-export)
- `app/schemas/task.py`
- `app/schemas/agent_io.py`
- `app/schemas/trace.py`
- `tests/test_schemas.py`

**커밋 메시지:** `feat(schemas): define pydantic schemas for task, agent IO, and trace`

### C2-2: Base Agent 클래스 구현 (Day 3~4)

**작업:** httpx + pydantic + timer를 조합한 LLM API 호출 래퍼

**산출물:**
- `app/agents/__init__.py`
- `app/agents/base_agent.py`
- `tests/test_base_agent.py`

**커밋 메시지:** `feat(agents): implement base agent with httpx and pydantic`

### C2-3: 역할별 프롬프트 파일 분리 + 문서 (Day 5~7)

**작업:** 8개 역할의 시스템 프롬프트를 `.md` 파일로 작성, 에이전트 역할 문서 작성

**산출물:**
- `app/prompts/*.md` (8개: planner, draft_analytical, draft_creative, draft_structured, critic, judge, rewrite, synthesizer)
- `docs/03_agent_roles.md`

**커밋 메시지:** `docs(agents): add role-specific prompt files and agent roles document`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `app/schemas/task.py` | TaskRequest, TaskPlan 스키마 | C2-1 |
| `app/schemas/agent_io.py` | AgentInput, AgentOutput 스키마 | C2-1 |
| `app/schemas/trace.py` | TraceRecord, RunSummary 스키마 | C2-1 |
| `tests/test_schemas.py` | 스키마 validation 테스트 | C2-1 |
| `app/agents/base_agent.py` | LLM API 호출 래퍼 | C2-2 |
| `tests/test_base_agent.py` | BaseAgent 단위 테스트 | C2-2 |
| `app/prompts/*.md` (8개) | 역할별 시스템 프롬프트 | C2-3 |
| `docs/03_agent_roles.md` | 에이전트 역할 명세 문서 | C2-3 |

---

## 완료 기준 (DoD)

- [x] `TaskRequest(prompt="test")` 등 스키마 validation 통과
- [x] `AgentOutput`이 필수 필드 누락 시 ValidationError 발생
- [x] `tests/test_schemas.py` 전체 통과
- [x] Base Agent가 실제 LLM API를 호출하고 `AgentOutput`으로 파싱
- [x] `tests/test_base_agent.py` 통과 (API 키 필요, 또는 mock 테스트)
- [x] 프롬프트 파일 8개가 `app/prompts/`에 존재
- [x] `BaseAgent.load_prompt("critic")` 호출 시 `critic.md` 내용 반환
- [x] `docs/03_agent_roles.md`에 8개 역할의 목적·입출력이 기술되어 있음

---

## 다음 주차 의존성

> 3주차가 의존하는 2주차 산출물:

| 산출물 | 3주차에서의 용도 |
|--------|-----------------|
| `app/schemas/task.py` | `run_single.py`가 벤치마크 데이터를 `TaskRequest`로 파싱 |
| `app/schemas/agent_io.py` | 단일 호출 결과를 `AgentOutput`으로 수집 |
| `app/schemas/trace.py` | 실행 결과를 `RunSummary`로 집계 |
| `app/agents/base_agent.py` | 단일 호출 파이프라인의 LLM 호출 엔진 |
| `app/prompts/*.md` | BaseAgent 테스트에 필요 |
