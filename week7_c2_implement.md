# Week 7 C7-2 Implement Guide

## 목표

Week 7의 두 번째 단계로 실동작 RAG를 연결한다.

- `ChromaRetriever`를 런타임 기본 경로로 도입
- 실제 문서 인덱싱과 검색 결과 주입 구현
- relevance 임계치 미달 시 `rag_miss` 폴백 동작 보장

## 범위

- `app/rag/` 하위 모듈
- `app/orchestrator/executor.py` (`requires_rag=True` 경로에서 `ChromaRetriever` 호출)
- `.gitignore`
- `tests/test_rag.py`

## 선행 조건

- C7-1이 먼저 완료되어 routing / trace / result schema가 준비되어 있어야 한다.
- `data/rag_docs/`에 실제 문서가 있어야 한다.

## 핵심 결정

### 1. Retriever 우선순위

- 기본: `ChromaRetriever`
- 예외: 초기화 실패, 인덱스 없음, 임베딩 실패 시 `SimpleRetriever` 폴백

폴백 발생 시 trace metadata에 `fallback_reason`을 남긴다.

### 2. 저장 경로

- 런타임 persistent store: `data/chroma/`
- integration test store: `tmp_path` 사용

`data/chroma/`는 `.gitignore`에 추가한다.

### 3. relevance 공식

Chroma collection은 `cosine` distance space로 고정한다.

```text
raw_distance: cosine distance in [0, 2]
normalized_relevance = max(0.0, min(1.0, 1.0 - (raw_distance / 2.0)))
```

폴백 판단은 `normalized_relevance` 기준으로 한다.

## 구현 상세

### A. 시작 전 검증

- `data/rag_docs/` 존재 여부 확인
- 비어 있는지 확인
- placeholder 수준 문서만 있는지 점검

### B. 인덱싱 파이프라인

- 문서 로드
- chunking
- embedding
- Chroma persistent collection 적재

필수 메타데이터:

- `doc_id`
- `source_path`
- `chunk_id`
- `title`
- `char_start`
- `char_end`

### C. 조회 파이프라인

- `retrieval_top_k=5`
- `injection_top_k=3`
- `min_normalized_relevance=0.20`
- `max_rag_context_tokens=1200`
- `max_total_enrichment_tokens=1600`

### D. ContextBuilder

검색 결과를 아래 형식으로 정규화한다.

```text
[참고 문서 1 | doc3.txt | chunk 2]
...

[참고 문서 2 | doc1.txt | chunk 4]
...
```

### E. rag_miss 폴백

- 검색 결과 없음
- relevance 임계치 미달
- retriever 초기화 실패

위 경우에는 일반 MOA로 폴백하고 trace에 `rag_miss`와 이유를 남긴다.

## 테스트 계획

- `tests/test_rag.py`: `SimpleRetriever` 기존 unit test 유지
- `tests/test_rag.py`: `ChromaRetriever` integration test 추가
- 인덱싱 / persistence / hit retrieval / executor enrichment 테스트 추가
- integration test는 `tmp_path` 기반 격리 저장소만 사용
- `.gitignore`에 `data/chroma/`가 추가되었는지 확인

## DoD

- RAG integration tests 통과
- 기존 회귀 없음
- retrieval context가 실제로 prompt에 주입됨
- `rag_miss` 폴백이 동작함
- `data/chroma/`가 git 추적 대상에서 제외됨

## 중단 조건

- `data/rag_docs/`가 비어 있거나 실험 가치가 없는 문서만 있을 때
- embedding API 접근이 불가할 때
- `chromadb` 설치 또는 라이선스가 프로젝트 정책과 충돌할 때

## 권장 커밋 메시지

```text
feat(rag): implement chroma retriever and real rag pipeline
```
