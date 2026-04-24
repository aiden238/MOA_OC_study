const state = {
  sessionId: null,
  registry: null,
  agentNames: [],
};

const messagesEl = document.getElementById("messages");
const metricsEl = document.getElementById("metrics");
const selectedModelsEl = document.getElementById("selected-models");
const sessionInfoEl = document.getElementById("session-info");
const presetSelectEl = document.getElementById("preset-select");
const globalProviderEl = document.getElementById("global-provider");
const globalModelEl = document.getElementById("global-model");
const pathSelectEl = document.getElementById("path-select");
const promptInputEl = document.getElementById("prompt-input");
const agentOverridesEl = document.getElementById("agent-overrides");

function appendMessage(role, content) {
  const item = document.createElement("div");
  item.className = `message ${role}`;
  item.innerHTML = `<strong>${role}</strong><p>${content}</p>`;
  messagesEl.appendChild(item);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderMetrics(response) {
  metricsEl.innerHTML = `
    <dt>Path</dt><dd>${response.path}</dd>
    <dt>Latency</dt><dd>${response.metrics.latency_ms} ms</dd>
    <dt>Prompt Tokens</dt><dd>${response.metrics.prompt_tokens}</dd>
    <dt>Completion Tokens</dt><dd>${response.metrics.completion_tokens}</dd>
    <dt>Cost</dt><dd>$${response.metrics.cost_estimate}</dd>
    <dt>Trace</dt><dd>${response.trace_path || "-"}</dd>
  `;
  selectedModelsEl.textContent = JSON.stringify(response.selected_models, null, 2);
  sessionInfoEl.textContent = `Session: ${response.session_id ?? "-"}`;
}

function modelOptionsForProvider(providerId) {
  return state.registry.models.filter((model) => model.provider === providerId);
}

function fillModelSelect(selectEl, providerId, selectedValue = "") {
  selectEl.innerHTML = "";
  for (const model of modelOptionsForProvider(providerId)) {
    const option = document.createElement("option");
    option.value = model.model;
    option.textContent = model.label + (model.available ? "" : " (Unavailable)");
    option.disabled = !model.available;
    if (model.model === selectedValue) {
      option.selected = true;
    }
    selectEl.appendChild(option);
  }
}

function renderProviderControls() {
  globalProviderEl.innerHTML = "";
  for (const provider of state.registry.providers) {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = provider.label + (provider.available ? "" : " (Unavailable)");
    option.disabled = !provider.available;
    globalProviderEl.appendChild(option);
  }
  if (!globalProviderEl.value) {
    globalProviderEl.value = "openai";
  }
  fillModelSelect(globalModelEl, globalProviderEl.value);
}

function renderPresets() {
  presetSelectEl.innerHTML = '<option value="">None</option>';
  for (const preset of state.registry.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label + (preset.available ? "" : " (Unavailable)");
    option.disabled = !preset.available;
    presetSelectEl.appendChild(option);
  }
}

function renderAgentOverrides() {
  agentOverridesEl.innerHTML = "";
  for (const agentName of state.agentNames) {
    const card = document.createElement("div");
    card.className = "agent-card";
    card.innerHTML = `
      <label class="checkbox-row">
        <input type="checkbox" data-agent-enable="${agentName}" />
        <span>${agentName}</span>
      </label>
      <select data-agent-provider="${agentName}"></select>
      <select data-agent-model="${agentName}"></select>
    `;
    agentOverridesEl.appendChild(card);

    const providerSelect = card.querySelector(`[data-agent-provider="${agentName}"]`);
    const modelSelect = card.querySelector(`[data-agent-model="${agentName}"]`);

    for (const provider of state.registry.providers) {
      const option = document.createElement("option");
      option.value = provider.id;
      option.textContent = provider.label + (provider.available ? "" : " (Unavailable)");
      option.disabled = !provider.available;
      providerSelect.appendChild(option);
    }
    providerSelect.value = "openai";
    fillModelSelect(modelSelect, providerSelect.value);

    providerSelect.addEventListener("change", () => fillModelSelect(modelSelect, providerSelect.value));
  }
}

function collectAgentOverrides() {
  const overrides = {};
  for (const agentName of state.agentNames) {
    const enabled = document.querySelector(`[data-agent-enable="${agentName}"]`).checked;
    if (!enabled) {
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
  messagesEl.innerHTML = "";
  sessionInfoEl.textContent = `Session: ${state.sessionId}`;
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

async function sendPrompt() {
  const prompt = promptInputEl.value.trim();
  if (!prompt) {
    return;
  }

  if (!state.sessionId) {
    await createSession();
  }

  appendMessage("user", prompt);
  promptInputEl.value = "";

  const payload = {
    session_id: state.sessionId,
    prompt,
    force_path: pathSelectEl.value,
    global_model: {
      provider: globalProviderEl.value,
      model: globalModelEl.value,
    },
    preset_id: presetSelectEl.value || null,
    agent_overrides: collectAgentOverrides(),
  };

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();

  if (!response.ok) {
    appendMessage("assistant", `Error: ${JSON.stringify(body.detail)}`);
    return;
  }

  state.sessionId = body.session_id;
  appendMessage("assistant", body.reply);
  renderMetrics(body);
}

globalProviderEl.addEventListener("change", () => {
  fillModelSelect(globalModelEl, globalProviderEl.value);
});
document.getElementById("send-btn").addEventListener("click", sendPrompt);
document.getElementById("new-session-btn").addEventListener("click", createSession);

loadRegistry().then(createSession);
