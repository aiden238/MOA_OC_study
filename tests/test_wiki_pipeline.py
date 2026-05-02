import json

import pytest

from app.wiki.pipeline import CollectedItem, WikiUpdateService


def test_manual_candidate_submission_creates_pending_record(tmp_path):
    service = WikiUpdateService(
        docs_dir=tmp_path / "rag_docs",
        state_dir=tmp_path / "wiki_state",
        knowledge_graph_dir=tmp_path / "knowledge_graph",
        chroma_dir=tmp_path / "chroma",
    )
    service.docs_dir.mkdir(parents=True, exist_ok=True)

    pending = service.submit_manual_candidate(
        CollectedItem(
            title="Context Compression Pattern",
            content="Compress long context before routing to downstream agents.",
            summary="A short note on context compression.",
            category="context_engineering",
            tags=["compression", "context"],
            related=["doc17_context_compression.txt"],
        )
    )

    assert pending.status == "pending"
    assert pending.filename.startswith("wiki_")
    assert len(service.list_pending()) == 1


@pytest.mark.asyncio
async def test_approve_pending_writes_doc_and_changelog(tmp_path):
    service = WikiUpdateService(
        docs_dir=tmp_path / "rag_docs",
        state_dir=tmp_path / "wiki_state",
        knowledge_graph_dir=tmp_path / "knowledge_graph",
        chroma_dir=tmp_path / "chroma",
    )
    service.docs_dir.mkdir(parents=True, exist_ok=True)

    pending = service.submit_manual_candidate(
        CollectedItem(
            title="Agent Loop Retry Budget",
            content="Retry budgets keep agent loops bounded and observable.",
            summary="Retry budgeting for agent loops.",
            category="harness_engineering",
            tags=["agent-loop", "retry"],
            related=["doc24_error_handling_fallback.txt"],
            source_url="https://example.com/retry-budget",
        )
    )

    result = await service.approve_pending(pending.pending_id)

    assert (service.docs_dir / pending.filename).exists()
    assert result["graph_snapshot"]["nodes_path"].endswith("nodes.json")
    changelog = json.loads(service.changelog_path.read_text(encoding="utf-8"))
    assert changelog[-1]["title"] == "Agent Loop Retry Budget"
