"""간이 임베더(Embedder).

실제 서비스에서는 LLM 임베딩 엔드포인트나 ChromaDB의 내장 임베딩을 사용합니다.
여기서는 테스트/로컬 실행을 위해 매우 단순한 수치화 방식을 제공합니다.
"""

from typing import List
import hashlib


class Embedder:
    """텍스트 리스트를 입력받아 고정 길이의 간단한 벡터(list[float])로 변환.

    구현은 단순 해시 기반이며, 실제 의미론적 유사도는 보장하지 않습니다.
    단위 테스트와 데모 목적에만 사용하세요.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # 바이트를 기반으로 고정 길이 벡터 생성
            vec = [float(b) / 255.0 for b in h[: self.dim]]
            # 필요한 경우 차원 맞추기
            if len(vec) < self.dim:
                vec += [0.0] * (self.dim - len(vec))
            vectors.append(vec[: self.dim])
        return vectors
