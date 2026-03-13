"""Judge Agent + Rewrite Agent 단위 테스트.

- JudgeAgent 초기화, JSON 파싱, Mock 판정
- RewriteAgent 초기화, Mock 재작성
- Judge → Rewrite 루프 통합 테스트
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.judge_agent import JudgeAgent
from app.agents.rewrite_agent import RewriteAgent
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest


# ── 테스트용 헬퍼 ──

def _mock_output(agent_name: str = "synthesizer", content: str = "테스트 결과") -> AgentOutput:
    """테스트용 mock AgentOutput 생성."""
    return AgentOutput(
        agent_name=agent_name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
    )


# ── JudgeAgent 테스트 ──

class TestJudgeAgent:

    def test_init(self):
        """JudgeAgent 초기화 확인."""
        agent = JudgeAgent()
        assert agent.agent_name == "judge"
        assert "judge" in agent.system_prompt.lower() or "판정" in agent.system_prompt

    def test_parse_decision_pass(self):
        """pass 판정 JSON 파싱."""
        raw = json.dumps({
            "decision": "pass",
            "confidence": 0.9,
            "reasoning": "품질 충분",
            "improvement_hints": [],
        })
        decision = JudgeAgent._parse_decision(raw)
        assert decision.decision == "pass"
        assert decision.confidence == 0.9
        assert decision.reasoning == "품질 충분"

    def test_parse_decision_rewrite(self):
        """rewrite 판정 JSON 파싱 + improvement_hints."""
        raw = json.dumps({
            "decision": "rewrite",
            "confidence": 0.6,
            "reasoning": "제약 조건 미준수",
            "improvement_hints": ["3문장 제한 준수", "논리 흐름 보강"],
        })
        decision = JudgeAgent._parse_decision(raw)
        assert decision.decision == "rewrite"
        assert len(decision.improvement_hints) == 2

    def test_parse_decision_code_block(self):
        """```json``` 블록으로 감싼 응답 파싱."""
        raw = '```json\n{"decision": "pass", "confidence": 0.85, "reasoning": "OK"}\n```'
        decision = JudgeAgent._parse_decision(raw)
        assert decision.decision == "pass"

    def test_parse_decision_invalid_falls_to_escalate(self):
        """잘못된 decision 값은 escalate로 처리."""
        raw = json.dumps({
            "decision": "unknown_value",
            "confidence": 0.5,
            "reasoning": "테스트",
        })
        decision = JudgeAgent._parse_decision(raw)
        assert decision.decision == "escalate"

    @pytest.mark.asyncio
    async def test_judge_with_mock(self):
        """Mock API로 Judge 판정 테스트."""
        judge_response = json.dumps({
            "decision": "rewrite",
            "confidence": 0.65,
            "reasoning": "제약 초과",
            "improvement_hints": ["3문장 제한 준수"],
        })

        mock_output = _mock_output(content=judge_response)

        with patch.object(JudgeAgent, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_output

            agent = JudgeAgent()
            task = TaskRequest(prompt="테스트 프롬프트")
            synth_output = _mock_output(content="합성 결과 텍스트")

            decision = await agent.judge(task, synth_output)

        assert decision.decision == "rewrite"
        assert decision.confidence == 0.65
        assert "3문장" in decision.improvement_hints[0]


# ── RewriteAgent 테스트 ──

class TestRewriteAgent:

    def test_init(self):
        """RewriteAgent 초기화 확인."""
        agent = RewriteAgent()
        assert agent.agent_name == "rewrite"

    @pytest.mark.asyncio
    async def test_rewrite_with_mock(self):
        """Mock API로 Rewrite 테스트."""
        improved_output = _mock_output(
            agent_name="rewrite",
            content="개선된 결과 텍스트",
        )

        with patch.object(RewriteAgent, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = improved_output

            agent = RewriteAgent()
            original = _mock_output(content="원본 텍스트")
            feedback = JudgeDecision(
                decision="rewrite",
                confidence=0.6,
                reasoning="제약 조건 미준수",
                improvement_hints=["3문장 제한 준수", "논리 보강"],
            )

            result = await agent.rewrite(original, feedback)

        assert result.content == "개선된 결과 텍스트"
        assert result.agent_name == "rewrite"
        # run 호출 시 피드백 내용이 메시지에 포함되었는지 확인
        call_msg = mock_run.call_args[0][0]
        assert "3문장 제한 준수" in call_msg
        assert "원본 텍스트" in call_msg


# ── JudgeDecision 스키마 테스트 ──

class TestJudgeDecision:

    def test_valid_creation(self):
        """정상 JudgeDecision 생성."""
        d = JudgeDecision(
            decision="pass",
            confidence=0.95,
            reasoning="완벽한 결과",
        )
        assert d.decision == "pass"
        assert d.improvement_hints == []

    def test_confidence_bounds(self):
        """confidence가 0~1 범위를 벗어나면 ValidationError."""
        with pytest.raises(Exception):
            JudgeDecision(decision="pass", confidence=1.5, reasoning="초과")

    def test_invalid_decision_raises(self):
        """허용되지 않은 decision 값은 ValidationError."""
        with pytest.raises(Exception):
            JudgeDecision(decision="invalid", confidence=0.5, reasoning="잘못됨")
