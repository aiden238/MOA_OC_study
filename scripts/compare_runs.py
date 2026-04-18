"""로컬에 저장된 per-case result JSON들을 그룹 단위로 비교합니다.

사용법:
    python scripts/compare_runs.py --dir outputs/ --format table
"""

import argparse
import json
from pathlib import Path

from app.eval.comparator import Comparator
from app.schemas.trace import CaseResult


def infer_path(file_path: Path, payload: dict) -> str:
    """저장된 결과에서 path를 추론."""
    path = payload.get("path")
    if path:
        return path

    name = file_path.name
    if name.startswith("single_"):
        return "single"
    if name.startswith("moa_"):
        return "moa"
    return "moa"


def load_case_results(folder: Path) -> dict:
    """출력 디렉토리의 케이스 결과를 path별로 로드."""
    runs = {}
    for p in folder.glob("*.json"):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            payload["path"] = infer_path(p, payload)
            result = CaseResult(**payload)
            runs.setdefault(result.path, []).append(result)
        except Exception:
            continue
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="outputs", help="per-case result JSON 폴더")
    parser.add_argument("--format", default="table", choices=["table", "csv"])
    args = parser.parse_args()

    folder = Path(args.dir)
    runs = load_case_results(folder)
    comp = Comparator()
    table = comp.compare(runs)

    if args.format == "csv":
        headers = [
            "group",
            "left_path",
            "right_path",
            "count",
            "avg_score_delta",
            "avg_cost_delta",
            "avg_latency_delta",
            "avg_tokens_delta",
        ]
        print(",".join(headers))
        for row in table:
            print(",".join(str(row.get(header, "")) for header in headers))
    else:
        for row in table:
            print(row)


if __name__ == "__main__":
    main()
