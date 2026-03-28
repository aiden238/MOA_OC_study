"""RAG embedding helpers."""

from __future__ import annotations

import asyncio
import hashlib
from typing import List

import httpx

from app.core.config import EMBEDDING_MODEL, MAX_RETRIES, resolve_embedding_settings


def _estimate_token_count(text: str) -> int:
    return max(1, len(text) // 4) if text else 0


class Embedder:
    """Deterministic hash embedder used for local fallback tests."""

    model_name = "hash-embedder"

    def __init__(self, dim: int = 64):
        self.dim = dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [float(byte) / 255.0 for byte in digest[: self.dim]]
            if len(vector) < self.dim:
                vector += [0.0] * (self.dim - len(vector))
            vectors.append(vector[: self.dim])
        return vectors

    async def embed_with_usage(self, texts: List[str]) -> tuple[List[List[float]], dict]:
        vectors = await self.embed(texts)
        input_tokens = sum(_estimate_token_count(text) for text in texts)
        return vectors, {
            "model": self.model_name,
            "input_tokens": input_tokens,
            "cost_estimate": 0.0,
        }


class OpenAIEmbedder:
    """Embedder for OpenAI or OpenAI-compatible embeddings endpoints."""

    EMBEDDING_PRICING_PER_TOKEN = {
        "text-embedding-3-small": 0.02 / 1_000_000,
    }

    def __init__(
        self,
        model_name: str | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model_name = model_name or EMBEDDING_MODEL
        self.provider_override = provider
        self.api_key_override = api_key
        self.base_url_override = base_url

    @staticmethod
    def _retryable_status(status_code: int) -> bool:
        if not isinstance(status_code, int):
            return False
        return status_code == 429 or 500 <= status_code < 600

    @staticmethod
    def _retry_delay_seconds(attempt_index: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(1.0, float(retry_after))
                except ValueError:
                    pass
        return min(8.0, float(2 ** attempt_index))

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors, _ = await self.embed_with_usage(texts)
        return vectors

    async def embed_with_usage(self, texts: List[str]) -> tuple[List[List[float]], dict]:
        settings = resolve_embedding_settings(
            provider=self.provider_override,
            model=self.model_name,
            api_key=self.api_key_override,
            base_url=self.base_url_override,
        )
        provider = settings["provider"]
        model_name = settings["model"]
        api_key = settings["api_key"]
        base_url = settings["base_url"]

        if not api_key:
            raise RuntimeError(f"{provider} embedding API key is not configured. Check .env.")
        if not texts:
            return [], {"model": model_name, "input_tokens": 0, "cost_estimate": 0.0}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            attempts = max(1, MAX_RETRIES)
            last_exc: Exception | None = None

            for attempt in range(attempts):
                try:
                    resp = await client.post(
                        f"{base_url.rstrip('/')}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    if self._retryable_status(resp.status_code) and attempt < attempts - 1:
                        await asyncio.sleep(self._retry_delay_seconds(attempt, resp))
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    if (
                        exc.response is not None
                        and self._retryable_status(exc.response.status_code)
                        and attempt < attempts - 1
                    ):
                        await asyncio.sleep(self._retry_delay_seconds(attempt, exc.response))
                        continue
                    raise
                except httpx.RequestError as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        await asyncio.sleep(self._retry_delay_seconds(attempt))
                        continue
                    raise
            else:
                raise RuntimeError("Embedding request failed without a response") from last_exc

        vectors = [item["embedding"] for item in data.get("data", [])]
        usage = data.get("usage", {})
        input_tokens = usage.get(
            "prompt_tokens",
            usage.get("total_tokens", sum(_estimate_token_count(text) for text in texts)),
        )
        token_rate = self.EMBEDDING_PRICING_PER_TOKEN.get(model_name, 0.0)
        cost_estimate = round(input_tokens * token_rate, 6)
        return vectors, {
            "model": model_name,
            "input_tokens": input_tokens,
            "cost_estimate": cost_estimate,
        }
