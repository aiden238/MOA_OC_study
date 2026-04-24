# Week 10 C10-2 Implement Guide - Web Chat API + Session State

## 목표

C10-1에서 만든 공용 런타임 서비스를 바탕으로  
브라우저에서 프롬프트를 입력하고 응답을 받는 최소 웹 챗 인터페이스를 완성한다.

이 단계의 핵심은 "예쁜 UI"가 아니라 아래 3가지다.

1. 웹에서 1턴 이상 대화 가능
2. 세션별 최근 히스토리 유지
3. `auto`, `single`, `moa` 경로 선택이 실제 실행에 반영

---

## 범위

- `requirements.txt` - `fastapi`, `uvicorn` 추가
- `app/web/server.py` - 신규 생성
- `app/web/__init__.py` - 필요 시 신규 생성
- `app/web/session_store.py` 또는 동등 구조 - 신규 생성
- `app/web/static/index.html` - 신규 생성
- `app/web/static/app.js` - 신규 생성
- `app/web/static/styles.css` - 신규 생성

이 단계에서는 모델 선택 고급 기능을 아직 완성하지 않는다.  
모델 목록/프리셋/API는 C10-3 범위다.

---

## 선행 조건

- **C10-1 완료**
- `app/services/chat_service.py` 기반 1턴 실행 가능
- `python -m pytest -q` 통과 상태 유지
- `python -c "import fastapi, uvicorn"` 가능하도록 의존성 설치

---

## 구현 원칙

- 웹은 CLI 파이프라인을 대체하지 않고 감싼다.
- 세션 저장은 1차에서 메모리 기반으로 충분하다.
- trace 경로와 주요 메트릭은 UI에서도 보여준다.
- 브라우저 요청 실패 시 디버깅 가능한 오류 메시지를 남긴다.
- 초기 UI는 plain HTML/CSS/JS로 제한한다.

---

## 구현 상세

### A. 의존성 추가

`requirements.txt`에 아래 후보를 추가한다.

```text
fastapi>=0.115,<1.0
uvicorn>=0.30,<1.0
```

라이선스 조건:

- `fastapi`: MIT
- `uvicorn`: BSD-3

### B. FastAPI 서버 골격

`app/web/server.py`를 생성하고 최소 엔드포인트를 구성한다.

권장 엔드포인트:

- `GET /health`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `POST /api/chat`
- `GET /` 또는 static index serving

핵심 역할:

- request validation
- session store 호출
- `run_chat_turn()` 호출
- 결과를 JSON으로 반환

### C. 세션 저장소 구현

메모리 기반 저장소를 추가한다.

권장 구조:

```text
app/web/
  session_store.py
```

최소 책임:

- 새 세션 생성
- 세션 조회
- 메시지 append
- 세션 초기화
- 최근 N턴 유지

메시지 최소 필드:

- `role`
- `content`
- `created_at`
- `run_id`
- `path`
- `trace_path`

### D. 히스토리 조합 규칙

웹 요청이 들어왔을 때 대화 히스토리를 prompt에 어떻게 주입할지 명시한다.

권장 1차 규칙:

- 라우터 판단은 현재 턴 중심
- 히스토리는 downstream response generation에만 포함
- 최근 6턴 또는 최대 문자수 제한 적용

예시:

```text
[Conversation History]
user: ...
assistant: ...

[Current User Prompt]
...
```

중요:

- 히스토리 전체를 무조건 라우터에 넣지 않는다.
- RAG/MCP 트리거가 과도하게 발생하지 않도록 현재 턴 우선 규칙 유지

### E. 최소 웹 UI 구현

초기 UI는 아래만 있으면 충분하다.

- 메시지 목록
- 입력 textarea
- send 버튼
- path 선택 (`auto`, `single`, `moa`)
- 현재 응답 메트릭 패널

메트릭 패널 최소 항목:

- `selected path`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `cost_estimate`
- `trace_path`

### F. 오류 처리

다음 오류는 사용자에게 명시적으로 보여준다.

- API key 누락
- provider 호출 실패
- MCP tool 실패
- RAG fallback 발생
- 세션 없음

응답 JSON에 최소 포함 권장:

- `error_code`
- `message`
- `details`

---

## 권장 실행 명령

```bash
python -m uvicorn app.web.server:app --reload
```

서버 기동 후 확인:

```bash
curl http://127.0.0.1:8000/health
```

세션 생성 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/sessions
```

1턴 실행 예시:

```bash
curl -X POST http://127.0.0.1:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"MOA 구조를 설명해줘\",\"force_path\":\"auto\"}"
```

---

## 검증 기준

| 항목 | 기준 |
|---|---|
| 서버 기동 | `uvicorn app.web.server:app` 정상 실행 |
| 세션 생성 | `POST /api/sessions` 성공 |
| 1턴 응답 | `POST /api/chat`에서 reply 반환 |
| 2턴 대화 | 동일 session_id로 연속 요청 시 history 반영 |
| 경로 제어 | `auto`, `single`, `moa` 선택이 응답 path에 반영 |
| trace 노출 | 응답에 `trace_path` 또는 동등 필드 존재 |

브라우저 수동 검증:

- 새 세션 생성
- 일반 질문 1건
- 후속 질문 1건
- `single` 강제 질문 1건
- `moa` 강제 질문 1건

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| FastAPI 서버는 뜨지만 chat 호출 실패 | C10-1 service layer를 직접 호출해 서버 문제인지 런타임 문제인지 분리 |
| 세션 히스토리로 prompt 과대 | 최근 턴 수 제한만 우선 적용하고 요약 메모리는 보류 |
| static file serving 충돌 | UI 파일은 별도 mount 또는 root endpoint inline serving으로 단순화 |
| MCP/RAG 질문에서 latency 과대 | 비스트리밍 1차 버전으로 유지하되 UI에 지연 메트릭 노출 |

---

## 커밋

```bash
git add requirements.txt app/web
git commit -m "feat(core): add web chat api and session state"
```

---

## 완료 기준 요약

- [ ] FastAPI 서버 추가
- [ ] 메모리 기반 세션 저장소 추가
- [ ] `/api/chat`, `/api/sessions` 동작
- [ ] 최소 웹 챗 UI 동작
- [ ] `auto`, `single`, `moa` 경로 선택 가능

---

## 권장 커밋 메시지

```text
feat(core): add web chat api and session state
```
