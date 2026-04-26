# Week 11 Plan — RAG · MCP 프론트엔드 연동

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 11주차 |
| **상태** | 계획 수립 |
| **작성일** | 2026-04-26 |
| **목표** | 백엔드가 이미 생성·반환하는 RAG·MCP 메타데이터를 웹 UI에서 시각화한다. |

---

## 배경

Week 7~9에서 `moa+rag`, `moa+mcp` 실행 경로가 CLI 기준으로 완성됐고,  
Week 10에서 웹 UI(FastAPI + plain HTML/CSS/JS)가 추가됐다.

그러나 현재 프론트엔드(`app.js`)는 `/api/chat` 응답에서 아래 필드를 **전혀 읽지 않는다**:

- `context_metadata.rag` — 선택된 청크, 토큰 예산, 소스 목록
- `context_metadata.rag_retrieval` — 히트 수, retriever 유형
- `context_metadata.mcp` — 도구명, 성공 여부, 결과 요약
- `context_metadata.routing.requires_rag / requires_mcp`
- `path` 값이 `"moa+rag"` 또는 `"moa+mcp"`일 때 UI 구분 없음

백엔드 `ChatTurnResponse`에는 이미 모든 데이터가 포함되어 있다.  
Week 11은 **표시층(JS·CSS·HTML)만** 추가하는 주차다.

---

## Week 11 원칙

- 백엔드 변경은 최소화한다 (스키마 추가가 필요하면 `ChatTurnResponse`에 필드 추가 한정).
- `app.js` 단일 파일에 RAG·MCP 렌더링 로직을 모두 담는다.
- `styles.css`의 `.path-moa-rag`, `.path-moa-mcp` 배지는 이미 정의되어 있으므로 재활용한다.
- RAG 소스 표시는 메시지 버블 하단, MCP 결과는 오른쪽 패널에 배치한다.
- 자동(auto) 모드에서 키워드만으로 RAG·MCP가 이미 트리거되므로,  
  UI 버튼 강제 경로(`force_path`)는 `constraints` 주입 방식으로 구현한다.
- 기존 CLI·pytest 회귀는 건드리지 않는다.

---

## 현재 데이터 흐름 (확인된 사실)

```
/api/chat 응답 (ChatTurnResponse)
├── path: "moa" | "moa+rag" | "moa+mcp" | "single"
├── agents: ["router", "draft_analytical", ..., "synthesizer"]
├── metrics: { latency_ms, prompt_tokens, completion_tokens, cost_estimate }
├── selected_models: { agent_name: { provider, model, active } }
├── context_metadata:
│   ├── routing: { requires_rag, requires_mcp, rag_query_hint, mcp_intent }
│   ├── rag_retrieval: { stage:"retrieval", hit_count, retriever_type }  ← RAG 시만
│   ├── rag: { selected_chunks, token_estimate, total_chunks }           ← RAG 시만
│   └── mcp: { tool_name, server_name, success, normalized_result_summary, args }  ← MCP 시만
└── trace_path
```

`context_metadata`는 서버에서 항상 직렬화되어 응답에 포함된다.  
`selected_chunks`가 소스 파일명을 포함하는지 **C11-1에서 먼저 확인·보완**한다.

---

## Week 11 목표 범위

### W11-1. 백엔드 소스 노출 검증

- `context_metadata.rag.selected_chunks`에 `source` 필드가 포함되는지 확인
- 없으면 `ContextBuilder` 또는 `_build_context_metadata`에서 source 목록 추출 추가
- `context_metadata.mcp.normalized_result_summary` 길이·품질 검증

### W11-2. RAG 프론트엔드 표시

- 메시지 버블 하단에 "📎 참조 문서" 섹션 렌더링
- 오른쪽 패널에 RAG 통계 카드 추가 (히트수, 선택 청크, 토큰)
- `path` 값이 `"moa+rag"`면 경로 배지를 틸(teal) 색으로 표시
- `path-moa-rag` CSS 클래스 활성화

### W11-3. MCP 프론트엔드 표시

- 오른쪽 패널에 MCP 도구 호출 결과 카드 추가
- 도구명·성공 여부·결과 요약 표시
- `path` 값이 `"moa+mcp"`면 경로 배지를 앰버(amber) 색으로 표시
- `path-moa-mcp` CSS 클래스 활성화

### W11-4. 실행 경로 확장 (사이드바)

- 세그먼트 버튼에 `[RAG]` · `[MCP]` 추가
- 선택 시 `constraints: { source: "rag_docs" }` 또는 MCP 트리거 키워드를 `prompt` prefix로 주입
- `auto` 모드와의 차이를 UI에서 명확히 구분

### W11-5. 검증·테스트

- RAG 질문으로 `moa+rag` 경로 트리거, UI에서 소스 표시 확인
- MCP 질문으로 `moa+mcp` 경로 트리거, UI에서 도구 결과 확인
- `path` 배지 색상 자동 전환 확인
- 기존 `single`, `moa` 경로에서 RAG·MCP 섹션 미표시 확인
- pytest 회귀 통과

---

## 권장 구현 구조

### app.js 추가 함수

```javascript
// RAG 소스 파싱 및 렌더링
function renderRagSources(contextMeta) { ... }

// MCP 도구 결과 렌더링
function renderMcpResult(contextMeta) { ... }

// path → CSS 배지 클래스
function pathBadgeClass(path) {
  if (path.includes("+rag")) return "path-moa-rag";
  if (path.includes("+mcp")) return "path-moa-mcp";
  if (path === "moa")        return "path-moa";
  return "path-single";
}

// 메시지 버블에 RAG 소스 섹션 추가
function appendAssistantMessage(content, agentsList, contextMeta) { ... }

// 메트릭 업데이트 확장
function updateMetrics(response) {
  // 기존 6개 카드 업데이트 유지
  // + path 배지 클래스 적용
  // + renderRagSources(response.context_metadata)
  // + renderMcpResult(response.context_metadata)
}
```

### index.html 추가 섹션 (오른쪽 패널)

```html
<!-- RAG 검색 결과 -->
<p class="sidebar__label" style="margin-top:18px">RAG 검색 결과</p>
<div id="rag-panel" class="rag-panel">
  <span class="pipeline-empty">—</span>
</div>

<!-- MCP 도구 결과 -->
<p class="sidebar__label" style="margin-top:18px">MCP 도구 호출</p>
<div id="mcp-panel" class="mcp-panel">
  <span class="pipeline-empty">—</span>
</div>
```

### 메시지 버블 RAG 소스 구조

```html
<div class="msg-rag-sources">
  <span class="rag-label">📎 참조 문서</span>
  <div class="rag-source-list">
    <span class="rag-source-item">doc1.txt</span>
    <span class="rag-source-item">doc3.md</span>
  </div>
</div>
```

---

## API 데이터 파싱 규칙

| `response` 필드 | 조건 | 프론트 동작 |
|-----------------|------|------------|
| `path == "moa+rag"` | — | 틸 배지, RAG 섹션 표시 |
| `path == "moa+mcp"` | — | 앰버 배지, MCP 섹션 표시 |
| `context_metadata.rag.selected_chunks` | 배열 길이 > 0 | 소스 목록 추출 |
| `context_metadata.rag_retrieval.hit_count` | 숫자 | RAG 히트 수 표시 |
| `context_metadata.mcp.tool_name` | 문자열 | MCP 도구명 표시 |
| `context_metadata.mcp.success` | bool | 성공/실패 아이콘 |
| `context_metadata.mcp.normalized_result_summary` | 문자열 | 결과 요약 텍스트 |

---

## 세부 구현 단계

| 단계 | 구현 문서 | 커밋 제안 | 핵심 작업 |
|------|-----------|-----------|-----------|
| C11-1 | `week11_c1_implement.md` | `fix(rag): expose source filenames in context_metadata` | 소스 노출 검증·보완 |
| C11-2 | `week11_c2_implement.md` | `feat(web): render rag sources and stats in UI` | RAG UI 표시 |
| C11-3 | `week11_c3_implement.md` | `feat(web): render mcp tool results and add path controls` | MCP UI + 경로 확장 |

---

## 변경 대상 파일

수정:
- `app/web/static/app.js` — 핵심 변경 (RAG·MCP 렌더링 함수 추가)
- `app/web/static/index.html` — RAG·MCP 패널, 세그먼트 버튼 확장
- `app/web/static/styles.css` — RAG 소스 카드, MCP 결과 카드 스타일

선택적 수정:
- `app/rag/context_builder.py` — selected_chunks에 source 필드 보장
- `app/services/chat_service.py` — `_build_context_metadata` source 추출 보완

신규:
- `week11_c1_implement.md`
- `week11_c2_implement.md`
- `week11_c3_implement.md`

---

## 단계 간 종속성

| 단계 | 선행조건 | 다음 단계로 넘기는 산출물 |
|------|----------|--------------------------|
| C11-1 | Week 10 웹 UI 동작 확인 | `selected_chunks[].source` 보장된 API 응답 |
| C11-2 | C11-1 완료 | RAG 메시지 버블 + 패널 |
| C11-3 | C11-2 완료 | MCP 패널 + 경로 버튼 |

---

## DoD

- [ ] `moa+rag` 응답 시 메시지 버블 하단에 참조 문서 목록 표시
- [ ] `moa+rag` 응답 시 오른쪽 패널에 RAG 통계 표시 (히트 수, 선택 청크, 토큰)
- [ ] `moa+mcp` 응답 시 오른쪽 패널에 MCP 도구명·결과 표시
- [ ] 경로 배지가 `moa+rag` → 틸, `moa+mcp` → 앰버, `moa` → 바이올렛, `single` → 회색으로 자동 전환
- [ ] RAG / MCP 버튼 클릭 시 해당 경로 강제 트리거
- [ ] `single` 경로에서 RAG·MCP 섹션이 표시되지 않음
- [ ] 기존 `single`, `moa` 동작에 회귀 없음
- [ ] pytest 통과

---

## 리스크

| 상황 | 대응 |
|------|------|
| `selected_chunks`에 source 파일명이 없음 | `ContextBuilder.build()`의 출력 포맷에서 source를 명시적으로 추출 |
| RAG/MCP가 자동(auto) 모드에서만 동작 | `constraints.source` 주입 방식으로 force-RAG 구현, force_path는 건드리지 않음 |
| MCP 응답이 너무 길어 UI에서 잘림 | `normalized_result_summary` 200자 truncation 적용 |
| RAG 미트리거 시 패널이 비어 있음 | 빈 상태 placeholder("이번 응답에서 RAG 미사용") 표시 |

---

## 변경 기록

### 2026-04-26

- Week 11 계획 문서를 최초 작성했다.
- 백엔드 RAG·MCP 구현이 완전하고 `ChatTurnResponse`에 `context_metadata`가 이미 포함됨을 확인했다.
- Week 11 범위를 프론트엔드 표시층 추가로 한정했다.
