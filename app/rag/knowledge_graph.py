"""Knowledge graph helpers for Week 12 graph-aware RAG."""

from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CATEGORY_CONFIG: dict[str, dict[str, str]] = {
    "basics": {"label": "Basics", "color": "#6B7280"},
    "prompt_engineering": {"label": "Prompt Engineering", "color": "#3B82F6"},
    "context_engineering": {"label": "Context Engineering", "color": "#10B981"},
    "harness_engineering": {"label": "Harness Engineering", "color": "#F59E0B"},
    "advanced": {"label": "Advanced", "color": "#8B5CF6"},
}

FILE_CATEGORY_RULES: list[tuple[str, str]] = [
    (r"doc0[1-5]", "basics"),
    (r"doc0[6-9]", "prompt_engineering"),
    (r"doc1[0-2]", "prompt_engineering"),
    (r"doc1[3-8]", "context_engineering"),
    (r"doc19", "harness_engineering"),
    (r"doc2[0-4]", "harness_engineering"),
    (r"doc25", "advanced"),
    (r"doc26", "advanced"),
    (r"doc27", "advanced"),
    (r"doc28_token", "advanced"),
    (r"doc28_harness", "harness_engineering"),
    (r"doc29", "advanced"),
    (r"doc30", "advanced"),
    (r"doc31", "context_engineering"),
]

DERIVED_TAG_MAP: dict[str, list[str]] = {
    "prompt engineering basics": ["prompting", "basics"],
    "zero few shot": ["zero-shot", "few-shot", "examples"],
    "chain of thought": ["chain-of-thought", "reasoning"],
    "role prompting": ["role-prompting", "persona"],
    "structured output": ["structured-output", "json"],
    "prompt chaining": ["prompt-chaining", "workflow"],
    "system prompt design": ["system-prompt", "instruction-design"],
    "context engineering overview": ["context-engineering", "overview"],
    "context window management": ["context-window", "token-budget"],
    "instruction file structure": ["instruction-file", "claude-md"],
    "memory hierarchy": ["memory", "hierarchy"],
    "context compression": ["compression", "summarization"],
    "multiturn context": ["multi-turn", "conversation-state"],
    "harness engineering overview": ["harness", "evaluation-loop"],
    "layer management": ["layer-management", "stacking"],
    "context persistence": ["persistence", "session-memory"],
    "tool integration": ["tool-use", "integration"],
    "agent loop design": ["agent-loop", "control-flow"],
    "error handling fallback": ["fallback", "error-handling"],
    "advanced rag design": ["rag", "retrieval-design"],
    "moa patterns": ["moa", "multi-agent"],
    "llm evaluation": ["evaluation", "rubric"],
    "harness layer patterns": ["harness", "layer-patterns"],
    "token cost optimization": ["token-optimization", "cost-control"],
    "prompt injection defense": ["prompt-injection", "security"],
    "llm wiki architecture": ["llm-wiki", "knowledge-base"],
    "context engineering techniques": ["context-techniques", "retrieval-context"],
}

STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "overview",
    "basics",
    "design",
    "engineering",
    "advanced",
    "llm",
    "of",
}


@dataclass(slots=True)
class RagDocumentMeta:
    """Structured metadata extracted from a RAG document."""

    file_path: Path
    filename: str
    stem: str
    title: str
    category: str
    tags: list[str]
    related: list[str]
    source_url: str | None
    confidence: float | None
    created_date: str | None
    last_updated: str | None
    content: str


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text or "node"


def classify_doc(filename: str) -> str:
    stem = Path(filename).stem
    for pattern, category in FILE_CATEGORY_RULES:
        if re.match(pattern, stem):
            return category
    return "basics"


def _parse_scalar(value: str) -> Any:
    raw = value.strip()
    if not raw:
        return ""
    if raw.startswith("[") and raw.endswith("]"):
        items = [item.strip().strip("'\"") for item in raw[1:-1].split(",") if item.strip()]
        return items
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw.strip("'\"")


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text

    lines = stripped.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    metadata: dict[str, Any] = {}
    current_key: str | None = None
    body_start = None

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = index + 1
            break

        if line.startswith("  - ") or line.startswith("- "):
            if current_key is None:
                continue
            if not isinstance(metadata.get(current_key), list):
                metadata[current_key] = []
            metadata[current_key].append(line.split("-", 1)[1].strip().strip("'\""))
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            parsed = _parse_scalar(value)
            metadata[current_key] = [] if parsed == "" else parsed
            if parsed != "":
                current_key = None

    if body_start is None:
        return {}, text

    body = "\n".join(lines[body_start:]).strip()
    return metadata, body


def _derive_title(lines: list[str], fallback: str) -> str:
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return fallback


def _derive_tags(stem: str, title: str, category: str) -> list[str]:
    stem_key = re.sub(r"^doc\d+_?", "", stem).replace("_", " ").strip()
    tags = list(DERIVED_TAG_MAP.get(stem_key, []))

    tokens = re.findall(r"[a-zA-Z0-9]+", f"{stem_key} {title.lower()}")
    for token in tokens:
        lowered = token.lower()
        if len(lowered) < 4 or lowered in STOPWORDS:
            continue
        tags.append(lowered)

    if category == "prompt_engineering":
        tags.append("prompting")
    if category == "context_engineering":
        tags.append("context")
    if category == "harness_engineering":
        tags.append("agent")
    if category == "advanced":
        tags.append("advanced")

    ordered: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = tag.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered[:6]


def parse_document_metadata(file_path: Path) -> RagDocumentMeta:
    text = file_path.read_text(encoding="utf-8")
    metadata, body = parse_front_matter(text)
    lines = body.splitlines() if body else text.splitlines()
    category = str(metadata.get("category") or classify_doc(file_path.name)).strip() or "basics"
    title = str(metadata.get("title") or _derive_title(lines, file_path.stem)).strip()
    related = metadata.get("related") or []
    if not isinstance(related, list):
        related = [str(related)]
    tags = metadata.get("tags") or _derive_tags(file_path.stem, title, category)
    if not isinstance(tags, list):
        tags = [str(tags)]

    return RagDocumentMeta(
        file_path=file_path,
        filename=file_path.name,
        stem=file_path.stem,
        title=title,
        category=category,
        tags=[str(tag).strip() for tag in tags if str(tag).strip()],
        related=[str(item).strip() for item in related if str(item).strip()],
        source_url=str(metadata.get("source_url") or "").strip() or None,
        confidence=float(metadata["confidence"]) if "confidence" in metadata else None,
        created_date=str(metadata.get("created_date") or "").strip() or None,
        last_updated=str(metadata.get("last_updated") or "").strip() or None,
        content=body.strip() if body else text.strip(),
    )


def load_documents(docs_dir: Path) -> list[RagDocumentMeta]:
    if not docs_dir.exists():
        return []
    return [parse_document_metadata(path) for path in sorted(docs_dir.glob("*.txt"))]


def build_knowledge_catalog(docs_dir: Path) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in load_documents(docs_dir):
        categories[doc.category].append(
            {
                "filename": doc.filename,
                "title": doc.title,
                "tags": doc.tags,
            }
        )

    payload = []
    for category, docs in categories.items():
        meta = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["basics"])
        payload.append(
            {
                "id": category,
                "label": meta["label"],
                "color": meta["color"],
                "doc_count": len(docs),
                "docs": docs,
            }
        )
    payload.sort(key=lambda item: item["label"])
    return {
        "categories": payload,
        "total_docs": sum(item["doc_count"] for item in payload),
    }


def build_knowledge_graph(docs_dir: Path) -> dict[str, Any]:
    docs = load_documents(docs_dir)
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}
    concept_docs: dict[str, set[str]] = defaultdict(set)

    for doc in docs:
        category_meta = CATEGORY_CONFIG.get(doc.category, CATEGORY_CONFIG["basics"])
        category_id = f"category_{doc.category}"
        nodes.setdefault(
            category_id,
            {
                "id": category_id,
                "type": "category",
                "label": category_meta["label"],
                "category": doc.category,
                "color": category_meta["color"],
                "doc_refs": [],
            },
        )

        document_id = f"document_{slugify(doc.stem)}"
        nodes[document_id] = {
            "id": document_id,
            "type": "document",
            "label": doc.title,
            "category": doc.category,
            "color": category_meta["color"],
            "filename": doc.filename,
            "doc_refs": [doc.filename],
            "tags": doc.tags,
            "related": doc.related,
            "source_url": doc.source_url,
        }

        edges[(category_id, document_id, "contains")] = {
            "source": category_id,
            "target": document_id,
            "relation": "contains",
            "weight": 1.0,
        }

        nodes[category_id]["doc_refs"].append(doc.filename)

        for tag in doc.tags:
            concept_id = f"concept_{slugify(tag)}"
            nodes.setdefault(
                concept_id,
                {
                    "id": concept_id,
                    "type": "concept",
                    "label": tag,
                    "category": doc.category,
                    "color": category_meta["color"],
                    "doc_refs": [],
                },
            )
            nodes[concept_id]["doc_refs"].append(doc.filename)
            concept_docs[concept_id].add(document_id)
            edges[(document_id, concept_id, "implements")] = {
                "source": document_id,
                "target": concept_id,
                "relation": "implements",
                "weight": 0.9,
            }

        for related_name in doc.related:
            related_stem = Path(related_name).stem
            related_id = f"document_{slugify(related_stem)}"
            edges[(document_id, related_id, "related_to")] = {
                "source": document_id,
                "target": related_id,
                "relation": "related_to",
                "weight": 0.75,
            }

    doc_ids = [node_id for node_id, node in nodes.items() if node["type"] == "document"]
    for index, left_id in enumerate(doc_ids):
        left = nodes[left_id]
        left_tags = set(left.get("tags", []))
        for right_id in doc_ids[index + 1 :]:
            right = nodes[right_id]
            if left["category"] != right["category"]:
                continue
            right_tags = set(right.get("tags", []))
            if left_tags & right_tags:
                edges[(left_id, right_id, "related_to")] = {
                    "source": left_id,
                    "target": right_id,
                    "relation": "related_to",
                    "weight": 0.55,
                }

    concept_ids = [node_id for node_id, node in nodes.items() if node["type"] == "concept"]
    for index, left_id in enumerate(concept_ids):
        left_docs = concept_docs.get(left_id, set())
        for right_id in concept_ids[index + 1 :]:
            right_docs = concept_docs.get(right_id, set())
            if not left_docs or not right_docs or left_docs.isdisjoint(right_docs):
                continue
            left_node = nodes[left_id]
            right_node = nodes[right_id]
            relation = "related_to"
            weight = 0.65 if left_node["category"] == right_node["category"] else 0.5
            edges[(left_id, right_id, relation)] = {
                "source": left_id,
                "target": right_id,
                "relation": relation,
                "weight": weight,
            }

    graph = {
        "nodes": sorted(nodes.values(), key=lambda node: (node["type"], node["label"])),
        "edges": sorted(edges.values(), key=lambda edge: (edge["relation"], edge["source"], edge["target"])),
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "document_count": len(docs),
        },
    }
    return graph


def save_graph_snapshot(graph: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "nodes.json"
    edges_path = output_dir / "edges.json"
    with open(nodes_path, "w", encoding="utf-8") as file:
        json.dump(graph["nodes"], file, ensure_ascii=False, indent=2)
    with open(edges_path, "w", encoding="utf-8") as file:
        json.dump(graph["edges"], file, ensure_ascii=False, indent=2)
    return {"nodes_path": str(nodes_path), "edges_path": str(edges_path)}


def _tokenize_query(value: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[a-zA-Z0-9]+", value) if len(token) >= 2]


def highlight_query_nodes(graph: dict[str, Any], query: str, limit: int = 6) -> list[dict[str, Any]]:
    query_tokens = _tokenize_query(query)
    if not query_tokens:
        return []

    ranked: list[dict[str, Any]] = []
    for node in graph["nodes"]:
        haystack = " ".join(
            [
                str(node.get("label", "")),
                str(node.get("filename", "")),
                " ".join(str(tag) for tag in node.get("tags", [])),
            ]
        ).lower()
        overlap = sum(1 for token in query_tokens if token in haystack)
        if overlap <= 0:
            continue
        ranked.append(
            {
                "id": node["id"],
                "label": node["label"],
                "type": node["type"],
                "score": round(overlap / max(1, len(query_tokens)), 3),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["label"]))
    return ranked[:limit]


def neighbor_subgraph(
    graph: dict[str, Any],
    node_id: str,
    depth: int = 1,
    min_weight: float = 0.5,
) -> dict[str, Any]:
    if depth < 1:
        depth = 1

    edge_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in graph["edges"]:
        if edge.get("weight", 0.0) < min_weight:
            continue
        edge_index[edge["source"]].append(edge)
        edge_index[edge["target"]].append(edge)

    node_lookup = {node["id"]: node for node in graph["nodes"]}
    if node_id not in node_lookup:
        return {"nodes": [], "edges": []}

    visited_nodes = {node_id}
    visited_edges: set[tuple[str, str, str]] = set()
    queue: deque[tuple[str, int]] = deque([(node_id, 0)])

    while queue:
        current, current_depth = queue.popleft()
        if current_depth >= depth:
            continue
        for edge in edge_index.get(current, []):
            key = (edge["source"], edge["target"], edge["relation"])
            visited_edges.add(key)
            neighbor = edge["target"] if edge["source"] == current else edge["source"]
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)
                queue.append((neighbor, current_depth + 1))

    return {
        "nodes": [node_lookup[item] for item in sorted(visited_nodes)],
        "edges": [
            edge
            for edge in graph["edges"]
            if (edge["source"], edge["target"], edge["relation"]) in visited_edges
        ],
    }


def expand_query_with_graph(
    docs_dir: Path,
    query: str,
    *,
    depth: int = 1,
    max_expansion_terms: int = 2,
) -> dict[str, Any]:
    graph = build_knowledge_graph(docs_dir)
    highlighted = highlight_query_nodes(graph, query)
    if not highlighted:
        return {
            "graph": graph,
            "expanded_query": query,
            "highlighted_nodes": [],
            "highlighted_node_ids": [],
            "expansion_terms": [],
            "subgraph": {"nodes": [], "edges": []},
        }

    edge_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    node_lookup = {node["id"]: node for node in graph["nodes"]}
    for edge in graph["edges"]:
        if edge.get("weight", 0.0) < 0.5:
            continue
        edge_index[edge["source"]].append(edge)
        edge_index[edge["target"]].append(edge)

    candidate_scores: dict[str, float] = defaultdict(float)
    subgraph_nodes: set[str] = set()
    subgraph_edges: set[tuple[str, str, str]] = set()

    for item in highlighted:
        start = item["id"]
        subgraph_nodes.add(start)
        queue: deque[tuple[str, int, float]] = deque([(start, 0, item["score"])])
        visited = {start}
        while queue:
            current, current_depth, base_score = queue.popleft()
            if current_depth >= depth:
                continue
            for edge in edge_index.get(current, []):
                relation_key = (edge["source"], edge["target"], edge["relation"])
                subgraph_edges.add(relation_key)
                neighbor = edge["target"] if edge["source"] == current else edge["source"]
                subgraph_nodes.add(neighbor)
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, current_depth + 1, base_score * edge["weight"]))
                if neighbor == start:
                    continue
                node = node_lookup.get(neighbor, {})
                if node.get("type") == "category":
                    continue
                candidate_scores[neighbor] += base_score * edge["weight"]

    expansion_terms: list[str] = []
    seen_labels = {item["label"].lower() for item in highlighted}
    for node_id, _score in sorted(candidate_scores.items(), key=lambda item: (-item[1], item[0])):
        label = str(node_lookup[node_id]["label"]).strip()
        if not label or label.lower() in seen_labels:
            continue
        expansion_terms.append(label)
        seen_labels.add(label.lower())
        if len(expansion_terms) >= max_expansion_terms:
            break

    expanded_query = query
    if expansion_terms:
        expanded_query = f"{query}\nRelated concepts: {', '.join(expansion_terms)}"

    return {
        "graph": graph,
        "expanded_query": expanded_query,
        "highlighted_nodes": highlighted,
        "highlighted_node_ids": [item["id"] for item in highlighted],
        "expansion_terms": expansion_terms,
        "subgraph": {
            "nodes": [node_lookup[node_id] for node_id in sorted(subgraph_nodes)],
            "edges": [
                edge
                for edge in graph["edges"]
                if (edge["source"], edge["target"], edge["relation"]) in subgraph_edges
            ],
        },
    }
