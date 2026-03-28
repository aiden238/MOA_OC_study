"""Single-path baseline runner."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.base_agent import BaseAgent
from app.core.config import BENCHMARK_DIR, OUTPUT_DIR
from app.core.logger import TraceLogger, generate_run_id
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary, TraceRecord


def load_benchmark(path: Path | None = None) -> list[dict]:
    benchmark_path = path or (BENCHMARK_DIR / "v1.json")
    with open(benchmark_path, encoding="utf-8") as file:
        data = json.load(file)
    return data["cases"]


def resolve_benchmark_path(path_str: str | None) -> Path | None:
    if not path_str:
        return None

    candidate = Path(path_str)
    if candidate.is_absolute() or candidate.exists():
        return candidate
    return BENCHMARK_DIR / candidate


def case_to_task(case: dict) -> TaskRequest:
    return TaskRequest(
        task_id=case["id"],
        prompt=case["prompt"],
        task_type=case["type"],
        constraints=case.get("constraints", {}),
        metadata={
            "difficulty": case.get("difficulty", ""),
            "expected_moa_advantage": case.get("expected_moa_advantage", ""),
        },
    )


async def run_single_case(task: TaskRequest, logger: TraceLogger) -> dict:
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
    )

    return {
        "case_id": task.task_id,
        "task_type": task.task_type,
        "prompt": task.prompt,
        "output": output.content,
        "model": output.model,
        "prompt_tokens": output.prompt_tokens,
        "completion_tokens": output.completion_tokens,
        "latency_ms": output.latency_ms,
        "cost_estimate": output.cost_estimate,
    }


def save_case_output(result: dict, output_dir: Path | None = None) -> Path:
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"single_{result['case_id']}.json"
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return file_path


def build_run_summary(run_id: str, results: list[dict], logger: TraceLogger) -> RunSummary:
    traces = [TraceRecord(**record) for record in logger.records]
    total_tokens = sum(item["prompt_tokens"] + item["completion_tokens"] for item in results)
    total_cost = sum(item["cost_estimate"] for item in results)
    total_latency = sum(item["latency_ms"] for item in results)
    final_output = results[-1]["output"] if results else ""

    return RunSummary(
        run_id=run_id,
        task_id="benchmark_v1",
        path="single",
        total_tokens=total_tokens,
        total_cost=round(total_cost, 6),
        total_latency_ms=round(total_latency, 2),
        agent_count=1,
        traces=traces,
        final_output=final_output,
    )


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    repeat: int = 1,
    output_dir: Path | None = None,
) -> list[RunSummary]:
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}' was not found.")
            return []

    summaries: list[RunSummary] = []
    for run_num in range(1, repeat + 1):
        run_id = generate_run_id()
        logger = TraceLogger(run_id=run_id)
        results: list[dict] = []

        if repeat > 1:
            print(f"\n{'=' * 50}")
            print(f"[Run {run_num}/{repeat}] run_id={run_id}")
            print(f"{'=' * 50}")

        for case in cases:
            task = case_to_task(case)
            print(f"  [{task.task_id}] {task.task_type} ...", end=" ", flush=True)
            result = await run_single_case(task, logger)
            results.append(result)
            save_case_output(result, output_dir)
            print(
                f"OK ({result['latency_ms']:.0f}ms, "
                f"{result['prompt_tokens'] + result['completion_tokens']} tokens, "
                f"${result['cost_estimate']:.6f})"
            )

        logger.save()
        summary = build_run_summary(run_id, results, logger)
        summaries.append(summary)

        print(f"\n--- Run Summary (run_id={run_id}) ---")
        print(f"  Cases:   {len(results)}")
        print(f"  Tokens:  {summary.total_tokens}")
        print(f"  Cost:    ${summary.total_cost:.6f}")
        print(f"  Latency: {summary.total_latency_ms:.0f}ms")

    return summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single path baseline pipeline")
    parser.add_argument("--case-id", type=str, default=None, help="Specific case id to run")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat count")
    parser.add_argument("--benchmark", type=str, default=None, help="Benchmark JSON path")
    return parser.parse_args()


def main():
    args = parse_args()
    benchmark_path = resolve_benchmark_path(args.benchmark)
    cases = load_benchmark(benchmark_path)
    benchmark_name = benchmark_path.name if benchmark_path else "v1.json"
    print(f"[Single Baseline] benchmark {benchmark_name} loaded: {len(cases)} cases")
    summaries = asyncio.run(run_pipeline(cases, args.case_id, args.repeat))
    print(f"\n[Done] {len(summaries)} run(s) completed")


if __name__ == "__main__":
    main()
