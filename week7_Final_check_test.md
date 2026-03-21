# Week 7 — Final Check & Test Report

> 작성일: 2026-04-18  
> 목적: Week 7 종료 시점 기준으로 실제 코드 상태, 테스트 상태, 미완료 항목을 정리한다.

---

## 1. 전체 테스트 결과

```text
python -m pytest tests -q
137 passed
```

핵심 변화:

- 기존 116개 기준 문서는 더 이상 최신 상태가 아니다.
- 현재는 Week 7 확장 테스트와 MCP/Evaluation 테스트가 추가되어 **137개 테스트**가 통과한다.

### 주요 추가 검증 범위

- `run_full.py`의 `routing` 전달
- `evaluation_context`와 `--evaluate` 저장 경로
- `Comparator`의 baseline / rag / mcp 그룹 비교
- `ChromaRetriever` 경로와 RAG 폴백 경로
- 공식 `mcp` SDK 기반 Filesystem MCP 클라이언트
- MCP whitelist / read-only 정책 / executor 통합

---

## 2. Week 7 구현 상태 판정

| 항목 | 판정 | 근거 |
|------|------|------|
| C7-1 실행선 정리 | ✅ 완료 | `routing` 전달, trace/cost/comparator 구조 반영 |
| C7-1 평가 인프라 | ✅ 1차 완료 | `--evaluate` 플래그로 실제 `evaluation` 저장 가능 |
| C7-2 Chroma RAG 코드 | ✅ 완료 | `ChromaRetriever` + `OpenAIEmbedder` + 폴백 구조 반영 |
| C7-2 실환경 증거 | ⏳ 미완료 | `.env`와 `OPENAI_API_KEY` 부재로 실측 output/trace 없음 |
| C7-3 실제 MCP 코드 | ✅ 1차 완료 | 공식 `mcp` SDK + stdio + Filesystem MCP 연결 |
| C7-3 실환경 full run | ⏳ 미완료 | 실제 `moa+mcp` output/trace 파일은 아직 없음 |
| C7-3 UI 문서 정렬 | ✅ 완료 | `week7_implement.md`를 플랫폼 UI 계약 문서로 재작성 |

---

## 3. 현재 코드 기준 핵심 상태

### 3-1. LLM / 평가

- 기본 모델: `gpt-4o-mini`
- 대체 가격표: `gpt-4o`
- 평가기는 `app/eval/rubric.py`에서 path-aware 추가 항목을 지원한다.
- `scripts/run_full.py --evaluate` 실행 시 결과 JSON의 `evaluation`이 실제 채워진다.

### 3-2. RAG

- 기본 경로: `ChromaRetriever` + `OpenAIEmbedder`
- 폴백 경로: `SimpleRetriever`
- relevance 정규화와 `rag_miss` 기준 존재
- trace에 retrieval/context metadata 기록

### 3-3. MCP

- 공식 `mcp` Python SDK 사용
- `stdio` transport 사용
- 공식 filesystem 서버를 `npx`로 실행
- whitelist 경로 검증, read-only tool 제한, fallback 기록 반영

### 3-4. 문서/구조 괴리

- 문서에는 Planner가 나오지만 실제 코드에는 독립 `Planner` 모듈이 없다.
- 현재 구현은 **Router 통합형 계획 단계 + 고정 MOA 파이프라인**으로 보는 것이 정확하다.

---

## 4. 실제 실행에 필요한 조건

### 필요한 환경

- `.env`
- `OPENAI_API_KEY`
- `node`
- `npx.cmd`
- `mcp` Python SDK

### 현재 확인된 것

- `node --version` 통과
- `npx.cmd --version` 통과
- filesystem MCP 클라이언트 단독 호출 성공

### 아직 남은 것

- `OPENAI_API_KEY`가 설정된 상태에서 `moa+rag` 실측 실행
- `OPENAI_API_KEY`가 설정된 상태에서 `moa+mcp` 실측 실행
- `data/outputs/`와 `data/traces/`에 실환경 산출물 남기기

---

## 5. 현재 웹 UI 상태

### 결론: 아직 코드로는 미구현

- `app/web/` 없음
- `scripts/run_web.py` 없음
- 브라우저 UI 없음

하지만 문서 상태는 바뀌었다.

- `week7_implement.md`는 더 이상 “웹 서버를 당장 추가하자”는 초안이 아니다.
- 이제는 **현재 MCP/RAG/evaluation 백엔드를 감싸는 플랫폼 UI 계약 문서** 역할을 한다.

---

## 6. Week 7 종료 시점 파일 기준 요약

### 핵심 코드 파일

- `app/orchestrator/router.py`
- `app/orchestrator/executor.py`
- `app/rag/retriever.py`
- `app/rag/embedder.py`
- `app/mcp_client/client.py`
- `scripts/run_full.py`
- `app/eval/rubric.py`
- `app/eval/comparator.py`

### 핵심 문서

- `week7_plan.md`
- `week7_c1_implement.md`
- `week7_c2_implement.md`
- `week7_c3_implement.md`
- `week7_implement.md`
- `week8_plan.md`

---

## 7. 남은 후속 작업

Week 7 종료 시점 기준으로 남은 것은 “코드가 없다”가 아니라 **실측 증거와 문서 정합화 마무리**다.

### 우선순위

1. `OPENAI_API_KEY` 설정 후 `moa+rag` 실측 output/trace 남기기
2. `OPENAI_API_KEY` 설정 후 `moa+mcp` 실측 output/trace 남기기
3. Planner 괴리를 문서에서 명시적으로 정리하기
4. 필요 시 UI 실제 구현을 Week 8 이후 범위로 진행하기

---

## 8. 한 줄 결론

> Week 7은 이제 “MCP mock 단계”가 아니라, **RAG는 코드 완료·실측 대기, MCP는 1차 실제화 완료·full run 실측 대기** 상태다.
