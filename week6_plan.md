# Week 6 Plan — MCP·RAG 통합 + 비교 실험 + 회고

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 6주차 |
| **상태** | 🔲 대기 |
| **시작일** | — |
| **완료일** | — |

---

## 이전 주차 산출물 요약

> 5주차에서 완성된 핵심 결과물:

| 산출물 | 검증 상태 | 설명 |
|--------|----------|------|
| `app/agents/judge_agent.py` | ✅ | pass/rewrite/escalate 판정, JSON 출력 |
| `app/agents/rewrite_agent.py` | ✅ | Judge 피드백 기반 재작성 (최대 2회 루프) |
| `app/orchestrator/router.py` | ✅ | Rule-based + LLM hybrid 2단계 라우팅 |
| `app/orchestrator/retry_policy.py` | ✅ | 재시도/폴백 정책 |
| `app/core/cost_tracker.py` | ✅ | 토큰·비용 경로별 집계 |
| `scripts/run_full.py` | ✅ | Router → 자동 분기 → end-to-end 실행 |
| `tests/test_router.py` | ✅ | Router 단위/통합 테스트 통과 |
| `docs/04_routing_rules.md` | ✅ | 라우팅 규칙 명세 |

**전주차 누적 산출물 (1~5주차):**
- ✅ 프로젝트 환경 + 디렉토리 구조 (1주차)
- ✅ config, logger, timer (1주차)
- ✅ Pydantic 스키마 3종 + BaseAgent + 프롬프트 8개 (2주차)
- ✅ 벤치마크 v1 (12건) + run_single.py + 루브릭 (3주차)
- ✅ Draft×3 + Critic + Synthesizer + run_moa.py (4주차)
- ✅ Router + Judge + Rewrite + run_full.py + cost_tracker (5주차)

---

## 이번 주차 목표

> **RAG 파이프라인과 MCP 클라이언트를 통합하고, 4경로 비교 실험을 실행하고, 프로젝트 회고를 작성한다.**

이 주차가 6주 프로젝트의 **마지막 주차**이며, 핵심 질문 "MOA가 실제로 나은가?"에 대한 데이터 기반 답변을 도출한다.

---

## 커밋 계획

### C6-1: RAG 파이프라인 구현 (Day 1~3)

**작업:** 문서 분할(chunker) → 임베딩(embedder) → ChromaDB 저장/검색(retriever) → Draft에 컨텍스트 주입

**산출물:**
- `app/rag/__init__.py`, `app/rag/chunker.py`, `app/rag/embedder.py`, `app/rag/retriever.py`
- `data/rag_docs/` (샘플 문서 5건)
- `tests/test_rag.py`

**커밋 메시지:** `feat(rag): implement RAG pipeline with chromadb retriever`

### C6-2: MCP 클라이언트 + Router 확장 (Day 4~5)

**작업:** MCP 서버 호출 래퍼 구현, Router에 rag/mcp 분기 추가

**산출물:**
- `app/mcp_client/__init__.py`, `app/mcp_client/client.py`
- `docs/08_mcp_rag_integration.md`

**커밋 메시지:** `feat(mcp): implement MCP client and extend router for rag/mcp paths`

### C6-3: 전체 비교 실험 + 회고 (Day 6~7)

**작업:** 4경로 비교 실험 실행, 비교 테이블 생성, 회고 문서 작성

**산출물:**
- `scripts/compare_runs.py`
- `app/eval/comparator.py`
- `docs/06_experiment_log.md`
- `docs/07_retrospective.md`

**커밋 메시지:** `docs(retrospective): run comparison experiments and write retrospective`

---

## 핵심 파일 목록

| 파일 경로 | 역할 | 커밋 |
|-----------|------|------|
| `app/rag/chunker.py` | 문서 분할 | C6-1 |
| `app/rag/embedder.py` | 임베딩 생성 | C6-1 |
| `app/rag/retriever.py` | ChromaDB 기반 벡터 검색 | C6-1 |
| `data/rag_docs/` (5건) | RAG용 샘플 문서 | C6-1 |
| `tests/test_rag.py` | RAG 파이프라인 테스트 | C6-1 |
| `app/mcp_client/client.py` | MCP 서버 호출 래퍼 | C6-2 |
| `docs/08_mcp_rag_integration.md` | MCP/RAG 통합 명세 | C6-2 |
| `scripts/compare_runs.py` | 4경로 비교 실험 스크립트 | C6-3 |
| `app/eval/comparator.py` | 비교 엔진 | C6-3 |
| `docs/06_experiment_log.md` | 실험 로그 | C6-3 |
| `docs/07_retrospective.md` | 프로젝트 회고 | C6-3 |

---

## 완료 기준 (DoD)

- [ ] RAG: 샘플 문서 5건이 ChromaDB에 저장됨
- [ ] RAG: 질의 시 관련 청크 top-3이 정상 검색됨
- [ ] RAG: 검색된 컨텍스트가 Draft Agent의 입력에 주입됨
- [ ] MCP: 최소 1개 MCP 서버에 연결하여 도구 호출 성공
- [ ] Router: `requires_rag`, `requires_mcp` 플래그가 활성화되어 5가지 경로 분기
- [ ] `tests/test_rag.py` 통과
- [ ] `compare_runs.py`가 single / moa / moa+rag / moa+mcp 결과를 비교 테이블로 출력
- [ ] `docs/06_experiment_log.md`에 모든 실험 결과 기록
- [ ] `docs/07_retrospective.md`에 가설 검증·비용 분석·개선 방향 기술
- [ ] `claude.md`의 진행 상태 테이블에 6주차 ✅ 표시

---

## 다음 주차 의존성

> 없음 (최종 주차)

**프로젝트 완료 후 선택적 확장 방향:**
- 멀티 모델 실험 (Router가 모델도 선택)
- 더 큰 벤치마크셋, 도메인 특화 데이터
- UI 레이어 (Streamlit 등)
