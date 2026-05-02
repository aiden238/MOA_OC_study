"""Manual self-updating wiki pipeline for Week 12."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import CHROMA_DIR, PROJECT_ROOT, RAG_DOCS_DIR
from app.rag.knowledge_graph import build_knowledge_graph, load_documents, save_graph_snapshot, slugify

try:
    from app.rag.retriever import ChromaRetriever
except Exception:  # pragma: no cover - import is runtime optional
    ChromaRetriever = None  # type: ignore[assignment]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@dataclass(slots=True)
class CollectedItem:
    """Collected wiki candidate."""

    title: str
    content: str
    summary: str
    category: str
    tags: list[str]
    related: list[str]
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluatedItem:
    """Evaluation result for a collected item."""

    relevance: float
    credibility: float
    novelty: float
    richness: float
    total_score: float
    include: bool
    rationale: str


@dataclass(slots=True)
class PendingWikiDocument:
    """Pending wiki document awaiting approval."""

    pending_id: str
    title: str
    filename: str
    category: str
    tags: list[str]
    related: list[str]
    source_url: str | None
    confidence: float
    status: str
    created_at: str
    updated_at: str
    summary: str
    content: str
    document_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CollectorAgent:
    """Collector agent MVP with manual candidate intake."""

    def collect_manual(self, item: CollectedItem) -> list[CollectedItem]:
        return [item]


class EvaluatorAgent:
    """Heuristic evaluator for collected wiki items."""

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir

    def _novelty_score(self, title: str) -> float:
        existing = [doc.title for doc in load_documents(self.docs_dir)]
        if not existing:
            return 1.0
        similarities = [SequenceMatcher(None, title.lower(), item.lower()).ratio() for item in existing]
        closest = max(similarities, default=0.0)
        return max(0.0, round(1.0 - closest, 3))

    def evaluate(self, item: CollectedItem) -> EvaluatedItem:
        relevance = 0.95 if item.category in {"prompt_engineering", "context_engineering", "harness_engineering", "advanced", "basics"} else 0.65
        credibility = 0.9 if item.source_url else 0.55
        novelty = self._novelty_score(item.title)
        richness = min(1.0, max(len(item.content.split()) / 180.0, 0.2))
        total = round((relevance + credibility + novelty + richness) / 4.0, 3)
        include = total >= 0.6
        rationale = (
            f"relevance={relevance:.2f}, credibility={credibility:.2f}, "
            f"novelty={novelty:.2f}, richness={richness:.2f}"
        )
        return EvaluatedItem(
            relevance=relevance,
            credibility=credibility,
            novelty=novelty,
            richness=richness,
            total_score=total,
            include=include,
            rationale=rationale,
        )


class WikiWriterAgent:
    """Format collected content as a wiki document with YAML front matter."""

    def build_document(
        self,
        item: CollectedItem,
        evaluation: EvaluatedItem,
    ) -> tuple[str, str]:
        stem = slugify(item.title)
        filename = f"wiki_{stem}.txt"
        related = item.related[:5]
        tags = item.tags[:8]

        front_matter = [
            "---",
            f"title: {item.title}",
            f"category: {item.category}",
            "tags:",
        ]
        if tags:
            front_matter.extend([f"  - {tag}" for tag in tags])
        else:
            front_matter.append("  - wiki")
        front_matter.append("related:")
        if related:
            front_matter.extend([f"  - {value}" for value in related])
        else:
            front_matter.append("  - doc30_llm_wiki_architecture.txt")
        if item.source_url:
            front_matter.append(f"source_url: {item.source_url}")
        front_matter.extend(
            [
                f"confidence: {evaluation.total_score}",
                f"created_date: {_today()}",
                f"last_updated: {_today()}",
                "---",
                "",
                item.title,
                "",
                item.summary.strip() or "Auto-generated wiki draft.",
                "",
                item.content.strip(),
            ]
        )
        return filename, "\n".join(front_matter).strip() + "\n"


class WikiUpdateService:
    """Manage pending wiki candidates and approval."""

    def __init__(
        self,
        *,
        docs_dir: Path | None = None,
        state_dir: Path | None = None,
        knowledge_graph_dir: Path | None = None,
        chroma_dir: Path | None = None,
    ):
        self.docs_dir = docs_dir or RAG_DOCS_DIR
        self.state_dir = state_dir or (PROJECT_ROOT / "data/wiki_state")
        self.knowledge_graph_dir = knowledge_graph_dir or (PROJECT_ROOT / "data/knowledge_graph")
        self.chroma_dir = chroma_dir or CHROMA_DIR
        self.collector = CollectorAgent()
        self.evaluator = EvaluatorAgent(self.docs_dir)
        self.writer = WikiWriterAgent()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pending_path = self.state_dir / "pending.json"
        self.changelog_path = self.state_dir / "changelog.json"
        self.versions_dir = self.docs_dir / "wiki_versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload: Any):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def list_pending(self) -> list[PendingWikiDocument]:
        rows = self._load_json(self.pending_path, [])
        return [PendingWikiDocument(**row) for row in rows]

    def _save_pending(self, rows: list[PendingWikiDocument]):
        self._save_json(self.pending_path, [asdict(row) for row in rows])

    def get_status(self) -> dict[str, Any]:
        pending = self.list_pending()
        changelog = self._load_json(self.changelog_path, [])
        return {
            "pending_count": len([row for row in pending if row.status == "pending"]),
            "approved_count": len(changelog),
            "last_updated": changelog[-1]["updated_at"] if changelog else None,
            "latest_entries": changelog[-5:],
        }

    def submit_manual_candidate(self, item: CollectedItem) -> PendingWikiDocument:
        collected = self.collector.collect_manual(item)[0]
        evaluation = self.evaluator.evaluate(collected)
        filename, document_text = self.writer.build_document(collected, evaluation)
        pending = PendingWikiDocument(
            pending_id=uuid4().hex[:12],
            title=collected.title,
            filename=filename,
            category=collected.category,
            tags=collected.tags,
            related=collected.related,
            source_url=collected.source_url,
            confidence=evaluation.total_score,
            status="pending" if evaluation.include else "rejected",
            created_at=_utc_now(),
            updated_at=_utc_now(),
            summary=collected.summary,
            content=collected.content,
            document_text=document_text,
            metadata={
                **collected.metadata,
                "evaluation": asdict(evaluation),
            },
        )
        pending_rows = self.list_pending()
        pending_rows.append(pending)
        self._save_pending(pending_rows)
        return pending

    def reject_pending(self, pending_id: str) -> PendingWikiDocument:
        rows = self.list_pending()
        for index, row in enumerate(rows):
            if row.pending_id != pending_id:
                continue
            rows[index] = PendingWikiDocument(
                **{
                    **asdict(row),
                    "status": "rejected",
                    "updated_at": _utc_now(),
                }
            )
            self._save_pending(rows)
            return rows[index]
        raise ValueError(f"Pending wiki document not found: {pending_id}")

    async def approve_pending(self, pending_id: str) -> dict[str, Any]:
        rows = self.list_pending()
        target_index = next((index for index, row in enumerate(rows) if row.pending_id == pending_id), None)
        if target_index is None:
            raise ValueError(f"Pending wiki document not found: {pending_id}")

        target = rows[target_index]
        target_path = self.docs_dir / target.filename
        target_path.write_text(target.document_text, encoding="utf-8")

        version_path = self.versions_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{target.filename}"
        shutil.copyfile(target_path, version_path)

        reindex_status = await self._refresh_retriever_index()
        graph = build_knowledge_graph(self.docs_dir)
        graph_snapshot = save_graph_snapshot(graph, self.knowledge_graph_dir)

        changelog = self._load_json(self.changelog_path, [])
        entry = {
            "action": "added",
            "pending_id": target.pending_id,
            "filename": target.filename,
            "title": target.title,
            "category": target.category,
            "updated_at": _utc_now(),
            "source_url": target.source_url,
            "confidence": target.confidence,
            "reindex_status": reindex_status,
        }
        changelog.append(entry)
        self._save_json(self.changelog_path, changelog)

        rows[target_index] = PendingWikiDocument(
            **{
                **asdict(target),
                "status": "approved",
                "updated_at": _utc_now(),
            }
        )
        self._save_pending(rows)

        return {
            "pending_id": target.pending_id,
            "filename": target.filename,
            "path": str(target_path),
            "graph_snapshot": graph_snapshot,
            "reindex_status": reindex_status,
            "changelog_entry": entry,
        }

    async def _refresh_retriever_index(self) -> dict[str, Any]:
        if ChromaRetriever is None:
            return {"status": "skipped", "reason": "chromadb unavailable"}

        try:
            retriever = ChromaRetriever(persist_directory=self.chroma_dir)
            result = await retriever.index_directory(self.docs_dir)
            return {"status": "indexed", **result}
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "reason": str(exc)}
