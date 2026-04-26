"""Service-layer tests for the Week 10 chat runtime."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.orchestrator.router import RoutingDecision
from app.schemas.agent_io import AgentOutput
from app.schemas.chat import ChatSessionMessage, ChatTurnRequest, ModelSelection
from app.services.chat_service import run_chat_turn


def _output(agent_name: str, content: str, model: str = "gpt-4o-mini") -> AgentOutput:
    return AgentOutput(
        agent_name=agent_name,
        content=content,
        model=model,
        prompt_tokens=12,
        completion_tokens=8,
        latency_ms=45.0,
        cost_estimate=0.0002,
    )


class TestRunChatTurn:
    @pytest.mark.asyncio
    async def test_single_turn_includes_history_and_persists_output(self, tmp_path: Path):
        captured_prompt: dict[str, str] = {}

        async def fake_run_single_task(task, logger, cost_tracker, model_settings=None):
            captured_prompt["value"] = task.prompt
            output = _output("single_baseline", "single reply", model_settings["model"])
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
            cost_tracker.add(
                model=output.model,
                prompt_tokens=output.prompt_tokens,
                completion_tokens=output.completion_tokens,
                path="single",
                agent_name=output.agent_name,
                cost_override=output.cost_estimate,
            )
            return output.content, [output]

        request = ChatTurnRequest(
            prompt="What changed?",
            history=[
                ChatSessionMessage(role="user", content="Summarize the logs."),
                ChatSessionMessage(role="assistant", content="The service restarted."),
            ],
            global_model=ModelSelection(provider="openai", model="gpt-5-mini"),
            save_output=True,
            output_tag="chat demo",
        )

        with patch(
            "app.services.chat_service.Router.route",
            new=AsyncMock(
                return_value=RoutingDecision(
                    selected_path="single",
                    reason="simple follow-up",
                    confidence=0.9,
                )
            ),
        ), patch(
            "app.services.chat_service.run_single_task",
            new=AsyncMock(side_effect=fake_run_single_task),
        ), patch(
            "app.services.chat_service.generate_run_id",
            return_value="run123",
        ), patch(
            "app.services.chat_service.TraceLogger.save",
            return_value=tmp_path / "trace.json",
        ):
            response = await run_chat_turn(request, output_dir=tmp_path)

        assert "[Conversation History]" in captured_prompt["value"]
        assert "Summarize the logs." in captured_prompt["value"]
        assert "[Current User Prompt]" in captured_prompt["value"]
        assert response.run_id == "run123"
        assert response.path == "single"
        assert response.reply == "single reply"
        assert response.metrics.prompt_tokens == 12
        assert response.selected_models["single_baseline"].model == "gpt-5-mini"
        assert response.selected_models["single_baseline"].active is True

        output_path = Path(response.output_path)
        assert output_path.exists()
        assert "__chat-demo" in output_path.name
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["path"] == "single"
        assert payload["selected_models"]["single_baseline"]["model"] == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_forced_moa_skips_router_and_runs_evaluation(self, tmp_path: Path):
        async def fake_run_moa_task(task, logger, cost_tracker, routing=None, model_settings=None):
            draft = _output("draft_creative", "creative draft", "glm-4.7-flash")
            synth = _output("synthesizer", "moa reply")
            for output in (draft, synth):
                logger.log(
                    agent_name=output.agent_name,
                    model=output.model,
                    input_prompt=task.prompt,
                    output_text=output.content,
                    prompt_tokens=output.prompt_tokens,
                    completion_tokens=output.completion_tokens,
                    latency_ms=output.latency_ms,
                    cost_estimate=output.cost_estimate,
                    path="moa",
                )
            cost_tracker.add(
                model=draft.model,
                prompt_tokens=draft.prompt_tokens,
                completion_tokens=draft.completion_tokens,
                path="moa",
                agent_name=draft.agent_name,
                cost_override=draft.cost_estimate,
            )
            cost_tracker.add(
                model=synth.model,
                prompt_tokens=synth.prompt_tokens,
                completion_tokens=synth.completion_tokens,
                path="moa",
                agent_name=synth.agent_name,
                cost_override=synth.cost_estimate,
            )
            return synth.content, [draft, synth]

        request = ChatTurnRequest(
            prompt="Design three product directions.",
            force_path="moa",
            evaluate=True,
            agent_overrides={
                "draft_creative": ModelSelection(provider="zai", model="glm-4.7-flash")
            },
        )

        with patch(
            "app.services.chat_service.Router.route",
            new=AsyncMock(),
        ) as mock_route, patch(
            "app.services.chat_service.run_moa_task",
            new=AsyncMock(side_effect=fake_run_moa_task),
        ), patch(
            "app.services.chat_service.evaluate_single",
            new=AsyncMock(return_value={"avg_score": 4.25, "path": "moa"}),
        ) as mock_eval, patch(
            "app.services.chat_service.TraceLogger.save",
            return_value=tmp_path / "trace.json",
        ):
            response = await run_chat_turn(request, output_dir=tmp_path)

        mock_route.assert_not_awaited()
        mock_eval.assert_awaited_once()
        assert response.path == "moa"
        assert response.evaluation["avg_score"] == 4.25
        assert response.selected_models["draft_creative"].provider == "zai"
        assert response.selected_models["draft_creative"].active is True

    @pytest.mark.asyncio
    async def test_forced_moa_with_rag_constraint_exposes_rag_sources(self, tmp_path: Path):
        async def fake_run_moa_task(task, logger, cost_tracker, routing=None, model_settings=None):
            assert routing is not None
            assert routing.requires_rag is True
            assert routing.requires_mcp is False

            draft = _output("draft_analytical", "draft")
            synth = _output("synthesizer", "rag reply")

            logger.log(
                agent_name="rag_retriever",
                model="text-embedding-3-small",
                input_prompt=task.prompt,
                output_text="retrieved context",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
                cost_estimate=0.0,
                path="moa+rag",
                operation_type="rag",
                metadata={
                    "stage": "context_build",
                    "selected_chunks": [
                        {
                            "source_path": "data/rag_docs/doc_a.txt",
                            "normalized_relevance": 0.91,
                            "text": "chunk a",
                        },
                        {
                            "source": "doc_b.md",
                            "score": 0.73,
                            "text": "chunk b",
                        },
                    ],
                    "context_token_estimate": 42,
                    "selected_count": 2,
                },
            )
            logger.log(
                agent_name=synth.agent_name,
                model=synth.model,
                input_prompt=task.prompt,
                output_text=synth.content,
                prompt_tokens=synth.prompt_tokens,
                completion_tokens=synth.completion_tokens,
                latency_ms=synth.latency_ms,
                cost_estimate=synth.cost_estimate,
                path="moa+rag",
                operation_type="llm_completion",
            )
            return synth.content, [draft, synth]

        request = ChatTurnRequest(
            prompt="Use the rag docs.",
            force_path="moa",
            constraints={"source": "rag_docs"},
        )

        with patch(
            "app.services.chat_service.run_moa_task",
            new=AsyncMock(side_effect=fake_run_moa_task),
        ), patch(
            "app.services.chat_service.TraceLogger.save",
            return_value=tmp_path / "trace.json",
        ):
            response = await run_chat_turn(request, output_dir=tmp_path)

        assert response.path == "moa+rag"
        assert response.context_metadata["routing"]["requires_rag"] is True
        assert response.context_metadata["rag"]["token_estimate"] == 42
        assert response.context_metadata["rag_sources"] == [
            {"source": "doc_a.txt", "score": 0.91},
            {"source": "doc_b.md", "score": 0.73},
        ]

    @pytest.mark.asyncio
    async def test_forced_moa_with_mcp_constraint_sets_mcp_routing(self, tmp_path: Path):
        async def fake_run_moa_task(task, logger, cost_tracker, routing=None, model_settings=None):
            assert routing is not None
            assert routing.requires_rag is False
            assert routing.requires_mcp is True
            assert routing.mcp_intent == "user_forced"

            synth = _output("synthesizer", "mcp reply")
            logger.log(
                agent_name="mcp_filesystem",
                model="filesystem",
                input_prompt=task.prompt,
                output_text="summary",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
                cost_estimate=0.0,
                path="moa+mcp",
                operation_type="mcp_tool",
                metadata={
                    "server_name": "filesystem",
                    "tool_name": "list_files",
                    "success": True,
                    "normalized_result_summary": "listed files",
                },
            )
            logger.log(
                agent_name=synth.agent_name,
                model=synth.model,
                input_prompt=task.prompt,
                output_text=synth.content,
                prompt_tokens=synth.prompt_tokens,
                completion_tokens=synth.completion_tokens,
                latency_ms=synth.latency_ms,
                cost_estimate=synth.cost_estimate,
                path="moa+mcp",
                operation_type="llm_completion",
            )
            return synth.content, [synth]

        request = ChatTurnRequest(
            prompt="List files with MCP.",
            force_path="moa",
            constraints={"use_mcp": True},
        )

        with patch(
            "app.services.chat_service.run_moa_task",
            new=AsyncMock(side_effect=fake_run_moa_task),
        ), patch(
            "app.services.chat_service.TraceLogger.save",
            return_value=tmp_path / "trace.json",
        ):
            response = await run_chat_turn(request, output_dir=tmp_path)

        assert response.path == "moa+mcp"
        assert response.context_metadata["routing"]["requires_mcp"] is True
        assert response.context_metadata["mcp"]["tool_name"] == "list_files"
