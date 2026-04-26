# Week 11 C11-3 Implement Guide — MCP 프론트엔드 표시 + 경로 확장

## 목표

- `context_metadata.mcp`를 파싱해 오른쪽 패널에 MCP 도구 호출 결과를 표시한다.
- 세그먼트 버튼에 `[RAG]` · `[MCP]` 를 추가해 사용자가 명시적으로 경로를 유도할 수 있게 한다.

---

## 선행 조건

- C11-2 완료: RAG 소스 표시 정상 동작
- `moa+mcp` 경로가 트리거되는 질문 1건 재현 가능

---

## MCP 트리거 질문 예시

```
"파일 목록을 보여줘"
"data/rag_docs 폴더에 어떤 파일이 있어?"
"refs/folder_structure.md 내용을 읽어줘"
```

---

## 구현 대상 파일

| 파일 | 작업 |
|------|------|
| `app/web/static/index.html` | MCP 패널 + RAG·MCP 세그먼트 버튼 추가 |
| `app/web/static/styles.css` | MCP 결과 카드 스타일 |
| `app/web/static/app.js` | MCP 렌더링 함수 + 경로 버튼 로직 |

---

## 1. index.html 수정

### 1-A. 오른쪽 패널에 MCP 섹션 추가

RAG 패널 바로 아래, `추적 로그` 위에 삽입한다.

```html
<p class="sidebar__label" style="margin-top:18px">MCP 도구 호출</p>
<div id="mcp-panel" class="mcp-panel">
  <span class="pipeline-empty">MCP 미사용</span>
</div>
```

### 1-B. 실행 경로 세그먼트 버튼 확장

기존 3개(`자동` / `단일` / `멀티에이전트`) → 5개로 확장한다.  
`data-value` 값은 `force_path`가 아니라 **경로 힌트** 역할을 한다  
(RAG·MCP는 `constraints` 주입 방식으로 트리거).

```html
<div class="segmented" id="path-segmented">
  <button class="seg-btn active" data-value="auto">자동</button>
  <button class="seg-btn" data-value="single">단일</button>
  <button class="seg-btn" data-value="moa">MOA</button>
  <button class="seg-btn" data-value="rag">RAG</button>
  <button class="seg-btn" data-value="mcp">MCP</button>
</div>
<input type="hidden" id="path-select" value="auto" />
```

---

## 2. styles.css 추가

```css
/* ══════════════════════════════════════
   MCP 도구 패널
══════════════════════════════════════ */
.mcp-panel {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.mcp-tool-card {
  background: var(--bg-card);
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mcp-tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mcp-tool-name {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--accent-amber);
}

.mcp-tool-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
}
.mcp-tool-status.success {
  background: rgba(6,214,160,0.15);
  color: var(--accent-teal);
}
.mcp-tool-status.failure {
  background: rgba(239,68,68,0.15);
  color: var(--accent-red);
}

.mcp-tool-summary {
  font-size: 10px;
  color: var(--text-secondary);
  line-height: 1.5;
  word-break: break-word;
  max-height: 60px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

/* 세그먼트 버튼 5개 시 폰트 더 축소 */
.segmented:has(.seg-btn:nth-child(5)) .seg-btn {
  font-size: 10px;
  padding: 6px 1px;
}
```

---

## 3. app.js 수정

### 3-A. `renderMcpPanel` 추가

`renderRagPanel` 바로 아래에 추가한다.

```javascript
/** 오른쪽 패널 MCP 섹션 렌더링 */
function renderMcpPanel(contextMeta) {
  const panelEl = document.getElementById("mcp-panel");
  const mcp = contextMeta?.mcp;

  if (!mcp || !mcp.tool_name) {
    panelEl.innerHTML = '<span class="pipeline-empty">MCP 미사용</span>';
    return;
  }

  const success    = mcp.success !== false;
  const statusCls  = success ? "success" : "failure";
  const statusText = success ? "성공" : "실패";
  const summary    = (mcp.normalized_result_summary || "").slice(0, 200);

  panelEl.innerHTML = `
    <div class="mcp-tool-card">
      <div class="mcp-tool-header">
        <span class="mcp-tool-name">${escapeHtml(mcp.tool_name)}</span>
        <span class="mcp-tool-status ${statusCls}">${statusText}</span>
      </div>
      ${mcp.server_name
        ? `<span style="font-size:10px;color:var(--text-secondary)">${escapeHtml(mcp.server_name)}</span>`
        : ""}
      ${summary
        ? `<div class="mcp-tool-summary">${escapeHtml(summary)}${summary.length >= 200 ? "…" : ""}</div>`
        : ""}
    </div>`;
}
```

### 3-B. `updateMetrics`에 MCP 패널 호출 추가

C11-2에서 이미 수정한 `updateMetrics` 끝에 한 줄 추가한다.

```javascript
renderRagPanel(response.context_metadata || {});
renderMcpPanel(response.context_metadata || {});   // ← 추가
```

### 3-C. 세그먼트 버튼 로직 확장

`pathSegmented` 클릭 핸들러를 아래로 교체한다.

```javascript
pathSegmented.addEventListener("click", (e) => {
  const btn = e.target.closest(".seg-btn");
  if (!btn) return;
  pathSegmented.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  pathSelectEl.value = btn.dataset.value;
});
```

`pathSelectEl.value`에 `"rag"` 또는 `"mcp"`가 세팅된다.  
이 값을 `sendPrompt`에서 읽어 `force_path`와 `constraints`를 결정한다.

### 3-D. `sendPrompt` 경로 로직 수정

```javascript
async function sendPrompt() {
  const prompt = promptInputEl.value.trim();
  if (!prompt) return;

  if (!state.sessionId) await createSession();
  messagesEl.querySelector(".welcome-card")?.remove();
  appendUserMessage(prompt);
  promptInputEl.value = "";

  const loadingEl = appendLoadingMessage();
  sendBtnEl.disabled = true;
  sendLabelEl.classList.add("hidden");
  sendSpinnerEl.classList.remove("hidden");

  /* ── 경로 결정 ── */
  const pathHint = pathSelectEl.value || "auto";  // auto | single | moa | rag | mcp

  let force_path = pathHint;          // "auto" | "single" | "moa"
  let constraints = {};

  if (pathHint === "rag") {
    /* RAG 강제: Router가 requires_rag=True를 설정하도록 constraints 주입 */
    force_path  = "moa";              // MOA 경로로 실행 (RAG는 executor가 결정)
    constraints = { source: "rag_docs" };
  } else if (pathHint === "mcp") {
    /* MCP 강제: Router가 requires_mcp=True를 설정하도록 프롬프트 prefix 주입 */
    force_path  = "moa";
    constraints = { use_mcp: true };
  }

  const selectedProvider = globalProviderEl.value;
  const globalModel = selectedProvider
    ? { provider: selectedProvider, model: globalModelEl.value }
    : null;

  const payload = {
    session_id:      state.sessionId,
    prompt,
    force_path,
    constraints,                      // ← 추가
    global_model:    globalModel,
    preset_id:       presetSelectEl.value || null,
    agent_overrides: collectAgentOverrides(),
  };

  try {
    const resp = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    const body = await resp.json();
    loadingEl.remove();

    if (!resp.ok) {
      appendErrorMessage(typeof body.detail === "object"
        ? JSON.stringify(body.detail) : body.detail);
      return;
    }

    state.sessionId = body.session_id;
    updateSessionBadge(state.sessionId);
    appendAssistantMessage(body.reply, body.agents || [], body.context_metadata || {});
    updateMetrics(body);

  } catch (err) {
    loadingEl.remove();
    appendErrorMessage(err.message);
  } finally {
    sendBtnEl.disabled = false;
    sendLabelEl.classList.remove("hidden");
    sendSpinnerEl.classList.add("hidden");
  }
}
```

---

## 4. ChatTurnRequest 스키마 확인

`constraints` 필드가 `ChatTurnRequest`에 이미 있는지 확인한다.

```python
# app/schemas/chat.py
class ChatTurnRequest(BaseModel):
    ...
    constraints: dict[str, Any] = Field(default_factory=dict)  # ← 이미 존재 ✅
```

**이미 존재한다면** 스키마 수정 불필요.  
없다면 해당 줄을 추가한다.

---

## RAG·MCP 강제 트리거 동작 원리

```
[RAG] 버튼 선택 + 전송
  ↓
payload.force_path = "moa"
payload.constraints = { source: "rag_docs" }
  ↓
Router (app/orchestrator/router.py)
  decision.requires_rag = constraints.source == "rag_docs" → True
  ↓
Executor: ChromaRetriever 실행 → context 주입
  ↓
path: "moa+rag"

[MCP] 버튼 선택 + 전송
  ↓
payload.force_path = "moa"
payload.constraints = { use_mcp: true }
  ↓
Router: constraints.use_mcp → requires_mcp = True (router.py에 규칙 추가 필요)
  ↓
Executor: MCPClient 실행
  ↓
path: "moa+mcp"
```

> **주의**: `use_mcp: true` constraint를 `router.py`가 처리하도록 규칙을 추가해야 할 수 있다.  
> `router.py`의 rule-based 섹션에서 `constraints.get("use_mcp")` 체크를 추가한다.

```python
# app/orchestrator/router.py — rule-based 섹션 (필요 시 추가)
if task.constraints.get("use_mcp"):
    return RoutingDecision(
        path="moa",
        requires_mcp=True,
        mcp_intent="user_forced",
        preferred_server="filesystem",
        ...
    )
```

---

## 검증 시나리오

### MCP 경로 확인

1. `[MCP]` 버튼 선택
2. "파일 목록을 보여줘" 입력
3. 확인 항목:
   - 경로 배지: 앰버(amber) 색 `moa+mcp`
   - MCP 패널: 도구명, 성공 여부, 결과 요약 표시

### RAG 경로 확인

1. `[RAG]` 버튼 선택
2. "에이전트 오케스트레이션이 뭔지 문서에서 찾아줘" 입력
3. 확인 항목:
   - 경로 배지: 틸(teal) 색 `moa+rag`
   - 메시지 버블: `📎 참조 문서` 칩 표시
   - RAG 패널: 히트 수·선택 청크 표시

### 자동(auto) 경로 확인

1. `[자동]` 버튼 선택
2. "파일 목록을 보여줘" 입력
3. Router가 자동으로 MCP를 선택하는지 확인

---

## 완료 기준

- [ ] `moa+mcp` 응답 시 오른쪽 패널에 도구명·성공 여부·결과 요약 표시
- [ ] 경로 배지 `moa+mcp` → 앰버 색 자동 전환
- [ ] 세그먼트 버튼 5개 (자동·단일·MOA·RAG·MCP) 표시
- [ ] `[RAG]` 버튼 → `constraints.source = "rag_docs"` 주입 확인
- [ ] `[MCP]` 버튼 → `constraints.use_mcp = true` 주입 확인
- [ ] JS 구문 오류 없음 (`node --check app.js`)
- [ ] pytest 회귀 없음

---

## 커밋

```
feat(web): render mcp tool results and add rag/mcp path controls
```
