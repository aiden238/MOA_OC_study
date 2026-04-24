"""In-memory session storage for the web chat UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from app.schemas.chat import ChatSessionMessage


@dataclass
class SessionRecord:
    session_id: str
    messages: list[ChatSessionMessage] = field(default_factory=list)


class SessionStore:
    """Simple in-memory session store."""

    def __init__(self, max_messages: int = 10):
        self.max_messages = max_messages
        self._sessions: dict[str, SessionRecord] = {}

    def create_session(self, session_id: str | None = None) -> SessionRecord:
        resolved = session_id or uuid4().hex[:12]
        record = self._sessions.get(resolved)
        if record is None:
            record = SessionRecord(session_id=resolved)
            self._sessions[resolved] = record
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._sessions.get(session_id)

    def list_messages(self, session_id: str) -> list[ChatSessionMessage]:
        record = self.get_session(session_id)
        if record is None:
            return []
        return list(record.messages)

    def append_message(self, session_id: str, message: ChatSessionMessage):
        record = self.create_session(session_id)
        record.messages.append(message)
        if len(record.messages) > self.max_messages:
            record.messages = record.messages[-self.max_messages :]

    def clear_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        self._sessions[session_id].messages = []
        return True
