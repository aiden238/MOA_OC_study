"""Shared test environment defaults."""

import pytest


@pytest.fixture(autouse=True)
def _set_test_api_env(monkeypatch):
    monkeypatch.setenv("LLM_API_PROVIDER", "openai")
    monkeypatch.setenv("DEFAULT_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")
    monkeypatch.setenv("XAI_BASE_URL", "https://api.x.ai/v1")
    monkeypatch.setenv("EMBEDDING_API_PROVIDER", "openai")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
