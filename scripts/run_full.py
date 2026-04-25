"""Full pipeline runner with reusable service-layer runtime."""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chat_service import (
    run_benchmark_pipeline,
    run_moa_task,
    run_single_task,
    save_case_output,
)
from scripts.run_single import load_benchmark, resolve_benchmark_path


async def run_single_path(task, logger, cost_tracker):
    return await run_single_task(task, logger, cost_tracker)


async def run_moa_path(task, logger, cost_tracker, routing=None):
    return await run_moa_task(task, logger, cost_tracker, routing=routing)


def save_full_output(result, output_dir=None, output_tag=None):
    return save_case_output(result, output_dir=output_dir, output_tag=output_tag)


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    force_path: str | None = None,
    cost_report: bool = False,
    evaluate: bool = False,
    output_dir: Path | None = None,
    output_tag: str | None = None,
):
    try:
        return await run_benchmark_pipeline(
            cases,
            case_id=case_id,
            force_path=force_path,
            cost_report=cost_report,
            evaluate=evaluate,
            output_dir=output_dir,
            output_tag=output_tag,
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full pipeline runner")
    parser.add_argument("--case-id", type=str, default=None, help="Specific case id to run")
    parser.add_argument(
        "--force-path",
        type=str,
        choices=["auto", "single", "moa"],
        default=None,
        help="Force execution path: 'auto' uses router, 'single'/'moa' bypass router",
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
            output_dir=None,
            output_tag=args.output_tag,
        )
    )


if __name__ == "__main__":
    main()
