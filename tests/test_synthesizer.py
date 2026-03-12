"""Synthesizer Agent 단위 테스트 — mock 기반."""

from unittest.mock import AsyncMock, patch

import pytest

from app.orchestrator.synthesizer import SynthesizerAgent
from app.schemas.agent_io import AgentOutput


@pytest.fixture
def sample_drafts():
    """3개의 mock draft 출력."""
    return [
        AgentOutput(
            agent_name="draft_analytical", content="분석적 초안",
            model="gpt-4o-mini", prompt_tokens=50, completion_tokens=30, latency_ms=100.0,
        ),
        AgentOutput(
            agent_name="draft_creative", content="창의적 초안",
            model="gpt-4o-mini", prompt_tokens=50, completion_tokens=30, latency_ms=120.0,
        ),
        AgentOutput(
            agent_name="draft_structured", content="구조적 초안",
            model="gpt-4o-mini", prompt_tokens=50, completion_tokens=30, latency_ms=110.0,
        ),
    ]


@pytest.fixture
def sample_critique():
    """Critic의 mock 분석 결과."""
    return AgentOutput(
        agent_name="critic",
        content='{"draft_analyses": [{"draft": "A", "strengths": ["논리적"]}], "recommendation": "A+C 조합"}',
        model="gpt-4o-mini",
        prompt_tokens=200, completion_tokens=100, latency_ms=150.0,
    )


@pytest.fixture
def mock_openai_synthesis():
    """Synthesizer의 mock API 응답."""
    return {
        "id": "chatcmpl-synth",
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "최종 조합된 결과물입니다."},
        }],
        "usage": {"prompt_tokens": 300, "completion_tokens": 150, "total_tokens": 450},
    }


class TestSynthesizerAgent:
    def test_init(self):
        """Synthesizer 에이전트 초기화 확인."""
        synth = SynthesizerAgent()
        assert synth.agent_name == "synthesizer"
        assert len(synth.system_prompt) > 0

    def test_format_inputs(self, sample_drafts, sample_critique):
        """입력 포맷팅이 올바른지 확인."""
        synth = SynthesizerAgent()
        formatted = synth._format_inputs(sample_drafts, sample_critique)
        assert "[Draft A — analytical]" in formatted
        assert "[Draft B — creative]" in formatted
        assert "[Draft C — structured]" in formatted
        assert "[Critic 분석]" in formatted

    @pytest.mark.asyncio
    async def test_synthesize_with_mock(self, sample_drafts, sample_critique, mock_openai_synthesis):
        """mock API로 synthesize 실행 확인."""
        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_synthesis
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            synth = SynthesizerAgent()
            result = await synth.synthesize(
                sample_drafts, sample_critique, original_prompt="테스트 요청"
            )

        assert isinstance(result, AgentOutput)
        assert result.agent_name == "synthesizer"
        assert result.content == "최종 조합된 결과물입니다."

    @pytest.mark.asyncio
    async def test_synthesize_without_original_prompt(self, sample_drafts, sample_critique, mock_openai_synthesis):
        """원래 요청 없이도 synthesize가 동작하는지 확인."""
        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_openai_synthesis
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            synth = SynthesizerAgent()
            result = await synth.synthesize(sample_drafts, sample_critique)

        assert isinstance(result, AgentOutput)
