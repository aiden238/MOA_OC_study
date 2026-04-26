const state = {
  sessionId: null,
  registry: null,
  agentNames: [],
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

const AGENT_TAG = {
  single_baseline: { label: "단일", cls: "router" },
  router: { label: "라우터", cls: "router" },
  draft_analytical: { label: "분석 초안", cls: "draft" },
  draft_creative: { label: "창의 초안", cls: "draft" },
  draft_structured: { label: "구조 초안", cls: "draft" },
  critic: { label: "비평", cls: "critic" },
  judge: { label: "판단", cls: "judge" },
  rewrite: { label: "재작성", cls: "rewrite" },
  synthesizer: { label: "합성", cls: "synth" },
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
    return fromMeta
      .map((item) => ({
        source: item?.source || "unknown",
        score: typeof item?.score === "number" ? item.score : null,
      }))
      .filter((item) => item.source);
  }

  const selectedChunks = Array.isArray(contextMeta?.rag?.selected_chunks)
    ? contextMeta.rag.selected_chunks
    : [];
  const seen = new Map();
  for (const chunk of selectedChunks) {
    const source = chunk?.source || chunk?.source_path?.split(/[\\/]/).pop() || "unknown";
    const rawScore = chunk?.score ?? chunk?.normalized_relevance;
    const score = typeof rawScore === "number" ? rawScore : null;
    const current = seen.get(source);
    if (current == null || (score != null && score > current)) {
      seen.set(source, score);
    }
  }
  return Array.from(seen.entries())
    .map(([source, score]) => ({ source, score }))
    .sort((left, right) => {
      const leftScore = left.score == null ? -1 : left.score;
      const rightScore = right.score == null ? -1 : right.score;
      return rightScore - leftScore || left.source.localeCompare(right.source);
    });
}

function resetMetricsPanel() {
  document.getElementById("m-path").textContent = "—";
  document.getElementById("m-latency").textContent = "—";
  document.getElementById("m-prompt-tok").textContent = "—";
  document.getElementById("m-comp-tok").textContent = "—";
  document.getElementById("m-cost").textContent = "—";
  document.getElementById("m-agents").textContent = "—";
  document.getElementById("pipeline-viz").innerHTML = '<span class="pipeline-empty">응답 후 표시됩니다</span>';
  document.getElementById("model-map").innerHTML = '<span class="pipeline-empty">—</span>';
  document.getElementById("trace-path").textContent = "—";
  renderRagPanel({});
  renderMcpPanel({});
}

function updateSessionBadge(sessionId) {
  if (!sessionId) {
    sessionBadgeEl.textContent = "세션 없음";
    return;
  }
  sessionBadgeEl.textContent = `세션 ${sessionId.slice(0, 8)}…`;
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
      <div class="msg-avatar">나</div>
      <span>나</span>
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

  const failedAgents = Array.isArray(contextMeta.failed_agents) ? contextMeta.failed_agents : [];
  const failedWarningHtml = failedAgents.length
    ? `<div class="msg-agent-warning">⚠ 드랍된 에이전트: ${failedAgents
        .map(({ agent_name, reason }) => {
          const { label } = agentInfo(agent_name);
          const short = reason.includes("429") ? "쿼터 초과" :
                        reason.includes("404") ? "모델 없음" :
                        reason.includes("401") ? "인증 오류" : "API 오류";
          return `<span class="agent-tag agent-failed" title="${escapeHtml(reason)}">${label}(${short})</span>`;
        })
        .join(" ")}
      </div>`
    : "";

  const ragSources = normalizeRagSources(contextMeta);
  const ragHtml = ragSources.length
    ? `
      <div class="msg-rag-sources">
        <span class="rag-label">RAG 참고 문서</span>
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
    ${failedWarningHtml}
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
      <span>오류</span>
    </div>
    <div class="msg-bubble" style="color: var(--accent-red)">⚠ ${escapeHtml(detail)}</div>
  `;
  appendNode(wrapper);
}

function renderPipelineViz(agentsList, failedAgents = []) {
  const element = document.getElementById("pipeline-viz");
  if (!agentsList.length && !failedAgents.length) {
    element.innerHTML = '<span class="pipeline-empty">응답 후 표시됩니다</span>';
    return;
  }

  const ordered = PIPELINE_ORDER.filter((name) => agentsList.includes(name));
  const rest = agentsList.filter((name) => !PIPELINE_ORDER.includes(name));
  const steps = [...ordered, ...rest];

  const activeHtml = steps
    .map((name, index) => {
      const { label, cls } = agentInfo(name);
      const arrow = index < steps.length - 1 ? '<span class="pipeline-arrow">→</span>' : "";
      return `<span class="pipeline-step agent-tag ${cls}">${label}</span>${arrow}`;
    })
    .join("");

  const failedHtml = failedAgents
    .map(({ agent_name, reason }) => {
      const { label } = agentInfo(agent_name);
      const shortReason = reason.includes("429") ? "쿼터 초과" :
                          reason.includes("404") ? "모델 없음" :
                          reason.includes("401") ? "인증 오류" : "API 오류";
      return `<span class="pipeline-step agent-tag agent-failed" title="${escapeHtml(reason)}">⚠ ${label}(${shortReason})</span>`;
    })
    .join("");

  element.innerHTML = activeHtml + (failedHtml ? `<span class="pipeline-sep"> | </span>${failedHtml}` : "");
}

function renderModelMap(selectedModels) {
  const element = document.getElementById("model-map");
  const entries = Object.entries(selectedModels).filter(([, info]) => info?.active);

  if (!entries.length) {
    element.innerHTML = '<span class="pipeline-empty">—</span>';
    return;
  }

  element.innerHTML = entries
    .map(([agentName, info]) => {
      const { label, cls } = agentInfo(agentName);
      const provider = info.provider || "";
      const model = info.model || "?";
      const display = provider ? `${provider}/${model}` : model;
      return `
        <div class="model-row is-active">
          <span class="model-row-agent agent-tag ${cls}">${label}</span>
          <span class="model-row-model">${escapeHtml(display)}</span>
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

  const hitCount = retrieval.hit_count ?? 0;
  const selectedCount = ragMeta.selected_count ?? ragSources.length ?? 0;
  const tokenEstimate = ragMeta.token_estimate ?? ragMeta.context_token_estimate ?? 0;

  if (!ragSources.length && !hitCount) {
    panelEl.innerHTML = '<span class="pipeline-empty">이번 응답에서 RAG 미사용</span>';
    return;
  }

  let html = `
    <div class="rag-stat-row">
      <span>검색 히트</span>
      <span class="rag-stat-val">${hitCount}</span>
    </div>
    <div class="rag-stat-row">
      <span>선택 청크</span>
      <span class="rag-stat-val">${selectedCount}</span>
    </div>
    <div class="rag-stat-row">
      <span>토큰 추정</span>
      <span class="rag-stat-val">${tokenEstimate}</span>
    </div>
  `;

  if (ragSources.length) {
    html += ragSources
      .map(({ source, score }) => `
        <div class="rag-source-item">
          <span class="rag-source-name" title="${escapeHtml(source)}">${escapeHtml(source)}</span>
          <span class="rag-source-score">${score != null ? Number(score).toFixed(2) : "—"}</span>
        </div>
      `)
      .join("");
  }

  panelEl.innerHTML = html;
}

function renderMcpPanel(contextMeta = {}) {
  const panelEl = document.getElementById("mcp-panel");
  const mcp = contextMeta.mcp;
  if (!mcp?.tool_name) {
    panelEl.innerHTML = '<span class="pipeline-empty">이번 응답에서 MCP 미사용</span>';
    return;
  }

  const success = mcp.success !== false;
  const statusClass = success ? "success" : "failure";
  const statusText = success ? "성공" : "실패";
  const summary = String(mcp.normalized_result_summary || "").slice(0, 200);

  panelEl.innerHTML = `
    <div class="mcp-tool-card">
      <div class="mcp-tool-header">
        <span class="mcp-tool-name">${escapeHtml(mcp.tool_name)}</span>
        <span class="mcp-tool-status ${statusClass}">${statusText}</span>
      </div>
      ${mcp.server_name
        ? `<span class="mcp-tool-server">${escapeHtml(mcp.server_name)}</span>`
        : ""}
      ${summary
        ? `<div class="mcp-tool-summary">${escapeHtml(summary)}${summary.length >= 200 ? "…" : ""}</div>`
        : '<div class="mcp-tool-summary">요약 없음</div>'}
    </div>
  `;
}

function updateMetrics(response) {
  const metrics = response.metrics || {};
  const path = response.path || "—";
  const pathElement = document.getElementById("m-path");
  pathElement.innerHTML =
    path === "—"
      ? "—"
      : `<span class="path-badge ${pathBadgeClass(path)}">${escapeHtml(path)}</span>`;

  document.getElementById("m-latency").textContent =
    metrics.latency_ms != null ? `${metrics.latency_ms} ms` : "—";
  document.getElementById("m-prompt-tok").textContent = metrics.prompt_tokens ?? "—";
  document.getElementById("m-comp-tok").textContent = metrics.completion_tokens ?? "—";
  document.getElementById("m-cost").textContent =
    metrics.cost_estimate != null ? `$${Number(metrics.cost_estimate).toFixed(5)}` : "—";
  document.getElementById("m-agents").textContent =
    Array.isArray(response.agents) && response.agents.length ? response.agents.length : "—";

  const failedAgents = response.context_metadata?.failed_agents || [];
  renderPipelineViz(response.agents || [], failedAgents);
  renderModelMap(response.selected_models || {});
  renderRagPanel(response.context_metadata || {});
  renderMcpPanel(response.context_metadata || {});
  document.getElementById("trace-path").textContent = response.trace_path || "—";
}

function modelOptionsForProvider(providerId) {
  return (state.registry?.models || []).filter((model) => model.provider === providerId);
}

function fillModelSelect(selectEl, providerId, selectedValue = "") {
  selectEl.innerHTML = "";
  for (const model of modelOptionsForProvider(providerId)) {
    const option = document.createElement("option");
    option.value = model.model;
    option.textContent = model.label + (model.available ? "" : " (사용불가)");
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
    globalModelEl.innerHTML = '<option value="">— 기본값 사용 —</option>';
    globalModelEl.disabled = true;
    return;
  }
  globalModelEl.disabled = false;
  fillModelSelect(globalModelEl, providerId);
}

function renderProviderControls() {
  globalProviderEl.innerHTML = '<option value="">— 에이전트별 기본값 —</option>';
  for (const provider of state.registry.providers) {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = provider.label + (provider.available ? "" : " (사용불가)");
    option.disabled = !provider.available;
    globalProviderEl.appendChild(option);
  }
  globalProviderEl.value = "";
  syncGlobalModelSelect();
}

function renderPresets() {
  presetSelectEl.innerHTML = '<option value="">— 없음 —</option>';
  for (const preset of state.registry.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label + (preset.available ? "" : " (사용불가)");
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
      option.textContent = provider.label + (provider.available ? "" : " (사용불가)");
      option.disabled = !provider.available;
      providerSelect.appendChild(option);
    }

    providerSelect.value = "openai";
    fillModelSelect(modelSelect, "openai");

    checkbox.addEventListener("change", () => {
      const enabled = checkbox.checked;
      providerSelect.disabled = !enabled;
      modelSelect.disabled = !enabled;
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
    if (!checkbox?.checked) {
      continue;
    }
    const provider = document.querySelector(`[data-agent-provider="${agentName}"]`).value;
    const model = document.querySelector(`[data-agent-model="${agentName}"]`).value;
    overrides[agentName] = { provider, model };
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
      <div class="welcome-icon">⬡</div>
      <h2>MOA Lab에 오신 것을 환영합니다</h2>
      <p>단일 LLM 호출부터 멀티 에이전트 오케스트레이션, RAG, MCP까지<br/>다양한 실행 경로로 AI 응답을 비교 실험합니다.</p>
      <div class="welcome-chips">
        <span class="chip">Draft × 3</span>
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
  state.agentNames = state.registry.agents.filter(
    (name) => !["single_baseline", "rubric_judge"].includes(name),
  );
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
  if (!prompt) {
    return;
  }

  if (!state.sessionId) {
    await createSession();
  }

  messagesEl.querySelector(".welcome-card")?.remove();
  appendUserMessage(prompt);
  promptInputEl.value = "";

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
      const detail = typeof body.detail === "object"
        ? JSON.stringify(body.detail)
        : body.detail;
      appendErrorMessage(detail);
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

pathSegmentedEl.addEventListener("click", (event) => {
  const button = event.target.closest(".seg-btn");
  if (!button) {
    return;
  }
  setPathSelection(button.dataset.value);
});

globalProviderEl.addEventListener("change", syncGlobalModelSelect);
sendBtnEl.addEventListener("click", sendPrompt);
document.getElementById("new-session-btn").addEventListener("click", createSession);

promptInputEl.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.key === "Enter") {
    event.preventDefault();
    sendPrompt();
  }
});

setPathSelection("auto");
loadRegistry().then(createSession);
