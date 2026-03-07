# Week 1 Plan — 프로젝트 뼈대 + 명세 확정

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 1주차 |
| **상태** | ✅ 완료 |
| **시작일** | 2026-04-17 |
| **완료일** | 2026-04-17 |

---

## 이전 주차 산출물 요약

> 없음 (첫 주차)

이 프로젝트는 빈 상태에서 시작합니다. 현재 존재하는 파일:
- `README.md` — 프로젝트 개요
- `requirements.txt` — 의존성 목록 (주석 포함)
- `env.example` — 환경변수 템플릿
- `MOA_오케스트레이션_최종기획서.md` — 전체 기획서 원본

---

## 이번 주차 목표

> **프로젝트 환경을 구성하고, 기획 문서를 확정하고, JSON trace 로거를 구현한다.**

모든 후속 주차의 기반이 되는 인프라 코드(config, logger, timer)와 기준 문서(docs/00~02)를 만든다.

---

## 커밋 계획

### C1-1: 프로젝트 초기화 (Day 1~2)

**작업:** 프로젝트 디렉토리 구조 생성, venv 설정, .gitignore 작성

**산출물:**
- `app/__init__.py`, `app/core/__init__.py`, `app/schemas/__init__.py`
- `app/agents/__init__.py`, `app/orchestrator/__init__.py`, `app/eval/__init__.py`
- `app/prompts/`, `tests/`, `scripts/`, `data/benchmarks/`, `data/traces/`, `data/outputs/`, `docs/`
- `.gitignore`

**커밋 메시지:** `chore(core): initialize project structure and venv`

### C1-2: 기획 문서 작성 (Day 3~4)

**작업:** 기획서 내용을 docs/ 하위 명세서 3건으로 분리

**산출물:**
- `docs/00_project_goal.md` — 프로젝트 목표, 왜 하는지, 최종 아키텍처
- `docs/01_scope_and_nongoals.md` — 6주 범위, Non-Goals, 가드레일
- `docs/02_architecture.md` — Single/MOA/Full 경로 아키텍처, 폴더 구조

**커밋 메시지:** `docs(project): add project goal, scope, and architecture documents`

### C1-3: JSON trace 로거 구현 + 테스트 (Day 5~7)

**작업:** config, logger, timer 모듈 구현 및 테스트

**산출물:**
- `app/core/config.py`
- `app/core/logger.py`
- `app/core/timer.py`
- `tests/test_logger.py`

**커밋 메시지:** `feat(core): implement JSON trace logger with config and timer`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `app/__init__.py` | 패키지 초기화 | C1-1 |
| `app/core/__init__.py` | core 패키지 초기화 | C1-1 |
| `app/core/config.py` | 환경변수 로딩, 전역 설정 | C1-3 |
| `app/core/logger.py` | JSON trace 로거 | C1-3 |
| `app/core/timer.py` | 레이턴시 측정 데코레이터 | C1-3 |
| `.gitignore` | Git 무시 파일 | C1-1 |
| `docs/00_project_goal.md` | 프로젝트 목표 문서 | C1-2 |
| `docs/01_scope_and_nongoals.md` | 범위 및 Non-Goals | C1-2 |
| `docs/02_architecture.md` | 아키텍처 명세 | C1-2 |
| `tests/test_logger.py` | 로거 단위 테스트 | C1-3 |

---

## 완료 기준 (DoD)

- [x] `python -m pytest tests/test_logger.py` 통과
- [x] logger가 `data/traces/`에 JSON 파일을 정상 생성
- [x] `data/traces/{run_id}.json`의 필드가 명세와 일치
- [x] `config.py`가 `.env` 파일에서 설정을 정상 로딩
- [x] `timer.py` 데코레이터가 밀리초 단위 레이턴시를 반환
- [x] `docs/00_project_goal.md` 뼈대가 채워져 있음
- [x] `docs/01_scope_and_nongoals.md` 뼈대가 채워져 있음
- [x] `docs/02_architecture.md` 뼈대가 채워져 있음
- [x] 모든 디렉토리 구조가 기획서 Section 2와 일치

---

## 다음 주차 의존성

> 2주차가 의존하는 1주차 산출물:

| 산출물 | 2주차에서의 용도 |
|--------|-----------------|
| `app/core/config.py` | BaseAgent가 모델명·API 키를 읽기 위해 필요 |
| `app/core/logger.py` | BaseAgent가 호출 결과를 trace로 기록하기 위해 필요 |
| `app/core/timer.py` | BaseAgent가 레이턴시를 측정하기 위해 필요 |
| 디렉토리 구조 | 스키마·에이전트 파일을 올바른 위치에 생성하기 위해 필요 |
