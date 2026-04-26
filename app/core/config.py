"""Project-wide configuration loaded from .env."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _get_env(key: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Environment variable '{key}' is not set. Check .env.")
    return value or ""


def _normalize_provider(provider: str | None) -> str:
    normalized = (provider or "").lower().strip()
    aliases = {
        "openai": "openai",
        "gemini": "gemini",
        "google": "gemini",
        "xai": "xai",
        "grok": "xai",
        "zai": "zai",
        "zhipu": "zai",
        "glm": "zai",
        "bigmodel": "zai",
        "cerebras": "cerebras",
    }
    return aliases.get(normalized, normalized or "openai")


def _default_api_base(provider: str) -> str:
    normalized = _normalize_provider(provider)
    if normalized == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta/openai"
    if normalized == "xai":
        return "https://api.x.ai/v1"
    if normalized == "zai":
        return "https://open.bigmodel.cn/api/paas/v4"
    if normalized == "cerebras":
        return "https://api.cerebras.ai/v1"
    return "https://api.openai.com/v1"


def _provider_api_key(provider: str) -> str:
    normalized = _normalize_provider(provider)
    if normalized == "gemini":
        return _get_env("GEMINI_API_KEY", _get_env("GOOGLE_API_KEY"))
    if normalized == "xai":
        return _get_env("XAI_API_KEY", _get_env("GROK_API_KEY"))
    if normalized == "zai":
        return _get_env("ZAI_API_KEY", _get_env("ZHIPU_API_KEY"))
    if normalized == "cerebras":
        return _get_env("CEREBRAS_API_KEY")
    return _get_env("OPENAI_API_KEY")


def _provider_api_base(provider: str) -> str:
    normalized = _normalize_provider(provider)
    if normalized == "gemini":
        return _get_env("GEMINI_BASE_URL", _default_api_base(normalized))
    if normalized == "xai":
        return _get_env("XAI_BASE_URL", _get_env("GROK_BASE_URL", _default_api_base(normalized)))
    if normalized == "zai":
        return _get_env("ZAI_BASE_URL", _get_env("ZHIPU_BASE_URL", _default_api_base(normalized)))
    if normalized == "cerebras":
        return _get_env("CEREBRAS_BASE_URL", _default_api_base(normalized))
    return _get_env("OPENAI_BASE_URL", _default_api_base(normalized))


def _agent_env_prefixes(agent_name: str | None) -> tuple[str, ...]:
    if not agent_name:
        return ()

    aliases = {
        "single_baseline": ("SINGLE", "SINGLE_BASELINE"),
        "router": ("ROUTER",),
        "draft_analytical": ("DRAFT_ANALYTICAL",),
        "draft_creative": ("DRAFT_CREATIVE",),
        "draft_structured": ("DRAFT_STRUCTURED",),
        "critic": ("CRITIC",),
        "synthesizer": ("SYNTH", "SYNTHESIZER"),
        "judge": ("JUDGE",),
        "rewrite": ("REWRITE",),
        "rubric_judge": ("EVAL", "RUBRIC_JUDGE"),
    }

    normalized_name = agent_name.upper().replace("-", "_")
    candidates: list[str] = []
    for prefix in (*aliases.get(agent_name, ()), normalized_name):
        if prefix and prefix not in candidates:
            candidates.append(prefix)
    return tuple(candidates)


def _first_prefixed_env(prefixes: tuple[str, ...], suffix: str) -> str:
    for prefix in prefixes:
        value = _get_env(f"{prefix}_{suffix}")
        if value:
            return value
    return ""


OPENAI_API_KEY: str = _get_env("OPENAI_API_KEY")
GEMINI_API_KEY: str = _get_env("GEMINI_API_KEY", _get_env("GOOGLE_API_KEY"))
XAI_API_KEY: str = _get_env("XAI_API_KEY", _get_env("GROK_API_KEY"))
ZAI_API_KEY: str = _get_env("ZAI_API_KEY", _get_env("ZHIPU_API_KEY"))
CEREBRAS_API_KEY: str = _get_env("CEREBRAS_API_KEY")
ANTHROPIC_API_KEY: str = _get_env("ANTHROPIC_API_KEY")

OPENAI_BASE_URL: str = _get_env("OPENAI_BASE_URL", _default_api_base("openai"))
GEMINI_BASE_URL: str = _get_env("GEMINI_BASE_URL", _default_api_base("gemini"))
XAI_BASE_URL: str = _get_env("XAI_BASE_URL", _get_env("GROK_BASE_URL", _default_api_base("xai")))
ZAI_BASE_URL: str = _get_env("ZAI_BASE_URL", _get_env("ZHIPU_BASE_URL", _default_api_base("zai")))
CEREBRAS_BASE_URL: str = _get_env("CEREBRAS_BASE_URL", _default_api_base("cerebras"))

LLM_API_PROVIDER: str = _normalize_provider(_get_env("LLM_API_PROVIDER", "openai"))
DEFAULT_MODEL: str = _get_env("DEFAULT_MODEL", "gpt-4o-mini")
LLM_API_KEY: str = _get_env("LLM_API_KEY") or _provider_api_key(LLM_API_PROVIDER)
LLM_API_BASE_URL: str = _get_env("LLM_API_BASE_URL") or _provider_api_base(LLM_API_PROVIDER)

DEFAULT_TEMPERATURE: float = float(_get_env("DEFAULT_TEMPERATURE", "0.7"))
MAX_TOKENS: int = int(_get_env("MAX_TOKENS", "1024"))
MAX_RETRIES: int = int(_get_env("MAX_RETRIES", "3"))

TRACE_DIR: Path = PROJECT_ROOT / _get_env("TRACE_DIR", "data/traces")
OUTPUT_DIR: Path = PROJECT_ROOT / _get_env("OUTPUT_DIR", "data/outputs")
BENCHMARK_DIR: Path = PROJECT_ROOT / _get_env("BENCHMARK_DIR", "data/benchmarks")
RAG_DOCS_DIR: Path = PROJECT_ROOT / _get_env("RAG_DOCS_DIR", "data/rag_docs")
CHROMA_DIR: Path = PROJECT_ROOT / _get_env("CHROMA_DIR", "data/chroma")

EMBEDDING_API_PROVIDER: str = _normalize_provider(_get_env("EMBEDDING_API_PROVIDER", "openai"))
EMBEDDING_MODEL: str = _get_env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_API_KEY: str = _get_env("EMBEDDING_API_KEY") or _provider_api_key(EMBEDDING_API_PROVIDER)
EMBEDDING_API_BASE_URL: str = _get_env("EMBEDDING_API_BASE_URL") or _provider_api_base(
    EMBEDDING_API_PROVIDER
)
RAG_COLLECTION_NAME: str = _get_env("RAG_COLLECTION_NAME", "rag_docs")


def resolve_llm_settings(
    agent_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    prefixes = _agent_env_prefixes(agent_name)

    resolved_provider = _normalize_provider(
        provider or _first_prefixed_env(prefixes, "MODEL_PROVIDER") or LLM_API_PROVIDER
    )
    resolved_model = model or _first_prefixed_env(prefixes, "MODEL") or DEFAULT_MODEL
    resolved_api_key = (
        api_key
        or _first_prefixed_env(prefixes, "API_KEY")
        or _provider_api_key(resolved_provider)
        or _get_env("LLM_API_KEY")
    )
    resolved_base_url = (
        base_url
        or _first_prefixed_env(prefixes, "API_BASE_URL")
        or _provider_api_base(resolved_provider)
        or _get_env("LLM_API_BASE_URL", _default_api_base(resolved_provider))
    )

    return {
        "provider": resolved_provider,
        "model": resolved_model,
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
    }


def resolve_embedding_settings(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    resolved_provider = _normalize_provider(provider or EMBEDDING_API_PROVIDER)
    resolved_model = model or EMBEDDING_MODEL
    resolved_api_key = api_key or _get_env("EMBEDDING_API_KEY") or _provider_api_key(
        resolved_provider
    )
    resolved_base_url = (
        base_url
        or _get_env("EMBEDDING_API_BASE_URL")
        or _provider_api_base(resolved_provider)
    )

    return {
        "provider": resolved_provider,
        "model": resolved_model,
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
    }
