# Week 12-2 Plan — 계층적 지식 그래프 RAG + 웹 UI 그래프 시각화

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 12주차 / Phase 2 |
| **상태** | 기획 완료 🗓️ (구현 대기) |
| **작성일** | 2026-05-02 |
| **목표** | RAG 문서 간의 연결 관계(지식 그래프)를 구축하고, 웹 UI에서 그래프 형태로 시각화한다. 검색 시 연결된 노드까지 함께 조회하여 RAG 품질을 향상시킨다. |

---

## 배경

Phase 1이 "RAG에 무엇이 있는지 보여주는" 패널이었다면,  
Phase 2는 **지식 간의 관계를 시각화하고 검색에 활용**하는 단계다.

현재 RAG의 한계:
- 각 청크는 독립적으로 검색 (문서 간 연결 없음)
- "CoT 프롬프팅"을 검색해도 연관된 "Few-shot"이나 "ReAct" 문서는 나오지 않음
- 사용자가 관련 개념을 탐색할 방법 없음

지식 그래프를 도입하면:
- "CoT" 노드 → 연결된 "Few-shot", "Chain-of-Thought", "ReAct" 노드도 자동 포함
- 사용자가 UI에서 노드를 클릭해 관련 지식 탐색
- 검색 범위가 의미적으로 확장됨

---

## 지식 그래프 구조 설계

### 노드 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| `concept` | 핵심 개념 노드 | "Chain-of-Thought", "컨텍스트 윈도우" |
| `document` | RAG 문서 노드 | "doc08_chain_of_thought.txt" |
| `category` | 카테고리 노드 | "프롬프트 엔지니어링" |
| `technique` | 구체적 기법 노드 | "HyDE", "Sliding Window" |

### 에지(관계) 유형

| 관계 | 방향 | 설명 |
|------|------|------|
| `contains` | category → document | 카테고리가 문서를 포함 |
| `implements` | document → concept | 문서가 개념을 설명 |
| `related_to` | concept ↔ concept | 개념 간 연관 관계 |
| `prerequisite` | concept → concept | A 이해 후 B 이해 가능 |
| `extends` | concept → concept | B가 A를 확장 |

### 그래프 표현 형식

```json
{
  "nodes": [
    {
      "id": "concept_cot",
      "type": "concept",
      "label": "Chain-of-Thought",
      "category": "prompt_engineering",
      "doc_refs": ["doc08_chain_of_thought.txt"]
    },
    {
      "id": "concept_few_shot",
      "type": "concept",
      "label": "Few-shot 프롬프팅",
      "category": "prompt_engineering",
      "doc_refs": ["doc07_zero_few_shot.txt"]
    }
  ],
  "edges": [
    {
      "source": "concept_few_shot",
      "target": "concept_cot",
      "relation": "prerequisite",
      "weight": 0.8
    }
  ]
}
```

---

## 그래프 강화 검색 알고리즘

### 현재 검색 흐름
```
쿼리 → 임베딩 → 유사도 검색 → 상위 5개 청크 → 컨텍스트 주입
```

### Phase 2 검색 흐름
```
쿼리 → 임베딩 → 유사도 검색 → 상위 3개 청크(직접 매칭)
                                     ↓
                          그래프 탐색: 연결된 노드 1~2 홉 확장
                                     ↓
                          관련 노드의 청크 추가 수집 (최대 2개)
                                     ↓
                          관련성 재순위(Reranking) 후 상위 5개 선택
                                     ↓
                          컨텍스트 주입
```

### 그래프 탐색 범위
- **1홉**: 직접 연결된 노드 (가장 높은 관련성)
- **2홉**: 연결된 노드의 연결 노드 (맥락 확장)
- **가중치 필터**: 에지 가중치 < 0.5는 탐색 제외

---

## 웹 UI 지식 그래프 시각화 기획

### 시각화 라이브러리 선택

| 라이브러리 | 장점 | 단점 | 판단 |
|-----------|------|------|------|
| D3.js | 완전 커스텀, 경량 | 구현 복잡 | ⭐ 추천 |
| Vis.js Network | 사용 쉬움, 노드 인터랙션 | 번들 크기 큼 | 대안 |
| Cytoscape.js | 그래프 분석 특화 | 학습 곡선 높음 | 복잡한 경우 |

**결정**: D3.js Force-directed Graph (CDN으로 로드, 의존성 최소화)

### UI 배치 계획

```
[메인 채팅 영역]          [오른쪽 사이드바]
                          ┌─────────────────┐
                          │ 📊 지식 그래프  │
                          │  [그래프 캔버스] │
                          │  ● CoT          │
                          │  ↗             │
                          │ ● Few-shot      │
                          │  ↘             │
                          │  ● ReAct        │
                          ├─────────────────┤
                          │ 선택된 노드 정보│
                          │ 제목: CoT 프롬프│
                          │ 연결: 3개 개념  │
                          │ [이 주제로 질문]│
                          └─────────────────┘
```

### 인터랙션 설계

1. **노드 클릭**: 노드 상세 정보 표시 (우측 패널)
2. **노드 더블클릭**: 해당 문서 내용 미리보기 팝업
3. **노드 우클릭**: "이 주제로 질문하기" 버튼 표시
4. **드래그**: 노드 위치 이동 (Force Layout 재계산)
5. **줌/패닝**: 마우스 휠 줌, 드래그 이동
6. **카테고리 필터**: 상단 필터로 특정 카테고리만 표시
7. **검색 후 강조**: RAG 쿼리 시 사용된 노드를 그래프에서 하이라이트

### 색상 코딩

| 카테고리 | 색상 | HEX |
|---------|------|-----|
| 프롬프트 엔지니어링 | 파란색 | #3B82F6 |
| 컨텍스트 엔지니어링 | 초록색 | #10B981 |
| 하네스 엔지니어링 | 주황색 | #F59E0B |
| 고급 기법 | 보라색 | #8B5CF6 |
| 기초 AI/검색 | 회색 | #6B7280 |

---

## 백엔드 그래프 API 설계

### 엔드포인트

```
GET /api/knowledge-graph
→ 전체 그래프 JSON 반환 (노드 + 에지)

GET /api/knowledge-graph/neighbors?node_id=concept_cot&depth=2
→ 특정 노드의 이웃 노드 반환

GET /api/knowledge-graph/highlight?query=CoT+프롬프팅
→ 쿼리와 관련된 노드 ID 목록 반환
```

### 그래프 저장소

```
data/
  knowledge_graph/
    nodes.json          ← 노드 정의
    edges.json          ← 에지 정의
    category_mapping.json ← 파일명 → 카테고리 매핑
```

---

## 구현 순서 (Phase 2)

| 단계 | 작업 | 예상 소요 |
|------|------|-----------|
| 1 | 그래프 데이터 JSON 수동 작성 (32개 노드) | 2시간 |
| 2 | `/api/knowledge-graph` 엔드포인트 구현 | 1시간 |
| 3 | 그래프 강화 검색 (`retriever.py` 수정) | 3시간 |
| 4 | D3.js 그래프 캔버스 UI 구현 | 4시간 |
| 5 | 인터랙션 (클릭, 강조, 필터) 구현 | 3시간 |
| 6 | RAG 검색 결과와 그래프 연동 (검색 시 노드 하이라이트) | 2시간 |

---

## 선행 조건

- [ ] Week 12-1 완료 (메타데이터 파서 준비)
- [ ] D3.js CDN 라이선스 확인 (BSD 3-Clause ✅)
- [ ] 그래프 데이터 JSON 수동 작성 완료

---

## DoD (Phase 2)

- [ ] `/api/knowledge-graph` 엔드포인트가 전체 노드·에지 반환
- [ ] 웹 UI 사이드바에 인터랙티브 D3.js 그래프 표시
- [ ] 노드 클릭 시 관련 문서 제목과 연결 노드 목록 표시
- [ ] RAG 검색 시 사용된 노드가 그래프에서 하이라이트됨
- [ ] 카테고리 필터 작동
- [ ] 그래프 강화 검색: 직접 매칭 + 인접 노드 확장
