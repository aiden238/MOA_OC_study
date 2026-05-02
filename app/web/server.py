"""FastAPI server for the Week 10 web chat UI."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import RAG_DOCS_DIR
from app.core.model_registry import get_model_registry_payload
from app.schemas.chat import ChatSessionMessage, ChatTurnRequest
from app.schemas.wiki import ManualWikiCandidateRequest
from app.rag.knowledge_graph import (
    build_knowledge_graph,
    highlight_query_nodes,
    neighbor_subgraph,
)
from app.services.chat_service import run_chat_turn
from app.web.session_store import SessionStore
from app.wiki.pipeline import CollectedItem, WikiUpdateService


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="MOA Web Chat")
session_store = SessionStore(max_messages=10)
wiki_update_service = WikiUpdateService()

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/models")
async def api_models():
    return get_model_registry_payload()


# ── RAG 지식 카탈로그 ──────────────────────────────────────────────────

_CATEGORY_MAP: dict[str, dict[str, Any]] = {
    "prompt_engineering": {
        "label": "프롬프트 엔지니어링",
        "color": "blue",
        "icon": "✏️",
        "example_questions": [
            "Few-shot 프롬프팅은 몇 개의 예시가 적당한가요?",
            "Chain-of-Thought 프롬프팅을 어떻게 사용하나요?",
            "역할 기반 프롬프팅이란 무엇인가요?",
        ],
    },
    "context_engineering": {
        "label": "컨텍스트 엔지니어링",
        "color": "green",
        "icon": "🧩",
        "example_questions": [
            "컨텍스트 윈도우 관리 방법을 알려주세요",
            "메모리 계층(단기/장기)을 어떻게 설계하나요?",
            "지침 파일(CLAUDE.md) 구조는 어떻게 구성하나요?",
        ],
    },
    "harness_engineering": {
        "label": "하네스 엔지니어링",
        "color": "orange",
        "icon": "⚙️",
        "example_questions": [
            "에이전트 레이어를 어떻게 구성하나요?",
            "ReAct 패턴과 Plan-and-Execute 차이가 뭔가요?",
            "에이전트 에러 처리와 폴백 전략을 설명해주세요",
        ],
    },
    "advanced": {
        "label": "고급 기법 (RAG·MOA·평가·보안)",
        "color": "purple",
        "icon": "🚀",
        "example_questions": [
            "고급 RAG 파이프라인 설계 방법은?",
            "MOA 오케스트레이션 패턴의 종류를 알려주세요",
            "프롬프트 인젝션 방어 방법을 알려주세요",
        ],
    },
    "basics": {
        "label": "기초 AI·검색",
        "color": "gray",
        "icon": "📖",
        "example_questions": [
            "RAG 파이프라인이란 무엇인가요?",
            "벡터 데이터베이스는 어떻게 동작하나요?",
            "자연어 처리 기초를 설명해주세요",
        ],
    },
}

_FILE_CATEGORY_RULES: list[tuple[str, str]] = [
    ("doc0[1-5]", "basics"),
    ("doc0[6-9]", "prompt_engineering"),
    ("doc1[0-2]", "prompt_engineering"),
    ("doc1[3-8]", "context_engineering"),
    ("doc19", "harness_engineering"),
    ("doc2[0-4]", "harness_engineering"),
    ("doc25", "advanced"),
    ("doc26", "advanced"),
    ("doc27", "advanced"),
    ("doc28_token", "advanced"),
    ("doc28_harness", "harness_engineering"),
    ("doc29", "advanced"),
    ("doc30", "advanced"),
    ("doc31", "context_engineering"),
]


def _classify_doc(filename: str) -> str:
    """파일명 패턴으로 카테고리를 분류한다."""
    import re
    stem = Path(filename).stem
    for pattern, category in _FILE_CATEGORY_RULES:
        if re.match(pattern, stem):
            return category
    return "basics"


def _build_knowledge_catalog(docs_dir: Path) -> list[dict[str, Any]]:
    """rag_docs 디렉토리를 스캔해 카테고리별 문서 목록을 구성한다."""
    categories: dict[str, list[dict]] = {k: [] for k in _CATEGORY_MAP}

    for file_path in sorted(docs_dir.glob("*.txt")):
        try:
            lines = file_path.read_text(encoding="utf-8").strip().split("\n")
            title = lines[0].strip() if lines else file_path.stem
        except Exception:
            title = file_path.stem

        category = _classify_doc(file_path.name)
        categories[category].append({
            "filename": file_path.name,
            "title": title,
        })

    result = []
    for key, docs in categories.items():
        if not docs:
            continue
        meta = _CATEGORY_MAP[key]
        result.append({
            "id": key,
            "label": meta["label"],
            "color": meta["color"],
            "icon": meta["icon"],
            "doc_count": len(docs),
            "docs": docs,
            "example_questions": meta["example_questions"],
        })
    return result


@app.get("/api/rag-knowledge")
async def get_rag_knowledge():
    """현재 RAG에 인덱싱된 지식 카탈로그를 반환한다."""
    docs_dir = RAG_DOCS_DIR
    if not docs_dir.exists():
        return {"categories": [], "total_docs": 0}
    categories = _build_knowledge_catalog(docs_dir)
    total = sum(c["doc_count"] for c in categories)
    return {"categories": categories, "total_docs": total}


@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    if not RAG_DOCS_DIR.exists():
        return {"nodes": [], "edges": [], "stats": {"node_count": 0, "edge_count": 0, "document_count": 0}}
    return build_knowledge_graph(RAG_DOCS_DIR)


@app.get("/api/knowledge-graph/neighbors")
async def get_knowledge_graph_neighbors(node_id: str, depth: int = 1):
    graph = build_knowledge_graph(RAG_DOCS_DIR)
    subgraph = neighbor_subgraph(graph, node_id=node_id, depth=depth)
    if not subgraph["nodes"]:
        raise HTTPException(status_code=404, detail="Knowledge graph node not found")
    return subgraph


@app.get("/api/knowledge-graph/highlight")
async def get_knowledge_graph_highlight(query: str):
    graph = build_knowledge_graph(RAG_DOCS_DIR)
    return {"query": query, "matches": highlight_query_nodes(graph, query)}


@app.get("/api/wiki/status")
async def get_wiki_status():
    return wiki_update_service.get_status()


@app.get("/api/wiki/pending")
async def get_wiki_pending():
    rows = wiki_update_service.list_pending()
    return {"items": [asdict(row) for row in rows]}


@app.post("/api/wiki/manual-candidate")
async def post_wiki_manual_candidate(request: ManualWikiCandidateRequest):
    pending = wiki_update_service.submit_manual_candidate(
        CollectedItem(
            title=request.title,
            content=request.content,
            summary=request.summary,
            category=request.category,
            tags=request.tags,
            related=request.related,
            source_url=request.source_url,
            metadata=request.metadata,
        )
    )
    return asdict(pending)


@app.post("/api/wiki/pending/{pending_id}/approve")
async def post_wiki_pending_approve(pending_id: str):
    try:
        return await wiki_update_service.approve_pending(pending_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/wiki/pending/{pending_id}/reject")
async def post_wiki_pending_reject(pending_id: str):
    try:
        return asdict(wiki_update_service.reject_pending(pending_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sessions")
async def create_session():
    record = session_store.create_session()
    return {
        "session_id": record.session_id,
        "messages": [message.model_dump() for message in record.messages],
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    record = session_store.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "messages": [message.model_dump() for message in record.messages],
    }


@app.delete("/api/sessions/{session_id}")
async def clear_session(session_id: str):
    if not session_store.clear_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "cleared": True}


@app.post("/api/chat")
async def api_chat(request: ChatTurnRequest):
    session = session_store.create_session(request.session_id)
    enriched_request = request.model_copy(
        update={
            "session_id": session.session_id,
            "history": session_store.list_messages(session.session_id),
        }
    )

    try:
        response = await run_chat_turn(enriched_request)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "validation_error", "message": str(exc)},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "runtime_error",
                "message": str(exc),
            },
        ) from exc

    session_store.append_message(
        session.session_id,
        ChatSessionMessage(role="user", content=request.prompt),
    )
    session_store.append_message(
        session.session_id,
        ChatSessionMessage(
            role="assistant",
            content=response.reply,
            run_id=response.run_id,
            path=response.path,
            trace_path=response.trace_path,
        ),
    )

    return response.model_copy(update={"session_id": session.session_id})
