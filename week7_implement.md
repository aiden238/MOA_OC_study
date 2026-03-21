# Week 7 Implement Guide — C7-3 Actual MCP + Platform UI Reframe

> 목적: Week 7의 남은 구현을 **실제 MCP 연결** 기준으로 마감하고, `week7_implement.md`를 더 이상 “웹 UI 선행 초안”이 아니라 **현재 백엔드 상태를 전제로 한 플랫폼 UI 명세**로 재정렬한다.

---

## 1. 현재 구현 상태

### 이미 완료된 백엔드 축

- `run_full.py`는 `Router`의 `routing` 정보를 실제 실행선까지 전달한다.
- `run_full.py`는 `--evaluate` 플래그로 path-aware 평가를 저장할 수 있다.
- RAG는 `ChromaRetriever` + `OpenAIEmbedder` 기본 경로와 `SimpleRetriever` 폴백 경로를 가진다.
- MCP는 공식 `mcp` Python SDK + `stdio` 기반 Filesystem MCP v1 코드가 반영되어 있다.
- `mcp_tool` trace와 `normalized_result_summary` 기록 구조가 존재한다.

### 아직 없는 것

- 실제 웹 서버 코드 (`app/web/`, `scripts/run_web.py`)
- 브라우저 UI
- OpenAI API 키가 설정된 환경에서 남겨진 실환경 `moa+rag`, `moa+mcp` 산출물

즉, **Week 7의 남은 본질은 UI 구현이 아니라 MCP 연동 완료를 플랫폼 UI 관점에서 문서화하는 것**이다.

---

## 2. 문서 역할 재정의

이 문서는 더 이상 “지금 바로 FastAPI를 추가하자”는 선행 구현안이 아니다.

이제의 역할은 아래와 같다.

1. 현재 CLI/trace 중심 백엔드를 **어떤 UI 계약**으로 감쌀지 정의한다.
2. 실제로 존재하는 RAG/MCP/evaluation 구조를 **UI에서 어떤 데이터로 보여줄지** 정리한다.
3. 추후 `app/web/` 구현 시, 기존 파이프라인을 다시 설계하지 않고 **표현 레이어만 추가**하도록 기준을 고정한다.

---

## 3. UI 구현 원칙

### 원칙 1. 백엔드를 새로 만들지 않는다

- UI는 `scripts/run_full.py`와 동일한 실행 의미를 가져야 한다.
- Router / MOA / RAG / MCP / Evaluation 로직은 기존 코드 재사용이 원칙이다.
- UI는 파이프라인을 대체하지 않고 **관찰·실행·비교를 돕는 레이어**여야 한다.

### 원칙 2. trace-first

- 사용자가 가장 먼저 봐야 하는 것은 “예쁜 답변”이 아니라 **어떤 경로로 실행됐는지**다.
- `path`, `routing_reason`, `requires_rag`, `requires_mcp`, `selected_chunks`, `tool_trace`를 결과와 함께 보여줘야 한다.

### 원칙 3. 실험 비교 가능성 유지

- UI는 단일 실행 데모가 아니라 `single`, `moa`, `moa+rag`, `moa+mcp`를 비교할 수 있어야 한다.
- 비용/토큰/지연/평가를 한 화면에서 같이 읽을 수 있어야 한다.

### 원칙 4. Planner는 당장 새로 만들지 않는다

- 현재 코드에는 독립 `Planner` 모듈이 없다.
- UI 문서에서도 Planner를 별도 API나 패널로 가정하지 않는다.
- 필요한 경우 “Router 통합형 계획 단계”로 표기한다.

---

## 4. 권장 UI 범위

### Phase A. 실행 콘솔 UI

최소 기능:

- 프롬프트 입력
- `task_type` 선택
- `force_path` 선택
- `evaluate` on/off
- 실행 결과 텍스트 표시
- 실행 메타데이터 표시

표시해야 할 메타데이터:

- `path`
- `routing_reason`
- `routing_confidence`
- `prompt_tokens`
- `completion_tokens`
- `latency_ms`
- `cost_estimate`
- `agent_count`
- `agents`

### Phase B. 컨텍스트 패널

RAG/MCP가 붙은 경우 아래를 별도 패널로 표시한다.

RAG:

- `retrieval_context`
- `selected_chunks`
- `doc_id`
- `chunk_id`
- `source_path`
- `normalized_relevance`

MCP:

- `server_name`
- `tool_name`
- `args`
- `success`
- `normalized_result_summary`
- `fallback_reason`

### Phase C. 비교/실험 패널

- 저장된 `data/outputs/*.json` 기반 실행 비교
- `baseline`, `rag`, `mcp` 그룹 비교 테이블
- `avg_score_delta`, `avg_cost_delta`, `avg_latency_delta`, `avg_tokens_delta` 표시

---

## 5. API/서비스 계약

UI를 구현할 때 필요한 최소 서비스 계약은 아래와 같다.

### 5-1. 실행 요청 계약

입력:

```json
{
  "prompt": "docs 폴더 파일 목록을 보여줘",
  "task_type": "explain",
  "force_path": null,
  "constraints": {},
  "evaluate": true
}
```

출력:

```json
{
  "run_id": "abc123",
  "path": "moa+mcp",
  "routing_reason": "프롬프트에 외부 도구 필요 키워드 포함 → MCP 필요",
  "routing_confidence": 0.9,
  "output": "최종 응답",
  "agents": ["draft_analytical", "draft_creative", "draft_structured", "critic", "synthesizer", "judge"],
  "agent_count": 6,
  "prompt_tokens": 1200,
  "completion_tokens": 700,
  "latency_ms": 4200.0,
  "cost_estimate": 0.0005,
  "evaluation": {
    "avg_score": 4.25
  },
  "evaluation_context": {
    "tool_trace": {
      "server_name": "filesystem",
      "tool_name": "list_directory"
    },
    "tool_result_summary": "[MCP Server] filesystem ..."
  },
  "context_metadata": {
    "routing": {
      "requires_rag": false,
      "requires_mcp": true
    },
    "mcp": {
      "server_name": "filesystem",
      "tool_name": "list_directory"
    }
  }
}
```

### 5-2. 상태 확인 계약

`/api/health` 수준에서 최소 아래를 확인 가능해야 한다.

- API 키 존재 여부
- 기본 모델
- `mcp` SDK 설치 여부
- filesystem MCP 실행 가능 여부

---

## 6. 실제 구현 시 파일 구조 권장안

현재는 문서만 정의하고, 구현 시 아래 구조를 권장한다.

```text
app/
  web/
    __init__.py
    server.py
    routes.py
    templates/
      index.html
      run_detail.html
      compare.html
scripts/
  run_web.py
```

주의:

- `app/web`는 표현 계층만 가진다.
- 기존 `app/orchestrator`, `app/agents`, `app/rag`, `app/mcp_client` 로직을 재구현하지 않는다.

---

## 7. 구현 시 필수 반영사항

### 7-1. 실행 경로

- `run_moa_path()` 호출 시 반드시 `routing=decision`을 전달해야 한다.
- 그렇지 않으면 `requires_rag`, `requires_mcp`가 UI 경로에서 무력화된다.

### 7-2. 평가

- 평가 실행은 기본 on이 아니라 **선택형**이 안전하다.
- 이유:
  - 추가 LLM 호출 비용 발생
  - 생성 경로와 평가 경로를 분리해야 지연시간 해석이 쉬움

권장:

- UI에 `평가 포함` 체크박스 제공
- 내부적으로는 `--evaluate` 또는 동일 옵션으로 연결

### 7-3. MCP 보안

- UI에서 임의 경로 입력을 직접 받지 않는다.
- 파일 읽기 요청은 Router/MCP policy가 결정한 안전한 요청만 허용한다.
- `.env`, `.git`, `.venv`, workspace 외부 경로는 노출하지 않는다.

### 7-4. 실험 파일 조회

- 비교 화면은 `data/outputs/`와 `data/traces/`만 읽는다.
- 직접 DB를 도입하지 않는다.

---

## 8. DoD

- [ ] UI 문서가 현재 백엔드 구조와 모순되지 않는다
- [ ] `routing`, `evaluation`, `rag`, `mcp` 메타데이터를 UI 계약에 포함한다
- [ ] `run_moa_path(..., routing=decision)` 전제를 명시한다
- [ ] Planner를 별도 모듈로 가정하지 않고 현재 코드 상태를 반영한다
- [ ] 플랫폼 UI가 단일 답변 화면이 아니라 실행/비교/추적 중심이라는 점을 문서화한다

---

## 9. 한 줄 요약

> `week7_implement.md`는 더 이상 “웹 서버를 빨리 만들자”는 문서가 아니라, **실제 RAG/MCP/evaluation 백엔드를 어떤 플랫폼 UI 계약으로 감쌀지 정의하는 문서**여야 한다.
