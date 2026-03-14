"""간단한 비교 스크립트 — 로컬에 저장된 RunSummary JSON들을 불러와 비교 테이블을 출력합니다.

사용법:
    python scripts/compare_runs.py --dir outputs/ --format table
"""

import argparse
import json
from pathlib import Path

from app.eval.comparator import Comparator
from app.schemas.trace import RunSummary


def load_summaries(folder: Path) -> dict:
    runs = {}
    for p in folder.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            path = j.get("path", "moa")
            runs.setdefault(path, []).append(RunSummary(**j))
        except Exception:
            continue
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="outputs", help="RunSummary JSON 폴더")
    parser.add_argument("--format", default="table", choices=["table", "csv"]) 
    args = parser.parse_args()

    folder = Path(args.dir)
    runs = load_summaries(folder)
    comp = Comparator()
    table = comp.compare(runs)

    if args.format == "csv":
        print("path,count,avg_tokens,avg_cost,avg_latency_ms")
        for r in table:
            print(f"{r['path']},{r['count']},{r['avg_tokens']},{r['avg_cost']},{r['avg_latency_ms']}")
    else:
        for r in table:
            print(r)


if __name__ == "__main__":
    main()
