"""검색 결과를 프롬프트 주입용 컨텍스트로 변환하는 빌더."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def estimate_tokens(text: str) -> int:
    """간단한 토큰 수 추정."""
    return max(1, len(text) // 4) if text else 0


class ContextBuilder:
    """검색 결과를 source label이 포함된 문자열로 정규화."""

    def __init__(self, injection_top_k: int = 3, max_context_tokens: int = 1200):
        self.injection_top_k = injection_top_k
        self.max_context_tokens = max_context_tokens

    def build(self, items: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        sections: list[str] = []
        selected_chunks: list[dict[str, Any]] = []
        seen_texts: set[str] = set()
        total_tokens = 0

        for item in items:
            if len(selected_chunks) >= self.injection_top_k:
                break

            text = item.get("text", "").strip()
            if not text or text in seen_texts:
                continue

            source_path = item.get("source_path", "")
            source_name = Path(source_path).name if source_path else item.get("title", "unknown")
            chunk_id = item.get("chunk_id", "?")
            label = f"[참고 문서 {len(selected_chunks) + 1} | {source_name} | chunk {chunk_id}]"
            section = f"{label}\n{text}"
            estimated_tokens = estimate_tokens(section)

            if selected_chunks and total_tokens + estimated_tokens > self.max_context_tokens:
                break

            sections.append(section)
            total_tokens += estimated_tokens
            seen_texts.add(text)

            selected_chunks.append({
                "label": label,
                "doc_id": item.get("doc_id"),
                "source_path": source_path,
                "chunk_id": chunk_id,
                "raw_distance": item.get("raw_distance"),
                "normalized_relevance": item.get("normalized_relevance"),
                "text": text,
            })

        metadata = {
            "selected_chunks": selected_chunks,
            "context_token_estimate": total_tokens,
            "selected_count": len(selected_chunks),
        }
        return "\n\n".join(sections), metadata
