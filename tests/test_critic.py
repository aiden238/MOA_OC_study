"""Critic Agent 단위 테스트 — mock 기반."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.critic_agent import CriticAgent
from app.schemas.agent_io import AgentOutput


@pytest.fixture
def sample_drafts():
    """3개의 mock draft 출력."""
    return [
        AgentOutput(
            agent_name="draft_analytical",
            content="분석적 관점의 초안입니다.",
            model="gpt-4o-mini",
            prompt_tokens=50, completion_tokens=30, latency_ms=100.0,
        ),
        AgentOutput(
            agent_name="draft_creative",
            content="창의적 관점의 초안입니다.",
            model="gpt-4o-mini",
            prompt_tokens=50, completion_tokens=30, latency_ms=120.0,
        ),
        AgentOutput(
            agent_name="draft_structured",
            content="구조적 관점의 초안입니다.",
            model="gpt-4o-mini",
            prompt_tokens=50, completion_tokens=30, latency_ms=110.0,
        ),
    ]


@pytest.fixture
def mock_openai_critique():
    """Critic의 mock API 응답."""
    return {
        "id": "chatcmpl-critic",
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"draft_analyses": [{"draft": "A", "strengths": ["논리적"], "weaknesses": ["창의성 부족"]}, {"draft": "B", "strengths": ["참신"], "weaknesses": ["구조 부족"]}, {"draft": "C", "strengths": ["체계적"], "weaknesses": ["딱딱함"]}], "recommendation": "A와 C의 장점을 조합", "key_improvements": ["창의적 비유 추가"]}'
            },
        }],
        "usage": {"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300},
    }


class TestCriticAgent:
    def test_init(self):
        """Critic 에이전트 초기화 확인."""
        critic = CriticAgent()
        assert critic.agent_name == "critic"
        assert len(critic.system_prompt) > 0

    def test_format_drafts(self, sample_drafts):
        """draft 포맷팅이 올바른지 확인."""
        critic = CriticAgent()
        formatted = critic._format_drafts(sample_drafts)
        assert "[Draft A — analytical]" in formatted
        assert "[Draft B — creative]" in formatted
        assert "[Draft C — structured]" in formatted

    @pytest.mark.asyncio
    async def test_critique_with_mock(self, sample_drafts, mock_openai_critique):
        """mock API로 critique 실행 확인."""
        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_critique
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            critic = CriticAgent()
            result = await critic.critique(sample_drafts, original_prompt="테스트 요청")

        assert isinstance(result, AgentOutput)
        assert result.agent_name == "critic"
        assert "draft_analyses" in result.content

    @pytest.mark.asyncio
    async def test_critique_with_two_drafts(self, mock_openai_critique):
        """2개 draft만으로도 critique가 동작하는지 확인."""
        drafts = [
            AgentOutput(
                agent_name="draft_analytical", content="초안A",
                model="gpt-4o-mini", prompt_tokens=30, completion_tokens=20, latency_ms=80.0,
            ),
            AgentOutput(
                agent_name="draft_structured", content="초안C",
                model="gpt-4o-mini", prompt_tokens=30, completion_tokens=20, latency_ms=90.0,
            ),
        ]

        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_critique
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            critic = CriticAgent()
            result = await critic.critique(drafts)

        assert isinstance(result, AgentOutput)
