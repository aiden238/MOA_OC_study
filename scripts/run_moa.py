"""MOA pipeline runner."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import OUTPUT_DIR
from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.executor import MOAExecutor, build_moa_summary
from app.schemas.task import TaskRequest
from scripts.run_single import case_to_task, load_benchmark, resolve_benchmark_path


async def run_moa_case(
    task: TaskRequest,
    executor: MOAExecutor,
    logger: TraceLogger,
) -> dict:
    final_output, all_outputs = await executor.execute(task, logger)

    total_prompt = sum(output.prompt_tokens for output in all_outputs)
    total_completion = sum(output.completion_tokens for output in all_outputs)
    total_cost = sum(output.cost_estimate for output in all_outputs)
    total_latency = sum(output.latency_ms for output in all_outputs)

    return {
        "case_id": task.task_id,
        "task_type": task.task_type,
        "prompt": task.prompt,
        "output": final_output,
        "agent_count": len(all_outputs),
        "agents": [output.agent_name for output in all_outputs],
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "latency_ms": round(total_latency, 2),
        "cost_estimate": round(total_cost, 6),
    }


def save_moa_output(result: dict, output_dir: Path | None = None) -> Path:
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"moa_{result['case_id']}.json"
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return file_path


def load_single_result(case_id: str, output_dir: Path | None = None) -> dict | None:
    out_dir = output_dir or OUTPUT_DIR
    path = out_dir / f"single_{case_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def print_comparison(moa_result: dict, single_result: dict | None):
    if not single_result:
        print("    (single baseline result not found)")
        return

    print(f"    {'Metric':<15} {'Single':>12} {'MOA':>12} {'Ratio':>8}")
    print(f"    {'-' * 47}")

    single_tokens = single_result["prompt_tokens"] + single_result["completion_tokens"]
    moa_tokens = moa_result["prompt_tokens"] + moa_result["completion_tokens"]
    token_ratio = f"{moa_tokens / single_tokens:.1f}x" if single_tokens else "N/A"

    single_cost = single_result["cost_estimate"]
    moa_cost = moa_result["cost_estimate"]
    cost_ratio = f"{moa_cost / single_cost:.1f}x" if single_cost else "N/A"

    single_latency = single_result["latency_ms"]
    moa_latency = moa_result["latency_ms"]
    latency_ratio = f"{moa_latency / single_latency:.1f}x" if single_latency else "N/A"

    print(f"    {'Tokens':<15} {single_tokens:>12} {moa_tokens:>12} {token_ratio:>8}")
    print(f"    {'Cost ($)':<15} {single_cost:>12.6f} {moa_cost:>12.6f} {cost_ratio:>8}")
    print(f"    {'Latency (ms)':<15} {single_latency:>12.0f} {moa_latency:>12.0f} {latency_ratio:>8}")


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    repeat: int = 1,
    compare: bool = False,
    output_dir: Path | None = None,
):
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}' was not found.")
            return

    executor = MOAExecutor()

    for run_num in range(1, repeat + 1):
        run_id = generate_run_id()
        logger = TraceLogger(run_id=run_id)

        if repeat > 1:
            print(f"\n{'=' * 50}")
            print(f"[Run {run_num}/{repeat}] run_id={run_id}")
            print(f"{'=' * 50}")

        result = None
        task = None
        for case in cases:
            task = case_to_task(case)
            print(f"\n  [{task.task_id}] {task.task_type} -> running MOA pipeline")

            result = await run_moa_case(task, executor, logger)
            save_moa_output(result, output_dir)

            print(
                f"    done: {result['agent_count']} agents, "
                f"{result['latency_ms']:.0f}ms, "
                f"{result['prompt_tokens'] + result['completion_tokens']} tokens, "
                f"${result['cost_estimate']:.6f}"
            )

            if compare:
                single = load_single_result(task.task_id, output_dir)
                print_comparison(result, single)

        logger.save()

        if task is not None and result is not None:
            summary = build_moa_summary(run_id, task, result["output"], logger)
            print(f"\n--- MOA Run Summary (run_id={run_id}) ---")
            print(f"  Cases:   {len(cases)}")
            print(f"  Agents:  {summary.agent_count}")
            print(f"  Tokens:  {summary.total_tokens}")
            print(f"  Cost:    ${summary.total_cost:.6f}")
            print(f"  Latency: {summary.total_latency_ms:.0f}ms")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MOA pipeline runner")
    parser.add_argument("--case-id", type=str, default=None, help="Specific case id to run")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat count")
    parser.add_argument("--compare", action="store_true", help="Compare against single outputs")
    parser.add_argument("--benchmark", type=str, default=None, help="Benchmark JSON path")
    return parser.parse_args()


def main():
    args = parse_args()
    benchmark_path = resolve_benchmark_path(args.benchmark)
    cases = load_benchmark(benchmark_path)
    benchmark_name = benchmark_path.name if benchmark_path else "v1.json"
    print(f"[MOA Pipeline] benchmark {benchmark_name} loaded: {len(cases)} cases")
    asyncio.run(run_pipeline(cases, args.case_id, args.repeat, args.compare))
    print("\n[Done]")


if __name__ == "__main__":
    main()
