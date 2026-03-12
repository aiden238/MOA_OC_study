"""Synthesizer Agent — Critic 피드백과 drafts를 기반으로 최종 결과를 생성.

Critic이 분석한 강점/약점과 3개의 draft를 모두 받아,
각 초안의 장점을 조합하고 약점을 보완하여 하나의 최종 결과물을 만든다.
"""

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput


class SynthesizerAgent(BaseAgent):
    """Critic 피드백과 drafts를 조합하여 최종 결과를 생성하는 에이전트."""

    def __init__(self):
        # synthesizer.md 프롬프트 파일 로딩
        prompt = self.load_prompt("synthesizer")
        super().__init__(agent_name="synthesizer", system_prompt=prompt)

    def _format_inputs(self, drafts: list[AgentOutput], critique: AgentOutput) -> str:
        """drafts와 critic 피드백을 하나의 메시지로 포맷."""
        labels = ["A", "B", "C"]
        parts = []

        # 각 draft 내용
        for i, draft in enumerate(drafts):
            label = labels[i] if i < len(labels) else f"D{i+1}"
            variant = draft.agent_name.replace("draft_", "")
            parts.append(f"[Draft {label} — {variant}]\n{draft.content}")

        drafts_text = "\n\n---\n\n".join(parts)

        # Critic 분석 결과
        critique_text = f"[Critic 분석]\n{critique.content}"

        return f"{drafts_text}\n\n{'='*50}\n\n{critique_text}"

    async def synthesize(
        self,
        drafts: list[AgentOutput],
        critique: AgentOutput,
        original_prompt: str = "",
    ) -> AgentOutput:
        """drafts + critic 피드백 → 최종 조합 결과 생성.

        Args:
            drafts: Draft Agent들의 출력 리스트
            critique: Critic Agent의 분석 결과
            original_prompt: 원래 사용자 요청

        Returns:
            최종 조합된 결과를 담은 AgentOutput
        """
        formatted = self._format_inputs(drafts, critique)

        # 원래 요청 컨텍스트
        context = ""
        if original_prompt:
            context = f"[원래 요청]\n{original_prompt}\n\n"

        message = f"""{context}아래 초안들과 Critic 분석을 참고하여 최종 결과물을 작성하세요.
각 초안의 강점을 살리고 약점을 보완하여 하나의 완성도 높은 결과를 만들어 주세요.

{formatted}"""

        return await self.run(message, temperature=0.5)
