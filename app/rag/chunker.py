"""간단한 텍스트 청커(SimpleChunker).

문서를 일정 크기의 겹치는 청크로 분할하여 RAG에서 사용합니다.
청크 크기와 오버랩은 생성자에서 조정 가능합니다.
"""

from typing import List


class SimpleChunker:
    """텍스트를 고정 크기(문자 수 기준)의 청크로 분할.

    overlap는 이전 청크와 겹치는 문자 수입니다.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """주어진 텍스트를 청크 리스트로 반환한다.

        간단한 구현이므로 문장 경계는 고려하지 않고 문자 단위로 분할합니다.
        """
        if not text:
            return []

        chunks: List[str] = []
        i = 0
        L = len(text)
        while i < L:
            end = i + self.chunk_size
            chunks.append(text[i:end])
            i = end - self.overlap
            if i < 0:
                i = 0

        return chunks
