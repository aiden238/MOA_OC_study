"""Full Pipeline 실행 스크립트 — Router → 자동 분기 → 결과 저장.

Router가 입력을 분석하여 single/moa 경로를 자동 선택하고,
해당 경로로 파이프라인을 실행하여 결과를 저장한다.
CostTracker로 전체 비용을 집계한다.

사용법:
  python scripts/run_full.py                     # 전체 12건, Router 자동 분기
  python scripts/run_full.py --case-id exp-002    # 특정 케이스
  python scripts/run_full.py --force-path moa     # 경로 강제 지정
  python scripts/run_full.py --cost-report        # 비용 요약 출력
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.base_agent import BaseAgent
from app.core.config import OUTPUT_DIR
from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.executor import MOAExecutor
from app.orchestrator.router import Router, RoutingDecision
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest
from app.schemas.trace import CaseResult
from scripts.run_single import load_benchmark, case_to_task


async def run_single_path(
    task: TaskRequest,
    logger: TraceLogger,
    cost_tracker: CostTracker,
) -> tuple[str, list[AgentOutput]]:
    """single 경로 — BaseAgent 단일 호출."""
    agent = BaseAgent(
        agent_name="single_baseline",
        system_prompt="당신은 도움이 되는 AI 어시스턴트입니다. 주어진 요청에 최선을 다해 응답하세요.",
    )
    output = await agent.run(task.prompt)

    # trace 기록
    logger.log(
        agent_name=output.agent_name,
        model=output.model,
        input_prompt=task.prompt,
        output_text=output.content,
        prompt_tokens=output.prompt_tokens,
        completion_tokens=output.completion_tokens,
        latency_ms=output.latency_ms,
        cost_estimate=output.cost_estimate,
        path="single",
        operation_type="llm_completion",
    )

    # 비용 집계
    cost_tracker.add(
        model=output.model,
        prompt_tokens=output.prompt_tokens,
        completion_tokens=output.completion_tokens,
        path="single",
        agent_name=output.agent_name,
        operation_type="llm_completion",
    )

    return output.content, [output]


async def run_moa_path(
    task: TaskRequest,
    logger: TraceLogger,
    cost_tracker: CostTracker,
    routing: RoutingDecision | None = None,
) -> tuple[str, list[AgentOutput]]:
    """moa 경로 — Draft×3 → Critic → Synthesizer → Judge → (Rewrite)."""
    executor = MOAExecutor()
    final_text, all_outputs = await executor.execute(task, logger, routing=routing)

    # 각 에이전트 출력을 비용 트래커에 등록
    for output in all_outputs:
        cost_tracker.add(
            model=output.model,
            prompt_tokens=output.prompt_tokens,
            completion_tokens=output.completion_tokens,
            path="moa",
            agent_name=output.agent_name,
            operation_type="llm_completion",
        )

    return final_text, all_outputs


def save_full_output(
    result: dict,
    output_dir: Path | None = None,
) -> Path:
    """full pipeline 결과를 JSON 파일로 저장."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"full_{result['case_id']}.json"
    payload = CaseResult(**result).model_dump()
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return file_path


def print_cost_report(cost_tracker: CostTracker):
    """비용 요약 보고서 출력."""
    s = cost_tracker.summary()
    print(f"\n{'='*50}")
    print(f"  비용 요약 보고서")
    print(f"{'='*50}")
    print(f"  총 호출 수:       {s['call_count']}")
    print(f"  총 토큰:         {s['total_tokens']:,}")
    print(f"    - 입력 토큰:   {s['total_prompt_tokens']:,}")
    print(f"    - 출력 토큰:   {s['total_completion_tokens']:,}")
    print(f"  총 비용:         ${s['total_cost']:.6f}")
    print(f"\n  경로별 집계:")
    for path, data in s["by_path"].items():
        print(f"    [{path}] {data['tokens']:,} tokens, ${data['cost']:.6f}")
    print(f"\n  연산 유형별 집계:")
    for operation_type, data in s["by_operation_type"].items():
        print(f"    [{operation_type}] {data['tokens']:,} tokens, ${data['cost']:.6f}")
    print(f"{'='*50}")


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    force_path: str | None = None,
    cost_report: bool = False,
    output_dir: Path | None = None,
):
    """전체 파이프라인 실행."""
    # 특정 케이스 필터링
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}'를 찾을 수 없습니다.")
            return

    run_id = generate_run_id()
    logger = TraceLogger(run_id=run_id)
    cost_tracker = CostTracker()
    router = Router()

    print(f"[Full Pipeline] run_id={run_id}, cases={len(cases)}")

    for case in cases:
        task = case_to_task(case)

        # 경로 결정 (강제 지정 or Router 자동)
        if force_path:
            decision = RoutingDecision(
                selected_path=force_path,
                reason=f"강제 지정: --force-path {force_path}",
                confidence=1.0,
            )
        else:
            decision = await router.route(task)

        print(f"\n  [{task.task_id}] {task.task_type}")
        print(f"    경로: {decision.selected_path} (확신도: {decision.confidence:.2f})")
        print(f"    사유: {decision.reason}")

        # 경로별 실행
        if decision.selected_path == "single":
            final_text, outputs = await run_single_path(task, logger, cost_tracker)
        else:
            final_text, outputs = await run_moa_path(task, logger, cost_tracker, routing=decision)

        # 결과 저장
        result = {
            "case_id": task.task_id,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "output": final_text,
            "path": decision.selected_path,
            "routing_reason": decision.reason,
            "routing_confidence": decision.confidence,
            "agent_count": len(outputs),
            "agents": [o.agent_name for o in outputs],
            "prompt_tokens": sum(o.prompt_tokens for o in outputs),
            "completion_tokens": sum(o.completion_tokens for o in outputs),
            "latency_ms": round(sum(o.latency_ms for o in outputs), 2),
            "cost_estimate": round(sum(o.cost_estimate for o in outputs), 6),
            "constraints": task.constraints,
            "evaluation": {},
            "evaluation_context": {},
            "context_metadata": {
                "routing": {
                    "requires_rag": decision.requires_rag,
                    "requires_mcp": decision.requires_mcp,
                    "rag_query_hint": decision.rag_query_hint,
                    "mcp_intent": decision.mcp_intent,
                    "preferred_server": decision.preferred_server,
                    "preferred_tool": decision.preferred_tool,
                }
            },
        }
        save_full_output(result, output_dir)

        total_tokens = result["prompt_tokens"] + result["completion_tokens"]
        print(
            f"    완료: {result['agent_count']}개 에이전트, "
            f"{result['latency_ms']:.0f}ms, "
            f"{total_tokens} tokens, "
            f"${result['cost_estimate']:.6f}"
        )

    # trace 저장
    logger.save()
    print(f"\n[완료] trace 저장: {run_id}.json")

    # 비용 보고서
    if cost_report:
        print_cost_report(cost_tracker)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Full pipeline: Router → single|moa → result"
    )
    parser.add_argument("--case-id", type=str, default=None, help="특정 케이스만 실행")
    parser.add_argument(
        "--force-path", type=str, choices=["single", "moa"], default=None,
        help="경로 강제 지정 (Router 무시)",
    )
    parser.add_argument("--cost-report", action="store_true", help="비용 요약 출력")
    return parser.parse_args()


def main():
    args = parse_args()
    cases = load_benchmark()
    print(f"[Full Pipeline] 벤치마크 v1 — {len(cases)}건 로딩 완료")
    asyncio.run(run_pipeline(
        cases,
        case_id=args.case_id,
        force_path=args.force_path,
        cost_report=args.cost_report,
    ))


if __name__ == "__main__":
    main()
