"""Model registry and request-scoped resolution tests."""

import pytest

from app.core.model_registry import get_model_registry_payload, resolve_request_models
from app.schemas.chat import ModelSelection


class TestGetModelRegistryPayload:
    def test_payload_exposes_week10_registry(self):
        payload = get_model_registry_payload()

        assert {provider["id"] for provider in payload["providers"]} == {"openai", "gemini", "zai"}
        assert "single_baseline" in payload["agents"]
        assert any(model["model"] == "gpt-4o-mini" for model in payload["models"])
        assert any(preset["id"] == "mixed_research_mode" for preset in payload["presets"])


class TestResolveRequestModels:
    def test_global_model_and_agent_override_are_applied(self):
        resolved = resolve_request_models(
            global_model=ModelSelection(provider="openai", model="gpt-5-mini"),
            agent_overrides={
                "draft_creative": ModelSelection(provider="zai", model="glm-4.7-flash")
            },
        )

        assert resolved["settings"]["single_baseline"]["model"] == "gpt-5-mini"
        assert resolved["settings"]["draft_creative"]["provider"] == "zai"
        assert resolved["settings"]["draft_creative"]["model"] == "glm-4.7-flash"
        assert resolved["selected_models"]["single_baseline"].source == "global_model"
        assert resolved["selected_models"]["draft_creative"].source == "agent_override"

    def test_preset_is_applied_to_multiple_agents(self, monkeypatch):
        # Simulate Gemini being available (key present, not explicitly disabled)
        monkeypatch.delenv("GEMINI_AVAILABLE", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

        resolved = resolve_request_models(preset_id="openai_gemini_drafts")

        assert resolved["preset_id"] == "openai_gemini_drafts"
        assert resolved["settings"]["draft_analytical"]["provider"] == "gemini"
        assert resolved["settings"]["draft_structured"]["provider"] == "gemini"
        assert resolved["selected_models"]["draft_analytical"].source == "preset_override"
        assert resolved["selected_models"]["single_baseline"].source == "preset_global"

    def test_unknown_preset_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown model preset"):
            resolve_request_models(preset_id="does_not_exist")

    def test_unavailable_provider_selection_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Gemini is unavailable"):
            resolve_request_models(
                global_model=ModelSelection(provider="gemini", model="gemini-2.5-flash")
            )
