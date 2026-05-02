const state = {
  sessionId: null,
  registry: null,
  agentNames: [],
  graphData: null,
  graphBaseData: null,
  graphHighlights: [],
  graphFilter: "all",
  graphTransform: null,
};

const messagesEl = document.getElementById("messages");
const sessionBadgeEl = document.getElementById("session-badge");
const presetSelectEl = document.getElementById("preset-select");
const globalProviderEl = document.getElementById("global-provider");
const globalModelEl = document.getElementById("global-model");
const pathSelectEl = document.getElementById("path-select");
const pathSegmentedEl = document.getElementById("path-segmented");
const promptInputEl = document.getElementById("prompt-input");
const agentOverridesEl = document.getElementById("agent-overrides");
const sendBtnEl = document.getElementById("send-btn");
const sendLabelEl = document.getElementById("send-label");
const sendSpinnerEl = document.getElementById("send-spinner");
const graphFilterEl = document.getElementById("graph-category-filter");
const graphExpandBtnEl = document.getElementById("graph-expand-btn");
const graphCanvasEl = document.getElementById("knowledge-graph-canvas");
const graphDetailEl = document.getElementById("knowledge-graph-detail");

const AGENT_TAG = {
  single_baseline: { label: "Single", cls: "router" },
  router: { label: "Router", cls: "router" },
  draft_analytical: { label: "Analytical", cls: "draft" },
  draft_creative: { label: "Creative", cls: "draft" },
  draft_structured: { label: "Structured", cls: "draft" },
  critic: { label: "Critic", cls: "critic" },
  judge: { label: "Judge", cls: "judge" },
  rewrite: { label: "Rewrite", cls: "rewrite" },
  synthesizer: { label: "Synth", cls: "synth" },
};

const PIPELINE_ORDER = [
  "router",
  "draft_analytical",
  "draft_creative",
  "draft_structured",
  "critic",
  "judge",
  "rewrite",
  "synthesizer",
  "single_baseline",
];

const GRAPH_CATEGORY_COLORS = {
  prompt_engineering: "#3B82F6",
  context_engineering: "#10B981",
  harness_engineering: "#F59E0B",
  advanced: "#8B5CF6",
  basics: "#6B7280",
};

function agentInfo(name) {
  return AGENT_TAG[name] || { label: name, cls: "router" };
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatContent(value) {
  return escapeHtml(value)
    .replace(/\n/g, "<br>")
    .replace(/`([^`\n]+)`/g, "<code>$1</code>");
}

function pathBadgeClass(path) {
  if (!path) return "path-single";
  if (path.includes("+rag")) return "path-moa-rag";
  if (path.includes("+mcp")) return "path-moa-mcp";
  if (path.startsWith("moa")) return "path-moa";
  return "path-single";
}

function normalizeRagSources(contextMeta = {}) {
  const fromMeta = Array.isArray(contextMeta.rag_sources) ? contextMeta.rag_sources : [];
  if (fromMeta.length) {
    return fromMeta.map((item) => ({
      source: item?.source || "unknown",
      score: typeof item?.score === "number" ? item.score : null,
    }));
  }

  const chunks = Array.isArray(contextMeta?.rag?.selected_chunks) ? contextMeta.rag.selected_chunks : [];
  const seen = new Map();
  for (const chunk of chunks) {
    const source =
      chunk?.source ||
      chunk?.source_path?.split(/[\\/]/).pop() ||
      chunk?.label ||
      "unknown";
    const score =
      typeof chunk?.score === "number"
        ? chunk.score
        : typeof chunk?.normalized_relevance === "number"
          ? chunk.normalized_relevance
          : null;
    const current = seen.get(source);
    if (current == null || (score != null && score > current)) {
      seen.set(source, score);
    }
  }
  return Array.from(seen.entries())
    .map(([source, score]) => ({ source, score }))
    .sort((left, right) => (right.score ?? -1) - (left.score ?? -1));
}

function resetMetricsPanel() {
  document.getElementById("m-path").textContent = "-";
  document.getElementById("m-latency").textContent = "-";
  document.getElementById("m-prompt-tok").textContent = "-";
  document.getElementById("m-comp-tok").textContent = "-";
  document.getElementById("m-cost").textContent = "-";
  document.getElementById("m-agents").textContent = "-";
  document.getElementById("pipeline-viz").innerHTML = '<span class="pipeline-empty">응답 후 표시됩니다.</span>';
  document.getElementById("model-map").innerHTML = '<span class="pipeline-empty">-</span>';
  document.getElementById("trace-path").textContent = "-";
  renderRagPanel({});
  renderMcpPanel({});
  renderWikiStatus({ pending_count: 0, approved_count: 0, latest_entries: [] });
}

function updateSessionBadge(sessionId) {
  sessionBadgeEl.textContent = sessionId ? `세션 ${sessionId.slice(0, 8)}` : "세션 없음";
}

function setPathSelection(value) {
  const allowed = new Set(["auto", "single", "moa", "rag", "mcp"]);
  const resolved = allowed.has(value) ? value : "auto";
  pathSelectEl.value = resolved;
  pathSegmentedEl.querySelectorAll(".seg-btn").forEach((button) => {
    button.classList.toggle("active", button.dataset.value === resolved);
  });
}

function appendNode(node) {
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendUserMessage(content) {
  const wrapper = document.createElement("div");
  wrapper.className = "message user";
  wrapper.innerHTML = `
    <div class="msg-header">
      <div class="msg-avatar">U</div>
      <span>User</span>
    </div>
    <div class="msg-bubble">${formatContent(content)}</div>
  `;
  appendNode(wrapper);
}

function appendAssistantMessage(content, agentsList = [], contextMeta = {}) {
  const tagsHtml = agentsList
    .map((name) => {
      const { label, cls } = agentInfo(name);
      return `<span class="agent-tag ${cls}">${label}</span>`;
    })
    .join("");

  const ragSources = normalizeRagSources(contextMeta);
  const ragHtml = ragSources.length
    ? `
      <div class="msg-rag-sources">
        <span class="rag-label">RAG sources</span>
        <div class="rag-source-chips">
          ${ragSources
            .slice(0, 6)
            .map(({ source }) => `<span class="rag-chip">${escapeHtml(source)}</span>`)
            .join("")}
        </div>
      </div>
    `
    : "";

  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";
  wrapper.innerHTML = `
    <div class="msg-header">
      <div class="msg-avatar">M</div>
      <span>MOA</span>
    </div>
    <div class="msg-bubble">${formatContent(content)}</div>
    ${ragHtml}
    ${tagsHtml ? `<div class="msg-pipeline">${tagsHtml}</div>` : ""}
  `;
  appendNode(wrapper);
}

function appendLoadingMessage() {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant loading";
  wrapper.innerHTML = `
    <div class="msg-header">
      <div class="msg-avatar">M</div>
      <span>MOA</span>
    </div>
    <div class="msg-bubble">
      <div class="dot-anim"><span></span><span></span><span></span></div>
    </div>
  `;
  appendNode(wrapper);
  return wrapper;
}

function appendErrorMessage(detail) {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";
  wrapper.innerHTML = `
    <div class="msg-header">
      <div class="msg-avatar">!</div>
      <span>Error</span>
    </div>
    <div class="msg-bubble" style="color: var(--accent-red)">${escapeHtml(detail)}</div>
  `;
  appendNode(wrapper);
}

function renderPipelineViz(agentsList, failedAgents = []) {
  const element = document.getElementById("pipeline-viz");
  if (!agentsList.length && !failedAgents.length) {
    element.innerHTML = '<span class="pipeline-empty">응답 후 표시됩니다.</span>';
    return;
  }

  const ordered = PIPELINE_ORDER.filter((name) => agentsList.includes(name));
  const extras = agentsList.filter((name) => !PIPELINE_ORDER.includes(name));
  const steps = [...ordered, ...extras];

  const activeHtml = steps
    .map((name, index) => {
      const { label, cls } = agentInfo(name);
      const arrow = index < steps.length - 1 ? '<span class="pipeline-arrow">→</span>' : "";
      return `<span class="pipeline-step agent-tag ${cls}">${label}</span>${arrow}`;
    })
    .join("");

  const failedHtml = failedAgents
    .map(({ agent_name }) => `<span class="pipeline-step agent-tag agent-failed">${escapeHtml(agent_name)}</span>`)
    .join("");

  element.innerHTML = activeHtml + (failedHtml ? `<span class="pipeline-sep"> | </span>${failedHtml}` : "");
}

function renderModelMap(selectedModels) {
  const element = document.getElementById("model-map");
  const entries = Object.entries(selectedModels).filter(([, info]) => info?.active);
  if (!entries.length) {
    element.innerHTML = '<span class="pipeline-empty">-</span>';
    return;
  }

  element.innerHTML = entries
    .map(([agentName, info]) => {
      const { label, cls } = agentInfo(agentName);
      return `
        <div class="model-row is-active">
          <span class="model-row-agent agent-tag ${cls}">${label}</span>
          <span class="model-row-model">${escapeHtml(`${info.provider}/${info.model}`)}</span>
        </div>
      `;
    })
    .join("");
}

function renderRagPanel(contextMeta = {}) {
  const panelEl = document.getElementById("rag-panel");
  const ragSources = normalizeRagSources(contextMeta);
  const ragMeta = contextMeta.rag || {};
  const retrieval = contextMeta.rag_retrieval || {};
  const tokenEstimate = ragMeta.token_estimate ?? ragMeta.context_token_estimate ?? 0;
  const hitCount = retrieval.hit_count ?? 0;
  const selectedCount = ragMeta.selected_count ?? ragSources.length ?? 0;

  if (!ragSources.length && !hitCount) {
    panelEl.innerHTML = '<span class="pipeline-empty">이번 응답에서 RAG 미사용</span>';
    return;
  }

  panelEl.innerHTML = `
    <div class="rag-stat-row"><span>검색 히트</span><span class="rag-stat-val">${hitCount}</span></div>
    <div class="rag-stat-row"><span>선택 청크</span><span class="rag-stat-val">${selectedCount}</span></div>
    <div class="rag-stat-row"><span>토큰 추정</span><span class="rag-stat-val">${tokenEstimate}</span></div>
    ${ragSources
      .map(
        ({ source, score }) => `
          <div class="rag-source-item">
            <span class="rag-source-name" title="${escapeHtml(source)}">${escapeHtml(source)}</span>
            <span class="rag-source-score">${score != null ? Number(score).toFixed(2) : "-"}</span>
          </div>
        `,
      )
      .join("")}
  `;
}

function renderMcpPanel(contextMeta = {}) {
  const panelEl = document.getElementById("mcp-panel");
  const mcp = contextMeta.mcp;
  if (!mcp?.tool_name) {
    panelEl.innerHTML = '<span class="pipeline-empty">이번 응답에서 MCP 미사용</span>';
    return;
  }

  const success = mcp.success !== false;
  const summary = String(mcp.normalized_result_summary || "").slice(0, 200);
  panelEl.innerHTML = `
    <div class="mcp-tool-card">
      <div class="mcp-tool-header">
        <span class="mcp-tool-name">${escapeHtml(mcp.tool_name)}</span>
        <span class="mcp-tool-status ${success ? "success" : "failure"}">${success ? "OK" : "FAIL"}</span>
      </div>
      ${mcp.server_name ? `<span class="mcp-tool-server">${escapeHtml(mcp.server_name)}</span>` : ""}
      <div class="mcp-tool-summary">${escapeHtml(summary || "No summary")}</div>
    </div>
  `;
}

function renderWikiStatus(status = {}) {
  const panelEl = document.getElementById("wiki-status-panel");
  const latestEntries = Array.isArray(status.latest_entries) ? status.latest_entries : [];
  panelEl.innerHTML = `
    <div class="wiki-status-row"><span>Pending</span><strong>${status.pending_count ?? 0}</strong></div>
    <div class="wiki-status-row"><span>Approved</span><strong>${status.approved_count ?? 0}</strong></div>
    <div class="wiki-status-row"><span>Last Updated</span><strong>${escapeHtml(status.last_updated || "-")}</strong></div>
    <div class="wiki-status-list">
      ${
        latestEntries.length
          ? latestEntries
              .map(
                (entry) => `
                  <div class="wiki-status-item">
                    ${escapeHtml(entry.action || "updated")} · ${escapeHtml(entry.title || entry.filename || "entry")}
                  </div>
                `,
              )
              .join("")
          : '<span class="pipeline-empty">No wiki updates yet.</span>'
      }
    </div>
  `;
}

function updateMetrics(response) {
  const metrics = response.metrics || {};
  const path = response.path || "-";
  const pathElement = document.getElementById("m-path");
  pathElement.innerHTML = `<span class="path-badge ${pathBadgeClass(path)}">${escapeHtml(path)}</span>`;
  document.getElementById("m-latency").textContent = metrics.latency_ms != null ? `${metrics.latency_ms} ms` : "-";
  document.getElementById("m-prompt-tok").textContent = metrics.prompt_tokens ?? "-";
  document.getElementById("m-comp-tok").textContent = metrics.completion_tokens ?? "-";
  document.getElementById("m-cost").textContent = metrics.cost_estimate != null ? `$${Number(metrics.cost_estimate).toFixed(5)}` : "-";
  document.getElementById("m-agents").textContent = Array.isArray(response.agents) ? response.agents.length : "-";

  const failedAgents = response.context_metadata?.failed_agents || [];
  renderPipelineViz(response.agents || [], failedAgents);
  renderModelMap(response.selected_models || {});
  renderRagPanel(response.context_metadata || {});
  renderMcpPanel(response.context_metadata || {});
  updateGraphHighlights(response.context_metadata?.graph || {});
  document.getElementById("trace-path").textContent = response.trace_path || "-";
}

function modelOptionsForProvider(providerId) {
  return (state.registry?.models || []).filter((model) => model.provider === providerId);
}

function fillModelSelect(selectEl, providerId, selectedValue = "") {
  selectEl.innerHTML = "";
  for (const model of modelOptionsForProvider(providerId)) {
    const option = document.createElement("option");
    option.value = model.model;
    option.textContent = model.label + (model.available ? "" : " (disabled)");
    option.disabled = !model.available;
    if (model.model === selectedValue) {
      option.selected = true;
    }
    selectEl.appendChild(option);
  }
}

function syncGlobalModelSelect() {
  const providerId = globalProviderEl.value;
  if (!providerId) {
    globalModelEl.innerHTML = '<option value="">기본값 사용</option>';
    globalModelEl.disabled = true;
    return;
  }
  globalModelEl.disabled = false;
  fillModelSelect(globalModelEl, providerId);
}

function renderProviderControls() {
  globalProviderEl.innerHTML = '<option value="">에이전트별 기본값</option>';
  for (const provider of state.registry.providers) {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = provider.label + (provider.available ? "" : " (disabled)");
    option.disabled = !provider.available;
    globalProviderEl.appendChild(option);
  }
  globalProviderEl.value = "";
  syncGlobalModelSelect();
}

function renderPresets() {
  presetSelectEl.innerHTML = '<option value="">없음</option>';
  for (const preset of state.registry.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label + (preset.available ? "" : " (disabled)");
    option.disabled = !preset.available;
    presetSelectEl.appendChild(option);
  }
}

function renderAgentOverrides() {
  agentOverridesEl.innerHTML = "";
  for (const agentName of state.agentNames) {
    const { label, cls } = agentInfo(agentName);
    const card = document.createElement("div");
    card.className = "agent-card";
    card.innerHTML = `
      <label class="checkbox-row">
        <input type="checkbox" data-agent-enable="${agentName}" />
        <span class="agent-tag ${cls}">${label}</span>
      </label>
      <select class="ctrl-select" data-agent-provider="${agentName}" disabled></select>
      <select class="ctrl-select" data-agent-model="${agentName}" disabled></select>
    `;
    agentOverridesEl.appendChild(card);

    const checkbox = card.querySelector(`[data-agent-enable="${agentName}"]`);
    const providerSelect = card.querySelector(`[data-agent-provider="${agentName}"]`);
    const modelSelect = card.querySelector(`[data-agent-model="${agentName}"]`);

    for (const provider of state.registry.providers) {
      const option = document.createElement("option");
      option.value = provider.id;
      option.textContent = provider.label + (provider.available ? "" : " (disabled)");
      option.disabled = !provider.available;
      providerSelect.appendChild(option);
    }

    providerSelect.value = "openai";
    fillModelSelect(modelSelect, "openai");

    checkbox.addEventListener("change", () => {
      providerSelect.disabled = !checkbox.checked;
      modelSelect.disabled = !checkbox.checked;
    });
    providerSelect.addEventListener("change", () => {
      fillModelSelect(modelSelect, providerSelect.value);
    });
  }
}

function collectAgentOverrides() {
  const overrides = {};
  for (const agentName of state.agentNames) {
    const checkbox = document.querySelector(`[data-agent-enable="${agentName}"]`);
    if (!checkbox?.checked) continue;
    overrides[agentName] = {
      provider: document.querySelector(`[data-agent-provider="${agentName}"]`).value,
      model: document.querySelector(`[data-agent-model="${agentName}"]`).value,
    };
  }
  return overrides;
}

async function createSession() {
  const response = await fetch("/api/sessions", { method: "POST" });
  const payload = await response.json();
  state.sessionId = payload.session_id;
  updateSessionBadge(state.sessionId);
  messagesEl.innerHTML = `
    <div class="welcome-card">
      <div class="welcome-icon">M</div>
      <h2>MOA Lab에서 질문을 시작하세요</h2>
      <p>Single, MOA, RAG, MCP 경로를 비교하면서 응답과 trace를 함께 볼 수 있습니다.</p>
      <div class="welcome-chips">
        <span class="chip">Draft x3</span>
        <span class="chip">Critic</span>
        <span class="chip">Judge</span>
        <span class="chip">Synthesizer</span>
      </div>
    </div>
  `;
  resetMetricsPanel();
}

async function loadRegistry() {
  const response = await fetch("/api/models");
  state.registry = await response.json();
  state.agentNames = state.registry.agents.filter((name) => !["single_baseline", "rubric_judge"].includes(name));
  renderProviderControls();
  renderPresets();
  renderAgentOverrides();
}

function buildPayload(prompt) {
  const pathHint = pathSelectEl.value || "auto";
  let forcePath = pathHint;
  let constraints = {};

  if (pathHint === "rag") {
    forcePath = "moa";
    constraints = { source: "rag_docs" };
  } else if (pathHint === "mcp") {
    forcePath = "moa";
    constraints = { use_mcp: true };
  } else if (!["auto", "single", "moa"].includes(pathHint)) {
    forcePath = "auto";
  }

  const selectedProvider = globalProviderEl.value;
  const globalModel = selectedProvider
    ? { provider: selectedProvider, model: globalModelEl.value }
    : null;

  return {
    session_id: state.sessionId,
    prompt,
    force_path: forcePath,
    constraints,
    global_model: globalModel,
    preset_id: presetSelectEl.value || null,
    agent_overrides: collectAgentOverrides(),
  };
}

async function sendPrompt() {
  const prompt = promptInputEl.value.trim();
  if (!prompt) return;
  if (!state.sessionId) {
    await createSession();
  }

  messagesEl.querySelector(".welcome-card")?.remove();
  appendUserMessage(prompt);
  promptInputEl.value = "";
  highlightGraphForPrompt(prompt);

  const loadingEl = appendLoadingMessage();
  sendBtnEl.disabled = true;
  sendLabelEl.classList.add("hidden");
  sendSpinnerEl.classList.remove("hidden");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload(prompt)),
    });
    const body = await response.json();
    loadingEl.remove();

    if (!response.ok) {
      appendErrorMessage(typeof body.detail === "object" ? JSON.stringify(body.detail) : body.detail);
      return;
    }

    state.sessionId = body.session_id;
    updateSessionBadge(state.sessionId);
    appendAssistantMessage(body.reply, body.agents || [], body.context_metadata || {});
    updateMetrics(body);
  } catch (error) {
    loadingEl.remove();
    appendErrorMessage(error.message);
  } finally {
    sendBtnEl.disabled = false;
    sendLabelEl.classList.remove("hidden");
    sendSpinnerEl.classList.add("hidden");
  }
}

function fillQuestionFromExample(question) {
  promptInputEl.value = question;
  promptInputEl.focus();
  setPathSelection("rag");
  highlightGraphForPrompt(question);
}

window.fillQuestionFromExample = fillQuestionFromExample;

function renderKnowledgePanel(data) {
  const panel = document.getElementById("knowledge-panel");
  if (!panel) return;
  if (!data?.categories?.length) {
    panel.innerHTML = '<span class="pipeline-empty">RAG 문서 없음</span>';
    return;
  }

  panel.innerHTML = `
    <div class="knowledge-summary">
      총 <strong>${data.total_docs}</strong>개 문서 · <strong>${data.categories.length}</strong>개 카테고리
    </div>
    ${data.categories
      .map((cat) => {
        const border = cat.color || "#6B7280";
        return `
          <details class="knowledge-cat" open>
            <summary class="knowledge-cat-header" style="border-left:3px solid ${border}; background:rgba(255,255,255,0.03)">
              <span class="knowledge-cat-label" style="color:${border}">${escapeHtml(cat.label)}</span>
              <span class="knowledge-cat-badge">${cat.doc_count}</span>
            </summary>
            <div class="knowledge-cat-body">
              <div class="knowledge-docs">
                ${cat.docs
                  .slice(0, 4)
                  .map((doc) => `<div class="knowledge-doc-item">${escapeHtml(doc.title)}</div>`)
                  .join("")}
              </div>
              <div class="knowledge-questions">
                ${(cat.example_questions || [])
                  .map(
                    (question) => `
                      <button class="knowledge-example-q" onclick="fillQuestionFromExample(${JSON.stringify(question)})">
                        ${escapeHtml(question)}
                      </button>
                    `,
                  )
                  .join("")}
              </div>
            </div>
          </details>
        `;
      })
      .join("")}
  `;
}

async function loadKnowledgePanel() {
  try {
    const response = await fetch("/api/rag-knowledge");
    renderKnowledgePanel(await response.json());
  } catch (error) {
    document.getElementById("knowledge-panel").innerHTML = '<span class="pipeline-empty">로딩 실패</span>';
  }
}

function graphNodesForRender() {
  if (!Array.isArray(state.graphData?.nodes)) return [];
  const filter = state.graphFilter;
  return state.graphData.nodes.filter((node) => filter === "all" || node.category === filter || node.type === "category");
}

function graphEdgesForRender(nodeIds) {
  if (!Array.isArray(state.graphData?.edges)) return [];
  const idSet = new Set(nodeIds);
  // D3 forceLink mutates source/target from string → node object; normalise to id string for filtering
  return state.graphData.edges
    .filter((edge) => {
      const src = typeof edge.source === "object" ? edge.source?.id : edge.source;
      const tgt = typeof edge.target === "object" ? edge.target?.id : edge.target;
      return idSet.has(src) && idSet.has(tgt);
    })
    .map((edge) => {
      // Always return fresh objects so D3 doesn't accumulate stale references
      const src = typeof edge.source === "object" ? edge.source.id : edge.source;
      const tgt = typeof edge.target === "object" ? edge.target.id : edge.target;
      return { ...edge, source: src, target: tgt };
    });
}

function colorForNode(node) {
  return GRAPH_CATEGORY_COLORS[node.category] || "#94A3B8";
}

function renderGraphDetail(node) {
  if (!node) {
    graphDetailEl.innerHTML = '<span class="pipeline-empty">Select a node to inspect graph details.</span>';
    return;
  }

  const related = Array.isArray(node.doc_refs) ? node.doc_refs : [];
  graphDetailEl.innerHTML = `
    <div class="graph-node-title">
      <span>${escapeHtml(node.label)}</span>
      <span class="graph-node-chip">${escapeHtml(node.type)}</span>
    </div>
    <div class="graph-node-meta">
      <span class="graph-node-chip">${escapeHtml(node.category || "uncategorized")}</span>
      ${node.filename ? `<span class="graph-node-chip">${escapeHtml(node.filename)}</span>` : ""}
      ${related.length ? `<span class="graph-node-chip">${related.length} refs</span>` : ""}
    </div>
    <div>${escapeHtml((node.doc_refs || []).slice(0, 4).join(", ") || "No linked docs")}</div>
    <div class="graph-node-actions">
      <button class="graph-node-button" type="button" onclick="useGraphNodePrompt(${JSON.stringify(node.label)})">Ask about this</button>
    </div>
  `;
}

function useGraphNodePrompt(label) {
  promptInputEl.value = label;
  promptInputEl.focus();
  setPathSelection("rag");
  highlightGraphForPrompt(label);
}

window.useGraphNodePrompt = useGraphNodePrompt;

function syncGraphExpandButton() {
  if (!graphExpandBtnEl) return;
  const expanded = document.body.classList.contains("graph-focus-mode");
  graphExpandBtnEl.textContent = expanded ? "닫기" : "크게 보기";
  graphExpandBtnEl.setAttribute("aria-pressed", expanded ? "true" : "false");
}

function toggleGraphFocusMode(forceValue) {
  const nextValue = typeof forceValue === "boolean"
    ? forceValue
    : !document.body.classList.contains("graph-focus-mode");
  document.body.classList.toggle("graph-focus-mode", nextValue);
  state.graphTransform = null;
  syncGraphExpandButton();
  requestAnimationFrame(() => renderKnowledgeGraph());
}

function graphZoomIdentityFromState() {
  if (!state.graphTransform || !window.d3) return null;
  return window.d3.zoomIdentity
    .translate(state.graphTransform.x, state.graphTransform.y)
    .scale(state.graphTransform.k);
}

function defaultGraphTransform(width, height) {
  if (!window.d3) return null;
  const isAll = state.graphFilter === "all";
  const isFocused = document.body.classList.contains("graph-focus-mode");
  const scale = isAll ? (isFocused ? 0.86 : 0.74) : (isFocused ? 1.02 : 0.92);
  const translateX = (width - width * scale) / 2;
  const translateY = (height - height * scale) / 2;
  return window.d3.zoomIdentity.translate(translateX, translateY).scale(scale);
}

function renderKnowledgeGraph() {
  const container = graphCanvasEl;
  if (!container) return;
  if (!state.graphData || !window.d3) {
    container.innerHTML = '<div class="knowledge-loading">Graph unavailable</div>';
    return;
  }

  const nodes = graphNodesForRender();
  const nodeIds = nodes.map((node) => node.id);
  const edges = graphEdgesForRender(nodeIds);
  if (!nodes.length) {
    container.innerHTML = '<div class="knowledge-loading">No graph nodes for this filter.</div>';
    return;
  }

  container.innerHTML = "";
  const width = Math.max(container.clientWidth || 320, 320);
  const height = Math.max(container.clientHeight || 360, 360);
  const scale = width >= 560 ? 1.35 : width >= 420 ? 1.15 : 1;
  const svg = window.d3
    .select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("role", "img")
    .attr("aria-label", "Knowledge graph. Drag to pan and use the mouse wheel to zoom.");

  const viewport = svg.append("g").attr("class", "graph-viewport");

  const simulation = window.d3
    .forceSimulation(nodes.map((node) => ({ ...node })))
    .force("link", window.d3.forceLink(edges).id((item) => item.id).distance((edge) => edge.relation === "contains" ? 48 * scale : 76 * scale))
    .force("charge", window.d3.forceManyBody().strength(-130 * scale))
    .force("center", window.d3.forceCenter(width / 2, height / 2))
    .force("collision", window.d3.forceCollide().radius((node) => node.type === "category" ? 20 * scale : 14 * scale));

  const highlighted = new Set(state.graphHighlights);

  const link = viewport
    .append("g")
    .attr("stroke", "rgba(255,255,255,0.18)")
    .selectAll("line")
    .data(edges)
    .enter()
    .append("line")
    .attr("stroke-width", (edge) => Math.max(1, edge.weight * 2.2));

  const node = viewport
    .append("g")
    .selectAll("circle")
    .data(simulation.nodes())
    .enter()
    .append("circle")
    .attr("r", (item) => item.type === "category" ? 13 : item.type === "concept" ? 8 : 9)
    .attr("fill", (item) => colorForNode(item))
    .attr("stroke", (item) => highlighted.has(item.id) ? "#F8FAFC" : "rgba(255,255,255,0.18)")
    .attr("stroke-width", (item) => highlighted.has(item.id) ? 2.5 : 1)
    .style("cursor", "pointer")
    .on("click", (_event, item) => renderGraphDetail(item));

  const labels = viewport
    .append("g")
    .selectAll("text")
    .data(simulation.nodes())
    .enter()
    .append("text")
    .text((item) => item.label)
    .attr("font-size", width >= 560 ? 10 : 9)
    .attr("fill", "rgba(255,255,255,0.82)")
    .attr("pointer-events", "none");

  simulation.on("tick", () => {
    link
      .attr("x1", (item) => item.source.x)
      .attr("y1", (item) => item.source.y)
      .attr("x2", (item) => item.target.x)
      .attr("y2", (item) => item.target.y);

    node
      .attr("cx", (item) => item.x)
      .attr("cy", (item) => item.y);

    labels
      .attr("x", (item) => item.x + 10)
      .attr("y", (item) => item.y + 3);
  });

  const zoom = window.d3
    .zoom()
    .scaleExtent([0.45, 2.6])
    .on("start", () => svg.classed("is-dragging", true))
    .on("zoom", (event) => {
      viewport.attr("transform", event.transform);
      state.graphTransform = {
        x: event.transform.x,
        y: event.transform.y,
        k: event.transform.k,
      };
    })
    .on("end", () => svg.classed("is-dragging", false));

  svg.call(zoom);
  svg.on("dblclick.zoom", null);
  svg.call(zoom.transform, graphZoomIdentityFromState() || defaultGraphTransform(width, height));

  const legend = document.createElement("div");
  legend.className = "graph-legend";
  legend.innerHTML = Object.entries(GRAPH_CATEGORY_COLORS)
    .map(
      ([key, color]) => `
        <span class="graph-legend-item">
          <span class="graph-legend-swatch" style="background:${color}"></span>${escapeHtml(key)}
        </span>
      `,
    )
    .join("");
  container.appendChild(legend);
}

function updateGraphHighlights(graphMeta = {}) {
  state.graphHighlights = Array.isArray(graphMeta.highlighted_node_ids) ? graphMeta.highlighted_node_ids : [];
  if (graphMeta.highlighted_nodes?.length) {
    renderGraphDetail(graphMeta.highlighted_nodes[0]);
  }
  renderKnowledgeGraph();
}

async function loadKnowledgeGraph() {
  try {
    const response = await fetch("/api/knowledge-graph");
    if (!response.ok) {
      throw new Error(`Knowledge graph endpoint returned ${response.status}`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload?.nodes) || !Array.isArray(payload?.edges)) {
      throw new Error("Knowledge graph payload is missing nodes or edges");
    }
    state.graphTransform = null;
    state.graphBaseData = payload;
    state.graphData = state.graphBaseData;
    renderKnowledgeGraph();
  } catch (error) {
    state.graphBaseData = null;
    state.graphData = null;
    graphCanvasEl.innerHTML = '<div class="knowledge-loading">Graph load failed</div>';
  }
}

async function highlightGraphForPrompt(query) {
  if (!query) return;
  try {
    const response = await fetch(`/api/knowledge-graph/highlight?query=${encodeURIComponent(query)}`);
    const payload = await response.json();
    state.graphHighlights = (payload.matches || []).map((item) => item.id);
    renderKnowledgeGraph();
  } catch (error) {
    // Ignore graph highlight failures.
  }
}

async function loadWikiStatus() {
  try {
    const response = await fetch("/api/wiki/status");
    if (!response.ok) {
      throw new Error(`Wiki status endpoint returned ${response.status}`);
    }
    renderWikiStatus(await response.json());
  } catch (error) {
    renderWikiStatus({ pending_count: 0, approved_count: 0, latest_entries: [] });
  }
}

pathSegmentedEl.addEventListener("click", (event) => {
  const button = event.target.closest(".seg-btn");
  if (!button) return;
  setPathSelection(button.dataset.value);
});

globalProviderEl.addEventListener("change", syncGlobalModelSelect);
sendBtnEl.addEventListener("click", sendPrompt);
document.getElementById("new-session-btn").addEventListener("click", createSession);
graphFilterEl.addEventListener("change", () => {
  state.graphFilter = graphFilterEl.value;
  state.graphTransform = null;
  renderKnowledgeGraph();
});

graphExpandBtnEl?.addEventListener("click", () => {
  toggleGraphFocusMode();
});

window.addEventListener("resize", () => {
  if (state.graphData) {
    renderKnowledgeGraph();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && document.body.classList.contains("graph-focus-mode")) {
    toggleGraphFocusMode(false);
  }
});

promptInputEl.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    event.preventDefault();
    sendPrompt();
  }
});

setPathSelection("auto");
syncGraphExpandButton();
loadRegistry().then(async () => {
  await createSession();
  await Promise.all([loadKnowledgePanel(), loadKnowledgeGraph(), loadWikiStatus()]);
});
