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
- 기본 provider 기준은 계속 `OpenAI`이며, `Gemini`, `Grok(xAI)`는 선택 확장으로 취급한다.
- 모델 선택 UI는 provider별 API key가 실제로 설정된 경우에만 활성화한다.
- RAG / MCP / 평가 / trace 저장 규칙은 기존과 동일하게 유지한다.

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
- OpenAI + Gemini + Grok 혼합 구성을 UI에서 preset으로 선택 가능
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
- `OpenAI + Grok Creative`
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
    "draft_creative": {"provider": "xai", "model": "grok-4"}
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
