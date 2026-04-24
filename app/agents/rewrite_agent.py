"""Rewrite Agent — Judge 피드백을 반영하여 출력을 개선하는 에이전트.

Judge가 "rewrite" 판정을 내린 경우, 원본 출력과 개선 포인트를 받아
품질을 높인 새 버전을 생성한다.
최대 2회까지만 재작성 (무한 루프 방지).
"""

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput, JudgeDecision


class RewriteAgent(BaseAgent):
    """Judge 피드백을 기반으로 출력을 개선하는 에이전트."""

    def __init__(self, model_settings: dict[str, str] | None = None):
        # rewrite.md 프롬프트 파일 로딩
        prompt = self.load_prompt("rewrite")
        settings = model_settings or {}
        super().__init__(
            agent_name="rewrite",
            system_prompt=prompt,
            provider=settings.get("provider"),
            model=settings.get("model"),
            api_key=settings.get("api_key"),
            base_url=settings.get("base_url"),
        )

    async def rewrite(self, original: AgentOutput, feedback: JudgeDecision) -> AgentOutput:
        """원본 출력 + Judge 피드백 → 개선된 텍스트 생성.

        Args:
            original: 개선 대상 원본 에이전트 출력
            feedback: Judge의 판정 결과 (reasoning, improvement_hints 활용)

        Returns:
            개선된 텍스트를 담은 AgentOutput
        """
        # 개선 포인트를 번호 목록으로 포맷
        hints_text = "\n".join(
            f"  {i+1}. {hint}" for i, hint in enumerate(feedback.improvement_hints)
        )
        if not hints_text:
            hints_text = "  (구체적 개선 포인트 없음 — 전반적 품질 향상 필요)"

        message = f"""[원본 텍스트]
{original.content}

[Judge 판정]
- 결과: {feedback.decision}
- 확신도: {feedback.confidence:.2f}
- 사유: {feedback.reasoning}

[개선 포인트]
{hints_text}

위의 Judge 피드백을 반영하여 원본 텍스트를 개선해 주세요.
개선 포인트를 하나씩 확인하며 반영하되, 원본의 장점은 유지하세요."""

        return await self.run(message, temperature=0.4)
