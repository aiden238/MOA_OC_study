# Week 8 Plan — C7-3 Completion + Evaluation Hardening + Runtime Validation

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 8주차 |
| **상태** | 🟡 계획 수립 / 구현 대기 |
| **작성일** | 2026-04-18 |
| **목표** | C7-3 실제 MCP 연결을 완료하고, Week 7의 평가 누락·RAG 실측 부재·문서 정합성 문제를 보정한다 |

---

## 입력 기준

이 문서는 아래 4개를 함께 반영한 보정 계획이다.

- 현재 코드베이스의 실제 구현 상태
- `week7_plan.md`, `week7_c3_implement.md`, `week7_implement.md`
- Codex 검토 결과
- Claude 검토 결과

---

## 현재 확정 사실

### 이미 구현된 것

- `Router`는 `selected_path`, `requires_rag`, `requires_mcp`, `rag_query_hint`, `mcp_intent`, `preferred_server`, `preferred_tool`을 반환한다.
- `run_full.py`는 `routing`을 실제로 `MOAExecutor.execute(..., routing=...)`까지 전달한다.
- `TraceLogger`, `TraceRecord`, `CostTracker`, `Comparator`, `rubric.py`는 Week 7 확장 구조를 일부 반영했다.
- RAG는 `ChromaRetriever` + `OpenAIEmbedder` 기본 경로와 `SimpleRetriever` 폴백 경로를 모두 가진다.
- 전체 테스트는 현재 `132 passed` 상태다.
- Windows 환경에서 `node --version`, `npx.cmd --version`은 통과한다.

### 아직 미완료인 것

- `run_full.py`는 `evaluation_context`를 만들지만 `evaluation`은 아직 `{}`로 저장한다.
- `data/outputs/`에 실환경 `moa+rag` 또는 `moa+mcp` 실행 산출물이 없다.
- MCP는 아직 `mock://local` 기반이며 공식 `mcp` SDK / stdio / whitelist / session manager가 없다.
- `app/orchestrator/planner.py`는 없는데 문서는 여전히 Planner를 핵심 단계로 서술한다.
- `week7_implement.md`는 플랫폼형 UI 명세라기보다 웹 래퍼 초안에 가깝다.

---

## Week 8 핵심 목표

### 1. C7-3 실제 MCP 완료

- 공식 `mcp` Python SDK 도입
- `stdio` transport 기반 Filesystem MCP 연동
- whitelist 경로 정책, read-only 정책, fallback 정책 구현
- `requires_mcp=True` 경로에서 실제 tool result를 prompt enrichment와 trace에 반영

### 2. 평가 파이프라인 실사용 가능 상태로 보정

- `run_full.py` 결과에 실제 `evaluation`을 채운다
- `groundedness`, `citation_traceability`, `tool_use_correctness`, `tool_result_faithfulness`가 path-aware하게 저장되도록 연결한다
- `Comparator`의 group 비교가 빈 형식 출력이 아니라 해석 가능한 출력이 되도록 만든다

### 3. RAG 실측 증거 확보

- OpenAI API 키가 설정된 환경에서 `moa+rag` 케이스를 최소 1건 실제 실행한다
- 아래 증거를 trace / output 파일로 남긴다
  - `retriever = ChromaRetriever`
  - `fallback_reason = null` 또는 비어 있음
  - `selected_count > 0`
  - `path = moa+rag`
  - `normalized_relevance >= 0.20` 청크 존재

### 4. 문서와 코드 정합화

- Planner를 실제 구현할지, Router에 통합된 상태를 문서에 명시할지 결정한다
- `week7_implement.md`는 C7-3 이후 실제 플랫폼/UI 요구사항에 맞춰 재정렬한다
- 테스트 수, 현재 상태, 주차별 진행 현황을 최신화한다

---

## 우선순위 실행 순서

### W8-0. 코드 변경 없는 실측 확인

먼저 현재 코드를 그대로 검증한다.

- `.env`에 `OPENAI_API_KEY` 설정
- `requires_rag=True` 케이스 1건 실행
- `data/outputs/full_*.json`과 `data/traces/*.json` 생성 확인
- 위 실행으로 C7-2의 런타임 증거를 확보한다

이 단계는 코드 수정이 아니라 **현상 파악과 기준선 생성**이다.

### W8-1. 평가 연결 보강

`run_full.py`에서 `evaluation_context`를 실제 평가 호출에 연결한다.

- 권장 기본안: `--evaluate` 플래그 추가
- 대안: 생성 후 후처리 스크립트로 평가 수행

선호안은 `--evaluate`다. 이유:

- 생성 경로와 평가 경로를 분리해 비용/지연 해석을 덜 오염시킨다
- 회귀 테스트에서 `evaluation != {}`를 명시적으로 검증할 수 있다
- API 비용이 큰 환경에서도 평가를 선택적으로 수행할 수 있다

### W8-2. C7-3 실제 MCP 구현

`week7_c3_implement.md`를 실행 계획으로 사용한다.

- `mcp` SDK 의존성 추가
- server registry / session manager 구현
- Filesystem MCP 1차 도입
- whitelist 절대경로 검증
- tool result normalization
- tool trace / fallback 반영

### W8-3. 테스트 보강

- `evaluation`이 비어 있지 않음을 검증하는 회귀 테스트 추가
- MCP whitelist / path validation 테스트 추가
- MCP timeout / session failure fallback 테스트 추가
- `moa+rag`, `moa+mcp` 평가 context 존재 여부 테스트 추가

### W8-4. 문서 보정

- `week7_implement.md`를 C7-3 이후 실제 UI 문서로 재작성
- Planner 관련 문서 정합화
- `week7_Final_check_test.md`의 테스트 수와 상태 최신화

---

## C7-3 구현 세부 계획

### 범위

- `app/mcp_client/`
- `app/orchestrator/executor.py`
- `scripts/run_full.py`
- MCP 관련 테스트
- `week7_implement.md`

### 구현 결정

- 1차는 Filesystem MCP만 실제화
- transport는 `stdio`
- tool 호출 수는 요청당 최대 2회
- 실패 시 `moa` 폴백 유지
- `normalized_result_summary`를 trace와 evaluation context 양쪽에 남긴다

### 필수 trace 메타데이터

- `server_name`
- `tool_name`
- `args`
- `latency_ms`
- `success`
- `normalized_result_summary`
- `fallback_reason`

### 보안 경계

허용:

- `docs/`
- `refs/`
- `data/rag_docs/`
- `data/outputs/`
- `data/traces/`
- `README.md`
- `week*_plan.md`
- `week*_implement.md`

차단:

- `.env`
- `.git/`
- `.venv/`
- workspace 외부 경로
- Windows system path

---

## Week 8에서 보정할 핵심 결함

### A. 평가 누락

- 현재 비교 실험 JSON에 `evaluation`이 비어 있음
- 결과적으로 group comparison은 형식만 있고 해석 가능한 점수 데이터가 없음

### B. RAG 실측 부재

- 코드 경로는 붙어 있지만 실제 OpenAI embedding + Chroma 경로 실행 증거가 없음
- 폴백이 조용히 동작하기 때문에 실환경 검증이 꼭 필요함

### C. MCP 미실장

- 현재는 mock 결과를 문자열로 주입하는 수준
- 실제 MCP 세션/서버/tool trace로 전환해야 함

### D. Planner 문서 괴리

- Planner를 구현하지 않을 경우 문서에서 “Router 통합형 계획 단계”로 명시해야 함
- Planner를 구현할 경우 범위를 최소화해 태스크 분해 역할만 수행해야 함

### E. 테스트 검출력 부족

- 테스트 총량은 충분하지만, `evaluation` 누락 같은 핵심 결함을 못 잡는 상태
- Week 8은 **테스트 수 증가보다 검출력 향상**이 목표다

---

## 산출물

- 실제 `mcp` SDK 기반 Filesystem MCP 연결 코드
- `evaluation`이 채워지는 `run_full.py` 결과 JSON
- `moa+rag` 실측 output/trace 1건 이상
- `moa+mcp` 실측 output/trace 1건 이상
- 업데이트된 `week7_implement.md`
- 문서/코드 정합화 반영

---

## DoD

- [ ] `OPENAI_API_KEY`가 설정된 환경에서 `moa+rag` 실측 output/trace를 남겼다
- [ ] trace에 `retriever=ChromaRetriever` 실환경 hit가 기록됐다
- [ ] `run_full.py` 결과 JSON의 `evaluation`이 실제 채워진다
- [ ] `Comparator` 출력이 `avg_score_delta`까지 포함해 해석 가능하다
- [ ] 공식 `mcp` SDK 기반 Filesystem MCP 연결이 성공한다
- [ ] `requires_mcp=True` 케이스에서 tool result가 trace와 prompt enrichment에 반영된다
- [ ] whitelist / fallback / timeout 테스트가 통과한다
- [ ] Planner 관련 문서/코드 괴리에 대한 처리 방침이 문서화된다

---

## 권장 작업 순서 요약

1. 코드 변경 없이 `moa+rag` 실환경 실행 증거를 먼저 남긴다.
2. 평가 연결을 선택형 실행으로 붙여 `evaluation`을 채운다.
3. C7-3 실제 MCP를 Filesystem 범위로 완성한다.
4. 테스트 검출력을 올린다.
5. UI 문서와 Planner 문서를 실제 코드 상태에 맞게 정리한다.

---

## 한 줄 요약

> Week 8의 목표는 새 기능을 더 넓히는 것이 아니라, **C7-3 실제 MCP를 완성하고, evaluation·RAG 실측·문서 정합성까지 묶어 Week 7 실험 라인을 진짜로 닫는 것**이다.
