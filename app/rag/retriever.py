"""간단한 in-memory retriever 구현.

ChromaDB 같은 벡터 DB를 사용하지 않는 환경에서도 RAG 흐름을
테스트할 수 있도록 텍스트 유사도 기반의 검색을 제공합니다.
"""

from typing import List, Optional
from collections import defaultdict
import math


class SimpleRetriever:
    """메모리 기반의 텍스트 청크 저장 및 유사도 검색기.

    검색은 단어 교집합 기반의 단순 스코어링으로 동작합니다.
    """

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

    def query(self, query_text: str, n_results: int = 3) -> List[str]:
        """질의어와 유사한 상위 n_results 청크의 텍스트를 반환한다."""
        scored = []
        for doc in self._docs:
            s = self._score(query_text, doc["text"])
            scored.append((s, doc["text"]))
        scored.sort(key=lambda x: x[0], reverse=True)
        # 상위 n_results의 텍스트만 반환
        return [t for s, t in scored[:n_results] if s > 0]
