# Week 12 — LLM Wiki + Knowledge Graph + RAG 통합 가이드

> **목적**: Week 12에서 추가된 컴포넌트의 역할과, LLM Wiki · Knowledge Graph · RAG 세 레이어가 어떻게 맞물려 동작하는지 설명한다.

---

## 1. Week 12 전체 역할

Week 12는 6주차까지 쌓아온 MOA 파이프라인 위에 **지식 관리 인프라**를 얹는 단계다.  
핵심 목표는 두 가지다.

1. **사용자가 RAG에 무엇이 들어있는지 보이게 한다** — 지식 패널 + 지식 그래프 UI
2. **RAG가 스스로 자라게 한다** — 새 문서를 Wiki 파이프라인으로 수집·검토·승인하면 자동으로 RAG 인덱스에 반영

### 추가된 컴포넌트 한눈에 보기

| 컴포넌트 | 파일 | 한 줄 설명 |
|---|---|---|
| Knowledge Graph 빌더 | `app/rag/knowledge_graph.py` | RAG 문서 → 노드/엣지 그래프 생성 + 쿼리 확장 |
| Wiki 파이프라인 | `app/wiki/pipeline.py` | 새 지식 수집 → 평가 → 승인 → RAG 반영 |
| Wiki 스키마 | `app/schemas/wiki.py` | Pydantic 요청/응답 모델 |
| RAG 지식 카탈로그 API | `app/web/server.py` | `/api/rag-knowledge` — 카테고리별 문서 목록 |
| Knowledge Graph API | `app/web/server.py` | `/api/knowledge-graph`, `/api/knowledge-graph/highlight` 등 |
| Wiki API | `app/web/server.py` | `/api/wiki/status`, `/api/wiki/pending`, `/api/wiki/manual-candidate` 등 |
| Web UI 지식 패널 | `app/web/static/` | 사이드바 — RAG 카탈로그 + D3.js 그래프 + Wiki 상태 |
| Cerebras 통합 | `app/core/config.py`, `model_registry.py` | `draft_creative` 에이전트 → Qwen3-235B (무료) |
| RAG 문서 27개 추가 | `data/rag_docs/doc06~doc31` | 프롬프트·컨텍스트·하네스·고급 기법 주제 |

---

## 2. LLM Wiki + RAG 상호 구성

세 레이어가 순환 구조로 연결된다.

```
┌─────────────────────────────────────────────────────┐
│                   사용자 질문                         │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│          LAYER 1: Knowledge Graph (쿼리 확장)        │
│                                                     │
│  expand_query_with_graph(docs_dir, query)           │
│    ├─ 노드 매칭: 질문 키워드 → 관련 개념 노드 탐색   │
│    ├─ 1-hop 이웃 탐색: 연관 개념/문서 수집           │
│    └─ 확장 쿼리 생성: "원본 질문\nRelated: A, B"    │
└───────────────────────┬─────────────────────────────┘
                        │ expanded_query
                        ▼
┌─────────────────────────────────────────────────────┐
│          LAYER 2: RAG 검색 (ChromaDB)               │
│                                                     │
│  ChromaRetriever.query_items(expanded_query)        │
│    ├─ OpenAI 임베딩으로 벡터 유사도 검색             │
│    ├─ 32개 문서 / 84개 청크 대상                    │
│    └─ 상위 5개 청크 반환 (score ≥ 0.20 필터)        │
│                                                     │
│  ContextBuilder.build(chunks)                       │
│    └─ 상위 3 청크 → "[참고 문서]" 텍스트로 조립      │
└───────────────────────┬─────────────────────────────┘
                        │ rag_context 주입
                        ▼
┌─────────────────────────────────────────────────────┐
│          LAYER 3: MOA 파이프라인 실행               │
│                                                     │
│  Draft×3 (analytical / creative / structured)      │
│    → Critic → Judge → (Rewrite) → Synthesizer      │
│                                                     │
│  draft_creative = Cerebras Qwen3-235B (무료)        │
└─────────────────────────────────────────────────────┘
```

### Wiki 피드백 루프 (RAG 자기성장)

```
새 지식 발견
     │
     ▼
POST /api/wiki/manual-candidate
     │
     ▼
CollectorAgent → EvaluatorAgent (자동 품질 평가)
     │  relevance / credibility / novelty / richness → 총점
     │  총점 ≥ 0.6 → status: "pending"
     │  총점 < 0.6 → status: "rejected"
     ▼
GET /api/wiki/pending  (사람이 목록 확인)
     │
     ├── POST /api/wiki/pending/{id}/reject  → 폐기
     │
     └── POST /api/wiki/pending/{id}/approve
               │
               ├─ data/rag_docs/wiki_*.txt 파일 생성 (YAML 프론트매터 포함)
               ├─ ChromaRetriever.index_directory() 재인덱싱
               └─ Knowledge Graph 스냅샷 갱신 (data/knowledge_graph/)
```

승인 후 다음 RAG 질문부터 새 문서가 검색 대상에 포함된다.

---

## 3. Knowledge Graph 구조

노드와 엣지 타입:

| 노드 타입 | 예시 | 설명 |
|---|---|---|
| `category` | "Prompt Engineering" | 5개 최상위 분류 |
| `document` | "Chain-of-Thought 기법" | RAG 문서 1개 = 노드 1개 |
| `concept` | "chain-of-thought", "reasoning" | 문서에서 추출된 태그/개념 |

| 엣지 관계 | 방향 | 설명 |
|---|---|---|
| `contains` | category → document | 카테고리가 문서를 포함 |
| `implements` | document → concept | 문서가 개념을 구현/설명 |
| `related_to` | document ↔ document | 같은 카테고리 + 공통 태그 |
| `related_to` | concept ↔ concept | 같은 문서에 공존하는 개념 |

현재 규모 (32개 문서 기준):
- 노드 127개 (category 5, document 32, concept 90)
- 엣지 442개

---

## 4. 카테고리 분류

| 카테고리 | 문서 | 파일 패턴 |
|---|---|---|
| Basics | 5개 | doc01~doc05 |
| Prompt Engineering | 7개 | doc06~doc12 |
| Context Engineering | 7개 | doc13~doc18, doc31 |
| Harness Engineering | 7개 | doc19~doc24, doc28_harness |
| Advanced (RAG·MOA·평가·보안·Wiki) | 6개 | doc25~doc30, doc28_token |

---

## 5. Web UI 신규 패널

### 사이드바 (좌측)

```
┌─ RAG 지식 베이스 ─────────────────┐
│  Prompt Engineering (7개)         │
│  • Chain-of-Thought 기법           │
│  💬 "CoT 프롬프팅이란?"  ← 클릭 시 입력창 자동 채워짐
│  Context Engineering (7개)        │
│  ...                               │
├─ Knowledge Graph ─────────────────┤
│  [All Categories ▾]  ← 카테고리 필터
│  D3.js Force-directed Graph       │
│  • 노드 클릭 → 상세 정보 + 관련 질문
└───────────────────────────────────┘
```

### 우측 패널

```
┌─ Wiki Update ─────────────────────┐
│  pending: 0  approved: 0          │
│  최근 승인 항목 5개 표시           │
└───────────────────────────────────┘
```

RAG 경로 실행 후에는 응답 메시지 하단에 **RAG sources 칩**이 표시되고,  
그래프의 관련 노드가 하이라이트된다.

---

## 6. API 엔드포인트 정리

| Method | Path | 설명 |
|---|---|---|
| `GET` | `/api/rag-knowledge` | 카테고리별 문서 카탈로그 |
| `GET` | `/api/knowledge-graph` | 전체 그래프 (nodes + edges + stats) |
| `GET` | `/api/knowledge-graph/neighbors` | 특정 노드의 이웃 서브그래프 |
| `GET` | `/api/knowledge-graph/highlight` | 쿼리 키워드와 매칭되는 노드 목록 |
| `GET` | `/api/wiki/status` | 전체 Wiki 상태 (pending/approved 수) |
| `GET` | `/api/wiki/pending` | 검토 대기 중인 Wiki 후보 목록 |
| `POST` | `/api/wiki/manual-candidate` | 새 Wiki 후보 제출 |
| `POST` | `/api/wiki/pending/{id}/approve` | 후보 승인 → RAG 자동 반영 |
| `POST` | `/api/wiki/pending/{id}/reject` | 후보 거부 |

---

## 7. 파일 구조 (Week 12 신규/수정)

```
MOA_OC_study/
├── app/
│   ├── rag/
│   │   ├── knowledge_graph.py     ★ 신규 — 그래프 빌드 + 쿼리 확장
│   │   ├── retriever.py           수정 — index_directory() async 지원
│   │   └── context_builder.py    (기존 유지)
│   ├── wiki/
│   │   ├── __init__.py
│   │   └── pipeline.py           ★ 신규 — Collector / Evaluator / Writer / UpdateService
│   ├── schemas/
│   │   └── wiki.py               ★ 신규 — ManualWikiCandidateRequest 등
│   ├── orchestrator/
│   │   └── executor.py           수정 — RAG 경로에서 expand_query_with_graph() 호출
│   └── web/
│       ├── server.py             수정 — Knowledge Graph / Wiki API 엔드포인트 추가
│       └── static/
│           ├── index.html        수정 — 지식 패널 / 그래프 캔버스 / Wiki 상태 패널
│           ├── app.js            수정 — D3.js 그래프 / Knowledge Panel / Wiki 렌더링
│           └── styles.css        수정 — 그래프·Wiki 스타일 추가
├── data/
│   ├── rag_docs/
│   │   ├── doc06~doc31.txt       ★ 신규 — 27개 문서 추가 (총 32개)
│   │   └── wiki_versions/        ★ 신규 — 승인된 Wiki 버전 이력
│   ├── wiki_state/
│   │   ├── pending.json          ★ 신규 — Wiki 후보 상태 저장소
│   │   └── changelog.json        ★ 신규 — 승인 이력
│   └── knowledge_graph/
│       ├── nodes.json            ★ 신규 — 그래프 스냅샷 (승인 시 갱신)
│       └── edges.json
├── week12_1_plan.md              Phase 1 구현 지침 (RAG 지식 패널)
├── week12_2_plan.md              Phase 2 기획 (Knowledge Graph D3 시각화)
└── week12_3_plan.md              Phase 3 기획 (Self-Updating Wiki)
```

---

## 8. 실행 흐름 예시

**"Chain-of-Thought 프롬프팅을 어떻게 사용하나요?"** → RAG 경로

```
1. Router: requires_rag = True, rag_query_hint = 질문 원문

2. expand_query_with_graph("chain-of-thought 프롬프팅")
   → 노드 매칭: document_doc08-chain-of-thought (score 0.75)
   → 이웃: concept_reasoning, concept_chain-of-thought
   → expanded_query = "Chain-of-Thought 프롬프팅을 어떻게 사용하나요?
                       Related concepts: reasoning, chain-of-thought"

3. ChromaRetriever.query_items(expanded_query, n_results=5)
   → doc08_chain_of_thought.txt (relevance 0.85)
   → doc07_zero_few_shot.txt (relevance 0.62)
   → doc06_prompt_engineering_basics.txt (relevance 0.55)

4. ContextBuilder: 상위 3청크 → "[참고 문서]" 텍스트 조립

5. MOA: Draft×3 + Critic + Synthesizer → 최종 답변

6. UI: RAG sources 칩 표시 + 그래프에서 doc08 노드 하이라이트
```
