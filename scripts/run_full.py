"""Full pipeline runner with router, RAG, MCP, and optional evaluation."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.base_agent import BaseAgent
from app.core.config import OUTPUT_DIR
from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger, generate_run_id
from app.eval.rubric import evaluate_single
from app.orchestrator.executor import MOAExecutor
from app.orchestrator.router import Router, RoutingDecision
from app.schemas.agent_io import AgentOutput
from app.schemas.task import TaskRequest
from app.schemas.trace import CaseResult
from scripts.run_single import case_to_task, load_benchmark, resolve_benchmark_path


async def run_single_path(
    task: TaskRequest,
    logger: TraceLogger,
    cost_tracker: CostTracker,
) -> tuple[str, list[AgentOutput]]:
    agent = BaseAgent(
        agent_name="single_baseline",
        system_prompt="You are a helpful AI assistant. Answer the user's request directly.",
    )
    output = await agent.run(task.prompt)

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
    start_index = len(logger.records)
    executor = MOAExecutor()
    final_text, all_outputs = await executor.execute(task, logger, routing=routing)

    new_records = logger.records[start_index:]
    for record in new_records:
        cost_tracker.add(
            model=record["model"],
            prompt_tokens=record["prompt_tokens"],
            completion_tokens=record["completion_tokens"],
            path=record["path"],
            agent_name=record["agent_name"],
            operation_type=record.get("operation_type", "llm_completion"),
            metadata=record.get("metadata", {}),
            cost_override=record.get("cost_estimate", 0.0),
        )

    return final_text, all_outputs


def _sanitize_output_tag(output_tag: str | None) -> str | None:
    if not output_tag:
        return None

    sanitized = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in output_tag.strip()
    ).strip("-")
    return sanitized or None


def save_full_output(
    result: dict,
    output_dir: Path | None = None,
    output_tag: str | None = None,
) -> Path:
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_tag = _sanitize_output_tag(output_tag)
    filename = f"full_{result['case_id']}.json"
    if safe_tag:
        filename = f"full_{result['case_id']}__{safe_tag}.json"

    file_path = out_dir / filename
    payload = CaseResult(**result).model_dump()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return file_path


def print_cost_report(cost_tracker: CostTracker):
    summary = cost_tracker.summary()
    print(f"\n{'=' * 50}")
    print("  Cost Report")
    print(f"{'=' * 50}")
    print(f"  Calls:            {summary['call_count']}")
    print(f"  Total tokens:     {summary['total_tokens']:,}")
    print(f"    Prompt tokens:  {summary['total_prompt_tokens']:,}")
    print(f"    Completion:     {summary['total_completion_tokens']:,}")
    print(f"  Total cost:       ${summary['total_cost']:.6f}")
    print("\n  By path:")
    for path, data in summary["by_path"].items():
        print(f"    [{path}] {data['tokens']:,} tokens, ${data['cost']:.6f}")
    print("\n  By operation:")
    for operation_type, data in summary["by_operation_type"].items():
        print(f"    [{operation_type}] {data['tokens']:,} tokens, ${data['cost']:.6f}")
    print(f"{'=' * 50}")


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    force_path: str | None = None,
    cost_report: bool = False,
    evaluate: bool = False,
    output_dir: Path | None = None,
    output_tag: str | None = None,
):
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}' was not found.")
            return

    run_id = generate_run_id()
    logger = TraceLogger(run_id=run_id)
    cost_tracker = CostTracker()
    router = Router()

    print(f"[Full Pipeline] run_id={run_id}, cases={len(cases)}")

    for case in cases:
        task = case_to_task(case)
        start_index = len(logger.records)

        if force_path:
            decision = RoutingDecision(
                selected_path=force_path,
                reason=f"Forced by --force-path {force_path}",
                confidence=1.0,
            )
        else:
            decision = await router.route(task)

        print(f"\n  [{task.task_id}] {task.task_type}")
        print(f"    path: {decision.selected_path} (confidence {decision.confidence:.2f})")
        print(f"    reason: {decision.reason}")

        if decision.selected_path == "single":
            final_text, outputs = await run_single_path(task, logger, cost_tracker)
        else:
            final_text, outputs = await run_moa_path(task, logger, cost_tracker, routing=decision)

        case_records = logger.records[start_index:]
        actual_path = case_records[-1]["path"] if case_records else decision.selected_path
        rag_records = [record for record in case_records if record.get("operation_type") == "rag"]
        mcp_records = [record for record in case_records if record.get("operation_type") == "mcp_tool"]

        retrieval_record = next(
            (
                record
                for record in reversed(rag_records)
                if record.get("metadata", {}).get("stage") == "retrieval"
            ),
            None,
        )
        context_build_record = next(
            (
                record
                for record in reversed(rag_records)
                if record.get("metadata", {}).get("stage") == "context_build"
            ),
            None,
        )
        mcp_record = next((record for record in reversed(mcp_records)), None)

        evaluation_context: dict = {}
        context_metadata = {
            "routing": {
                "requires_rag": decision.requires_rag,
                "requires_mcp": decision.requires_mcp,
                "rag_query_hint": decision.rag_query_hint,
                "mcp_intent": decision.mcp_intent,
                "preferred_server": decision.preferred_server,
                "preferred_tool": decision.preferred_tool,
            }
        }

        if retrieval_record is not None:
            context_metadata["rag_retrieval"] = retrieval_record.get("metadata", {})
        if context_build_record is not None:
            context_metadata["rag"] = context_build_record.get("metadata", {})
            evaluation_context["retrieval_context"] = context_build_record.get("output_text", "")
            evaluation_context["selected_chunks"] = (
                context_build_record.get("metadata", {}).get("selected_chunks", [])
            )
        if mcp_record is not None:
            context_metadata["mcp"] = mcp_record.get("metadata", {})
            evaluation_context["tool_trace"] = {
                "server_name": mcp_record.get("metadata", {}).get("server_name"),
                "tool_name": mcp_record.get("metadata", {}).get("tool_name"),
                "args": mcp_record.get("metadata", {}).get("args", {}),
                "success": mcp_record.get("metadata", {}).get("success"),
            }
            evaluation_context["tool_result_summary"] = (
                mcp_record.get("metadata", {}).get("normalized_result_summary", "")
            )

        evaluation = {}
        if evaluate:
            evaluation = await evaluate_single(
                prompt=task.prompt,
                output=final_text,
                constraints=task.constraints,
                path=actual_path,
                evaluation_context=evaluation_context,
            )

        result = {
            "case_id": task.task_id,
            "task_type": task.task_type,
            "prompt": task.prompt,
            "output": final_text,
            "path": actual_path,
            "routing_reason": decision.reason,
            "routing_confidence": decision.confidence,
            "agent_count": len(outputs),
            "agents": [output.agent_name for output in outputs],
            "prompt_tokens": sum(output.prompt_tokens for output in outputs),
            "completion_tokens": sum(output.completion_tokens for output in outputs),
            "latency_ms": round(sum(output.latency_ms for output in outputs), 2),
            "cost_estimate": round(sum(record["cost_estimate"] for record in case_records), 6),
            "constraints": task.constraints,
            "evaluation": evaluation,
            "evaluation_context": evaluation_context,
            "context_metadata": context_metadata,
        }
        save_full_output(result, output_dir, output_tag=output_tag)

        total_tokens = result["prompt_tokens"] + result["completion_tokens"]
        print(
            f"    done: {result['agent_count']} agents, "
            f"{result['latency_ms']:.0f}ms, "
            f"{total_tokens} tokens, "
            f"${result['cost_estimate']:.6f}"
        )

    logger.save()
    print(f"\n[Done] trace saved: {run_id}.json")

    if cost_report:
        print_cost_report(cost_tracker)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full pipeline runner")
    parser.add_argument("--case-id", type=str, default=None, help="Specific case id to run")
    parser.add_argument(
        "--force-path",
        type=str,
        choices=["single", "moa"],
        default=None,
        help="Force single or moa path and skip router selection",
    )
    parser.add_argument("--cost-report", action="store_true", help="Print cost summary")
    parser.add_argument("--evaluate", action="store_true", help="Run rubric evaluation")
    parser.add_argument("--benchmark", type=str, default=None, help="Benchmark JSON path")
    parser.add_argument(
        "--output-tag",
        type=str,
        default=None,
        help="Optional file tag to avoid overwriting previous runs",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    benchmark_path = resolve_benchmark_path(args.benchmark)
    cases = load_benchmark(benchmark_path)
    benchmark_name = benchmark_path.name if benchmark_path else "v1.json"
    print(f"[Full Pipeline] benchmark {benchmark_name} loaded: {len(cases)} cases")
    asyncio.run(
        run_pipeline(
            cases,
            case_id=args.case_id,
            force_path=args.force_path,
            cost_report=args.cost_report,
            evaluate=args.evaluate,
            output_tag=args.output_tag,
        )
    )


if __name__ == "__main__":
    main()
