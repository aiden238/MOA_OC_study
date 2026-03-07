"""BaseAgent 단위 테스트 — mock 기반 (API 키 불필요)."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput


@pytest.fixture
def mock_openai_response():
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Mock response"}}
        ],
        "usage": {
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }


class TestBaseAgent:
    def test_init(self):
        agent = BaseAgent(agent_name="test_agent", system_prompt="You are helpful.")
        assert agent.agent_name == "test_agent"
        assert agent.system_prompt == "You are helpful."

    def test_init_no_prompt(self):
        agent = BaseAgent(agent_name="bare")
        assert agent.system_prompt == ""

    @pytest.mark.asyncio
    async def test_run_with_mock(self, mock_openai_response):
        agent = BaseAgent(agent_name="test_agent", system_prompt="Be concise.")

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: mock_openai_response
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_resp
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            output = await agent.run("Hello, world!")

        assert isinstance(output, AgentOutput)
        assert output.agent_name == "test_agent"
        assert output.content == "Mock response"
        assert output.model == "gpt-4o-mini"
        assert output.prompt_tokens == 20
        assert output.completion_tokens == 10
        assert output.latency_ms >= 0


class TestLoadPrompt:
    def test_load_existing_prompt(self, tmp_path):
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("# Role: Tester\n\nYou are a test agent.", encoding="utf-8")

        with patch.object(BaseAgent, "PROMPTS_DIR", tmp_path):
            content = BaseAgent.load_prompt("test_prompt")
        assert "Role: Tester" in content

    def test_load_missing_prompt_raises(self):
        with pytest.raises(FileNotFoundError):
            BaseAgent.load_prompt("nonexistent_prompt_xyz")


class TestCostEstimation:
    def test_gpt4o_mini_cost(self):
        cost = BaseAgent._estimate_cost(1000, 500, "gpt-4o-mini")
        expected = 1000 * (0.15 / 1_000_000) + 500 * (0.60 / 1_000_000)
        assert cost == round(expected, 6)

    def test_unknown_model_zero_cost(self):
        cost = BaseAgent._estimate_cost(1000, 500, "unknown-model")
        assert cost == 0.0
