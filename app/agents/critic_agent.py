"""Critic Agent — 3개 draft를 비교 분석하여 강점/약점을 정리하는 에이전트.

Draft Agent들이 생성한 3개의 초안을 받아 각각의 강점과 약점을 분석하고,
최종 조합을 위한 권고사항을 구조화된 JSON으로 출력한다.
"""

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput


class CriticAgent(BaseAgent):
    """3개 draft를 비교 분석하는 비평 에이전트."""

    def __init__(self):
        # critic.md 프롬프트 파일 로딩
        prompt = self.load_prompt("critic")
        super().__init__(agent_name="critic", system_prompt=prompt)

    def _format_drafts(self, drafts: list[AgentOutput]) -> str:
        """3개 draft를 [Draft A], [Draft B], [Draft C] 형식으로 포맷."""
        labels = ["A", "B", "C"]
        parts = []
        for i, draft in enumerate(drafts):
            label = labels[i] if i < len(labels) else f"D{i+1}"
            variant = draft.agent_name.replace("draft_", "")  # analytical, creative, structured
            parts.append(f"[Draft {label} — {variant}]\n{draft.content}")
        return "\n\n---\n\n".join(parts)

    async def critique(self, drafts: list[AgentOutput], original_prompt: str = "") -> AgentOutput:
        """3개 draft의 강점/약점을 비교 분석.

        Args:
            drafts: Draft Agent들의 출력 리스트 (2~3개)
            original_prompt: 원래 사용자 요청 (컨텍스트 제공용)

        Returns:
            비교 분석 결과를 담은 AgentOutput
        """
        formatted = self._format_drafts(drafts)

        # 원래 요청이 있으면 컨텍스트로 포함
        context = ""
        if original_prompt:
            context = f"[원래 요청]\n{original_prompt}\n\n"

        message = f"""{context}아래 {len(drafts)}개의 초안을 비교 분석해 주세요.
각 초안의 강점과 약점을 정리하고, 최종 결과물을 위한 권고사항을 제시하세요.

반드시 JSON 형식으로 응답하세요:
{{"draft_analyses": [{{"draft": "A", "strengths": ["..."], "weaknesses": ["..."]}}, ...], "recommendation": "...", "key_improvements": ["..."]}}

{formatted}"""

        return await self.run(message, temperature=0.3)
