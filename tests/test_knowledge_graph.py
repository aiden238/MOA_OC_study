from pathlib import Path

from app.rag.knowledge_graph import (
    build_knowledge_graph,
    expand_query_with_graph,
    highlight_query_nodes,
    neighbor_subgraph,
)


def _write_doc(path: Path, title: str, body: str):
    path.write_text(f"{title}\n\n{body}\n", encoding="utf-8")


def test_build_knowledge_graph_creates_document_and_concept_nodes(tmp_path):
    docs_dir = tmp_path / "rag_docs"
    docs_dir.mkdir()
    _write_doc(docs_dir / "doc08_chain_of_thought.txt", "Chain-of-Thought", "Reasoning steps improve answers.")
    _write_doc(docs_dir / "doc07_zero_few_shot.txt", "Few-shot Prompting", "Examples steer output style.")

    graph = build_knowledge_graph(docs_dir)

    assert graph["stats"]["document_count"] == 2
    assert any(node["type"] == "document" for node in graph["nodes"])
    assert any(node["type"] == "concept" for node in graph["nodes"])
    assert any(edge["relation"] == "contains" for edge in graph["edges"])
    assert any(edge["relation"] == "implements" for edge in graph["edges"])


def test_highlight_and_neighbor_subgraph_follow_related_nodes(tmp_path):
    docs_dir = tmp_path / "rag_docs"
    docs_dir.mkdir()
    _write_doc(docs_dir / "doc08_chain_of_thought.txt", "Chain-of-Thought", "Reasoning steps improve answers.")
    _write_doc(docs_dir / "doc07_zero_few_shot.txt", "Few-shot Prompting", "Examples steer output style.")

    graph = build_knowledge_graph(docs_dir)
    matches = highlight_query_nodes(graph, "chain of thought reasoning")

    assert matches
    subgraph = neighbor_subgraph(graph, matches[0]["id"], depth=1)
    assert subgraph["nodes"]
    assert subgraph["edges"]


def test_expand_query_with_graph_adds_related_terms(tmp_path):
    docs_dir = tmp_path / "rag_docs"
    docs_dir.mkdir()
    _write_doc(docs_dir / "doc08_chain_of_thought.txt", "Chain-of-Thought", "Reasoning steps improve answers.")
    _write_doc(docs_dir / "doc07_zero_few_shot.txt", "Few-shot Prompting", "Examples steer output style.")

    expanded = expand_query_with_graph(docs_dir, "How should I use chain of thought?")

    assert expanded["highlighted_node_ids"]
    assert expanded["subgraph"]["nodes"]
    assert expanded["expanded_query"].startswith("How should I use chain of thought?")
