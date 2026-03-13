"""MOA 파이프라인 실행 엔진 — Draft → Critic → Synthesizer → Judge → (Rewrite).

전체 MOA 파이프라인을 관리하는 실행 엔진.
1) Draft Agent 3종 비동기 병렬 실행
2) Critic Agent가 3개 draft 비교 분석
3) Synthesizer Agent가 최종 결과 생성
4) Judge Agent가 품질 판정 (pass/rewrite/escalate)
5) Rewrite Agent가 피드백 기반 개선 (최대 2회 루프)
6) 모든 에이전트 호출을 trace로 기록
"""

from app.agents.critic_agent import CriticAgent
from app.agents.draft_agent import run_all_drafts
from app.agents.judge_agent import JudgeAgent
from app.agents.rewrite_agent import RewriteAgent
from app.core.logger import TraceLogger
from app.orchestrator.synthesizer import SynthesizerAgent
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary, TraceRecord

# Judge → Rewrite 루프 최대 횟수 (무한 루프 방지)
MAX_REWRITE_LOOPS = 2


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
    """Draft → Critic → Synthesizer → Judge → (Rewrite) 파이프라인을 실행."""

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

        # ── 4단계: Judge가 품질 판정 ──
        judge = JudgeAgent()
        current_output = final
        decision = None

        for loop in range(MAX_REWRITE_LOOPS + 1):
            decision = await judge.judge(task, current_output)
            # Judge 호출도 trace에 기록 (AgentOutput 생성)
            judge_output = AgentOutput(
                agent_name="judge",
                content=decision.model_dump_json(),
                model="gpt-4o-mini",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
            )
            _log_output(logger, judge_output, task.prompt)
            all_outputs.append(judge_output)

            if decision.decision == "pass":
                break
            elif decision.decision == "escalate":
                print(f"  [ESCALATE] 사람 검토 필요: {decision.reasoning}")
                break
            elif decision.decision == "rewrite" and loop < MAX_REWRITE_LOOPS:
                # ── 5단계: Rewrite Agent가 피드백 반영 ──
                rewriter = RewriteAgent()
                current_output = await rewriter.rewrite(current_output, decision)
                _log_output(logger, current_output, task.prompt)
                all_outputs.append(current_output)
            else:
                # 최대 rewrite 횟수 초과 → 마지막 결과 채택
                print(f"  [WARNING] 최대 rewrite 횟수({MAX_REWRITE_LOOPS}) 초과 → 마지막 결과 채택")
                break

        return current_output.content, all_outputs


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
