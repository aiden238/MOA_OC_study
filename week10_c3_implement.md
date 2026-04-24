# Week 10 C10-3 Implement Guide - Runtime Model Selector and Presets

## 목표

웹 UI와 API에서 모델 선택 기능을 제공한다.  
이 단계가 끝나면 사용자는

- 글로벌 모델 1개를 전체 agent에 적용하거나
- 특정 agent만 override하거나
- preset으로 mixed-provider 구성을 빠르게 선택

할 수 있어야 한다.

---

## 범위

- `app/core/model_registry.py` - 신규 생성
- `app/schemas/chat.py` - 확장
- `app/services/chat_service.py` - request-level override 반영
- `app/web/server.py` - `/api/models` 및 validation 추가
- `app/web/static/app.js` - 모델 선택 UI 추가
- `app/web/static/index.html` - selector/preset 패널 추가
- `app/web/static/styles.css` - 패널 스타일 보강

필요 시:

- `app/services/agent_factory.py` 또는 동등 helper

---

## 선행 조건

- **C10-1 완료**
- **C10-2 완료**
- 웹 API로 1턴 실행과 세션 저장 가능
- 현재 provider 정책이 `OpenAI`, `Gemini`, `Z.AI(Zhipu/GLM)` 기준으로 정리된 상태

---

## 구현 원칙

- env는 기본값 source of truth이고, request override는 해당 요청에만 적용한다.
- 전역 환경 변수를 런타임에 덮어쓰지 않는다.
- UI에는 사용 가능한 모델만 노출한다.
- unavailable provider는 숨기지 말고 disable + 이유 표시를 우선한다.
- trace에는 실제 선택 결과와 fallback 사유를 남긴다.

---

## 구현 상세

### A. 모델 레지스트리 추가

`app/core/model_registry.py`를 생성한다.

최소 역할:

- UI 노출용 모델 목록 정의
- provider capability 정보 제공
- API key 존재 여부 기반 availability 계산
- preset 목록 정의

권장 registry 항목:

- `provider`
- `model`
- `label`
- `category`
- `supports_reasoning`
- `supports_temperature`
- `default_for`
- `available`
- `unavailable_reason`

초기 provider/model 예시:

- OpenAI
  - `gpt-4o-mini`
  - `gpt-5-nano`
  - `gpt-5-mini`
- Gemini
  - `gemini-2.5-flash`
- Z.AI
  - `glm-4.7-flash`

### B. chat schema 확장

`ChatTurnRequest`에 아래 필드를 추가한다.

- `global_model`
- `agent_overrides`
- `preset_id`

예상 구조:

```json
{
  "global_model": {"provider": "openai", "model": "gpt-4o-mini"},
  "agent_overrides": {
    "draft_creative": {"provider": "zai", "model": "glm-4.7-flash"}
  },
  "preset_id": "openai_zai_creative"
}
```

`ChatTurnResponse`에는 아래를 추가한다.

- `selected_models`
- `resolved_provider_map`
- `preset_id`
- `fallback_reasons`

### C. request-level override 해석

서비스 계층에서 override 우선순위를 명시한다.

권장 우선순위:

1. `agent_overrides`
2. `preset_id`가 제공한 agent 설정
3. `global_model`
4. env default

예시:

- 사용자가 글로벌 모델을 OpenAI로 선택
- `draft_creative`만 Z.AI override
- 나머지 agent는 글로벌 값 상속

### D. agent 생성 방식 정리

request-scoped override를 적용할 때는 전역 config mutation이 아니라  
agent 생성 시 constructor override를 넘긴다.

권장 방식:

```python
BaseAgent(
    agent_name="draft_creative",
    provider=resolved_provider,
    model=resolved_model,
    api_key=resolved_api_key,
    base_url=resolved_base_url,
)
```

주의:

- 기존 `resolve_llm_settings()`와 충돌하지 않게 한다.
- request override가 없으면 기존 env 기반 동작을 그대로 유지한다.

### E. preset 설계

최소 4개 preset을 제공한다.

권장 예시:

- `openai_default`
- `low_cost_baseline`
- `openai_gemini_drafts`
- `openai_zai_creative`
- `mixed_research_mode`

각 preset 포함 정보:

- 표시 이름
- 설명
- 글로벌 기본 모델
- agent override map
- 필요한 provider 목록

### F. `/api/models` 추가

서버에서 현재 사용 가능한 모델 목록과 preset 목록을 반환한다.

권장 응답:

```json
{
  "providers": [...],
  "models": [...],
  "presets": [...]
}
```

이 API는 프론트 초기 로딩 시 호출한다.

### G. UI 모델 선택 패널

기본 UI:

- 글로벌 provider 선택
- 글로벌 model 선택
- preset selector

고급 UI:

- agent별 override panel
- `Use global model` 체크박스
- unavailable 모델 disable 처리

대상 agent:

- `router`
- `draft_analytical`
- `draft_creative`
- `draft_structured`
- `critic`
- `synth`
- `judge`
- `rewrite`
- `eval`

### H. trace / metadata 확장

응답과 trace에 아래를 남긴다.

- 사용자가 선택한 설정
- 실제 적용된 설정
- preset id
- provider unavailable/fallback 사유

예상 필드:

```json
{
  "selected_models": {
    "draft_creative": {"provider": "zai", "model": "glm-4.7-flash"}
  },
  "fallback_reasons": {
    "draft_creative": null
  }
}
```

---

## 검증 기준

| 항목 | 기준 |
|---|---|
| `/api/models` | provider/model/preset 목록 반환 |
| global model | 모든 agent에 기본 상속 |
| agent override | 지정 agent만 개별 모델 적용 |
| preset 적용 | preset 선택 후 실제 selected_models 반영 |
| unavailable 처리 | key 없는 provider는 disable 또는 validation error |
| trace 확장 | selected model map이 trace/output metadata에 기록 |

빠른 수동 검증 시나리오:

1. global only - OpenAI
2. global OpenAI + `draft_creative`만 Z.AI
3. preset `openai_zai_creative`
4. key 없는 provider 선택 시 거절 또는 경고

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| provider capability 차이로 호출 실패 | registry에 capability 메타데이터 추가 후 사전 validation 강화 |
| Gemini key는 있으나 quota 문제로 실호출 실패 | `available`과 별도로 `runtime_error`를 UI에 경고 표시 |
| override 해석이 복잡해짐 | `resolve_request_models()` 같은 단일 helper로 우선순위 고정 |
| trace 필드 확장으로 evaluator 충돌 | 기존 필드는 유지하고 새 필드는 metadata 아래에만 추가 |

---

## 커밋

```bash
git add app/core/model_registry.py app/schemas/chat.py app/services app/web
git commit -m "feat(core): add runtime model selector and presets"
```

---

## 완료 기준 요약

- [ ] `app/core/model_registry.py` 생성
- [ ] `/api/models` 동작
- [ ] global model 선택 가능
- [ ] agent override 가능
- [ ] preset 2개 이상 적용 가능
- [ ] selected model 정보가 trace에 기록됨

---

## 권장 커밋 메시지

```text
feat(core): add runtime model selector and presets
```
