"""CostTracker C7-1 확장 테스트."""

from app.core.cost_tracker import CostTracker


class TestCostTracker:
    def test_summary_tracks_path_and_operation_type(self):
        tracker = CostTracker()
        tracker.add(
            model="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            path="single",
            agent_name="single_baseline",
            operation_type="llm_completion",
        )
        tracker.add(
            model="gpt-4o-mini",
            prompt_tokens=0,
            completion_tokens=0,
            path="moa+rag",
            agent_name="retriever",
            operation_type="rag",
            metadata={"stage": "retrieval"},
            cost_override=0.0002,
        )

        summary = tracker.summary()
        assert summary["call_count"] == 2
        assert "single" in summary["by_path"]
        assert "moa+rag" in summary["by_path"]
        assert summary["by_operation_type"]["llm_completion"]["tokens"] == 150
        assert summary["by_operation_type"]["rag"]["cost"] == 0.0002

    def test_add_supports_zero_token_operation(self):
        tracker = CostTracker()
        cost = tracker.add(
            model="gpt-4o-mini",
            prompt_tokens=0,
            completion_tokens=0,
            path="moa+mcp",
            agent_name="filesystem",
            operation_type="mcp_tool",
            cost_override=0.0,
        )
        assert cost == 0.0
        assert tracker.summary()["by_operation_type"]["mcp_tool"]["tokens"] == 0
