# Week 10 C10-1 Implement Guide - Runtime Service Extraction

## 목표

CLI 전용으로 흩어져 있는 실행 로직을 웹/CLI 공용 서비스 계층으로 분리한다.  
이 단계가 끝나면 `scripts/run_full.py`는 orchestration 로직을 직접 들고 있지 않고,  
공용 `chat runtime service`를 호출하는 thin adapter가 되어야 한다.

---

## 범위

- `app/services/chat_service.py` - 신규 생성
- `app/services/__init__.py` - 필요 시 신규 생성
- `app/schemas/chat.py` - 신규 생성
- `scripts/run_full.py` - 리팩터링
- 필요 시 `app/schemas/__init__.py` - export 정리

이 단계에서는 **웹 서버를 아직 만들지 않는다.**  
FastAPI, 세션 저장소, UI는 C10-2 범위다.

---

## 선행 조건

- `AGENTS.md` 숙지
- `week10_plan.md`의 C10-1 섹션 숙지
- `python -m pytest -q`가 현재 기준에서 통과
- `scripts/run_full.py`가 benchmark 기준으로 정상 동작
- `scripts/run_full.py`, `scripts/run_single.py`, `app/orchestrator/executor.py`의 현재 책임 분리를 이해한 상태

---

## 구현 원칙

- 서비스 계층은 CLI와 웹에서 모두 재사용 가능해야 한다.
- 전역 config mutation은 금지한다.
- 기존 trace / evaluation / output metadata 구조는 최대한 유지한다.
- 기존 CLI 옵션 인터페이스는 깨지지 않아야 한다.
- request 1건을 처리하는 표준 entrypoint를 먼저 만든다.

---

## 구현 상세

### A. 서비스 패키지 생성

`app/services/` 디렉토리를 만들고 공용 런타임 진입점을 정의한다.

예상 파일:

```text
app/services/
  __init__.py
  chat_service.py
```

핵심 역할:

- `TaskRequest` 또는 자유 프롬프트를 입력받아 1턴 실행
- path 결정, 실행, trace 저장, evaluation, metadata 조립을 한 곳에서 처리

권장 함수 초안:

```python
async def run_chat_turn(request: ChatTurnRequest) -> ChatTurnResponse:
    ...

async def run_single_task(...):
    ...

async def run_moa_task(...):
    ...
```

### B. chat schema 추가

`app/schemas/chat.py`를 추가해 CLI/웹 공용 request-response 모델을 정의한다.

최소 포함 권장 항목:

- `ChatTurnRequest`
- `ChatTurnResponse`
- `ChatMetrics`
- `SelectedModelInfo`
- `ChatSessionMessage`

`ChatTurnRequest` 최소 필드:

- `prompt`
- `session_id`
- `force_path`
- `evaluate`
- `metadata`

이 단계에서는 `agent_overrides`를 placeholder 수준으로만 넣거나 비워 둘 수 있다.  
실제 모델 선택 로직은 C10-3에서 붙인다.

### C. `run_full.py` 로직 분리

현재 `scripts/run_full.py`에 있는 아래 책임을 서비스 계층으로 이동한다.

- `run_single_path`
- `run_moa_path`
- routing 이후 result 조립
- `context_metadata`, `evaluation_context` 조립
- output 파일 저장 payload 생성

`scripts/run_full.py`에는 아래만 남기는 것을 목표로 한다.

- CLI argument parsing
- benchmark file loading
- case loop
- 서비스 함수 호출
- 결과 출력

즉, `scripts/run_full.py`는 orchestration owner가 아니라 runner adapter가 되어야 한다.

### D. 자유 입력 기반 1턴 실행 추가

benchmark case가 아닌 자유 프롬프트 실행용 path를 추가한다.

예상 흐름:

1. `prompt` 문자열을 받는다.
2. 필요 시 `TaskRequest`로 변환한다.
3. `Router`로 `single` 또는 `moa`를 선택한다.
4. 선택 경로 실행 후 결과를 `ChatTurnResponse`로 묶는다.

초기 버전은 `task_type="explain"` 기본값으로 두고,  
후속 단계에서 세션 히스토리와 입력 메타데이터를 붙인다.

### E. trace / cost / evaluation 표준화

서비스 계층에서 아래를 한 번에 조립하는 helper를 둔다.

- `run_id`
- `path`
- `routing_reason`
- `routing_confidence`
- `prompt_tokens`
- `completion_tokens`
- `cost_estimate`
- `latency_ms`
- `context_metadata`
- `evaluation_context`
- `trace_path`

중요:

- 기존 `CaseResult` 또는 output JSON 구조와 최대한 호환
- 나중에 웹 응답에도 그대로 재사용 가능

### F. CLI 회귀 유지

`scripts/run_full.py`는 기존과 같은 명령이 계속 동작해야 한다.

검증 대상 명령:

```bash
python scripts/run_full.py --benchmark v1.json --case-id sum-001
python scripts/run_full.py --benchmark v1.json --case-id sum-001 --force-path moa
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
```

---

## 권장 구현 순서

1. `app/schemas/chat.py` 추가
2. `app/services/chat_service.py` 생성
3. `run_single_path`, `run_moa_path`를 service로 이동
4. `run_full.py`를 thin adapter로 정리
5. 자유 입력 `run_chat_turn` 직접 호출 테스트

---

## 검증 기준

| 항목 | 기준 |
|---|---|
| 공용 서비스 함수 존재 | `run_chat_turn()` 또는 동등 함수가 import 가능 |
| CLI 회귀 유지 | `scripts/run_full.py` 기존 명령 정상 실행 |
| 자유 입력 실행 가능 | benchmark 없이 prompt 1건 직접 실행 가능 |
| trace 유지 | trace JSON 저장 경로와 records 구조 유지 |
| evaluation 유지 | `evaluate=True` 시 기존 rubric 경로 동작 |

빠른 수동 검증 예시:

```bash
python -c "
import asyncio
from app.schemas.chat import ChatTurnRequest
from app.services.chat_service import run_chat_turn

result = asyncio.run(run_chat_turn(ChatTurnRequest(prompt='MOA 구조를 간단히 설명해줘')))
print(result.path)
print(bool(result.reply))
print(result.trace_path)
"
```

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| `run_full.py` 리팩터링 중 CLI 회귀 발생 | service 함수 이동 범위를 줄이고 wrapper 방식으로 1차 복구 |
| `CaseResult`/`ChatTurnResponse` 구조 충돌 | output 저장용 모델과 웹 응답용 모델을 분리하고 공유 필드만 공통화 |
| routing/evaluation metadata가 service 이동 중 누락 | `run_full.py` 기존 payload와 diff 비교 후 필드별 체크리스트로 보완 |
| import 순환 발생 | service 계층이 `scripts`를 참조하지 않도록 의존 방향을 `app -> scripts`로 고정 |

---

## 커밋

```bash
git add app/services app/schemas/chat.py scripts/run_full.py
git commit -m "refactor(core): extract reusable chat runtime service"
```

---

## 완료 기준 요약

- [ ] `app/services/chat_service.py` 생성
- [ ] `app/schemas/chat.py` 생성
- [ ] `scripts/run_full.py`가 service layer 호출 구조로 정리됨
- [ ] 자유 입력 1턴 실행 가능
- [ ] 기존 CLI 명령 회귀 없음

---

## 권장 커밋 메시지

```text
refactor(core): extract reusable chat runtime service
```
