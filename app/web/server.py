"""FastAPI server for the Week 10 web chat UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.model_registry import get_model_registry_payload
from app.schemas.chat import ChatSessionMessage, ChatTurnRequest
from app.services.chat_service import run_chat_turn
from app.web.session_store import SessionStore


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="MOA Web Chat")
session_store = SessionStore(max_messages=10)

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
