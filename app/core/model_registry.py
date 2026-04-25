"""Runtime model registry and request-scoped model resolution helpers."""

from __future__ import annotations

import os
from typing import Any

from app.core.config import resolve_llm_settings
from app.schemas.chat import ModelSelection, SelectedModelInfo


CANONICAL_AGENT_NAMES: tuple[str, ...] = (
    "single_baseline",
    "router",
    "draft_analytical",
    "draft_creative",
    "draft_structured",
    "critic",
    "synthesizer",
    "judge",
    "rewrite",
    "rubric_judge",
)

AGENT_ALIAS_MAP = {
    "single": "single_baseline",
    "single_baseline": "single_baseline",
    "router": "router",
    "draft_analytical": "draft_analytical",
    "draft_creative": "draft_creative",
    "draft_structured": "draft_structured",
    "critic": "critic",
    "synth": "synthesizer",
    "synthesizer": "synthesizer",
    "judge": "judge",
    "rewrite": "rewrite",
    "eval": "rubric_judge",
    "rubric_judge": "rubric_judge",
}

PROVIDER_LABELS = {
    "openai": "OpenAI",
    "gemini": "Gemini",
    "zai": "Z.AI",
}

PROVIDER_KEY_ENV = {
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "zai": ("ZAI_API_KEY", "ZHIPU_API_KEY"),
}

MODEL_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "label": "GPT-4o Mini",
        "category": "default",
        "supports_reasoning": False,
        "supports_temperature": True,
    },
    {
        "provider": "openai",
        "model": "gpt-5-nano",
        "label": "GPT-5 Nano",
        "category": "fast",
        "supports_reasoning": True,
        "supports_temperature": False,
    },
    {
        "provider": "openai",
        "model": "gpt-5-mini",
        "label": "GPT-5 Mini",
        "category": "reasoning",
        "supports_reasoning": True,
        "supports_temperature": False,
    },
    {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "label": "Gemini 2.5 Flash",
        "category": "fast",
        "supports_reasoning": False,
        "supports_temperature": True,
    },
    {
        "provider": "zai",
        "model": "glm-4.7-flash",
        "label": "GLM-4.7 Flash",
        "category": "creative",
        "supports_reasoning": True,
        "supports_temperature": False,
    },
)

PRESET_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "openai_default",
        "label": "OpenAI Default",
        "description": "Use the same OpenAI model across all agents.",
        "global_model": {"provider": "openai", "model": "gpt-4o-mini"},
        "agent_overrides": {},
        "required_providers": ["openai"],
    },
    {
        "id": "low_cost_baseline",
        "label": "Low Cost Baseline",
        "description": "Bias the whole run toward low-cost OpenAI defaults.",
        "global_model": {"provider": "openai", "model": "gpt-5-nano"},
        "agent_overrides": {},
        "required_providers": ["openai"],
    },
    {
        "id": "openai_gemini_drafts",
        "label": "OpenAI + Gemini Drafts",
        "description": "Use Gemini for draft generation while keeping judgment on OpenAI.",
        "global_model": {"provider": "openai", "model": "gpt-4o-mini"},
        "agent_overrides": {
            "draft_analytical": {"provider": "gemini", "model": "gemini-2.5-flash"},
            "draft_structured": {"provider": "gemini", "model": "gemini-2.5-flash"},
        },
        "required_providers": ["openai", "gemini"],
    },
    {
        "id": "openai_zai_creative",
        "label": "OpenAI + Z.AI Creative",
        "description": "Keep control agents on OpenAI and creative draft on Z.AI.",
        "global_model": {"provider": "openai", "model": "gpt-4o-mini"},
        "agent_overrides": {
            "draft_creative": {"provider": "zai", "model": "glm-4.7-flash"},
        },
        "required_providers": ["openai", "zai"],
    },
    {
        "id": "mixed_research_mode",
        "label": "Mixed Research Mode",
        "description": "Distribute work across OpenAI, Gemini, and Z.AI.",
        "global_model": {"provider": "openai", "model": "gpt-4o-mini"},
        "agent_overrides": {
            "draft_analytical": {"provider": "gemini", "model": "gemini-2.5-flash"},
            "draft_creative": {"provider": "zai", "model": "glm-4.7-flash"},
            "draft_structured": {"provider": "openai", "model": "gpt-4o-mini"},
        },
        "required_providers": ["openai", "gemini", "zai"],
    },
)


def canonicalize_agent_name(agent_name: str) -> str:
    normalized = (agent_name or "").strip().lower()
    canonical = AGENT_ALIAS_MAP.get(normalized)
    if canonical is None:
        raise ValueError(f"Unsupported agent override target: {agent_name}")
    return canonical


def _provider_key_configured(provider: str) -> bool:
    # Allow explicit override: {PROVIDER_UPPER}_AVAILABLE=false disables even if key is set
    # Useful for e.g. GEMINI_AVAILABLE=false when key exists but quota is exhausted
    available_flag = os.getenv(f"{provider.upper()}_AVAILABLE", "").strip().lower()
    if available_flag == "false":
        return False
    for env_name in PROVIDER_KEY_ENV.get(provider, ()):
        if os.getenv(env_name):
            return True
    return False


def _provider_unavailable_reason(provider: str) -> str | None:
    available_flag = os.getenv(f"{provider.upper()}_AVAILABLE", "").strip().lower()
    if available_flag == "false":
        label = PROVIDER_LABELS.get(provider, provider)
        return f"{label} is explicitly disabled (set {provider.upper()}_AVAILABLE=false)"
    if _provider_key_configured(provider):
        return None
    label = PROVIDER_LABELS.get(provider, provider)
    return f"{label} API key is not configured"


def _model_entry(provider: str, model: str) -> dict[str, Any] | None:
    provider_norm = (provider or "").strip().lower()
    model_norm = (model or "").strip()
    for entry in MODEL_CATALOG:
        if entry["provider"] != provider_norm:
            continue
        catalog_model = entry["model"]
        # Exact match or versioned suffix match (e.g. "gpt-5-nano-2025-08-07" → "gpt-5-nano")
        if model_norm == catalog_model or model_norm.startswith(catalog_model + "-"):
            return entry
    return None


def _serialize_model_entry(entry: dict[str, Any]) -> dict[str, Any]:
    provider = entry["provider"]
    available = _provider_key_configured(provider)
    return {
        **entry,
        "provider_label": PROVIDER_LABELS.get(provider, provider),
        "available": available,
        "unavailable_reason": _provider_unavailable_reason(provider),
    }


def _serialize_preset_entry(entry: dict[str, Any]) -> dict[str, Any]:
    required = entry.get("required_providers", [])
    unavailable = [
        PROVIDER_LABELS.get(provider, provider)
        for provider in required
        if not _provider_key_configured(provider)
    ]
    return {
        **entry,
        "available": not unavailable,
        "unavailable_reason": ", ".join(unavailable) if unavailable else None,
    }


def get_model_registry_payload() -> dict[str, Any]:
    providers = []
    for provider, label in PROVIDER_LABELS.items():
        providers.append(
            {
                "id": provider,
                "label": label,
                "available": _provider_key_configured(provider),
                "unavailable_reason": _provider_unavailable_reason(provider),
            }
        )
    return {
        "providers": providers,
        "models": [_serialize_model_entry(entry) for entry in MODEL_CATALOG],
        "presets": [_serialize_preset_entry(entry) for entry in PRESET_CATALOG],
        "agents": list(CANONICAL_AGENT_NAMES),
    }


def _coerce_selection(value: ModelSelection | dict[str, Any] | None) -> ModelSelection | None:
    if value is None:
        return None
    if isinstance(value, ModelSelection):
        return value
    return ModelSelection(**value)


def _get_preset_entry(preset_id: str | None) -> dict[str, Any] | None:
    if not preset_id:
        return None
    for entry in PRESET_CATALOG:
        if entry["id"] == preset_id:
            return entry
    raise ValueError(f"Unknown model preset: {preset_id}")


def _validate_explicit_selection(selection: ModelSelection, source: str):
    entry = _model_entry(selection.provider, selection.model)
    if entry is None:
        raise ValueError(
            f"Unsupported model selection for {source}: {selection.provider}/{selection.model}"
        )
    if not _provider_key_configured(selection.provider):
        raise ValueError(
            f"{PROVIDER_LABELS.get(selection.provider, selection.provider)} is unavailable for {source}: "
            f"{_provider_unavailable_reason(selection.provider)}"
        )


def resolve_request_models(
    *,
    global_model: ModelSelection | dict[str, Any] | None = None,
    agent_overrides: dict[str, ModelSelection | dict[str, Any]] | None = None,
    preset_id: str | None = None,
) -> dict[str, Any]:
    """Resolve request-scoped model configuration for all runtime agents."""

    selected_global = _coerce_selection(global_model)
    if selected_global is not None:
        _validate_explicit_selection(selected_global, "global_model")

    preset = _get_preset_entry(preset_id)
    preset_global = _coerce_selection(preset["global_model"]) if preset else None
    if preset_global is not None:
        _validate_explicit_selection(preset_global, f"preset:{preset_id}")

    preset_overrides: dict[str, ModelSelection] = {}
    if preset:
        for agent_name, selection in preset.get("agent_overrides", {}).items():
            preset_overrides[canonicalize_agent_name(agent_name)] = _coerce_selection(selection)  # type: ignore[assignment]
            _validate_explicit_selection(preset_overrides[canonicalize_agent_name(agent_name)], f"preset:{preset_id}:{agent_name}")

    explicit_overrides: dict[str, ModelSelection] = {}
    for agent_name, selection in (agent_overrides or {}).items():
        resolved_agent_name = canonicalize_agent_name(agent_name)
        explicit_overrides[resolved_agent_name] = _coerce_selection(selection)  # type: ignore[assignment]
        _validate_explicit_selection(explicit_overrides[resolved_agent_name], f"agent_override:{agent_name}")

    resolved_settings: dict[str, dict[str, str]] = {}
    selected_models: dict[str, SelectedModelInfo] = {}
    resolved_provider_map: dict[str, str] = {}
    fallback_reasons: dict[str, str | None] = {}

    for agent_name in CANONICAL_AGENT_NAMES:
        selection = explicit_overrides.get(agent_name)
        source = "env"
        if selection is not None:
            source = "agent_override"
        else:
            selection = preset_overrides.get(agent_name)
            if selection is not None:
                source = "preset_override"
            elif selected_global is not None:
                selection = selected_global
                source = "global_model"
            elif preset_global is not None:
                selection = preset_global
                source = "preset_global"

        if selection is not None:
            settings = resolve_llm_settings(
                agent_name=agent_name,
                provider=selection.provider,
                model=selection.model,
                api_key=selection.api_key,
                base_url=selection.base_url,
            )
        else:
            settings = resolve_llm_settings(agent_name=agent_name)

        resolved_settings[agent_name] = settings
        resolved_provider_map[agent_name] = settings["provider"]
        selected_models[agent_name] = SelectedModelInfo(
            provider=settings["provider"],
            model=settings["model"],
            base_url=settings["base_url"],
            source=source,
            available=bool(settings["api_key"]),
            api_key_configured=bool(settings["api_key"]),
            active=False,
        )
        fallback_reasons[agent_name] = None

    return {
        "settings": resolved_settings,
        "selected_models": selected_models,
        "resolved_provider_map": resolved_provider_map,
        "fallback_reasons": fallback_reasons,
        "preset_id": preset_id,
    }
