"""경로별 실행 결과를 비교하는 간단한 비교기.

입력으로 여러 경로(single / moa / moa_rag / moa_mcp)의 RunSummary 리스트를 받아
핵심 지표(평균 점수, 비용, 토큰 사용 등)를 요약합니다.
"""

from typing import Dict, List

from app.schemas.trace import RunSummary


class Comparator:
    """여러 경로의 실행 결과를 비교하는 도구.

    현재는 평균 점수와 비용 비율을 계산하는 간단한 구현입니다.
    """

    def compare(self, runs: Dict[str, List[RunSummary]]) -> List[dict]:
        table = []
        for path, summaries in runs.items():
            if not summaries:
                continue
            avg_tokens = sum(s.total_tokens for s in summaries) / len(summaries)
            avg_cost = sum(s.total_cost for s in summaries) / len(summaries)
            avg_latency = sum(s.total_latency_ms for s in summaries) / len(summaries)
            table.append({
                "path": path,
                "count": len(summaries),
                "avg_tokens": avg_tokens,
                "avg_cost": round(avg_cost, 6),
                "avg_latency_ms": round(avg_latency, 2),
            })
        return table
