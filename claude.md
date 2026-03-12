# MOA Orchestration Lab — AI Agent Instructions

> 항상 이 파일을 첨부. 주차 작업 시 `weekN_plan.md` + `weekN_implement.md`도 함께 첨부.

---

## 프로젝트 정체성

**한 줄 정의:** 단일 LLM 호출 → Multi-Agent Orchestration → MCP·RAG 통합까지 6주 단계적 확장 실험

**핵심 질문:** "멀티 에이전트 오케스트레이션이 단일 호출보다 **실제로** 나은가?"

**최종 아키텍처:** `Input → Router → Planner → [RAG/MCP] → Draft×3 → Critic → Judge → (Rewrite) → Synthesizer → Output + Trace`

---

## 가드레일 (8항목)

| # | 제약 조건 |
|---|----------|
| 1 | LangChain / CrewAI / AutoGen 사용 금지 |
| 2 | 1~5주차 동안 모델 단일화 (하나만 사용) |
| 3 | UI 개발 금지 (CLI + JSON 로그만) |
| 4 | 도메인 데이터 지양 (범용 벤치마크만) |
| 5 | RAG·MCP는 6주차에만 (그 전에 도입 금지) |
| 6 | 한 주에 3커밋 초과 금지 |
| 7 | 새 의존성 추가 시 라이선스 확인 필수 (MIT / Apache 2.0만) |
| 8 | 문서 없이 코드만 커밋하지 않기 (문서가 기준, 코드가 증명) |

---

## 커밋 컨벤션

```
<type>(<scope>): <subject>
type: docs | feat | test | fix | refactor | chore
scope: core | schemas | agents | orchestrator | eval | rag | mcp | scripts
```

---

## 진행 상태 추적

| 주차 | 상태 | 핵심 산출물 | 완료일 |
|------|------|------------|--------|
| 1주차 | ✅ 완료 | logger, config, timer, docs/00~02 | 2026-04-17 |
| 2주차 | ✅ 완료 | 스키마 3종, BaseAgent, 프롬프트 파일 | 2026-04-18 |
| 3주차 | ✅ 완료 | 벤치마크 v1, run_single.py, 루브릭 | 2026-03-08 |
| 4주차 | ✅ 완료 | Draft×3, Critic, Synthesizer, run_moa.py | 2026-03-12 |
| 5주차 | 🔲 대기 | Router, Judge, Rewrite, run_full.py | — |
| 6주차 | 🔲 대기 | RAG, MCP, compare_runs.py, 회고 | — |

---

## 세부 지침 파일 (refs/)

| 파일 | 내용 |
|------|------|
| `refs/tech_stack.md` | 허용/금지 의존성, LLM 모델 정책, 라이선스 원칙 |
| `refs/folder_structure.md` | 전체 디렉토리 트리 + 역할 설명 |
| `refs/eval_framework.md` | 품질·시스템 지표, 비교 축, 비용 추정, 평가 프로토콜 |

---

## 주차별 컨텍스트 파일

| 주차 | 계획 (상태·커밋·DoD) | 구현 (코드 설계·참고) |
|------|---------------------|---------------------|
| 1주차 | `week1_plan.md` | `week1_implement.md` |
| 2주차 | `week2_plan.md` | `week2_implement.md` |
| 3주차 | `week3_plan.md` | `week3_implement.md` |
| 4주차 | `week4_plan.md` | `week4_implement.md` |
| 5주차 | `week5_plan.md` | `week5_implement.md` |
| 6주차 | `week6_plan.md` | `week6_implement.md` |

---

## 사용 안내

1. **항상 이 파일(`claude.md`)을 첨부**
2. **현재 주차의 `weekN_plan.md` + `weekN_implement.md`를 함께 첨부**
3. 이전 주차가 ✅ 완료인지 확인 후 작업 시작
4. 세부 스택·구조·평가 정보가 필요하면 `refs/` 파일 참조
5. 작업 완료 후 진행 상태 테이블 업데이트
