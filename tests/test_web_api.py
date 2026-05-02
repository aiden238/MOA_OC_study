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
        assert {provider["id"] for provider in payload["providers"]} == {"openai", "gemini", "zai", "cerebras"}
        assert "single_baseline" in payload["agents"]

    def test_knowledge_graph_endpoint_returns_nodes_and_edges(self):
        client = _client()

        response = client.get("/api/knowledge-graph")

        assert response.status_code == 200
        payload = response.json()
        assert payload["stats"]["node_count"] > 0
        assert payload["stats"]["edge_count"] > 0
        assert any(node["type"] == "document" for node in payload["nodes"])

    def test_wiki_manual_candidate_round_trip(self, tmp_path):
        client = _client()
        original_service = server.wiki_update_service
        server.wiki_update_service = server.WikiUpdateService(
            docs_dir=tmp_path / "rag_docs",
            state_dir=tmp_path / "wiki_state",
            knowledge_graph_dir=tmp_path / "knowledge_graph",
            chroma_dir=tmp_path / "chroma",
        )
        server.wiki_update_service.docs_dir.mkdir(parents=True, exist_ok=True)
        try:
            create_response = client.post(
                "/api/wiki/manual-candidate",
                json={
                    "title": "Reasoning Trace Compression",
                    "content": "Compress long reasoning traces before synthesis.",
                    "summary": "A compact reasoning compression note.",
                    "category": "advanced",
                    "tags": ["reasoning", "compression"],
                },
            )
            assert create_response.status_code == 200
            pending_id = create_response.json()["pending_id"]

            pending_response = client.get("/api/wiki/pending")
            assert pending_response.status_code == 200
            assert len(pending_response.json()["items"]) == 1

            approve_response = client.post(f"/api/wiki/pending/{pending_id}/approve")
            assert approve_response.status_code == 200
            payload = approve_response.json()
            assert payload["filename"].startswith("wiki_")

            status_response = client.get("/api/wiki/status")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            assert status_payload["approved_count"] == 1
        finally:
            server.wiki_update_service = original_service

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
