# Week 10 Plan - Web Chat UI + Runtime Model Selection

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 10주차 |
| **상태** | 계획 수립 |
| **작성일** | 2026-04-20 |
| **목표** | CLI 중심 실험 파이프라인을 유지하면서 웹 UI 기반 챗봇 인터페이스와 런타임 모델 선택 기능을 추가한다. |

---

## 배경

Week 8~9에서 `single`, `moa`, `moa+rag`, `moa+mcp` 경로는 CLI 기준으로 실주행 검증이 끝났다.  
다음 단계는 이 파이프라인을 사용자가 프롬프트를 직접 입력하는 챗봇 형태로 노출하되, 기존 실험 프로젝트의 성격을 훼손하지 않는 것이다.

Week 10의 핵심 질문은 아래 두 가지다.

1. 현재 CLI 파이프라인을 웹 UI 요청/응답 구조로 안전하게 재사용할 수 있는가?
2. 다른 AI 서비스처럼 모델을 선택하되, 이 프로젝트의 강점인 agent-level mixed-provider 구성을 UI에서도 제어할 수 있는가?

---

## Week 10 원칙

- CLI + JSON trace를 계속 source of truth로 유지한다.
- 웹 UI는 기존 파이프라인을 감싸는 보조 인터페이스로 구현한다.
- LangChain / CrewAI / AutoGen은 계속 사용하지 않는다.
- Streamlit / Gradio는 도입하지 않는다.
- 기본 provider 기준은 계속 `OpenAI`이며, `Gemini`, `Z.AI(Zhipu/GLM)`는 선택 확장으로 취급한다.
- 모델 선택 UI는 provider별 API key가 실제로 설정된 경우에만 활성화한다.
- RAG / MCP / 평가 / trace 저장 규칙은 기존과 동일하게 유지한다.

---

## Week 10 실행 가정

- 기본 LLM provider는 계속 `OpenAI`다.
- 선택 provider는 `Gemini`, `Z.AI(Zhipu/GLM)`다.
- 기본 모델명은 `.env`의 `DEFAULT_MODEL`을 source of truth로 유지한다.
- `glm-4.7-flash`는 reasoning model로 취급하며, `BaseAgent`의 reasoning fallback 규칙을 그대로 재사용한다.
- UI의 모델 목록은 하드코딩이 아니라 `.env` key 존재 여부와 provider capability를 반영해 동적으로 노출한다.
- request-level override는 env를 영구 변경하지 않고, 해당 요청 실행 컨텍스트에만 적용한다.

---

## Week 10 목표 범위

### W10-1. 웹 챗 서비스 레이어 분리

- `scripts/run_full.py`에 섞여 있는 실행 로직을 재사용 가능한 서비스 함수로 분리
- 벤치마크 케이스가 아니라 임의 사용자 프롬프트를 직접 처리하는 `chat turn` 진입점 추가
- 웹 요청에서도 `Router`, `MOAExecutor`, `TraceLogger`, `CostTracker`를 동일하게 사용
- CLI 동작은 깨지지 않도록 유지

### W10-2. 웹 UI 기반 챗봇 인터페이스

- 브라우저에서 프롬프트 입력
- 대화 히스토리 표시
- 응답 결과와 함께 선택된 경로 표시
- `single`, `moa`, `auto` 선택 토글 제공
- 비용, 토큰, latency, trace 요약 표시

### W10-3. 모델 선택 기능

- 일반 사용자용: 상단 단일 모델 선택
- 고급 사용자용: agent별 모델 override 패널
- provider/model 선택 결과를 실제 실행에 반영
- 현재 사용 가능한 모델만 UI에 노출

### W10-4. 다중 모델 선택 / mixed-provider 제어

- Draft 계열을 서로 다른 모델로 분리 선택 가능
- `router`, `critic`, `judge`, `rewrite`, `synth`, `eval`도 개별 선택 가능
- OpenAI + Gemini + Z.AI 혼합 구성을 UI에서 preset으로 선택 가능
- 선택된 구성이 trace와 output metadata에 기록되도록 확장

---

## 권장 구현 구조

### A. 서비스 분리

예상 신규/수정 파일:

- `app/services/chat_service.py`
- `app/schemas/chat.py`
- `app/core/model_registry.py`
- `scripts/run_full.py`

핵심 방향:

- `run_single_path`, `run_moa_path` 같은 현재 실행 함수를 `scripts/` 바깥으로 이동
- `TaskRequest` 기반 단일 요청 실행 함수 추가
- 웹과 CLI가 같은 런타임 함수를 공유

예상 함수 예시:

```python
async def run_chat_turn(
    prompt: str,
    session_id: str | None = None,
    force_path: str | None = None,
    model_profile: dict | None = None,
    evaluate: bool = False,
) -> dict:
    ...
```

### B. 웹 서버

권장 스택:

- `FastAPI` + `uvicorn`
- 프론트는 초기 버전에서 plain HTML/CSS/JS

이유:

- MIT/BSD 계열로 라이선스 조건 충족
- Streamlit/Gradio 금지 규칙과 충돌하지 않음
- 기존 async 파이프라인과 자연스럽게 연결 가능

예상 신규 파일:

- `app/web/server.py`
- `app/web/static/index.html`
- `app/web/static/app.js`
- `app/web/static/styles.css`

### C. 세션/대화 상태

초기 범위:

- 메모리 기반 세션 저장
- 세션별 최근 대화 `N`턴 유지
- 새 대화 / 세션 초기화 기능 제공

후속 확장 여지:

- 세션 JSON 저장
- 최근 세션 복원
- trace 파일과 세션 연결

---

## 모델 선택 기능 설계

### 1. 기본 모드

상단에서 하나의 모델을 고르면 아래에 일괄 적용한다.

- `single`
- `router`
- `draft_*`
- `critic`
- `synth`
- `judge`
- `rewrite`
- `eval`

기본 UX:

- Provider 드롭다운
- Model 드롭다운
- `DEFAULT_MODEL 사용` 옵션

### 2. 고급 모드

에이전트별 override를 개별적으로 설정한다.

대상:

- `SINGLE`
- `ROUTER`
- `DRAFT_ANALYTICAL`
- `DRAFT_CREATIVE`
- `DRAFT_STRUCTURED`
- `CRITIC`
- `SYNTH`
- `JUDGE`
- `REWRITE`
- `EVAL`

예상 UI:

- `Use global model` 토글
- agent별 provider/model 드롭다운
- 미설정 시 글로벌 선택값 상속

### 3. 다중 모델 / mixed-provider preset

초기 preset 예시:

- `OpenAI Default`
- `Fast Cheap`
- `OpenAI + Gemini Drafts`
- `OpenAI + Z.AI Creative`
- `Mixed Research Mode`

원칙:

- key가 없는 provider는 preset 적용 시 비활성 또는 경고 처리
- preset은 실제 env를 덮어쓰는 것이 아니라 request-level runtime override로 동작

### 4. 모델 레지스트리

`app/core/model_registry.py`에서 UI 노출용 모델 목록을 관리한다.

포함 항목:

- provider id
- model id
- 표시 이름
- 용도 태그 (`default`, `fast`, `reasoning`, `creative`, `eval`)
- API key 필요 여부
- 사용 가능 여부

중요:

- `.env`에 key가 없는 provider/model은 `available=false`
- 실제 source of truth는 계속 `.env` + request override 조합으로 유지

---

## API / UI 초안

### API

- `GET /api/models`
  - 현재 사용 가능한 provider/model 목록 반환
- `POST /api/chat`
  - 프롬프트 1턴 실행
- `POST /api/sessions`
  - 세션 생성
- `GET /api/sessions/{session_id}`
  - 대화 이력 조회
- `DELETE /api/sessions/{session_id}`
  - 세션 초기화

### `/api/chat` 요청 초안

```json
{
  "session_id": "optional",
  "prompt": "사용자 입력",
  "force_path": "auto",
  "evaluate": false,
  "global_model": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "agent_overrides": {
    "draft_analytical": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "draft_creative": {"provider": "zai", "model": "glm-4.7-flash"}
  }
}
```

### 응답 초안

```json
{
  "session_id": "abc123",
  "run_id": "run123",
  "reply": "최종 응답",
  "path": "moa+rag",
  "routing_reason": "...",
  "metrics": {
    "latency_ms": 1234,
    "prompt_tokens": 1000,
    "completion_tokens": 500,
    "cost_estimate": 0.0123
  },
  "selected_models": {
    "router": {"provider": "openai", "model": "gpt-4o-mini"},
    "draft_analytical": {"provider": "gemini", "model": "gemini-2.5-flash"}
  },
  "trace_path": "data/traces/....json"
}
```

---

## 세부 구현 단계

| 단계 | 구현 문서 | 권장 커밋 | 핵심 작업 |
|---|---|---|---|
| C10-1 | `week10_c1_implement.md` | `refactor(core): extract reusable chat runtime service` | CLI 실행 로직 서비스화, chat schema 추가 |
| C10-2 | `week10_c2_implement.md` | `feat(core): add web chat api and session state` | FastAPI 서버, 세션, API 엔드포인트 추가 |
| C10-3 | `week10_c3_implement.md` | `feat(core): add runtime model selector and presets` | 모델 레지스트리, 글로벌/에이전트별 선택, preset |
| C10-4 | `week10_c4_implement.md` | `docs(core): document web chat workflow and validation` | README/refs/week10 문서, 테스트, 검증 로그 정리 |

---

## C10 다층 실행 플랜

Week 10은 단일 덩어리 작업이 아니라 아래 4단계 게이트를 순차 통과하는 방식으로 진행한다.  
각 단계는 "선행조건 충족 -> 구현 -> 검증 -> 문서화 -> 다음 단계 진입" 구조를 가진다.

### C10-1. Runtime Service Extraction

#### C10-1 목표

- CLI 전용 실행 코드를 웹/CLI 공용 런타임 서비스로 분리한다.
- 사용자 자유 입력을 처리하는 `chat turn` 진입점을 만든다.
- 이후 단계가 이 서비스 계층만 호출하도록 기준을 잡는다.

#### C10-1A. 서비스 경계 정의

- `scripts/run_full.py`에서 CLI 파서와 실행 로직을 분리한다.
- 공용 런타임 책임을 `app/services/chat_service.py`로 이동한다.
- `single`, `moa`, `auto-routing` 실행 경로를 서비스 함수 기준으로 재정의한다.

예상 작업:

- `run_single_path`, `run_moa_path` 이동 또는 thin wrapper화
- `run_chat_turn(...)`, `build_chat_result(...)` 함수 설계
- CLI는 service call만 수행하는 adapter 형태로 축소

#### C10-1B. 입력/출력 스키마 추가

- `app/schemas/chat.py` 추가
- 웹/CLI 공용 request/response 모델 정의
- `TaskRequest`와 chat schema 간 변환 규칙 명시

예상 스키마:

- `ChatTurnRequest`
- `ChatTurnResponse`
- `ChatSessionMessage`
- `ChatMetrics`
- `SelectedModelInfo`

#### C10-1C. 실행 컨텍스트 표준화

- `TraceLogger`, `CostTracker`, `RoutingDecision`, `evaluation_context` 조립을 서비스 계층으로 집중한다.
- 현재 `run_full.py`에 흩어진 metadata 조립 로직을 재사용 가능 구조로 옮긴다.
- 요청별 `run_id`, `session_id`, `force_path`, `evaluate` 옵션을 서비스 함수에서 일관 처리한다.

#### C10-1D. CLI 회귀 보존

- `scripts/run_full.py`는 기존 CLI 옵션을 그대로 유지한다.
- 내부적으로는 새 서비스 함수 호출만 하도록 변경한다.
- `scripts/run_single.py`, `scripts/run_moa.py`는 즉시 대수술하지 않고, 깨지는 import만 없도록 둔다.

#### C10-1 산출물

- `app/services/chat_service.py`
- `app/schemas/chat.py`
- 수정된 `scripts/run_full.py`

#### C10-1 검증 게이트

- 기존 `python scripts/run_full.py --benchmark v1.json --case-id sum-001` 동작 유지
- 서비스 함수 직접 호출로 단일 프롬프트 1건 처리 가능
- trace/output metadata 구조가 기존 evaluator와 충돌하지 않음

#### C10-1 완료 기준

- CLI와 웹이 같은 런타임 함수를 공유한다.
- `chat turn`을 코드에서 직접 호출할 수 있다.
- 이후 C10-2는 서비스 계층만 의존하고 `scripts/` 로직에 직접 의존하지 않는다.

### C10-2. Web Chat API + Session Layer

#### C10-2 목표

- 브라우저에서 챗봇처럼 프롬프트를 주고받는 최소 동작을 완성한다.
- 세션별 대화 상태를 유지한다.
- 아직 모델 선택 고급 기능 없이도 `auto/single/moa` 토글 기반 실행이 가능해야 한다.

#### C10-2A. FastAPI 서버 골격

- `app/web/server.py` 생성
- `/health`, `/api/chat`, `/api/sessions` 계열 엔드포인트 추가
- static file serving 구성

예상 작업:

- app startup/shutdown 처리
- request validation / error response 규격화
- async service call 연결

#### C10-2B. 세션 상태 저장소

- 메모리 기반 `SessionStore` 또는 동등 구조 추가
- 세션 생성, 조회, 초기화, 최근 N턴 유지 규칙 정의
- 세션 메시지와 `run_id`, `path`, `trace_path` 연결

초기 정책:

- 최근 6~10턴 유지
- 세션 TTL은 일단 미적용 또는 단순 메모리 생존 범위
- 서버 재시작 시 세션 휘발 허용

#### C10-2C. 프롬프트 조합 전략

- 현재 턴 입력과 대화 히스토리를 어떤 규칙으로 합칠지 명시한다.
- 라우터는 기본적으로 현재 턴 중심으로 판단하고, 히스토리는 downstream prompt enrichment에만 쓰는 방식을 우선 검토한다.
- 히스토리 과적재를 막기 위해 최대 문자수 또는 최대 턴 수 제한을 둔다.

#### C10-2D. 최소 웹 UI 셸

- `index.html`, `app.js`, `styles.css` 생성
- 메시지 리스트, 입력창, 전송 버튼, 경로 선택 토글 구현
- 응답 패널에 `path`, `latency`, `cost`, `tokens` 표시

#### C10-2E. 오류 처리 / 운영성

- API key 누락, provider 비활성, RAG/MCP 실패 시 UI 경고 메시지 설계
- 서버 콘솔과 응답 JSON 모두에 디버그 가능한 오류 정보 남기기
- trace 파일 경로를 응답에 포함해 실험 추적성을 유지

#### C10-2 산출물

- `app/web/server.py`
- `app/web/static/index.html`
- `app/web/static/app.js`
- `app/web/static/styles.css`
- 세션 저장 구조

#### C10-2 검증 게이트

- 브라우저에서 2턴 이상 대화 가능
- `auto`, `single`, `moa` 선택이 실제 실행 경로에 반영
- 세션 초기화 후 히스토리 리셋 확인
- trace 파일이 turn마다 생성되거나 연결됨

#### C10-2 완료 기준

- 웹에서 최소 챗 UX가 동작한다.
- 세션 상태가 서버 메모리에 유지된다.
- C10-3은 모델 선택 레이어만 추가하면 되는 상태가 된다.

### C10-3. Runtime Model Selector + Mixed-Provider Control

#### C10-3 목표

- 일반 사용자용 글로벌 모델 선택과 고급 사용자용 agent-level override를 동시에 지원한다.
- 현재 사용 가능한 provider/model만 노출한다.
- mixed-provider preset을 request-level runtime override로 반영한다.

#### C10-3A. 모델 레지스트리

- `app/core/model_registry.py` 생성
- provider/model 목록, capability, 가용성, UI label 정의
- `.env` key 유무를 반영해 `available` 값을 계산한다.

레지스트리 항목 예시:

- `provider`
- `model`
- `label`
- `category`
- `supports_reasoning`
- `supports_temperature`
- `requires_api_key`
- `available`

#### C10-3B. request-level override 구조

- `ChatTurnRequest`에 `global_model`, `agent_overrides`, `preset_id`를 명시적으로 포함한다.
- service layer가 request payload를 runtime settings로 변환하도록 설계한다.
- env는 fallback이고, request override가 우선인 규칙을 문서와 코드에 같이 반영한다.

#### C10-3C. BaseAgent 연동 방식

- 현재 `resolve_llm_settings()`를 손상시키지 않고 request-scoped override를 주입하는 방법을 결정한다.
- 선택지:
  - 서비스 계층에서 각 agent 생성 시 provider/model/base_url/api_key override 전달
  - 또는 context object를 두고 agent factory에서 생성

권장:

- C10에서는 agent factory 또는 service-level constructor override 방식을 우선 채택
- 전역 config mutation은 금지

#### C10-3D. UI 모델 선택 패널

- 글로벌 모델 선택 드롭다운
- agent-level advanced panel
- preset selector
- provider unavailable 시 disable + 이유 표시

#### C10-3E. preset 설계

- `OpenAI Default`
- `OpenAI + Gemini Drafts`
- `OpenAI + Z.AI Creative`
- `Low Cost Baseline`
- `Mixed Research Mode`

각 preset은 다음 정보를 가진다.

- display name
- global default
- agent override map
- 필요 provider 목록
- unavailable 시 경고 메시지

#### C10-3F. trace / metadata 확장

- 응답과 trace에 `selected_models`, `resolved_provider_map`, `preset_id`를 기록
- 실제 실행된 모델과 사용자가 선택한 모델이 다를 경우 fallback 사유를 남긴다.

#### C10-3 산출물

- `app/core/model_registry.py`
- 확장된 `app/schemas/chat.py`
- 수정된 서비스 계층 및 UI 패널

#### C10-3 검증 게이트

- global model 적용 시 모든 agent가 동일 상속
- override 적용 시 해당 agent만 개별 모델 사용
- `Z.AI` reasoning model 선택 시 기존 fallback 규칙이 깨지지 않음
- provider key 미설정 시 UI 비활성 및 request validation 동작
- trace에 selected model map 기록 확인

#### C10-3 완료 기준

- 일반 사용자와 고급 사용자가 모두 모델 선택을 제어할 수 있다.
- mixed-provider preset이 실제 요청 실행에 반영된다.
- 모델 선택 결과가 추적 가능한 metadata로 남는다.

### C10-4. Validation, Docs, and Operator Hardening

#### C10-4 목표

- Week 10 구현 결과를 문서와 테스트까지 포함해 닫는다.
- 회귀 검증과 운영 기준을 남긴다.
- 다음 주차에서 바로 실험 또는 UI 개선으로 넘어갈 수 있게 만든다.

#### C10-4A. 테스트 확장

- service layer 단위 테스트
- session store 테스트
- model registry availability 테스트
- `/api/chat`, `/api/models`, `/api/sessions` API 테스트
- selected model metadata 검증 테스트

#### C10-4B. 수동 검증 시나리오

- OpenAI only
- OpenAI + Z.AI
- RAG 질문
- MCP 질문
- `single`, `moa`, `auto`
- global model only
- global + agent override

각 시나리오에서 확인 항목:

- 응답 정상 여부
- 경로 선택 일치 여부
- trace 생성 여부
- 모델 선택 metadata 일치 여부

#### C10-4C. 문서 동기화

- `README.md`
- `AGENTS.md`
- `claude.md`
- `refs/tech_stack.md`
- `week10_plan.md`
- `week10_c1_implement.md` ~ `week10_c4_implement.md`

동기화 내용:

- 웹 실행 방법
- 새 의존성 설치 방법
- 모델 선택 구조
- preset 정책
- known limitations

#### C10-4D. 운영 가드레일 정리

- 세션 메모리 저장의 한계 명시
- 비스트리밍 1차 버전이라는 점 명시
- provider key 미설정 시 행동 규칙 문서화
- trace/output evidence를 어떤 방식으로 남길지 정리

#### C10-4E. Week 10 마감 산출물

- 구현 문서 4종 정리
- 테스트 통과 기록
- 웹 UI 수동 검증 기록
- known issues 목록
- 다음 주차 backlog 제안

#### C10-4 산출물

- 테스트 코드
- 문서 동기화 결과
- 검증 로그 / 회고 메모

#### C10-4 검증 게이트

- pytest 회귀 통과
- 웹 주요 시나리오 수동 검증 완료
- 문서와 실제 구현이 불일치하지 않음

#### C10-4 완료 기준

- Week 10 결과를 제3자가 읽고 실행할 수 있다.
- 코드, 테스트, 문서, 운영 기준이 함께 닫힌다.

---

## 단계 간 종속성

| 단계 | 선행조건 | 다음 단계로 넘기는 핵심 산출물 |
|---|---|---|
| C10-1 | 기존 CLI 파이프라인 정상 동작 | 공용 chat runtime service |
| C10-2 | C10-1 완료 | 웹 API + 세션형 chat UX |
| C10-3 | C10-2 완료 | 모델 선택 + mixed-provider 제어 |
| C10-4 | C10-1~C10-3 완료 | 테스트/문서/운영 마감 |

---

## 주간 운영 플랜

### 1차 우선순위

- C10-1 완료
- C10-2 최소 동작 완료

### 2차 우선순위

- C10-3 모델 선택 기본 모드
- C10-3 agent override / preset

### 3차 우선순위

- C10-4 테스트 / 문서 / 운영 정리

### 보류 가능 항목

- 스트리밍 응답
- 세션 영속 저장
- 프론트엔드 프레임워크 도입
- 복잡한 인증/사용자 관리

---

## 브로커 대응 순서

1. 공용 런타임 분리가 예상보다 커지면 C10-1에서 service extraction만 우선 닫고 web/server는 다음 커밋으로 넘긴다.
2. provider별 capability 차이로 모델 선택이 불안정하면 C10-3에서 global model only를 먼저 닫고 agent override는 2차로 연다.
3. 세션 히스토리로 prompt가 급격히 커지면 C10-2에서 recent-turn window만 유지하고 요약 메모리는 후순위로 미룬다.
4. UI 작업량이 커지면 HTML/CSS를 최소화하고 API/trace/metrics 노출을 우선한다.

---

## 예상 변경 파일

신규:

- `app/services/chat_service.py`
- `app/schemas/chat.py`
- `app/core/model_registry.py`
- `app/web/server.py`
- `app/web/static/index.html`
- `app/web/static/app.js`
- `app/web/static/styles.css`
- `week10_c1_implement.md`
- `week10_c2_implement.md`
- `week10_c3_implement.md`
- `week10_c4_implement.md`

수정:

- `app/core/config.py`
- `scripts/run_full.py`
- `requirements.txt`
- `README.md`
- `refs/tech_stack.md`
- `AGENTS.md`
- `claude.md`

---

## 예상 의존성

추가 후보:

- `fastapi` (MIT)
- `uvicorn` (BSD-3)

추가하지 않는 것:

- `streamlit`
- `gradio`
- 대형 프론트엔드 프레임워크

---

## 검증 기준

### 기능 검증

- 브라우저에서 프롬프트 입력 후 응답 수신 가능
- `auto`, `single`, `moa` 선택이 실제 실행 경로에 반영됨
- 모델 선택값이 응답 메타데이터와 trace에 기록됨
- 대화 2턴 이상에서 히스토리가 유지됨
- RAG 질문은 웹에서도 `moa+rag`로 동작 가능
- MCP 질문은 웹에서도 `moa+mcp`로 동작 가능

### 모델 선택 검증

- global model 선택 시 모든 agent가 동일 값 상속
- agent override 선택 시 해당 agent만 개별 모델 사용
- key 없는 provider는 선택 불가 또는 명시적 경고 표시
- mixed-provider preset 적용 후 실제 selected_models에 반영

### 회귀 검증

- 기존 `scripts/run_single.py`, `scripts/run_moa.py`, `scripts/run_full.py` 동작 유지
- 기존 pytest 전부 통과
- trace JSON 구조가 기존 evaluator / comparator와 충돌하지 않음

---

## 리스크 / 브로커 조건

| 상황 | 대응 |
|---|---|
| 대화 히스토리 누적으로 prompt가 과대해짐 | 최근 N턴만 유지하고 요약 메모리 도입은 후순위로 둔다 |
| provider별 파라미터 차이로 UI 선택은 되지만 호출 실패 | 모델 레지스트리에 provider capability 메타데이터를 두고 사전 검증 |
| GPT-5 reasoning 계열과 일반 chat 모델이 혼재 | `BaseAgent`의 provider/model capability 판단 로직을 재사용하고 테스트 추가 |
| MCP 호출 지연으로 웹 체감 속도가 저하 | 1차 버전은 비스트리밍으로 두고 latency 표시를 노출 |
| 웹 UI 도입으로 프로젝트 정체성이 흐려짐 | CLI와 JSON trace를 계속 기준으로 유지하고 README에도 명시 |

---

## DoD

- [ ] 웹 UI에서 1턴 이상 대화 가능
- [ ] 세션별 대화 이력이 유지됨
- [ ] `auto`, `single`, `moa` 경로 선택 가능
- [ ] 글로벌 모델 선택 기능 제공
- [ ] agent별 고급 모델 override 제공
- [ ] mixed-provider preset 2개 이상 제공
- [ ] 선택된 모델 구성이 trace/output metadata에 기록됨
- [ ] RAG/MCP 경로가 웹 UI에서도 동작
- [ ] 기존 CLI 실행 및 pytest 회귀 통과
- [ ] README / AGENTS / refs / week10 문서 동기화 완료

---

## 권장 실행 순서

1. C10-1에서 서비스 레이어를 먼저 분리한다.
2. C10-2에서 최소 웹 챗 API와 세션 상태를 붙인다.
3. C10-3에서 모델 선택과 mixed-provider preset을 넣는다.
4. C10-4에서 문서와 테스트를 정리한다.

우선순위는 `웹 UI 모양`보다 `런타임 재사용`, `모델 선택 반영`, `trace 보존`에 둔다.

---

## 변경 기록

### 2026-04-20

- Week 10 계획 문서를 최초 작성했다.
- 웹 UI 챗봇 전환을 CLI 유지 원칙 위에서 진행하는 범위로 정의했다.
- 글로벌 모델 선택, agent-level override, mixed-provider preset을 Week 10 핵심 범위로 포함했다.
