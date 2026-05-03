# Week 13 Plan — RAG·Knowledge Graph·Wiki 완성 및 안정화

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 13주차 |
| **상태** | 계획 작성 |
| **작성일** | 2026-06-22 |
| **목표** | Week 12에서 기획한 RAG 지식 패널, Knowledge Graph, Self-Updating Wiki를 구현하고 안정화한다. |

---

## 목표

1. `Week 12-1`의 RAG 지식 패널을 실제 웹 UI와 백엔드에 완성하고 회귀 테스트를 통과시킨다.
2. `Week 12-2`의 Knowledge Graph를 실제 API와 D3 시각화로 구현하며, 검색 시 그래프 기반 query expansion을 적용한다.
3. `Week 12-3`의 Self-Updating Wiki를 MVP로 구현하여 수동 후보 제출 → 평가 → 승인 → RAG 재인덱싱까지 동작하도록 만든다.
4. 전체 파이프라인을 통합 검증하고, 문서화 및 주차별 산출물을 정리한다.

---

## 우선순위

1. 핵심 기능 완성: Graph API + Graph UI + Wiki approval flow
2. 검색/검색 품질: graph-augmented RAG retrieval
3. Web UI 통합: knowledge panel + graph + wiki status
4. 테스트/회귀: API + 서비스 + end-to-end 확인
5. 문서화: README, week13_plan.md, week13_implement.md

---

## 세부 작업

### 1. 백엔드 구현

- W13-1-A. `app/rag/knowledge_graph.py` 및 `app/rag/retriever.py` 완성
  - 노드/엣지 JSON 생성 및 저장
  - `/api/knowledge-graph`, `/api/knowledge-graph/neighbors`, `/api/knowledge-graph/highlight` API 구현
  - query expansion을 위한 `expand_query_with_graph()` 함수 완성

- W13-1-B. `app/wiki/pipeline.py` MVP 완성
  - `CollectorAgent` (수동/고정 후보 수집 지원)
  - `EvaluatorAgent` (관련성/신뢰도/중복 검증)
  - `WikiWriterAgent` (YAML 메타데이터 포함 문서 생성)
  - `UpdaterService` (승인 시 `data/rag_docs/` 저장 + 재인덱싱 + graph 갱신)

- W13-1-C. Wiki API 보강
  - `/api/wiki/status`, `/api/wiki/pending`, `/api/wiki/manual-candidate`
  - `/api/wiki/pending/{id}/approve`, `/api/wiki/pending/{id}/reject`
  - 상태 저장소(`data/wiki_state/pending.json`, `changelog.json`) 트랜잭션 보장

### 2. 프론트엔드 구현

- W13-2-A. RAG 지식 패널 완성
  - `/api/rag-knowledge` 호출
  - 사이드바에 카테고리 + 예시 질문 표시
  - 클릭 시 입력창 자동 채우기

- W13-2-B. Knowledge Graph UI 구현
  - D3.js Force-directed 그래프 캔버스
  - 노드 선택 시 관련 문서/개념 정보 표시
  - 검색 시 관련 노드 하이라이트
  - 카테고리 필터 / zoom / pan

- W13-2-C. Wiki 상태 패널 및 승인 UI
  - pending candidate 목록 표시
  - 후보 승인/거부 버튼
  - 최근 승인 이력 및 마지막 업데이트 시각 표시

- W13-2-D. RAG/MCP/graph 상태 통합 표시
  - 응답 시 RAG 소스/graph highlight
  - 경로 배지와 함께 RAG·MCP 사용 여부 시각화

### 3. 검색/평가 통합

- W13-3-A. Graph-augmented retrieval 알고리즘 도입
  - 1~2홉 그래프 확장, 가중치 필터, reranking
  - 직접 매칭 청크 + 이웃 개념 청크 병합

- W13-3-B. Search quality 검증
  - 동일 쿼리에서 기존 RAG 대비 관련도 개선 여부 확인
  - `context_metadata`에 graph usage 메타 추가

### 4. 테스트 및 검증

- W13-4-A. 단위 테스트 추가
  - `test_knowledge_graph.py` 확장
  - `test_wiki_pipeline.py` 추가/완성
  - `test_web_api.py`에 Graph/Wiki API 검증

- W13-4-B. 통합/회귀 테스트
  - 전체 `pytest` 실행 및 통과
  - `scripts/run_full.py --benchmark data/benchmarks/v1_rag_mcp.json`으로 RAG/MCP 샘플 확인
  - `run_full` 결과에서 `path=moa+rag`, `path=moa+mcp` 이상 없음 확인

- W13-4-C. Web UI 수동 검증
  - RAG 지식 패널 로딩 여부 확인
  - 그래프 노드 선택/하이라이트 확인
  - Wiki pending 후보 승인/거부 플로우 확인

### 5. 문서화 및 릴리스 준비

- W13-5-A. `README.md`에 Week 13 주요 추가 사항 반영
- W13-5-B. `week13_implement.md` 작성
- W13-5-C. `docs/06_experiment_log.md`에 Week 13 핵심 결과 요약
- W13-5-D. 커밋 메시지 규칙에 맞춘 변경 기록 작성

---

## 작업 분류

| ID | 작업 | 파일 / 위치 | 예상 완료 순서 |
|---|---|---|---|
| C13-1 | Graph API 및 graph expansion 완성 | `app/rag` | 1 |
| C13-2 | Wiki approval workflow MVP | `app/wiki`, `app/web/server.py` | 2 |
| C13-3 | Knowledge Graph UI 구현 | `app/web/static` | 3 |
| C13-4 | RAG 지식 패널 완성 | `app/web/static` | 3 |
| C13-5 | 검색 품질/graph 활용 검증 | `app/rag`, `tests/` | 4 |
| C13-6 | 테스트/문서 정리 | `tests/`, `README.md`, `week13_implement.md` | 5 |

---

## DoD

- [ ] `/api/rag-knowledge`가 카테고리별 문서 목록과 예시 질문을 반환한다.
- [ ] `/api/knowledge-graph` 및 관련 서브그래프 API가 정상 동작한다.
- [ ] Knowledge Graph가 웹 UI에 시각화되어 노드 클릭/하이라이트가 가능하다.
- [ ] RAG 검색 시 graph-augmented query expansion이 실제로 실행된다.
- [ ] Wiki 후보 수동 제출 → 평가 → 승인 → RAG 재인덱싱이 완료된다.
- [ ] 정적 웹 UI에서 Wiki pending 목록과 최신 승인 이력이 표시된다.
- [ ] `pytest` 전체 통과 또는 기존 주요 테스트 회귀 없음.
- [ ] `README.md` 및 week13 문서가 업데이트되어 구현 범위와 사용법을 명확히 설명한다.

---

## 리스크 및 대응

- 리스크: Graph 확장 도입 후 검색 품질이 저하될 수 있음
  - 대응: 1~2홉 확장에 가중치 필터를 적용하고, 기존 RAG 결과와 A/B 비교를 수행한다.

- 리스크: Wiki 자동화 품질이 불안정할 수 있음
  - 대응: 우선은 `수동 후보 제출 + Human-in-the-Loop 승인` MVP로 시작한다.

- 리스크: Web UI가 복잡해질 경우 유지보수가 어려워짐
  - 대응: UI 컴포넌트를 작게 나누고, `app.js`에 명확한 렌더링 함수 분리.

- 리스크: `data/rag_docs/` 재인덱싱이 느릴 수 있음
  - 대응: 변경된 문서만 재인덱싱하거나, 빠른 인덱싱 모드를 별도 구현.

---

## Week 13 종료 후 기대 산출물

- 완전 동작하는 RAG 지식 패널 + Knowledge Graph UI
- graph-augmented RAG 검색 경로
- Self-Updating Wiki MVP (manual candidate → approve → reindex)
- 통합 테스트/회귀 테스트 통과
- `week13_implement.md`와 관련 문서 정리
