"""FastAPI tests for the Week 10 web chat server."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.schemas.chat import ChatMetrics, ChatTurnResponse
from app.web import server


def _client() -> TestClient:
    server.session_store._sessions.clear()
    return TestClient(server.app)


class TestWebApi:
    def test_models_endpoint_returns_registry(self):
        client = _client()

        response = client.get("/api/models")

        assert response.status_code == 200
        payload = response.json()
        assert {provider["id"] for provider in payload["providers"]} == {"openai", "gemini", "zai"}
        assert "single_baseline" in payload["agents"]

    def test_chat_endpoint_creates_session_and_persists_messages(self):
        client = _client()
        mock_response = ChatTurnResponse(
            run_id="run123",
            prompt="Hello",
            reply="Hi there",
            path="single",
            routing_reason="simple request",
            routing_confidence=0.9,
            metrics=ChatMetrics(prompt_tokens=10, completion_tokens=4, latency_ms=12.0),
            trace_path="trace.json",
            agents=["single_baseline"],
            agent_count=1,
        )

        with patch("app.web.server.run_chat_turn", new=AsyncMock(return_value=mock_response)):
            response = client.post("/api/chat", json={"prompt": "Hello"})

        assert response.status_code == 200
        payload = response.json()
        session_id = payload["session_id"]
        assert session_id
        assert payload["reply"] == "Hi there"

        session_response = client.get(f"/api/sessions/{session_id}")
        assert session_response.status_code == 200
        messages = session_response.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_chat_endpoint_returns_400_for_validation_error(self):
        client = _client()

        with patch(
            "app.web.server.run_chat_turn",
            new=AsyncMock(side_effect=ValueError("invalid preset")),
        ):
            response = client.post("/api/chat", json={"prompt": "Hello"})

        assert response.status_code == 400
        assert response.json()["detail"]["error_code"] == "validation_error"

    def test_delete_session_clears_messages(self):
        client = _client()
        create_response = client.post("/api/sessions")
        session_id = create_response.json()["session_id"]
        server.session_store.append_message(
            session_id,
            server.ChatSessionMessage(role="user", content="hello"),
        )

        response = client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        session_response = client.get(f"/api/sessions/{session_id}")
        assert session_response.status_code == 200
        assert session_response.json()["messages"] == []
