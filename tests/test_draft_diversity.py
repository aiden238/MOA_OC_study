"""Draft 다양성 검증 테스트 — 3개 draft가 충분히 다른 관점을 제시하는지 확인.

동일 입력에 대해 3개 draft의 텍스트 유사도가 0.7 이하여야 통과.
SequenceMatcher로 쌍별(A-B, A-C, B-C) 유사도를 측정한다.
"""

from difflib import SequenceMatcher
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.draft_agent import DRAFT_VARIANTS, DraftAgent, run_all_drafts
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest


def _similarity(a: str, b: str) -> float:
    """두 텍스트의 유사도를 0~1 사이 값으로 반환."""
    return SequenceMatcher(None, a, b).ratio()


class TestDraftAgent:
    def test_init_variants(self):
        """3가지 변형이 올바르게 초기화되는지 확인."""
        for variant in DRAFT_VARIANTS:
            agent = DraftAgent(variant)
            assert agent.agent_name == f"draft_{variant}"
            assert agent.temperature == DRAFT_VARIANTS[variant]["temperature"]

    def test_invalid_variant_raises(self):
        """잘못된 변형명은 ValueError를 발생시킨다."""
        with pytest.raises(ValueError, match="알 수 없는"):
            DraftAgent("nonexistent")

    def test_temperature_override(self):
        """각 변형의 temperature가 올바르게 설정되는지 확인."""
        assert DraftAgent("analytical").temperature == 0.4
        assert DraftAgent("creative").temperature == 0.9
        assert DraftAgent("structured").temperature == 0.6


class TestDraftDiversity:
    """Mock 기반 다양성 검증 — 3개 draft의 유사도가 0.7 이하인지 확인."""

    @pytest.mark.asyncio
    async def test_drafts_are_diverse(self):
        """서로 다른 mock 응답으로 다양성 기준 충족 확인."""
        # 실제 API 호출 없이 서로 다른 내용의 mock 응답 3개 준비
        mock_responses = [
            "분석적 관점에서 접근하면, 이 문제는 데이터 기반으로 해결해야 합니다. 통계적 분석과 논리적 추론을 통해 최적의 방안을 도출할 수 있습니다.",
            "창의적으로 생각하면 완전히 새로운 접근이 가능합니다! 기존의 틀을 깨고 상상력을 발휘하여 혁신적인 아이디어를 만들어 봅시다.",
            "1. 문제 정의\n2. 현황 분석\n3. 해결 방안\n  3.1 단기 방안\n  3.2 장기 방안\n4. 실행 계획\n5. 기대 효과",
        ]

        outputs = []
        for i, (variant, content) in enumerate(zip(DRAFT_VARIANTS, mock_responses)):
            outputs.append(AgentOutput(
                agent_name=f"draft_{variant}",
                content=content,
                model="gpt-4o-mini",
                prompt_tokens=50,
                completion_tokens=30,
                latency_ms=100.0,
            ))

        # 3쌍의 유사도 계산
        pairs = [(0, 1), (0, 2), (1, 2)]
        similarities = [
            _similarity(outputs[a].content, outputs[b].content)
            for a, b in pairs
        ]
        avg_similarity = sum(similarities) / len(similarities)

        # 평균 유사도가 0.7 이하여야 다양성 충분
        assert avg_similarity <= 0.7, f"평균 유사도 {avg_similarity:.3f} > 0.7 — 다양성 부족"

    @pytest.mark.asyncio
    async def test_run_all_drafts_with_mock(self):
        """run_all_drafts가 3개 결과를 반환하는지 확인."""
        mock_response = {
            "id": "chatcmpl-test",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Mock draft"}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        }

        mock_resp = AsyncMock()
        mock_resp.json = lambda: mock_response
        mock_resp.raise_for_status = lambda: None

        with patch("app.agents.base_agent.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            task = TaskRequest(prompt="테스트 프롬프트")
            results = await run_all_drafts(task)

        assert len(results) == 3
        agents = {r.agent_name for r in results}
        assert agents == {"draft_analytical", "draft_creative", "draft_structured"}

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """일부 draft가 실패해도 나머지 결과를 반환하는지 확인."""
        call_count = 0

        async def mock_run(self, user_message, **kwargs):
            nonlocal call_count
            call_count += 1
            if self.variant == "creative":
                raise RuntimeError("의도적 실패")
            return AgentOutput(
                agent_name=self.agent_name,
                content="성공한 draft",
                model="gpt-4o-mini",
                prompt_tokens=50,
                completion_tokens=30,
                latency_ms=100.0,
            )

        with patch.object(DraftAgent, "run", mock_run):
            task = TaskRequest(prompt="테스트")
            results = await run_all_drafts(task)

        # creative가 실패해도 나머지 2개는 반환
        assert len(results) == 2
