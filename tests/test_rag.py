import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.logger import TraceLogger
from app.orchestrator.executor import MOAExecutor
from app.orchestrator.router import RoutingDecision
from app.rag.chunker import SimpleChunker
from app.rag.context_builder import ContextBuilder
from app.rag.embedder import Embedder
from app.rag.retriever import ChromaRetriever, SimpleRetriever
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest


class FakeEmbedder:
    model_name = "fake-embedder"

    def _vector_for(self, text: str) -> list[float]:
        lowered = text.lower()
        if "embedding" in lowered:
            return [1.0, 0.0, 0.0]
        if "filesystem" in lowered:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]

    async def embed_with_usage(self, texts: list[str]) -> tuple[list[list[float]], dict]:
        return await self.embed(texts), {
            "model": self.model_name,
            "input_tokens": max(1, sum(len(text) // 4 for text in texts)),
            "cost_estimate": 0.0,
        }


def _mock_output(name: str, content: str = "mock") -> AgentOutput:
    return AgentOutput(
        agent_name=name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
        cost_estimate=0.001,
    )


def test_chunker_basic():
    text = "abcdefghij" * 60
    chunker = SimpleChunker(chunk_size=200, overlap=20)
    chunks = chunker.chunk(text)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 200 for chunk in chunks)


def test_simple_retriever_from_directory():
    retriever = SimpleRetriever.from_directory(Path("data/rag_docs"))
    results = retriever.query_items("임베딩", n_results=3)
    assert isinstance(results, list)


async def _run_embedder():
    embedder = Embedder(dim=16)
    return await embedder.embed(["hello world", "인공지능"])


def test_embedder_async():
    vectors = asyncio.run(_run_embedder())
    assert len(vectors) == 2
    assert all(len(vector) == 16 for vector in vectors)


def test_context_builder_formats_chunks():
    builder = ContextBuilder(injection_top_k=2, max_context_tokens=200)
    context, metadata = builder.build([
        {
            "doc_id": "doc1",
            "source_path": "data/rag_docs/doc1.txt",
            "chunk_id": 0,
            "text": "첫 번째 문서 내용",
            "raw_distance": 0.2,
            "normalized_relevance": 0.9,
        },
        {
            "doc_id": "doc2",
            "source_path": "data/rag_docs/doc2.txt",
            "chunk_id": 1,
            "text": "두 번째 문서 내용",
            "raw_distance": 0.4,
            "normalized_relevance": 0.8,
        },
    ])
    assert "[참고 문서 1 | doc1.txt | chunk 0]" in context
    assert metadata["selected_count"] == 2
    assert metadata["token_estimate"] == metadata["context_token_estimate"]
    assert metadata["total_chunks"] == 2
    assert metadata["selected_chunks"][0]["source"] == "doc1.txt"
    assert metadata["selected_chunks"][0]["score"] == 0.9


@pytest.mark.asyncio
async def test_chroma_retriever_indexes_and_queries(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "doc1.txt").write_text("Embedding retrieval is useful for grounded answers.", encoding="utf-8")
    (docs_dir / "doc2.txt").write_text("Filesystem tools help inspect local project files.", encoding="utf-8")

    retriever = ChromaRetriever(
        persist_directory=tmp_path / "chroma",
        collection_name="test_rag",
        embedder=FakeEmbedder(),
    )
    index_info = await retriever.index_directory(docs_dir)
    hits = await retriever.query_items("embedding question", n_results=3)

    assert index_info["indexed_count"] >= 2
    assert hits
    assert hits[0]["source_path"].endswith("doc1.txt")
    assert 0.0 <= hits[0]["normalized_relevance"] <= 1.0


@pytest.mark.asyncio
async def test_executor_rag_hit_enriches_prompt():
    mock_drafts = [_mock_output("draft_analytical"), _mock_output("draft_creative"), _mock_output("draft_structured")]
    mock_critic = _mock_output("critic", '{"analyses": []}')
    mock_synth = _mock_output("synthesizer", "MOA 최종 결과")
    mock_judge = JudgeDecision(decision="pass", confidence=0.95, reasoning="OK")

    fake_retriever = AsyncMock()
    fake_retriever.embedder = SimpleNamespace(model_name="fake-embedder")
    fake_retriever.collection_name = "rag_docs"
    fake_retriever.ensure_indexed.return_value = {"indexed_count": 2, "source_count": 1, "embedding_tokens": 20, "embedding_cost_estimate": 0.0}
    fake_retriever.query_items.return_value = [{
        "doc_id": "doc1",
        "source_path": "data/rag_docs/doc1.txt",
        "chunk_id": 0,
        "text": "문서 기반 근거 문장",
        "raw_distance": 0.1,
        "normalized_relevance": 0.95,
    }]

    with patch("app.rag.retriever.ChromaRetriever", return_value=fake_retriever), \
         patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
         patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
         patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
         patch("app.orchestrator.executor.JudgeAgent") as MockJudge:

        mock_run_drafts.return_value = mock_drafts
        MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
        MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
        MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))

        executor = MOAExecutor()
        logger = TraceLogger(run_id="rag-hit")
        routing = RoutingDecision(
            selected_path="moa",
            reason="rag hit",
            confidence=0.9,
            requires_rag=True,
            rag_query_hint="문서 기반 질문",
        )
        task = TaskRequest(prompt="원본 질문", task_type="explain")

        final_output, _ = await executor.execute(task, logger, routing=routing)

    assert final_output == "MOA 최종 결과"
    enriched_task = mock_run_drafts.await_args.args[0]
    assert "[참고 문서]" in enriched_task.prompt
    assert "문서 기반 근거 문장" in enriched_task.prompt
    rag_records = [record for record in logger.records if record["operation_type"] == "rag"]
    assert any(record["metadata"]["stage"] == "context_build" for record in rag_records)
    assert logger.records[-1]["path"] == "moa+rag"


@pytest.mark.asyncio
async def test_executor_rag_miss_falls_back_to_plain_moa():
    mock_drafts = [_mock_output("draft_analytical"), _mock_output("draft_creative"), _mock_output("draft_structured")]
    mock_critic = _mock_output("critic", '{"analyses": []}')
    mock_synth = _mock_output("synthesizer", "MOA 최종 결과")
    mock_judge = JudgeDecision(decision="pass", confidence=0.95, reasoning="OK")

    fake_retriever = AsyncMock()
    fake_retriever.embedder = SimpleNamespace(model_name="fake-embedder")
    fake_retriever.collection_name = "rag_docs"
    fake_retriever.ensure_indexed.return_value = {"indexed_count": 0, "source_count": 0, "embedding_tokens": 0, "embedding_cost_estimate": 0.0}
    fake_retriever.query_items.return_value = [{
        "doc_id": "doc1",
        "source_path": "data/rag_docs/doc1.txt",
        "chunk_id": 0,
        "text": "낮은 관련도 문장",
        "raw_distance": 1.9,
        "normalized_relevance": 0.05,
    }]

    with patch("app.rag.retriever.ChromaRetriever", return_value=fake_retriever), \
         patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
         patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
         patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
         patch("app.orchestrator.executor.JudgeAgent") as MockJudge:

        mock_run_drafts.return_value = mock_drafts
        MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
        MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
        MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))

        executor = MOAExecutor()
        logger = TraceLogger(run_id="rag-miss")
        routing = RoutingDecision(
            selected_path="moa",
            reason="rag miss",
            confidence=0.9,
            requires_rag=True,
            rag_query_hint="관련도 낮은 질문",
        )
        task = TaskRequest(prompt="원본 질문", task_type="explain")

        await executor.execute(task, logger, routing=routing)

    enriched_task = mock_run_drafts.await_args.args[0]
    assert "[참고 문서]" not in enriched_task.prompt
    context_record = next(
        record for record in logger.records
        if record["operation_type"] == "rag" and record["metadata"]["stage"] == "context_build"
    )
    assert context_record["metadata"]["rag_miss"] is True
    assert logger.records[-1]["path"] == "moa"


@pytest.mark.asyncio
async def test_executor_rag_falls_back_to_simple_retriever():
    mock_drafts = [_mock_output("draft_analytical"), _mock_output("draft_creative"), _mock_output("draft_structured")]
    mock_critic = _mock_output("critic", '{"analyses": []}')
    mock_synth = _mock_output("synthesizer", "MOA 최종 결과")
    mock_judge = JudgeDecision(decision="pass", confidence=0.95, reasoning="OK")

    fake_simple = SimpleNamespace(query_items=lambda *args, **kwargs: [{
        "doc_id": "doc2",
        "source_path": "data/rag_docs/doc2.txt",
        "chunk_id": 1,
        "text": "SimpleRetriever fallback 문장",
        "raw_distance": 0.2,
        "normalized_relevance": 0.8,
    }])

    with patch("app.rag.retriever.ChromaRetriever", side_effect=RuntimeError("chroma unavailable")), \
         patch("app.rag.retriever.SimpleRetriever.from_directory", return_value=fake_simple), \
         patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
         patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
         patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
         patch("app.orchestrator.executor.JudgeAgent") as MockJudge:

        mock_run_drafts.return_value = mock_drafts
        MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
        MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
        MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))

        executor = MOAExecutor()
        logger = TraceLogger(run_id="rag-fallback")
        routing = RoutingDecision(
            selected_path="moa",
            reason="rag fallback",
            confidence=0.9,
            requires_rag=True,
        )
        task = TaskRequest(prompt="원본 질문", task_type="explain")

        await executor.execute(task, logger, routing=routing)

    retrieval_record = next(
        record for record in logger.records
        if record["operation_type"] == "rag" and record["metadata"]["stage"] == "retrieval"
    )
    assert retrieval_record["metadata"]["retriever"] == "SimpleRetriever"
    assert retrieval_record["metadata"]["fallback_reason"] == "chroma unavailable"
    assert logger.records[-1]["path"] == "moa+rag"


def test_gitignore_contains_chroma_path():
    content = Path(".gitignore").read_text(encoding="utf-8")
    assert "data/chroma/" in content
