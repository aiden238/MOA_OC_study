"""MOA 파이프라인 통합 테스트 — Draft×3 → Critic → Synthesizer 전체 파이프라인.

Mock API를 사용하여 MOAExecutor의 전체 흐름과 trace 기록을 검증한다.
- 전체 파이프라인 실행 정상 여부
- trace 기록 개수 (3 draft + 1 critic + 1 synthesizer = 5)
- build_moa_summary 집계 정확성
- run_moa.py의 유틸리티 함수 (save/load/case_to_task)
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.executor import MOAExecutor, build_moa_summary
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest


def _mock_agent_output(agent_name: str, content: str = "mock output") -> AgentOutput:
    """테스트용 mock AgentOutput 생성 헬퍼."""
    return AgentOutput(
        agent_name=agent_name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
    )


class TestMOAExecutor:
    """MOAExecutor 전체 파이프라인 통합 테스트."""

    @pytest.mark.asyncio
    async def test_full_pipeline_execution(self):
        """Draft → Critic → Synthesizer 전체 파이프라인이 정상 실행되는지 확인."""
        mock_drafts = [
            _mock_agent_output("draft_analytical", "분석적 결과"),
            _mock_agent_output("draft_creative", "창의적 결과"),
            _mock_agent_output("draft_structured", "구조적 결과"),
        ]
        mock_critique = _mock_agent_output("critic", '{"draft_analyses": [], "recommendation": "A+B"}')
        mock_final = _mock_agent_output("synthesizer", "최종 결과물")

        with patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth:

            mock_run_drafts.return_value = mock_drafts

            mock_critic_instance = AsyncMock()
            mock_critic_instance.critique.return_value = mock_critique
            MockCritic.return_value = mock_critic_instance

            mock_synth_instance = AsyncMock()
            mock_synth_instance.synthesize.return_value = mock_final
            MockSynth.return_value = mock_synth_instance

            executor = MOAExecutor()
            logger = TraceLogger(run_id="test-run-001")
            task = TaskRequest(prompt="테스트 프롬프트", task_type="summarize")

            final_output, all_outputs = await executor.execute(task, logger)

        # 최종 출력 확인
        assert final_output == "최종 결과물"
        # 에이전트 5개 (draft×3 + critic + synthesizer)
        assert len(all_outputs) == 5
        # trace 기록 5건
        assert len(logger.records) == 5

    @pytest.mark.asyncio
    async def test_trace_records_agent_names(self):
        """trace에 기록된 에이전트 이름이 정확한지 확인."""
        mock_drafts = [
            _mock_agent_output("draft_analytical"),
            _mock_agent_output("draft_creative"),
            _mock_agent_output("draft_structured"),
        ]
        mock_critique = _mock_agent_output("critic")
        mock_final = _mock_agent_output("synthesizer")

        with patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth:

            mock_run_drafts.return_value = mock_drafts
            MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critique))
            MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_final))

            executor = MOAExecutor()
            logger = TraceLogger(run_id="test-run-002")
            task = TaskRequest(prompt="테스트")

            await executor.execute(task, logger)

        # 기록된 에이전트 이름 확인
        agent_names = [r["agent_name"] for r in logger.records]
        assert agent_names == [
            "draft_analytical", "draft_creative", "draft_structured",
            "critic", "synthesizer",
        ]

    @pytest.mark.asyncio
    async def test_partial_drafts_pipeline(self):
        """draft가 2개만 성공해도 파이프라인이 동작하는지 확인."""
        mock_drafts = [
            _mock_agent_output("draft_analytical", "분석적 결과"),
            _mock_agent_output("draft_structured", "구조적 결과"),
        ]
        mock_critique = _mock_agent_output("critic")
        mock_final = _mock_agent_output("synthesizer", "2개 draft 합성")

        with patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth:

            mock_run_drafts.return_value = mock_drafts
            MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critique))
            MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_final))

            executor = MOAExecutor()
            logger = TraceLogger(run_id="test-run-003")
            task = TaskRequest(prompt="테스트")

            final_output, all_outputs = await executor.execute(task, logger)

        assert final_output == "2개 draft 합성"
        # draft 2 + critic 1 + synthesizer 1 = 4
        assert len(all_outputs) == 4


class TestBuildMOASummary:
    """build_moa_summary 함수 테스트."""

    def test_summary_aggregation(self):
        """trace 기록에서 올바르게 집계되는지 확인."""
        logger = TraceLogger(run_id="test-summary-001")

        # 5건의 trace 기록 (draft×3 + critic + synthesizer)
        agents = [
            ("draft_analytical", 50, 30, 100.0, 0.001),
            ("draft_creative", 60, 40, 120.0, 0.002),
            ("draft_structured", 55, 35, 110.0, 0.0015),
            ("critic", 200, 100, 300.0, 0.005),
            ("synthesizer", 300, 150, 250.0, 0.008),
        ]

        for name, pt, ct, lat, cost in agents:
            logger.log(
                agent_name=name,
                model="gpt-4o-mini",
                input_prompt="test",
                output_text="result",
                prompt_tokens=pt,
                completion_tokens=ct,
                latency_ms=lat,
                cost_estimate=cost,
                path="moa",
            )

        task = TaskRequest(prompt="벤치마크 테스트", task_id="test-001")
        summary = build_moa_summary("test-summary-001", task, "최종 결과", logger)

        # 토큰 합계: (50+30) + (60+40) + (55+35) + (200+100) + (300+150) = 1020
        assert summary.total_tokens == 1020
        # 비용 합계
        assert summary.total_cost == round(0.001 + 0.002 + 0.0015 + 0.005 + 0.008, 6)
        # 5개 고유 에이전트
        assert summary.agent_count == 5
        # trace 5건
        assert len(summary.traces) == 5
        assert summary.path == "moa"

    def test_summary_with_empty_logger(self):
        """빈 로거에서도 정상 동작하는지 확인."""
        logger = TraceLogger(run_id="test-empty")
        task = TaskRequest(prompt="빈 테스트")
        summary = build_moa_summary("test-empty", task, "", logger)

        assert summary.total_tokens == 0
        assert summary.total_cost == 0
        assert summary.agent_count == 0
        assert summary.traces == []


class TestRunMOAUtils:
    """run_moa.py 유틸리티 함수 테스트."""

    def test_save_and_load_moa_output(self, tmp_path):
        """MOA 결과 저장/로드 라운드트립 테스트."""
        from scripts.run_moa import save_moa_output

        result = {
            "case_id": "test-001",
            "task_type": "general",
            "prompt": "테스트",
            "output": "결과",
            "agent_count": 5,
            "agents": ["draft_analytical", "draft_creative", "draft_structured", "critic", "synthesizer"],
            "prompt_tokens": 665,
            "completion_tokens": 385,
            "latency_ms": 880.0,
            "cost_estimate": 0.0175,
        }

        path = save_moa_output(result, output_dir=tmp_path)
        assert path.exists()
        assert path.name == "moa_test-001.json"

        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["case_id"] == "test-001"
        assert loaded["agent_count"] == 5

    def test_load_single_result_missing(self, tmp_path):
        """존재하지 않는 single 결과 로딩 시 None 반환."""
        from scripts.run_moa import load_single_result

        result = load_single_result("nonexistent", output_dir=tmp_path)
        assert result is None

    def test_load_single_result_exists(self, tmp_path):
        """존재하는 single 결과를 로딩."""
        from scripts.run_moa import load_single_result

        data = {"case_id": "test-002", "output": "baseline"}
        single_path = tmp_path / "single_test-002.json"
        with open(single_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = load_single_result("test-002", output_dir=tmp_path)
        assert result is not None
        assert result["case_id"] == "test-002"
