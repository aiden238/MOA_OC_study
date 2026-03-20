"""RAG 임베더 구현.

- `Embedder`: 테스트/로컬 폴백용 해시 기반 임베더
- `OpenAIEmbedder`: 실제 실행용 OpenAI embeddings API 래퍼
"""

from __future__ import annotations

import hashlib
from typing import List

import httpx

from app.core.config import EMBEDDING_MODEL, OPENAI_API_KEY


def _estimate_token_count(text: str) -> int:
    """대략적인 토큰 수 추정."""
    return max(1, len(text) // 4) if text else 0


class Embedder:
    """해시 기반 임베더.

    의미론적 유사도는 보장하지 않지만, 테스트와 로컬 폴백에서는 충분하다.
    """

    model_name = "hash-embedder"

    def __init__(self, dim: int = 64):
        self.dim = dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [float(b) / 255.0 for b in h[: self.dim]]
            if len(vec) < self.dim:
                vec += [0.0] * (self.dim - len(vec))
            vectors.append(vec[: self.dim])
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
    """OpenAI embeddings API 기반 임베더."""

    EMBEDDING_PRICING_PER_TOKEN = {
        "text-embedding-3-small": 0.02 / 1_000_000,
    }

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors, _ = await self.embed_with_usage(texts)
        return vectors

    async def embed_with_usage(self, texts: List[str]) -> tuple[List[List[float]], dict]:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY가 없어 OpenAI 임베딩을 호출할 수 없습니다.")
        if not texts:
            return [], {"model": self.model_name, "input_tokens": 0, "cost_estimate": 0.0}

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        vectors = [item["embedding"] for item in data.get("data", [])]
        usage = data.get("usage", {})
        input_tokens = usage.get("total_tokens", sum(_estimate_token_count(text) for text in texts))
        token_rate = self.EMBEDDING_PRICING_PER_TOKEN.get(self.model_name, 0.0)
        cost_estimate = round(input_tokens * token_rate, 6)
        return vectors, {
            "model": self.model_name,
            "input_tokens": input_tokens,
            "cost_estimate": cost_estimate,
        }
