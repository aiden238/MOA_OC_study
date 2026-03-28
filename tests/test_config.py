"""Configuration resolution tests."""

from app.core.config import resolve_embedding_settings, resolve_llm_settings


class TestResolveLLMSettings:
    def test_default_runtime_is_openai(self):
        settings = resolve_llm_settings()
        assert settings["provider"] == "openai"
        assert settings["model"]
        assert settings["base_url"] == "https://api.openai.com/v1"
        assert settings["api_key"] == "test-openai-key"

    def test_agent_specific_gemini_override(self, monkeypatch):
        monkeypatch.setenv("DRAFT_ANALYTICAL_MODEL_PROVIDER", "gemini")
        monkeypatch.setenv("DRAFT_ANALYTICAL_MODEL", "gemini-2.5-flash")

        settings = resolve_llm_settings(agent_name="draft_analytical")

        assert settings["provider"] == "gemini"
        assert settings["model"] == "gemini-2.5-flash"
        assert settings["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"
        assert settings["api_key"] == "test-gemini-key"

    def test_eval_alias_uses_xai(self, monkeypatch):
        monkeypatch.setenv("EVAL_MODEL_PROVIDER", "grok")
        monkeypatch.setenv("EVAL_MODEL", "grok-4")

        settings = resolve_llm_settings(agent_name="rubric_judge")

        assert settings["provider"] == "xai"
        assert settings["model"] == "grok-4"
        assert settings["base_url"] == "https://api.x.ai/v1"
        assert settings["api_key"] == "test-xai-key"


class TestResolveEmbeddingSettings:
    def test_embedding_defaults_to_openai(self):
        settings = resolve_embedding_settings()
        assert settings["provider"] == "openai"
        assert settings["model"] == "text-embedding-3-small"
        assert settings["base_url"] == "https://api.openai.com/v1"
