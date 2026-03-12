"""MOA 파이프라인 실행 엔진 — Draft → Critic → Synthesizer 오케스트레이션.

전체 MOA 파이프라인을 관리하는 실행 엔진.
1) Draft Agent 3종 비동기 병렬 실행
2) Critic Agent가 3개 draft 비교 분석
3) Synthesizer Agent가 최종 결과 생성
4) 모든 에이전트 호출을 trace로 기록
"""

from app.agents.critic_agent import CriticAgent
from app.agents.draft_agent import run_all_drafts
from app.core.logger import TraceLogger
from app.orchestrator.synthesizer import SynthesizerAgent
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary, TraceRecord


def _log_output(logger: TraceLogger, output: AgentOutput, input_prompt: str, path: str = "moa"):
    """AgentOutput을 TraceLogger에 기록하는 헬퍼."""
    logger.log(
        agent_name=output.agent_name,
        model=output.model,
        input_prompt=input_prompt,
        output_text=output.content,
        prompt_tokens=output.prompt_tokens,
        completion_tokens=output.completion_tokens,
        latency_ms=output.latency_ms,
        cost_estimate=output.cost_estimate,
        path=path,
    )


class MOAExecutor:
    """Draft → Critic → Synthesizer 파이프라인을 실행하고 결과를 집계."""

    async def execute(self, task: TaskRequest, logger: TraceLogger) -> tuple[str, list[AgentOutput]]:
        """MOA 파이프라인 전체 실행.

        Args:
            task: 처리할 태스크 요청
            logger: trace 기록용 로거

        Returns:
            (최종 출력 텍스트, 모든 에이전트 출력 리스트)
        """
        all_outputs: list[AgentOutput] = []

        # ── 1단계: Draft 3종 비동기 병렬 실행 ──
        drafts = await run_all_drafts(task)
        for draft in drafts:
            _log_output(logger, draft, task.prompt)
            all_outputs.append(draft)

        # ── 2단계: Critic이 draft 비교 분석 ──
        critic = CriticAgent()
        critique = await critic.critique(drafts, original_prompt=task.prompt)
        _log_output(logger, critique, task.prompt)
        all_outputs.append(critique)

        # ── 3단계: Synthesizer가 최종 결과 생성 ──
        synthesizer = SynthesizerAgent()
        final = await synthesizer.synthesize(drafts, critique, original_prompt=task.prompt)
        _log_output(logger, final, task.prompt)
        all_outputs.append(final)

        return final.content, all_outputs


def build_moa_summary(
    run_id: str,
    task: TaskRequest,
    final_output: str,
    logger: TraceLogger,
) -> RunSummary:
    """MOA 실행 결과를 RunSummary로 집계."""
    traces = [TraceRecord(**record) for record in logger.records]
    total_tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in logger.records)
    total_cost = sum(r["cost_estimate"] for r in logger.records)
    total_latency = sum(r["latency_ms"] for r in logger.records)
    agents = {r["agent_name"] for r in logger.records}

    return RunSummary(
        run_id=run_id,
        task_id=task.task_id,
        path="moa",
        total_tokens=total_tokens,
        total_cost=round(total_cost, 6),
        total_latency_ms=round(total_latency, 2),
        agent_count=len(agents),
        traces=traces,
        final_output=final_output,
    )
