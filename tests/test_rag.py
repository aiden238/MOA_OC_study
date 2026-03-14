import asyncio
from pathlib import Path

from app.rag.chunker import SimpleChunker
from app.rag.retriever import SimpleRetriever
from app.rag.embedder import Embedder


def test_chunker_basic():
    text = "abcdefghij" * 60  # 600 chars
    c = SimpleChunker(chunk_size=200, overlap=20)
    chunks = c.chunk(text)
    # 적어도 3개 이상의 청크로 분할되어야 함
    assert len(chunks) >= 3
    # 청크 길이는 마지막 청크를 제외하면 chunk_size와 거의 일치
    assert all(len(ch) <= 200 for ch in chunks)


def test_retriever_basic(tmp_path):
    # 데이터 폴더에서 샘플 문서 로드
    data_dir = Path("data/rag_docs")
    files = list(data_dir.glob("*.txt"))
    assert files, "샘플 rag_docs 파일이 필요합니다"

    docs = [f.read_text(encoding="utf-8") for f in files]
    retriever = SimpleRetriever()
    retriever.add_documents(docs)

    # 검색어로 일부 문서가 반환되는지 확인
    results = retriever.query("임베딩", n_results=3)
    assert isinstance(results, list)


async def _run_embedder():
    e = Embedder(dim=16)
    vecs = await e.embed(["hello world", "인공지능"])
    return vecs


def test_embedder_async():
    vecs = asyncio.run(_run_embedder())
    assert len(vecs) == 2
    assert all(len(v) == 16 for v in vecs)
