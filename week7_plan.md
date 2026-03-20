# Week 7 Plan — PRD for Real RAG + Real MCP + Platform Prep

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 7주차 |
| **상태** | 🟡 기획 완료 / 구현 대기 |
| **작성일** | 2026-04-18 |
| **목표** | 실동작 RAG와 실제 MCP를 MOA 파이프라인에 붙일 수 있도록 제품 요구사항과 구현 기준을 확정 |

---

## 현재 상태 요약

### 이미 있는 것
- `Router`가 `requires_rag`, `requires_mcp` 플래그를 판정함
- `MOAExecutor`에 RAG/MCP 컨텍스트 주입 포인트가 존재함
- `app/rag/`, `app/mcp_client/` 디렉토리와 최소 mock 테스트가 존재함
- 전체 테스트는 현재 `116 passed` 상태임

### 현재 한계
- RAG는 런타임에서 실제 문서를 인덱싱하지 않아 검색 결과가 비는 상태
- `Embedder`가 실서비스용 임베딩이 아니라 해시 기반 플레이스홀더임
- MCP는 `mock://local` 수준이며, 실제 MCP 프로토콜 세션/서버 연동이 아님
- `run_full.py` 경로에서 `routing` 정보가 실행기로 전달되지 않아 RAG/MCP 플래그가 실효성이 약함
- `week7_implement.md`의 웹 UI 설계는 백엔드 실제 연동이 완성되지 않은 상태를 전제로 함

---

## Week 7 제품 목표

> **MOA 오케스트레이션 실험을 위한 “실제로 동작하는 외부 컨텍스트 계층”을 설계한다.**

이 주차의 핵심은 UI가 아니라 아래 두 축이다.

1. **RAG를 실제 검색 가능한 상태로 만든다**
2. **MCP를 mock이 아닌 실제 도구 호출 구조로 바꾼다**

Week 7의 웹 UI는 위 두 축이 정리된 뒤에 붙는 **표현 레이어**로 본다.

---

## 제품 원칙

### 1. 실험 목적 우선
- 이 프로젝트의 핵심 질문은 여전히 "MOA가 단일 호출보다 실제로 나은가?"이다.
- RAG/MCP는 기능 과시가 아니라 **MOA가 어떤 유형의 외부 컨텍스트에서 강점을 보이는지**를 측정하기 위한 수단이어야 한다.

### 2. 재현성 우선
- 1차 구현은 재현 가능한 로컬 환경에서 돌아가야 한다.
- 네트워크 의존, 브라우저 의존, 가변성이 큰 외부 서비스는 2차 우선순위로 둔다.

### 3. 최소 단위로 검증
- 한 번에 많은 MCP 서버를 붙이지 않는다.
- RAG도 우선은 “실제 검색이 붙는다”를 목표로 하고, 그 다음에 성능 개선을 본다.

### 4. 기존 MOA 구조 유지
- `single` vs `moa` 비교 축은 유지한다.
- RAG/MCP는 MOA 파이프라인의 앞단 컨텍스트 강화 계층으로 붙이고, Draft/Critic/Judge 구조 자체는 보존한다.

---

## C7-0 평가 및 회귀 프로토콜

> Week 7 구현은 기능 추가가 아니라 **비교 실험의 확장**이어야 한다. 따라서 구현 착수 전 평가 축을 먼저 고정한다.

### 참조 기준
- `refs/eval_framework.md`를 Week 7에서도 그대로 기준 문서로 사용한다.
- 품질 지표는 기존 `clarity`, `structure`, `constraint_following`, `usefulness`를 유지한다.
- 시스템 지표는 `total_latency_ms`, `total_tokens`, `total_cost_estimate`, `retry_count`를 유지한다.

### Week 7 비교 축

| 경로 | 목적 | 비고 |
|------|------|------|
| `single` | 단일 호출 baseline | 기존 경로 유지 |
| `moa` | 기존 MOA baseline | 기존 경로 유지 |
| `moa+rag` | 외부 문서 검색이 붙은 MOA | 신규 실동작 검증 |
| `moa+mcp` | 외부 도구 호출이 붙은 MOA | 신규 실동작 검증 |

### 벤치마크 운영 원칙

#### 1. 기존 12건 재실행
- 기존 `data/benchmarks/v1.json` 12건은 Week 7에서도 다시 실행한다.
- 목적은 RAG/MCP 도입 후에도 `single`/`moa` 기존 경로가 회귀하지 않았는지 확인하는 것이다.
- `moa+rag`, `moa+mcp`를 기존 12건에 강제로 적용한 결과는 **진단용**으로만 사용한다.

#### 2. 외부 컨텍스트 전용 케이스 추가
- Week 7의 주된 비교는 기존 12건만으로 충분하지 않다.
- 아래 두 보조 세트를 추가하는 방향을 기본 방침으로 둔다.
  - `rag-*`: 문서 기반 답변이 필요한 케이스 4건 이상
  - `mcp-*`: 도구 호출 없이는 답이 불완전한 케이스 4건 이상
- 최종 비교 표는 `기존 12건 + rag 전용 + mcp 전용`을 묶어서 본다.

#### 3. 해석 원칙
- 기존 12건:
  - `single` vs `moa` 품질/비용/지연 비교
  - `moa+rag`, `moa+mcp`는 회귀/오버헤드 진단
- RAG 전용 케이스:
  - `moa` vs `moa+rag`가 주 비교축
- MCP 전용 케이스:
  - `moa` vs `moa+mcp`가 주 비교축

### Week 7 추가 평가 항목

| 항목 | 적용 대상 | 설명 |
|------|-----------|------|
| `groundedness` | RAG | 검색된 문서 근거를 실제로 반영했는가 |
| `citation_traceability` | RAG | 어떤 청크/문서를 썼는지 추적 가능한가 |
| `tool_use_correctness` | MCP | 적절한 도구를 적절한 인자로 호출했는가 |
| `tool_result_faithfulness` | MCP | 도구 결과를 왜곡 없이 반영했는가 |

### 컨텍스트 인지 평가 인프라

#### 배경
- 현재 `app/eval/rubric.py`는 `prompt + output + constraints`만 judge에게 전달한다.
- 따라서 Week 7에서 추가한 `groundedness`, `citation_traceability`, `tool_use_correctness`, `tool_result_faithfulness`는 **평가 입력 확장 없이는 실제 측정이 불가능**하다.

#### 요구사항
- Week 7부터 평가기는 경로별로 입력 구성이 달라져야 한다.

##### baseline / moa 평가 입력
- 원래 요청
- 제약 조건
- 생성 결과

##### `moa+rag` 평가 입력
- 원래 요청
- 제약 조건
- 생성 결과
- 실제로 주입된 retrieval context
- 선택된 청크 메타데이터
- 출력에 표시된 source label 또는 citation label

##### `moa+mcp` 평가 입력
- 원래 요청
- 제약 조건
- 생성 결과
- 실제 tool call trace
- tool result summary

#### 권장 구현 방향
- `rubric.py`는 단일 프롬프트 빌더가 아니라 경로별 평가 입력을 조립하는 확장 가능한 구조로 바꾼다.
- 최소 인터페이스 예시는 아래와 같다.
  - `evaluate_single(...)`
  - `evaluate_rag(...)`
  - `evaluate_mcp(...)`
- 또는 공통 함수 1개를 유지하되 `evaluation_context`를 명시적으로 받도록 한다.

#### trace 선행조건
- `groundedness`와 `citation_traceability`를 측정하려면 trace에 최소 아래 정보가 남아야 한다.
  - 주입된 청크 원문 또는 요약
  - `doc_id`, `chunk_id`, `source_path`
  - 출력이 사용한 citation label
- `tool_use_correctness`와 `tool_result_faithfulness`를 측정하려면 trace에 최소 아래 정보가 남아야 한다.
  - `server_name`
  - `tool_name`
  - `args`
  - `normalized_result_summary`

#### 해석 원칙
- Week 7 추가 지표는 trace가 없는 경우 채점하지 않는다.
- trace 누락 시 0점을 주는 방식이 아니라 `not_evaluable` 상태로 기록하고, 시스템 결함으로 분리 집계한다.

### 산출물 요구사항
- `compare_runs.py`는 Week 7 이후 아래 그룹 비교를 지원해야 한다.
  - baseline table: `single` vs `moa`
  - rag table: `moa` vs `moa+rag`
  - mcp table: `moa` vs `moa+mcp`
- `docs/06_experiment_log.md` 또는 후속 로그 문서에 Week 7 재실험 결과가 남아야 한다.

## Comparator / compare_runs 확장 명세

### 현재 상태
- 현재 `compare_runs.py`와 `Comparator`는 path 기준 평균 집계만 수행한다.
- 따라서 Week 7 PRD가 요구하는 `baseline table`, `rag table`, `mcp table`을 직접 지원하지 못한다.

### Week 7 요구사항
- `Comparator`는 단순 path 집계를 넘어서 **비교 그룹** 개념을 지원해야 한다.
- 최소 지원 그룹:
  - `baseline`: `single` vs `moa`
  - `rag`: `moa` vs `moa+rag`
  - `mcp`: `moa` vs `moa+mcp`

### 출력 요구사항
- 각 그룹은 최소 아래 필드를 제공한다.
  - `group`
  - `left_path`
  - `right_path`
  - `count`
  - `avg_score_delta`
  - `avg_cost_delta`
  - `avg_latency_delta`
  - `avg_tokens_delta`

### 소유 시점
- 이 확장은 **C7-1**에서 처리한다.
- 이유는 Week 7의 모든 후속 구현이 이 비교 출력 포맷을 기준으로 결과를 적재해야 하기 때문이다.

---

## 비용 추적 확장 명세

### 배경
- 현재 `CostTracker`는 prompt/completion 토큰 비용 중심이다.
- Week 7부터는 임베딩 호출과 MCP 호출 비용/시간도 별도 추적해야 한다.

### 요구사항
- 비용 기록 단위를 최소 아래 4종으로 분리한다.
  - `llm_completion`
  - `embedding`
  - `retrieval`
  - `mcp_tool`
- `embedding`은 모델명, 입력 토큰, 추정 비용을 별도로 기록한다.
- `mcp_tool`은 로컬 Filesystem MCP처럼 직접 비용이 0이어도 latency와 호출 횟수는 기록한다.
- 경로별 합계 외에 `operation_type`별 집계도 가능해야 한다.

### 기대 효과
- "RAG 품질 향상"이 실제로는 임베딩 비용 증가를 감수할 가치가 있는지 평가할 수 있다.
- "MCP 품질 향상"이 실제로는 도구 호출 지연을 얼마나 유발하는지 측정할 수 있다.

---

## RAG PRD

## 목표

> 사용자가 문서 기반 질문을 했을 때, 관련 문서 청크를 실제로 검색하여 MOA 입력에 주입하고, 최종 답변이 그 근거를 반영하도록 만든다.

## 비목표
- 대규모 벡터 검색 서비스 운영
- 다중 컬렉션, 고급 권한 관리
- RAG 자체 최적화가 목적이 되는 별도 제품화

## 권장 설계 결정

### 선택안
- **컬렉션 거리 공간:** Chroma collection을 명시적으로 `cosine` space로 생성
- **임베딩:** OpenAI `text-embedding-3-small`
- **벡터 저장소:** ChromaDB local persistent store
- **문서 소스:** `data/rag_docs/`
- **검색 결과 수:** top-k 5 검색 후, 실제 프롬프트 주입은 상위 2~3개 청크만 사용

### 이 선택을 추천하는 이유
- 현재 프로젝트가 이미 OpenAI 호출 구조를 사용하고 있어 통합 난도가 낮다
- 로컬 임베딩 모델을 추가하는 것보다 의존성과 환경 복잡도가 낮다
- ChromaDB는 로컬 persistent store로 실험 재현성이 좋다
- “실제 semantic retrieval”을 구현하면서도 운영 부담이 낮다
- 거리 공간을 명시적으로 고정해야 relevance 해석과 폴백 기준을 안정적으로 문서화할 수 있다

## RAG 아키텍처

```text
data/rag_docs/*.txt
  -> Chunker
  -> Embedding
  -> Chroma persistent collection

TaskRequest
  -> Router.requires_rag = True
  -> Retriever.query(task.prompt)
  -> ContextBuilder(top chunks + source labels)
  -> MOAExecutor(enriched prompt)
  -> Draft x3 -> Critic -> Judge -> Rewrite -> Synthesizer
  -> Output + citations + trace
```

## 필요한 구성 요소

### 1. 인덱싱 파이프라인
- 문서를 읽어 청크로 분할
- 청크별 메타데이터 저장
- 메타데이터 필수 항목:
  - `doc_id`
  - `source_path`
  - `chunk_id`
  - `title`
  - `char_start`
  - `char_end`

### 2. 조회 파이프라인
- 질의 임베딩 생성
- 벡터 검색 수행
- 상위 청크와 점수를 반환
- 임계치 이하이면 `rag_miss`로 기록하고 일반 MOA로 폴백

### 3. 컨텍스트 빌더
- 검색 결과를 단순 문자열 덤프가 아니라 아래 형식으로 정규화:

```text
[참고 문서 1 | doc3.txt | chunk 2]
...

[참고 문서 2 | doc1.txt | chunk 4]
...
```

- 총 컨텍스트 길이 상한을 둔다
- 중복 정보는 제거한다

### 4. 추적 로그
- 질의어
- 검색된 문서 수
- 선택된 청크 ID
- 유사도 점수
- 최종 주입 토큰 수

## RAG 기본 파라미터

| 항목 | 기본값 | 비고 |
|------|--------|------|
| `chunk_size` | 500 chars | 현재 코드 기본값 유지 |
| `chunk_overlap` | 50 chars | 현재 코드 기본값 유지 |
| `retrieval_top_k` | 5 | 검색 후보 수 |
| `injection_top_k` | 3 | 실제 prompt 주입 청크 수 |
| `min_normalized_relevance` | 0.20 | 이 값 미만이면 `rag_miss` |
| `max_rag_context_tokens` | 1200 | 주입 컨텍스트 상한 |
| `max_total_enrichment_tokens` | 1600 | RAG+MCP 합산 상한 |

### 파라미터 해석 원칙
- Chroma collection은 구현 시점에 반드시 `cosine` distance space로 명시 생성한다.
- Week 7에서는 relevance 변환 공식을 아래처럼 고정한다.

```text
raw_distance: cosine distance in [0, 2]
normalized_relevance = max(0.0, min(1.0, 1.0 - (raw_distance / 2.0)))
```

- trace에는 `raw_distance`와 `normalized_relevance`를 함께 남긴다.
- 폴백 판단은 raw distance가 아니라 normalized relevance 기준으로 한다.
- 이후 컬렉션 metric을 바꾸면 이 공식도 함께 바뀌어야 하며, PRD와 trace schema를 동시에 갱신해야 한다.

## RAG 응답 정책

- Synthesizer 또는 최종 출력은 가능하면 source label을 인용한다
- 1차 버전에서는 Markdown citation까지 강제하지 않고, 최소한 출처 식별자가 trace에 남아야 한다
- 검색 실패 시 “문서 기반 답변”처럼 행동하지 않는다

## RAG 구현 범위

### v1 필수
- 실제 문서 인덱싱
- 실제 semantic retrieval
- 검색 결과 프롬프트 주입
- trace 기록
- RAG 성공/실패 테스트

### v1 제외
- reranker 추가
- hybrid search(BM25 + vector)
- 멀티 컬렉션
- 자동 문서 감시/증분 인덱싱

## RAG 테스트 마이그레이션 전략

### 현재 문제
- 기존 `tests/test_rag.py`는 `SimpleRetriever` 기반의 빠른 단위 테스트다.
- 런타임을 Chroma 기반으로 바꾸면 이 테스트를 단순 치환하는 방식은 회귀 리스크가 크다.

### 방침
- 현재 `SimpleRetriever`는 즉시 삭제하지 않는다.
- 역할을 아래처럼 분리한다.
  - `SimpleRetriever` 또는 `InMemoryRetriever`: 빠른 단위 테스트 및 로컬 폴백용
  - `ChromaRetriever`: 실제 런타임 경로용

### 테스트 분리
- unit:
  - chunker 동작
  - in-memory retriever 로직
  - context builder 정규화
- integration:
  - 문서 인덱싱
  - Chroma persistence
  - 실제 검색 hit
  - Executor 주입

### 마이그레이션 원칙
- "기존 116개 테스트 유지 + 신규 integration test 추가"를 원칙으로 한다.
- 기존 테스트를 깨면서 갈아엎는 방식이 아니라, 런타임 경로만 점진적으로 교체한다.

## RAG 완료 기준 (DoD)

- [ ] `data/rag_docs/` 문서가 로컬 인덱스로 적재된다
- [ ] `requires_rag=True` 케이스에서 검색 hit가 실제로 발생한다
- [ ] Executor가 빈 결과가 아니라 실제 컨텍스트를 주입한다
- [ ] trace에 retrieval metadata가 남는다
- [ ] 관련 테스트가 mock이 아니라 실제 인덱싱 흐름을 검증한다

---

## MCP PRD

## 목표

> MOA 파이프라인이 외부 도구를 실제로 호출할 수 있게 만들어, “모델만으로는 해결이 어려운 과제”를 도구 기반 오케스트레이션으로 처리한다.

## 비목표
- 다수의 MCP 서버를 동시에 복잡하게 관리하는 플랫폼 구축
- 다단계 tool loop 에이전트 시스템
- 브라우저 자동화 중심 제품

## 권장 설계 결정

### 선택안
- **클라이언트 구현:** 공식 `mcp` Python SDK 기반
- **1차 전송 방식:** `stdio` 우선
- **서버 등록 방식:** 명시적 registry 파일 또는 설정 객체
- **1차 호출 제한:** 요청당 최대 1~2회 도구 호출

### 이 선택을 추천하는 이유
- stdio 기반 MCP 서버는 로컬 재현성이 좋고 네트워크 변수에 덜 흔들린다
- 공식 SDK를 사용해야 “실제 MCP”라고 말할 수 있다
- 도구 호출 횟수를 제한해야 실험 비용과 trace 해석이 쉬워진다

## MCP 아키텍처

```text
TaskRequest
  -> Router.requires_mcp = True
  -> ToolPolicy(task_type, prompt, constraints)
  -> MCPClient(session open)
  -> list_tools / call_tool
  -> ToolResultNormalizer
  -> MOAExecutor(enriched prompt)
  -> Draft x3 -> Critic -> Judge -> Rewrite -> Synthesizer
  -> Output + tool trace
```

## 필요한 구성 요소

### 1. 서버 레지스트리
- 서버 이름
- transport 유형
- 실행 command / args
- 허용 tool 목록
- timeout

### 2. 세션 관리자
- 연결 생성/종료
- handshake
- tool 목록 캐시
- 예외 처리

### 3. Tool Policy
- 단순 bool이 아니라 “어느 서버의 어떤 도구를 왜 호출할지”를 결정
- Router는 최소한 아래 수준까지 확장하는 것을 권장:
  - `requires_mcp: bool`
  - `mcp_intent: str | None`
  - `preferred_server: str | None`
  - `preferred_tool: str | None`

### 4. Tool Result Normalizer
- 원시 JSON 결과를 그대로 던지지 않는다
- 모델이 읽기 쉬운 형태로 정리해서 주입:
  - tool name
  - arguments
  - 핵심 결과 요약
  - provenance

### 5. 추적 로그
- 서버명
- tool명
- args
- latency
- success/failure
- result summary

## MCP 기본 파라미터

| 항목 | 기본값 | 비고 |
|------|--------|------|
| `mcp_session_start_timeout_s` | 10 | 세션 연결 상한 |
| `mcp_tool_timeout_s` | 8 | 개별 호출 상한 |
| `max_tool_calls_per_request` | 2 | 1차 구현 제한 |
| `max_tool_result_chars` | 4000 | 주입 전 요약 기준 |
| `max_tool_summary_tokens` | 600 | prompt 주입 상한 |

## Filesystem MCP 보안 경계

### 1차 허용 정책
- **읽기 전용**만 허용
- 허용 루트는 워크스페이스 내부 아래 경로로 제한한다.
  - `docs/`
  - `refs/`
  - `data/rag_docs/`
  - `data/outputs/`
  - `data/traces/`
  - `README.md`
  - `week*_plan.md`
  - `week*_implement.md`

### 명시적 차단 대상
- `.env`
- `.git/`
- `.venv/`
- 워크스페이스 외부 경로
- 사용자 홈 디렉토리 및 Windows 시스템 경로

### Windows 경로 원칙
- 경로 검증은 반드시 resolved absolute path 기준으로 수행한다.
- 심볼릭 링크나 상대 경로(`..`)를 통해 화이트리스트를 우회하지 못하게 한다.

## MCP 호출 정책

- 요청당 최대 2회 호출
- 도구 실패 시 전체 파이프라인을 죽이지 않고 MOA-only로 폴백
- tool 결과가 없는데 있는 척 답하지 않는다
- tool output이 길면 요약 후 주입한다

## MCP 구현 범위

### v1 필수
- 공식 SDK 기반 실제 세션 연결
- 서버 1개 이상 실제 호출 성공
- tool trace 기록
- Executor에 실제 주입

### v1 제외
- 다중 서버 병렬 호출
- 동적 tool planner
- recursive tool loop
- 장기 메모리

## MCP 완료 기준 (DoD)

- [ ] mock이 아닌 실제 MCP 서버에 연결된다
- [ ] `list_tools`, `call_tool`이 실제로 성공한다
- [ ] `requires_mcp=True` 케이스에서 tool result가 prompt에 주입된다
- [ ] tool metadata가 trace에 남는다
- [ ] 실패 시 MOA-only 폴백이 동작한다

---

## 이 프로젝트에 추천하는 MCP 우선순위

## P1. Filesystem MCP

### 추천 이유
- 현재 mock `list_files`와 가장 자연스럽게 이어진다
- 로컬 문서/trace/output을 읽는 과제는 재현성이 높다
- 네트워크 의존이 없고, MOA가 tool grounding을 다루는 방식을 보기 좋다
- Week 7 웹 UI에서도 결과를 설명하기 쉽다

### 적합한 실험 유형
- 특정 문서 읽기
- 디렉토리 목록 확인
- 파일 내용 요약
- trace/log 기반 비교

### 주의점
- 워크스페이스 범위를 벗어나지 않도록 읽기 범위를 제한해야 한다

## P2. Fetch / Web MCP

### 추천 이유
- “현재 정보”나 외부 참조가 필요한 질문에서 MOA + tool 사용 가치를 보여주기 좋다
- RAG와 달리 로컬 문서가 아닌 최신성 문제를 다룰 수 있다

### 적합한 실험 유형
- 최신 정보 확인
- 특정 URL 요약
- 공개 문서 참조

### 주의점
- 재현성이 낮고 네트워크 변수에 영향을 받는다
- 벤치마크 비교에는 불리하고, 데모/플랫폼 성격에는 유리하다

## P3. SQLite 또는 Structured Data MCP

### 추천 이유
- 실험 로그, 평가 결과, run summary를 구조적으로 조회하기 좋다
- 나중에 compare_runs를 인터랙티브하게 확장할 수 있다

### 적합한 실험 유형
- 실행 결과 비교
- 비용/레이턴시 질의
- run metadata 분석

### 주의점
- 현재 저장 구조가 JSON 중심이므로, 1차 우선순위는 아니다

## 권장 결론

> **1차 구현은 Filesystem MCP만 실제화한다.**

그 다음 우선순위는 아래와 같다.

1. `filesystem` MCP
2. `fetch/web` MCP
3. `sqlite/structured-data` MCP

브라우저 자동화, GitHub, shell 실행형 MCP는 현재 실험 목적 대비 범위가 크므로 뒤로 미룬다.

---

## Router / Executor 설계 변경 요구사항

## Router
- 현재의 `requires_rag`, `requires_mcp` bool만으로는 부족하다
- Week 7 구현 전 아래 정보를 추가로 다루는 방향을 권장:
  - `rag_query_hint`
  - `mcp_intent`
  - `preferred_server`
  - `preferred_tool`

## Executor
- 반드시 `routing` 객체를 실제 실행에 전달해야 한다
- RAG 조회와 MCP 호출 결과를 각각 trace에 별도 기록해야 한다
- prompt enrichment는 아래 순서를 권장:
  1. 원래 요청
  2. RAG 컨텍스트
  3. MCP tool result
  4. 이후 MOA 파이프라인 실행

---

## 문서 운영 방침

### `week7_plan.md`
- Week 7의 **소스 오브 트루스**로 사용한다.
- 구현 전에 바뀌어야 하는 범위, 우선순위, 평가 축, DoD를 여기서 확정한다.

### `week7_implement.md`
- 현재 문서는 "웹 UI 선행 구현안" 성격이 강하므로, 즉시 구현 기준 문서로 사용하지 않는다.
- Week 7 구현 시작 전 처리 방침은 아래와 같다.
  - C7-1, C7-2가 끝나기 전까지는 **참고용 초안**으로 유지
  - C7-3 착수 시점에 **웹 UI 전용 구현 명세**로 재작성
- 즉, 폐기보다는 **범위 축소 후 재정렬**이 원칙이다.

---

## Week 7 구현 순서 권장안

> 가드레일 #6에 따라 Week 7 구현 커밋은 **최대 3개**로 제한한다.

### C7-1: 실행선 정리 + 평가/비용 스캐폴딩
- `routing` 전달 수정
- Week 7 비교 프로토콜 반영
- `CostTracker` 확장 명세 반영
- trace schema 확장 준비
- `Comparator` / `compare_runs.py` 그룹 비교 확장
- context-aware rubric 입력 스캐폴딩

### C7-2: 실동작 RAG
- 실제 인덱싱/검색 구현
- `ChromaRetriever` 도입
- retrieval trace 추가
- 테스트 마이그레이션 수행

### C7-3: 실제 MCP 연결 + UI 명세 재정렬
- 공식 SDK 기반 세션 구현
- Filesystem MCP 연동
- tool trace + failure fallback 추가
- `week7_implement.md`를 C7-3 전용 UI 구현 문서로 재작성

---

## 최종 의사결정

### RAG
- **실제 구현 방식:** OpenAI embeddings + Chroma local persist + `data/rag_docs` 기반 검색
- **우선순위:** 즉시 구현 대상

### MCP
- **실제 구현 방식:** 공식 `mcp` Python SDK + stdio transport + Filesystem MCP 1차 도입
- **우선순위:** RAG 다음 단계

### 웹 UI
- **역할:** 플랫폼 레이어
- **선행조건:** RAG/MCP 실행선이 먼저 정상화되어야 함

---

## 한 줄 요약

> Week 7의 본질은 웹 UI가 아니라, **RAG는 실제 검색이 되게 만들고, MCP는 mock이 아니라 실제 도구 호출로 바꾸며, 그 결과를 MOA trace 안에서 비교 가능하게 만드는 것**이다.
