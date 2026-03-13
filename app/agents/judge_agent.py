"""Judge Agent — Synthesizer 출력의 품질을 판정하는 심판 에이전트.

최종 합성 결과를 받아 pass / rewrite / escalate 중 하나를 판정한다.
- pass:     품질 충분 → 최종 출력으로 확정
- rewrite:  개선 필요 → Rewrite Agent에게 전달 (최대 2회 루프)
- escalate: 근본적 문제 → 사람 검토 플래그 기록 후 중단
"""

import json

from app.agents.base_agent import BaseAgent
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest


class JudgeAgent(BaseAgent):
    """최종 출력의 품질을 판정하는 에이전트."""

    def __init__(self):
        # judge.md 프롬프트 파일 로딩
        prompt = self.load_prompt("judge")
        super().__init__(agent_name="judge", system_prompt=prompt)

    async def judge(self, task: TaskRequest, output: AgentOutput) -> JudgeDecision:
        """합성 결과의 품질을 판정하여 JudgeDecision을 반환.

        Args:
            task: 원래 태스크 요청 (프롬프트·제약 조건 참조)
            output: 평가 대상 에이전트 출력

        Returns:
            JudgeDecision (decision, confidence, reasoning, improvement_hints)
        """
        # 제약 조건 텍스트 구성
        constraint_text = ""
        if task.constraints:
            constraint_text = f"\n\n[제약 조건]\n{json.dumps(task.constraints, ensure_ascii=False)}"

        message = f"""[원래 요청]
{task.prompt}{constraint_text}

[생성된 결과]
{output.content}

위의 [원래 요청]과 [생성된 결과]를 비교 분석하고, 품질을 판정하세요.
반드시 아래 JSON 형식으로만 응답하세요:
{{"decision": "pass|rewrite|escalate", "confidence": 0.0~1.0, "reasoning": "판정 근거", "improvement_hints": ["개선 포인트1", ...]}}"""

        # 낮은 temperature로 일관된 판정 유도
        result = await self.run(message, temperature=0.2)

        # JSON 파싱 → JudgeDecision 변환
        return self._parse_decision(result.content)

    @staticmethod
    def _parse_decision(response_text: str) -> JudgeDecision:
        """Judge 응답 텍스트에서 JSON을 추출하여 JudgeDecision으로 변환."""
        text = response_text.strip()

        # ```json ... ``` 블록 처리
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        data = json.loads(text)

        # decision 값 검증: 허용되지 않은 값이면 escalate로 처리
        if data.get("decision") not in ("pass", "rewrite", "escalate"):
            data["decision"] = "escalate"
            data["reasoning"] = f"잘못된 판정값: {data.get('decision', 'N/A')}"

        return JudgeDecision(
            decision=data["decision"],
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning", ""),
            improvement_hints=data.get("improvement_hints", []),
        )
