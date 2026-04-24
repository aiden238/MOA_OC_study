"""Session store tests for the web chat UI."""

from app.schemas.chat import ChatSessionMessage
from app.web.session_store import SessionStore


class TestSessionStore:
    def test_create_session_reuses_explicit_id(self):
        store = SessionStore(max_messages=3)

        first = store.create_session("abc123")
        second = store.create_session("abc123")

        assert first.session_id == "abc123"
        assert second is first

    def test_append_message_trims_to_max_messages(self):
        store = SessionStore(max_messages=2)
        session = store.create_session("trim")

        store.append_message(session.session_id, ChatSessionMessage(role="user", content="one"))
        store.append_message(session.session_id, ChatSessionMessage(role="assistant", content="two"))
        store.append_message(session.session_id, ChatSessionMessage(role="user", content="three"))

        messages = store.list_messages(session.session_id)
        assert [message.content for message in messages] == ["two", "three"]

    def test_clear_session_preserves_record_and_empties_messages(self):
        store = SessionStore(max_messages=2)
        session = store.create_session("clear")
        store.append_message(session.session_id, ChatSessionMessage(role="user", content="hello"))

        assert store.clear_session(session.session_id) is True
        assert store.list_messages(session.session_id) == []
        assert store.get_session(session.session_id) is not None
