"""RAG (Retrieval-Augmented Generation) 관련 모듈 패키지.

현재는 간단한 in-memory retriever와 청킹 로직을 제공하여
외부 DB 없이도 RAG 흐름을 로컬에서 시뮬레이션할 수 있도록 합니다.
"""

from .chunker import SimpleChunker
from .embedder import Embedder
from .retriever import SimpleRetriever

__all__ = ["SimpleChunker", "Embedder", "SimpleRetriever"]
