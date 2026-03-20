"""SimpleRetriever + ChromaRetriever 구현."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, List, Optional

from app.core.config import CHROMA_DIR, RAG_COLLECTION_NAME, RAG_DOCS_DIR
from app.rag.chunker import SimpleChunker
from app.rag.embedder import Embedder, OpenAIEmbedder

try:
    import chromadb
except ImportError:  # pragma: no cover - 설치 여부는 런타임에서 확인
    chromadb = None


def normalize_relevance(raw_distance: float) -> float:
    """Week 7 고정 relevance 변환 공식."""
    return max(0.0, min(1.0, 1.0 - (raw_distance / 2.0)))


class SimpleRetriever:
    """메모리 기반 텍스트 청크 저장 및 검색기."""

    def __init__(self, collection_name: str = "rag_docs"):
        self.collection_name = collection_name
        self._docs: list[dict] = []

    def add_documents(self, docs: List[str], metadatas: Optional[List[dict]] = None):
        """문서 청크들을 저장. metadatas가 주어지면 함께 저장한다."""
        metadatas = metadatas or [{} for _ in docs]
        for i, d in enumerate(docs):
            self._docs.append({"id": f"{len(self._docs)}", "text": d, "meta": metadatas[i]})

    def _score(self, query: str, text: str) -> float:
        qwords = set(query.lower().split())
        twords = set(text.lower().split())
        if not twords:
            return 0.0
        inter = qwords & twords
        score = len(inter) / math.sqrt(max(1, len(twords)))
        return float(score)

    @classmethod
    def from_directory(
        cls,
        docs_dir: Path | None = None,
        chunker: SimpleChunker | None = None,
    ) -> "SimpleRetriever":
        """로컬 rag_docs 디렉토리에서 retriever를 구성."""
        docs_dir = docs_dir or RAG_DOCS_DIR
        chunker = chunker or SimpleChunker()
        retriever = cls()

        for file_path in sorted(docs_dir.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            for chunk_id, chunk_text in enumerate(chunker.chunk(text)):
                start = chunk_id * max(1, chunker.chunk_size - chunker.overlap)
                retriever.add_documents(
                    [chunk_text],
                    [{
                        "doc_id": file_path.stem,
                        "source_path": str(file_path),
                        "chunk_id": chunk_id,
                        "title": file_path.name,
                        "char_start": start,
                        "char_end": start + len(chunk_text),
                    }],
                )
        return retriever

    def query_items(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        """질의어와 유사한 상위 n_results 청크의 구조화 결과를 반환한다."""
        scored = []
        for doc in self._docs:
            score = self._score(query_text, doc["text"])
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored[:n_results]:
            if score <= 0:
                continue
            meta = doc.get("meta", {})
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "doc_id": meta.get("doc_id"),
                "source_path": meta.get("source_path"),
                "chunk_id": meta.get("chunk_id"),
                "title": meta.get("title"),
                "char_start": meta.get("char_start"),
                "char_end": meta.get("char_end"),
                "raw_distance": round(2.0 * (1.0 - min(1.0, score)), 6),
                "normalized_relevance": round(max(0.0, min(1.0, score)), 6),
            })
        return results

    def query(self, query_text: str, n_results: int = 3) -> List[str]:
        """질의어와 유사한 상위 n_results 청크의 텍스트를 반환한다."""
        return [item["text"] for item in self.query_items(query_text, n_results=n_results)]


class ChromaRetriever:
    """Chroma persistent store 기반 retriever."""

    def __init__(
        self,
        persist_directory: Path | None = None,
        collection_name: str = RAG_COLLECTION_NAME,
        embedder: OpenAIEmbedder | Embedder | None = None,
        chunker: SimpleChunker | None = None,
    ):
        if chromadb is None:
            raise RuntimeError("chromadb가 설치되지 않았습니다.")

        self.persist_directory = Path(persist_directory or CHROMA_DIR)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedder = embedder or OpenAIEmbedder()
        self.chunker = chunker or SimpleChunker()
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _build_chunk_records(self, docs_dir: Path) -> list[dict[str, Any]]:
        records = []
        for file_path in sorted(docs_dir.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            chunks = self.chunker.chunk(text)
            for chunk_id, chunk_text in enumerate(chunks):
                start = chunk_id * max(1, self.chunker.chunk_size - self.chunker.overlap)
                records.append({
                    "id": f"{file_path.stem}:{chunk_id}",
                    "text": chunk_text,
                    "metadata": {
                        "doc_id": file_path.stem,
                        "source_path": str(file_path),
                        "chunk_id": chunk_id,
                        "title": file_path.name,
                        "char_start": start,
                        "char_end": start + len(chunk_text),
                    },
                })
        return records

    async def index_directory(self, docs_dir: Path | None = None) -> dict[str, Any]:
        """문서 디렉토리를 읽어 collection에 upsert."""
        docs_dir = docs_dir or RAG_DOCS_DIR
        records = self._build_chunk_records(docs_dir)
        if not records:
            raise RuntimeError("RAG 인덱싱할 문서가 없습니다.")

        documents = [record["text"] for record in records]
        metadatas = [record["metadata"] for record in records]
        ids = [record["id"] for record in records]
        embeddings, usage = await self.embedder.embed_with_usage(documents)

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return {
            "indexed_count": len(records),
            "source_count": len({record["metadata"]["doc_id"] for record in records}),
            "embedding_model": usage.get("model", getattr(self.embedder, "model_name", "unknown")),
            "embedding_tokens": usage.get("input_tokens", 0),
            "embedding_cost_estimate": usage.get("cost_estimate", 0.0),
        }

    async def ensure_indexed(self, docs_dir: Path | None = None) -> dict[str, Any]:
        """collection이 비어 있으면 문서를 인덱싱한다."""
        existing_count = self.collection.count()
        if existing_count > 0:
            return {
                "indexed_count": 0,
                "existing_count": existing_count,
                "embedding_model": getattr(self.embedder, "model_name", "unknown"),
                "embedding_tokens": 0,
                "embedding_cost_estimate": 0.0,
            }
        return await self.index_directory(docs_dir=docs_dir)

    async def query_items(self, query_text: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Chroma collection에서 구조화된 검색 결과를 반환한다."""
        if not query_text.strip():
            return []

        query_embedding, _ = await self.embedder.embed_with_usage([query_text])
        result = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        items: list[dict[str, Any]] = []
        for index, text in enumerate(documents):
            metadata = metadatas[index] or {}
            raw_distance = float(distances[index]) if index < len(distances) else 2.0
            items.append({
                "id": metadata.get("doc_id", f"result-{index}"),
                "text": text,
                "doc_id": metadata.get("doc_id"),
                "source_path": metadata.get("source_path"),
                "chunk_id": metadata.get("chunk_id"),
                "title": metadata.get("title"),
                "char_start": metadata.get("char_start"),
                "char_end": metadata.get("char_end"),
                "raw_distance": round(raw_distance, 6),
                "normalized_relevance": round(normalize_relevance(raw_distance), 6),
            })
        return items
