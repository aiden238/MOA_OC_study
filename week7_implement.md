# Week 7 — 웹 UI 구현 지침

> 목표: 기존 CLI 파이프라인을 건드리지 않고, 웹 UI를 추가하여 사용자가 브라우저에서 프롬프트를 입력하면 MOA 파이프라인이 실행되도록 구현

---

## 1. 현재 상태 분석

### 문제점
- 모든 실행이 CLI (`scripts/run_full.py`) + 벤치마크 파일 (`v1.json`) 기반
- 사용자가 자유롭게 프롬프트를 입력하여 MOA를 실행할 수 있는 인터페이스 없음
- 가드레일 #3 "UI 개발 금지"는 6주차까지의 제약 → 7주차부터는 해제

### 재사용 가능한 기존 코드
- `scripts/run_full.py` → `run_single_path()`, `run_moa_path()` 함수를 그대로 호출 가능
- `app/orchestrator/router.py` → `Router.route(task)` 로 경로 자동 결정
- `app/core/cost_tracker.py` → 비용 추적
- `app/core/logger.py` → trace 기록

---

## 2. 기술 스택 선정

| 항목 | 선택 | 이유 |
|------|------|------|
| 웹 프레임워크 | **FastAPI** | async 네이티브, 가볍고 빠름, MIT 라이선스 |
| 프론트엔드 | **Jinja2 + HTMX** 또는 **순수 HTML/JS** | 별도 빌드 도구 불필요 |
| ASGI 서버 | **uvicorn** | FastAPI 표준 서버, BSD 라이선스 |

### requirements.txt 추가 항목
```
# Web UI (Week 7)
fastapi>=0.110.0            # MIT - 웹 API 프레임워크
uvicorn>=0.27.0             # BSD-3 - ASGI 서버
jinja2>=3.1.0               # BSD-3 - HTML 템플릿 (선택)
```

---

## 3. 파일 구조

기존 코드를 **전혀 수정하지 않고** 아래 파일만 추가:

```
MOA_OC_study/
├── app/
│   └── web/                       # ← 새로 추가
│       ├── __init__.py
│       ├── server.py              # FastAPI 앱 정의
│       ├── routes.py              # API 엔드포인트
│       └── templates/
│           └── index.html         # 웹 UI 페이지
├── scripts/
│   └── run_web.py                 # ← 새로 추가: 웹 서버 실행 스크립트
```

---

## 4. API 설계

### 4-1. POST `/api/run` — 프롬프트 실행

**요청:**
```json
{
  "prompt": "인공지능의 미래에 대해 설명해주세요",
  "task_type": "explain",
  "force_path": null,
  "constraints": {}
}
```

**응답:**
```json
{
  "run_id": "20260418_143025_abc123",
  "path": "moa",
  "routing_reason": "explain = 복합 분석 필요",
  "routing_confidence": 0.85,
  "output": "인공지능의 미래는...",
  "agents": ["draft_analytical", "draft_creative", "draft_structured", "critic", "synthesizer", "judge"],
  "agent_count": 6,
  "prompt_tokens": 1200,
  "completion_tokens": 800,
  "latency_ms": 5432.1,
  "cost_estimate": 0.00045,
  "requires_rag": false,
  "requires_mcp": false
}
```

### 4-2. GET `/api/health` — 상태 확인

```json
{
  "status": "ok",
  "model": "gpt-4o-mini",
  "api_key_set": true
}
```

---

## 5. 핵심 구현 코드 가이드

### 5-1. `app/web/server.py`

```python
"""웹 UI 서버 — FastAPI + 기존 파이프라인 연동."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="MOA Orchestration Lab", version="1.0.0")

# 템플릿 경로 설정
templates = Jinja2Templates(directory="app/web/templates")
```

### 5-2. `app/web/routes.py`

```python
"""API 엔드포인트 — 기존 파이프라인 함수 재사용."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.router import Router
from app.schemas.task import TaskRequest

# run_full.py의 함수를 직접 재사용
from scripts.run_full import run_single_path, run_moa_path

router = APIRouter(prefix="/api")

class PromptRequest(BaseModel):
    prompt: str
    task_type: str = "explain"
    force_path: str | None = None
    constraints: dict = {}

@router.post("/run")
async def run_prompt(req: PromptRequest):
    task = TaskRequest(
        prompt=req.prompt,
        task_type=req.task_type,
        constraints=req.constraints,
    )

    run_id = generate_run_id()
    logger = TraceLogger(run_id=run_id)
    cost_tracker = CostTracker()
    moa_router = Router()

    # 경로 결정
    if req.force_path:
        from app.orchestrator.router import RoutingDecision
        decision = RoutingDecision(
            selected_path=req.force_path,
            reason=f"사용자 지정: {req.force_path}",
            confidence=1.0,
        )
    else:
        decision = await moa_router.route(task)

    # 파이프라인 실행
    if decision.selected_path == "single":
        text, outputs = await run_single_path(task, logger, cost_tracker)
    else:
        text, outputs = await run_moa_path(task, logger, cost_tracker)

    logger.save()

    return {
        "run_id": run_id,
        "path": decision.selected_path,
        "routing_reason": decision.reason,
        "routing_confidence": decision.confidence,
        "output": text,
        "agents": [o.agent_name for o in outputs],
        "agent_count": len(outputs),
        "prompt_tokens": sum(o.prompt_tokens for o in outputs),
        "completion_tokens": sum(o.completion_tokens for o in outputs),
        "latency_ms": round(sum(o.latency_ms for o in outputs), 2),
        "cost_estimate": round(sum(o.cost_estimate for o in outputs), 6),
        "requires_rag": getattr(decision, "requires_rag", False),
        "requires_mcp": getattr(decision, "requires_mcp", False),
    }
```

### 5-3. `app/web/templates/index.html`

핵심 구조:
- 프롬프트 입력 텍스트에어리어
- task_type 셀렉트 (summarize / explain / ideate / critique_rewrite)
- force_path 셀렉트 (auto / single / moa)
- 실행 버튼 → `POST /api/run` 으로 fetch 호출
- 결과 영역에 output, 라우팅 경로, 에이전트 목록, 토큰/비용 표시

### 5-4. `scripts/run_web.py`

```python
"""웹 서버 실행 스크립트."""
import uvicorn
from app.web.server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 6. 구현 순서 (커밋 3개 이내)

### C7-1: 웹 서버 + API 엔드포인트
1. `requirements.txt`에 fastapi, uvicorn 추가
2. `app/web/server.py` — FastAPI 앱
3. `app/web/routes.py` — `/api/run`, `/api/health` 엔드포인트
4. `scripts/run_web.py` — 서버 실행 스크립트
5. 기존 코드 수정 없음

### C7-2: 프론트엔드 UI
1. `app/web/templates/index.html` — 프롬프트 입력 폼 + 결과 표시
2. `/` 라우트에서 HTML 제공
3. JavaScript로 `/api/run` 호출 + 결과 렌더링

### C7-3: 테스트 + 문서
1. `tests/test_web.py` — FastAPI TestClient 기반 API 테스트
2. 문서 업데이트

---

## 7. 주의사항

### 기존 코드 변경 금지
- `app/agents/`, `app/orchestrator/`, `app/core/` 등 기존 모듈은 일절 수정하지 않음
- `scripts/run_full.py`의 함수를 **import하여 재사용**만 함
- 웹 UI는 기존 파이프라인을 감싸는 **래퍼 레이어**

### API 키 필수
- `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있어야 실제 작동
- `/api/health`에서 API 키 설정 여부를 확인할 수 있도록 구현
- 미설정 시 명확한 에러 메시지 반환

### 보안 고려
- API 키를 프론트엔드에 노출하지 않음
- 입력 길이 제한 (프롬프트 최대 10,000자)
- Rate limiting 고려 (비용 폭주 방지)

### 라이선스 준수
- FastAPI: MIT ✅
- uvicorn: BSD-3 ✅  
- Jinja2: BSD-3 ✅

---

## 8. 실행 방법 (구현 완료 후)

```bash
# 1. 추가 의존성 설치
pip install fastapi uvicorn jinja2

# 2. .env 파일에 API 키 설정
echo "OPENAI_API_KEY=sk-proj-your-key-here" > .env

# 3. 웹 서버 실행
python scripts/run_web.py

# 4. 브라우저에서 접속
# http://localhost:8000
```

---

## 9. 검증 기준 (DoD)

- [ ] `http://localhost:8000` 접속 시 프롬프트 입력 UI 표시
- [ ] 프롬프트 입력 후 MOA 파이프라인 실행 결과가 화면에 표시
- [ ] Router가 자동으로 single/moa 경로 선택
- [ ] 경로 강제 지정 옵션 동작
- [ ] 토큰 수, 비용, 레이턴시가 결과에 포함
- [ ] 기존 116개 테스트가 그대로 통과
- [ ] 새 웹 API 테스트 추가 및 통과
