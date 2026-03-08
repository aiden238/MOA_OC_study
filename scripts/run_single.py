"""Baseline 단일 호출 파이프라인 — 벤치마크 케이스를 단일 LLM으로 실행."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.base_agent import BaseAgent
from app.core.config import BENCHMARK_DIR, OUTPUT_DIR, TRACE_DIR
from app.core.logger import TraceLogger, generate_run_id
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary, TraceRecord


def load_benchmark(path: Path | None = None) -> list[dict]:
    """벤치마크 JSON 파일에서 케이스 목록을 로딩."""
    benchmark_path = path or (BENCHMARK_DIR / "v1.json")
    with open(benchmark_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


def case_to_task(case: dict) -> TaskRequest:
    """벤치마크 케이스를 TaskRequest로 변환."""
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


async def run_single_case(
    task: TaskRequest,
    logger: TraceLogger,
) -> dict:
    """단일 LLM 호출로 태스크를 처리하고 결과를 반환."""
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
    """개별 케이스 결과를 JSON 파일로 저장."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"single_{result['case_id']}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return file_path


def build_run_summary(
    run_id: str,
    results: list[dict],
    logger: TraceLogger,
) -> RunSummary:
    """실행 결과를 RunSummary로 집계."""
    traces = [
        TraceRecord(**record) for record in logger.records
    ]
    total_tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in results)
    total_cost = sum(r["cost_estimate"] for r in results)
    total_latency = sum(r["latency_ms"] for r in results)
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
    """전체 파이프라인 실행."""
    # 특정 케이스만 필터링
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}'를 찾을 수 없습니다.")
            return []

    summaries = []
    for run_num in range(1, repeat + 1):
        run_id = generate_run_id()
        logger = TraceLogger(run_id=run_id)
        results = []

        if repeat > 1:
            print(f"\n{'='*50}")
            print(f"[Run {run_num}/{repeat}] run_id={run_id}")
            print(f"{'='*50}")

        for case in cases:
            task = case_to_task(case)
            print(f"  [{task.task_id}] {task.task_type} ...", end=" ", flush=True)
            result = await run_single_case(task, logger)
            results.append(result)
            save_case_output(result, output_dir)
            print(
                f"OK ({result['latency_ms']:.0f}ms, "
                f"{result['prompt_tokens']+result['completion_tokens']} tokens, "
                f"${result['cost_estimate']:.6f})"
            )

        # trace 저장
        logger.save()

        # RunSummary 집계
        summary = build_run_summary(run_id, results, logger)
        summaries.append(summary)

        # 요약 출력
        print(f"\n--- Run Summary (run_id={run_id}) ---")
        print(f"  Cases:   {len(results)}")
        print(f"  Tokens:  {summary.total_tokens}")
        print(f"  Cost:    ${summary.total_cost:.6f}")
        print(f"  Latency: {summary.total_latency_ms:.0f}ms")

    return summaries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Single path baseline pipeline")
    parser.add_argument("--case-id", type=str, default=None, help="특정 케이스만 실행")
    parser.add_argument("--repeat", type=int, default=1, help="반복 실행 횟수")
    return parser.parse_args()


def main():
    args = parse_args()
    cases = load_benchmark()
    print(f"[Single Baseline] 벤치마크 v1 — {len(cases)}건 로딩 완료")
    summaries = asyncio.run(run_pipeline(cases, args.case_id, args.repeat))
    print(f"\n[완료] {len(summaries)}회 실행 완료")


if __name__ == "__main__":
    main()
