from unittest.mock import AsyncMock, patch

import pytest

from app.core.logger import TraceLogger
from app.mcp_client.client import MCPClient, MCPToolRequest
from app.orchestrator.executor import MOAExecutor
from app.orchestrator.router import RoutingDecision
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest


def _mock_output(name: str, content: str = "mock") -> AgentOutput:
    return AgentOutput(
        agent_name=name,
        content=content,
        model="gpt-4o-mini",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100.0,
        cost_estimate=0.001,
    )


class TestMCPClient:
    def test_plan_filesystem_request_prefers_safe_targets(self):
        client = MCPClient()

        request = client.plan_filesystem_request("README.md 내용을 읽어줘")
        assert request.tool_name == "read_text_file"
        assert request.args["path"] == "README.md"

        request = client.plan_filesystem_request("docs 폴더 파일 목록을 보여줘", preferred_tool="list_files")
        assert request.tool_name == "list_directory"
        assert request.args["path"] == "docs"

    def test_validate_tool_request_blocks_sensitive_paths(self):
        client = MCPClient()

        with pytest.raises(ValueError, match="차단된 파일"):
            client.validate_tool_request("read_text_file", {"path": ".env"})

        with pytest.raises(ValueError, match="차단된 경로"):
            client.validate_tool_request("list_directory", {"path": ".venv"})

        with pytest.raises(ValueError, match="읽기 전용이 아닌 도구"):
            client.validate_tool_request("write_file", {"path": "docs/test.txt"})

    @pytest.mark.asyncio
    async def test_execute_filesystem_lookup_uses_planned_request(self):
        client = MCPClient()
        expected = {
            "server_name": "filesystem",
            "tool_name": "read_text_file",
            "args": {"path": "README.md"},
            "available_tools": ["read_text_file"],
            "success": True,
            "latency_ms": 12.3,
            "normalized_result_summary": "summary",
            "result_text": "README",
        }

        with patch.object(client, "_run_tool_request", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = expected
            result = await client.execute_filesystem_lookup("README.md 내용을 읽어줘")

        assert result == expected
        request = mock_run.await_args.args[0]
        assert isinstance(request, MCPToolRequest)
        assert request.tool_name == "read_text_file"


class TestMCPExecutorIntegration:
    @pytest.mark.asyncio
    async def test_executor_mcp_success_injects_context_and_trace(self):
        mock_drafts = [_mock_output("draft_analytical"), _mock_output("draft_creative"), _mock_output("draft_structured")]
        mock_critic = _mock_output("critic", '{"analyses": []}')
        mock_synth = _mock_output("synthesizer", "MOA 최종 결과")
        mock_judge = JudgeDecision(decision="pass", confidence=0.95, reasoning="OK")

        tool_result = {
            "server_name": "filesystem",
            "tool_name": "list_directory",
            "args": {"path": "docs"},
            "available_tools": ["list_directory"],
            "success": True,
            "latency_ms": 20.0,
            "normalized_result_summary": "[MCP Server] filesystem\n[Tool] list_directory",
            "result_text": "[FILE] 00_project_goal.md",
        }

        with patch("app.orchestrator.executor.run_all_drafts", new_callable=AsyncMock) as mock_run_drafts, \
             patch("app.orchestrator.executor.CriticAgent") as MockCritic, \
             patch("app.orchestrator.executor.SynthesizerAgent") as MockSynth, \
             patch("app.orchestrator.executor.JudgeAgent") as MockJudge, \
             patch("app.mcp_client.client.MCPClient.execute_filesystem_lookup", new_callable=AsyncMock) as mock_mcp:

            mock_run_drafts.return_value = mock_drafts
            MockCritic.return_value = AsyncMock(critique=AsyncMock(return_value=mock_critic))
            MockSynth.return_value = AsyncMock(synthesize=AsyncMock(return_value=mock_synth))
            MockJudge.return_value = AsyncMock(judge=AsyncMock(return_value=mock_judge))
            mock_mcp.return_value = tool_result

            executor = MOAExecutor()
            logger = TraceLogger(run_id="mcp-hit")
            routing = RoutingDecision(
                selected_path="moa",
                reason="mcp hit",
                confidence=0.9,
                requires_mcp=True,
                preferred_server="filesystem",
                preferred_tool="list_files",
            )
            task = TaskRequest(prompt="docs 파일 목록을 보여줘", task_type="explain")

            final_output, _ = await executor.execute(task, logger, routing=routing)

        assert final_output == "MOA 최종 결과"
        enriched_task = mock_run_drafts.await_args.args[0]
        assert "[도구 호출 결과]" in enriched_task.prompt
        mcp_records = [record for record in logger.records if record["operation_type"] == "mcp_tool"]
        assert mcp_records
        assert mcp_records[-1]["metadata"]["tool_name"] == "list_directory"
        assert logger.records[-1]["path"] == "moa+mcp"
