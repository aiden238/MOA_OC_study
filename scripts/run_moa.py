"""MOA 파이프라인 실행 스크립트 — Draft×3 → Critic → Synthesizer.

벤치마크 케이스를 MOA 파이프라인으로 처리하고 결과를 저장.
--compare 옵션으로 single baseline과 나란히 비교 가능.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import BENCHMARK_DIR, OUTPUT_DIR
from app.core.logger import TraceLogger, generate_run_id
from app.orchestrator.executor import MOAExecutor, build_moa_summary
from app.schemas.task import TaskRequest
from scripts.run_single import load_benchmark, case_to_task


async def run_moa_case(
    task: TaskRequest,
    executor: MOAExecutor,
    logger: TraceLogger,
) -> dict:
    """단일 케이스를 MOA 파이프라인으로 처리."""
    final_output, all_outputs = await executor.execute(task, logger)

    # 에이전트별 토큰·비용 집계
    total_prompt = sum(o.prompt_tokens for o in all_outputs)
    total_completion = sum(o.completion_tokens for o in all_outputs)
    total_cost = sum(o.cost_estimate for o in all_outputs)
    total_latency = sum(o.latency_ms for o in all_outputs)

    return {
        "case_id": task.task_id,
        "task_type": task.task_type,
        "prompt": task.prompt,
        "output": final_output,
        "agent_count": len(all_outputs),
        "agents": [o.agent_name for o in all_outputs],
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "latency_ms": round(total_latency, 2),
        "cost_estimate": round(total_cost, 6),
    }


def save_moa_output(result: dict, output_dir: Path | None = None) -> Path:
    """MOA 결과를 JSON 파일로 저장."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    file_path = out_dir / f"moa_{result['case_id']}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return file_path


def load_single_result(case_id: str, output_dir: Path | None = None) -> dict | None:
    """single baseline 결과를 로딩 (비교용)."""
    out_dir = output_dir or OUTPUT_DIR
    path = out_dir / f"single_{case_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def print_comparison(moa_result: dict, single_result: dict | None):
    """single vs moa 결과를 나란히 비교 출력."""
    if not single_result:
        print("    (single baseline 결과 없음 — 비교 불가)")
        return

    print(f"    {'항목':<15} {'Single':>12} {'MOA':>12} {'배율':>8}")
    print(f"    {'-'*47}")

    s_tokens = single_result["prompt_tokens"] + single_result["completion_tokens"]
    m_tokens = moa_result["prompt_tokens"] + moa_result["completion_tokens"]
    ratio_t = f"{m_tokens/s_tokens:.1f}x" if s_tokens else "N/A"

    s_cost = single_result["cost_estimate"]
    m_cost = moa_result["cost_estimate"]
    ratio_c = f"{m_cost/s_cost:.1f}x" if s_cost else "N/A"

    s_lat = single_result["latency_ms"]
    m_lat = moa_result["latency_ms"]
    ratio_l = f"{m_lat/s_lat:.1f}x" if s_lat else "N/A"

    print(f"    {'Tokens':<15} {s_tokens:>12} {m_tokens:>12} {ratio_t:>8}")
    print(f"    {'Cost ($)':<15} {s_cost:>12.6f} {m_cost:>12.6f} {ratio_c:>8}")
    print(f"    {'Latency (ms)':<15} {s_lat:>12.0f} {m_lat:>12.0f} {ratio_l:>8}")


async def run_pipeline(
    cases: list[dict],
    case_id: str | None = None,
    repeat: int = 1,
    compare: bool = False,
    output_dir: Path | None = None,
):
    """전체 MOA 파이프라인 실행."""
    # 특정 케이스 필터링
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            print(f"[ERROR] case_id '{case_id}'를 찾을 수 없습니다.")
            return

    executor = MOAExecutor()

    for run_num in range(1, repeat + 1):
        run_id = generate_run_id()
        logger = TraceLogger(run_id=run_id)

        if repeat > 1:
            print(f"\n{'='*50}")
            print(f"[Run {run_num}/{repeat}] run_id={run_id}")
            print(f"{'='*50}")

        for case in cases:
            task = case_to_task(case)
            print(f"\n  [{task.task_id}] {task.task_type} — MOA 파이프라인 실행 중...")

            result = await run_moa_case(task, executor, logger)
            save_moa_output(result, output_dir)

            print(
                f"    완료: {result['agent_count']}개 에이전트, "
                f"{result['latency_ms']:.0f}ms, "
                f"{result['prompt_tokens']+result['completion_tokens']} tokens, "
                f"${result['cost_estimate']:.6f}"
            )

            # single vs moa 비교
            if compare:
                single = load_single_result(task.task_id, output_dir)
                print_comparison(result, single)

        # trace 저장
        logger.save()

        # 전체 요약
        summary = build_moa_summary(run_id, task, result["output"], logger)
        print(f"\n--- MOA Run Summary (run_id={run_id}) ---")
        print(f"  Cases:   {len(cases)}")
        print(f"  Agents:  {summary.agent_count}")
        print(f"  Tokens:  {summary.total_tokens}")
        print(f"  Cost:    ${summary.total_cost:.6f}")
        print(f"  Latency: {summary.total_latency_ms:.0f}ms")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MOA pipeline (Draft×3 → Critic → Synthesizer)")
    parser.add_argument("--case-id", type=str, default=None, help="특정 케이스만 실행")
    parser.add_argument("--repeat", type=int, default=1, help="반복 실행 횟수")
    parser.add_argument("--compare", action="store_true", help="single baseline과 비교 출력")
    return parser.parse_args()


def main():
    args = parse_args()
    cases = load_benchmark()
    print(f"[MOA Pipeline] 벤치마크 v1 — {len(cases)}건 로딩 완료")
    asyncio.run(run_pipeline(cases, args.case_id, args.repeat, args.compare))
    print(f"\n[완료]")


if __name__ == "__main__":
    main()
