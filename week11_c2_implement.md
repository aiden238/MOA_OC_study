# Week 11 C11-2 Implement Guide — RAG 프론트엔드 표시

## 목표

`/api/chat` 응답의 `context_metadata.rag*`를 파싱해  
메시지 버블 하단에 참조 문서 목록을, 오른쪽 패널에 RAG 통계를 표시한다.

---

## 선행 조건

- C11-1 완료: `context_metadata.rag_sources[].source` 보장
- RAG 트리거 질문 1건으로 `path == "moa+rag"` 재현 가능

---

## 구현 대상 파일

| 파일 | 작업 |
|------|------|
| `app/web/static/index.html` | 오른쪽 패널에 RAG 섹션 추가 |
| `app/web/static/styles.css` | RAG 소스 카드, 통계 스타일 |
| `app/web/static/app.js` | RAG 파싱·렌더링 함수 추가 |

---

## 1. index.html 수정

오른쪽 패널(`<aside class="metrics-panel">`) 안에서  
`추적 로그` 섹션 **바로 위**에 RAG 패널을 삽입한다.

```html
<!-- 기존 모델 배치 섹션 아래에 추가 -->

<p class="sidebar__label" style="margin-top:18px">RAG 검색 결과</p>
<div id="rag-panel" class="rag-panel">
  <span class="pipeline-empty">RAG 미사용</span>
</div>
```

---

## 2. styles.css 추가

파일 끝(`@media` 섹션 바로 위)에 아래를 추가한다.

```css
/* ══════════════════════════════════════
   RAG 소스 패널
══════════════════════════════════════ */
.rag-panel {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.rag-stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-secondary);
  padding: 3px 0;
}

.rag-stat-val {
  color: var(--accent-teal);
  font-family: var(--font-mono);
  font-weight: 600;
}

.rag-source-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border: 1px solid var(--border-dark);
  border-radius: var(--radius-sm);
  padding: 5px 8px;
  font-size: 11px;
}

.rag-source-name {
  color: var(--accent-teal);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}

.rag-source-score {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
  flex-shrink: 0;
}

/* 메시지 버블 RAG 소스 섹션 */
.msg-rag-sources {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(6, 214, 160, 0.06);
  border: 1px solid rgba(6, 214, 160, 0.2);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rag-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--accent-teal);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.rag-source-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 2px;
}

.rag-chip {
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(6, 214, 160, 0.12);
  border: 1px solid rgba(6, 214, 160, 0.25);
  color: #059669;
  border-radius: 20px;
  font-family: var(--font-mono);
}
```

---

## 3. app.js 수정

### 3-A. `pathBadgeClass` 헬퍼 추가

파일 상단 상수 정의 영역에 추가한다.

```javascript
/** path 문자열 → CSS 배지 클래스 */
function pathBadgeClass(path) {
  if (!path) return "path-single";
  if (path.includes("+rag")) return "path-moa-rag";
  if (path.includes("+mcp")) return "path-moa-mcp";
  if (path.startsWith("moa"))  return "path-moa";
  return "path-single";
}
```

### 3-B. `renderRagPanel` 추가

`updateMetrics` 함수 **위**에 추가한다.

```javascript
/** 오른쪽 패널 RAG 섹션 렌더링 */
function renderRagPanel(contextMeta) {
  const panelEl = document.getElementById("rag-panel");
  const ragSources = contextMeta?.rag_sources || [];
  const ragMeta    = contextMeta?.rag || {};
  const retrieval  = contextMeta?.rag_retrieval || {};

  if (!ragSources.length && !retrieval.hit_count) {
    panelEl.innerHTML = '<span class="pipeline-empty">RAG 미사용</span>';
    return;
  }

  const hitCount      = retrieval.hit_count ?? ragSources.length;
  const tokenEstimate = ragMeta.token_estimate ?? "—";
  const selectedCount = ragSources.length || ragMeta.selected_chunks?.length || "—";

  let html = `
    <div class="rag-stat-row">
      <span>히트 수</span>
      <span class="rag-stat-val">${hitCount}</span>
    </div>
    <div class="rag-stat-row">
      <span>선택 청크</span>
      <span class="rag-stat-val">${selectedCount}</span>
    </div>
    <div class="rag-stat-row">
      <span>토큰 예산</span>
      <span class="rag-stat-val">${tokenEstimate}</span>
    </div>
  `;

  if (ragSources.length) {
    html += ragSources
      .map(({ source, score }) => `
        <div class="rag-source-item">
          <span class="rag-source-name" title="${escapeHtml(source)}">${escapeHtml(source)}</span>
          <span class="rag-source-score">${score != null ? score.toFixed(2) : "—"}</span>
        </div>`)
      .join("");
  }

  panelEl.innerHTML = html;
}
```

### 3-C. `appendAssistantMessage` 수정 — RAG 소스 버블 추가

`agentsList` 다음에 `contextMeta` 매개변수를 추가한다.

```javascript
function appendAssistantMessage(content, agentsList = [], contextMeta = {}) {
  const tagsHtml = agentsList
    .map((name) => {
      const { label, cls } = agentInfo(name);
      return `<span class="agent-tag ${cls}">${label}</span>`;
    })
    .join(" ");

  /* RAG 소스 섹션 (path에 +rag가 포함될 때만) */
  const ragSources = contextMeta?.rag_sources || [];
  let ragHtml = "";
  if (ragSources.length) {
    const chips = ragSources
      .map(({ source }) => `<span class="rag-chip">${escapeHtml(source)}</span>`)
      .join("");
    ragHtml = `
      <div class="msg-rag-sources">
        <span class="rag-label">📎 참조 문서</span>
        <div class="rag-source-chips">${chips}</div>
      </div>`;
  }

  const wrap = document.createElement("div");
  wrap.className = "message assistant";
  wrap.innerHTML = `
    <div class="msg-header">
      <div class="msg-avatar">M</div>
      <span>MOA</span>
    </div>
    <div class="msg-bubble">${formatContent(content)}</div>
    ${ragHtml}
    ${tagsHtml ? `<div class="msg-pipeline">${tagsHtml}</div>` : ""}
  `;
  _appendMsg(wrap);
}
```

### 3-D. `updateMetrics` 수정 — path 배지 + RAG 패널 호출

```javascript
function updateMetrics(response) {
  const m = response.metrics || {};

  /* 기존 6개 카드 */
  const pathEl = document.getElementById("m-path");
  const pathStr = response.path || "—";
  pathEl.innerHTML = pathStr !== "—"
    ? `<span class="path-badge ${pathBadgeClass(pathStr)}">${pathStr}</span>`
    : "—";

  document.getElementById("m-latency").textContent =
    m.latency_ms != null ? `${m.latency_ms} ms` : "—";
  document.getElementById("m-prompt-tok").textContent  = m.prompt_tokens    ?? "—";
  document.getElementById("m-comp-tok").textContent    = m.completion_tokens ?? "—";
  document.getElementById("m-cost").textContent =
    m.cost_estimate != null ? `$${Number(m.cost_estimate).toFixed(5)}` : "—";

  const agents = response.agents || [];
  document.getElementById("m-agents").textContent = agents.length > 0 ? agents.length : "—";

  renderPipelineViz(agents);
  renderModelMap(response.selected_models || {});
  renderRagPanel(response.context_metadata || {});   // ← 추가

  document.getElementById("trace-path").textContent = response.trace_path || "—";
}
```

### 3-E. `sendPrompt` 수정 — contextMeta를 appendAssistantMessage에 전달

```javascript
// 기존:
appendAssistantMessage(body.reply, body.agents || []);

// 변경:
appendAssistantMessage(body.reply, body.agents || [], body.context_metadata || {});
```

---

## 검증 시나리오

### RAG 트리거 질문 예시

```
"rag_docs 폴더에 있는 문서를 기반으로 MOA 구조를 설명해줘"
"문서에서 에이전트 오케스트레이션 방법을 찾아줘"
```

### 확인 항목

| 항목 | 확인 방법 |
|------|-----------|
| 경로 배지 | `m-path` 카드에 틸(teal) 색 `moa+rag` 배지 표시 |
| 메시지 소스 | 버블 하단에 `📎 참조 문서` + 파일명 칩 표시 |
| RAG 패널 | 오른쪽 패널에 히트 수·선택 청크·토큰 예산 표시 |
| single 경로 | RAG 섹션 미표시, 패널에 "RAG 미사용" |

---

## 완료 기준

- [ ] `moa+rag` 응답 시 메시지 버블에 `📎 참조 문서` 섹션 표시
- [ ] 오른쪽 패널 RAG 통계 표시 (히트 수, 선택 청크, 토큰)
- [ ] 경로 배지 `moa+rag` → 틸 색상 자동 전환
- [ ] `single` / `moa` 경로에서 RAG 섹션 미표시
- [ ] JS 구문 오류 없음 (`node --check app.js`)

---

## 커밋

```
feat(web): render rag sources and stats in chat UI
```
