"""run_full.py 시범 실행 테스트 — Mock API를 사용하여 전체 파이프라인 흐름과 결과 저장을 검증.

API 키 없이도 Router → single/moa 분기 → 결과 JSON 저장까지의
전체 흐름이 올바르게 동작하는지 확인한다.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.router import Router, RoutingDecision, rule_based_route
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest
from scripts.run_full import run_single_path, run_moa_path, save_full_output, run_pipeline


def _mock_output(name: str, content: str = "mock") -> AgentOutput:
    """테스트용 AgentOutput 생성 헬퍼."""
    return AgentOutput(
        agent_name=name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
        cost_estimate=0.001,
    )


class TestRunFullPipeline:
    """run_full.py의 핵심 함수를 Mock으로 검증."""

    @pytest.mark.asyncio
    async def test_single_path(self):
        """single 경로가 BaseAgent 단일 호출로 동작하는지 확인."""
        mock_output = _mock_output("single_baseline", "단일 결과")

        with patch("scripts.run_full.BaseAgent") as MockAgent:
            MockAgent.return_value = AsyncMock(run=AsyncMock(return_value=mock_output))

            task = TaskRequest(prompt="간단한 요약", task_type="summarize")
            logger = TraceLogger(run_id="test-single")
            tracker = CostTracker()

            text, outputs = await run_single_path(task, logger, tracker)

        assert text == "단일 결과"
        assert len(outputs) == 1
        assert tracker.total_tokens > 0

    @pytest.mark.asyncio
    async def test_moa_path(self):
        """moa 경로가 MOAExecutor를 통해 실행되는지 확인."""
        mock_drafts = [_mock_output(f"draft_{v}") for v in ["analytical", "creative", "structured"]]
        mock_critic = _mock_output("critic", '{"analyses": []}')
        mock_synth = _mock_output("synthesizer", "MOA 최종 결과")
        mock_judge = JudgeDecision(decision="pass", confidence=0.95, reasoning="OK")

        with patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
             patch("app.orchestrator.executor.JudgeAgent") as MockJudge:

            mock_run.return_value = mock_drafts
            MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
            MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
            MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))

            task = TaskRequest(prompt="창의적 아이디어", task_type="ideate")
            logger = TraceLogger(run_id="test-moa")
            tracker = CostTracker()

            text, outputs = await run_moa_path(task, logger, tracker)

        assert text == "MOA 최종 결과"
        assert len(outputs) == 6  # 3 draft + critic + synth + judge

    @pytest.mark.asyncio
    async def test_moa_path_passes_routing(self):
        """run_moa_path가 routing decision을 executor까지 전달하는지 확인."""
        mock_outputs = [_mock_output("draft_analytical", "MOA 결과")]
        routing = RoutingDecision(
            selected_path="moa",
            reason="routing 전달 테스트",
            confidence=0.9,
            requires_rag=True,
            rag_query_hint="test query",
        )

        with patch("scripts.run_full.MOAExecutor") as MockExecutor:
            executor = AsyncMock()
            executor.execute.return_value = ("MOA 결과", mock_outputs)
            MockExecutor.return_value = executor

            task = TaskRequest(prompt="문서 기반 질문", task_type="explain")
            logger = TraceLogger(run_id="test-moa-routing")
            tracker = CostTracker()

            text, outputs = await run_moa_path(task, logger, tracker, routing=routing)

        assert text == "MOA 결과"
        assert outputs == mock_outputs
        executor.execute.assert_awaited_once_with(task, logger, routing=routing)

    def test_save_full_output(self, tmp_path):
        """결과 JSON이 올바르게 저장되는지 확인."""
        result = {
            "case_id": "test-001",
            "task_type": "summarize",
            "prompt": "테스트",
            "output": "결과",
            "path": "single",
            "routing_reason": "test",
            "routing_confidence": 0.9,
            "agent_count": 1,
            "agents": ["single_baseline"],
            "prompt_tokens": 50,
            "completion_tokens": 30,
            "latency_ms": 100.0,
            "cost_estimate": 0.001,
        }
        path = save_full_output(result, output_dir=tmp_path)
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["case_id"] == "test-001"
        assert loaded["output"] == "결과"
        assert loaded["evaluation"] == {}
        assert loaded["evaluation_context"] == {}
        assert loaded["context_metadata"] == {}

    @pytest.mark.asyncio
    async def test_run_pipeline_with_evaluation(self, tmp_path):
        """--evaluate 경로에서 evaluation이 비어 있지 않게 저장되는지 확인."""
        cases = [{
            "id": "sum-001",
            "prompt": "간단 요약",
            "type": "summarize",
            "constraints": {"difficulty": "low"},
            "metadata": {},
        }]

        mock_single_output = _mock_output("single_baseline", "단일 결과")
        mock_scores = {
            "clarity": 4,
            "structure": 4,
            "constraint_following": 5,
            "usefulness": 4,
            "avg_score": 4.25,
            "path": "single",
        }

        with patch("scripts.run_full.BaseAgent") as MockSingleAgent, \
             patch("scripts.run_full.evaluate_single", new_callable=AsyncMock) as mock_evaluate:
            MockSingleAgent.return_value = AsyncMock(run=AsyncMock(return_value=mock_single_output))
            mock_evaluate.return_value = mock_scores

            await run_pipeline(
                cases,
                evaluate=True,
                output_dir=tmp_path,
            )

        output_files = list(tmp_path.glob("full_*.json"))
        assert len(output_files) == 1
        payload = json.loads(output_files[0].read_text(encoding="utf-8"))
        assert payload["evaluation"] == mock_scores

    def test_router_single_case(self):
        """summarize + low difficulty → single 경로로 라우팅되는지 확인."""
        task = TaskRequest(
            prompt="간단 요약",
            task_type="summarize",
            constraints={"difficulty": "low"},
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "single"

    def test_router_moa_case(self):
        """ideate → moa 경로로 라우팅되는지 확인."""
        task = TaskRequest(prompt="창의적 아이디어 5가지", task_type="ideate")
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.selected_path == "moa"

    def test_router_rag_case(self):
        """constraints에 source:rag_docs → requires_rag=True 라우팅 확인."""
        task = TaskRequest(
            prompt="문서 기반으로 설명하세요",
            task_type="explain",
            constraints={"source": "rag_docs"},
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.requires_rag is True

    def test_router_mcp_case(self):
        """프롬프트에 MCP 키워드 → requires_mcp=True 라우팅 확인."""
        task = TaskRequest(
            prompt="현재 날씨 정보를 알려주세요",
            task_type="explain",
        )
        decision = rule_based_route(task)
        assert decision is not None
        assert decision.requires_mcp is True

    @pytest.mark.asyncio
    async def test_full_pipeline_3_cases(self):
        """벤치마크에서 3개 케이스(sum-001, ide-001, crw-001)를 시범 실행."""
        from scripts.run_single import load_benchmark, case_to_task

        cases = load_benchmark()
        selected_ids = {"sum-001", "ide-001", "crw-001"}
        selected = [c for c in cases if c["id"] in selected_ids]
        assert len(selected) == 3

        mock_single_output = _mock_output("single_baseline", "단일 결과")
        mock_drafts = [_mock_output(f"draft_{v}") for v in ["analytical", "creative", "structured"]]
        mock_critic = _mock_output("critic", '{"analyses": []}')
        mock_synth = _mock_output("synthesizer", "MOA 최종")
        mock_judge = JudgeDecision(decision="pass", confidence=0.9, reasoning="OK")

        results = []

        with patch("scripts.run_full.BaseAgent") as MockSingleAgent, \
             patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
             patch("app.orchestrator.executor.JudgeAgent") as MockJudge:

            MockSingleAgent.return_value = AsyncMock(run=AsyncMock(return_value=mock_single_output))
            mock_run.return_value = mock_drafts
            MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
            MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
            MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))

            for case in selected:
                task = case_to_task(case)
                logger = TraceLogger(run_id=f"test-{case['id']}")
                tracker = CostTracker()

                decision = rule_based_route(task)
                if decision is None:
                    decision = RoutingDecision(
                        selected_path="moa", reason="fallback", confidence=0.5
                    )

                if decision.selected_path == "single":
                    text, outputs = await run_single_path(task, logger, tracker)
                else:
                    text, outputs = await run_moa_path(task, logger, tracker)

                results.append({
                    "case_id": case["id"],
                    "path": decision.selected_path,
                    "output": text,
                    "agent_count": len(outputs),
                    "tokens": tracker.total_tokens,
                })

        # sum-001은 single, ide-001/crw-001은 moa
        paths = {r["case_id"]: r["path"] for r in results}
        assert paths["sum-001"] == "single"
        assert paths["ide-001"] == "moa"
        assert paths["crw-001"] == "moa"

        # 모든 결과가 출력을 포함
        for r in results:
            assert r["output"]
            assert r["agent_count"] >= 1
