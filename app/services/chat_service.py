"""Reusable chat runtime service for CLI and web entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agents.base_agent import BaseAgent
from app.core.config import OUTPUT_DIR
from app.core.cost_tracker import CostTracker
from app.core.logger import TraceLogger, generate_run_id
from app.core.model_registry import resolve_request_models
from app.eval.rubric import evaluate_single
from app.orchestrator.executor import MOAExecutor
from app.orchestrator.router import Router, RoutingDecision
from app.schemas.agent_io import AgentOutput
from app.schemas.chat import (
    ChatMetrics,
    ChatSessionMessage,
    ChatTurnRequest,
    ChatTurnResponse,
    SelectedModelInfo,
)
from app.schemas.task import TaskRequest
from app.schemas.trace import CaseResult


def _sanitize_output_tag(output_tag: str | None) -> str | None:
    if not output_tag:
        return None

    sanitized = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in output_tag.strip()
    ).strip("-")
    return sanitized or None


def _build_history_text(history: list[ChatSessionMessage], max_messages: int = 6, max_chars: int = 4000) -> str:
    if not history:
        return ""

    selected = history[-max_messages:]
    parts: list[str] = []
    for message in selected:
        parts.append(f"{message.role}: {message.content}")

    text = "\n".join(parts)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text.strip()


def _build_execution_prompt(prompt: str, history: list[ChatSessionMessage]) -> str:
    history_text = _build_history_text(history)
    if not history_text:
        return prompt
    return (
        "[Conversation History]\n"
        f"{history_text}\n\n"
        "[Current User Prompt]\n"
        f"{prompt}"
    )


def _coerce_task_from_chat(request: ChatTurnRequest) -> TaskRequest:
    return TaskRequest(
        prompt=request.prompt,
        task_type=request.task_type,
        constraints=request.constraints,
        metadata=request.metadata,
    )


def _serialize_selected_models(
    selected_models: dict[str, Any],
    active_agents: set[str] | None = None,
) -> dict[str, Any]:
    active_agents = active_agents or set()
    serialized = {}
    for agent_name, info in selected_models.items():
        payload = info.model_dump() if hasattr(info, "model_dump") else dict(info)
        payload["active"] = agent_name in active_agents
        serialized[agent_name] = payload
    return serialized


def _chunk_source_name(chunk: dict[str, Any]) -> str:
    source = str(chunk.get("source") or "").strip()
    if source:
        return source

    source_path = str(chunk.get("source_path") or "").strip()
    if source_path:
        return Path(source_path).name

    label = str(chunk.get("label") or "").strip()
    if label:
        return label

    return "unknown"


def _chunk_score(chunk: dict[str, Any]) -> float | None:
    for key in ("score", "normalized_relevance"):
        value = chunk.get(key)
        if isinstance(value, (int, float)):
            return round(float(value), 3)
    return None


def _extract_rag_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_source: dict[str, float | None] = {}
    for chunk in chunks:
        source = _chunk_source_name(chunk)
        score = _chunk_score(chunk)
        current = best_by_source.get(source)
        if current is None or (score is not None and score > current):
            best_by_source[source] = score

    ordered = sorted(
        best_by_source.items(),
        key=lambda item: (-1.0 if item[1] is None else -item[1], item[0]),
    )
    return [{"source": source, "score": score} for source, score in ordered]


def _build_forced_decision(task: TaskRequest, force_path: str) -> RoutingDecision:
    constraints = task.constraints if isinstance(task.constraints, dict) else {}
    requires_rag = constraints.get("source") == "rag_docs"
    requires_mcp = bool(constraints.get("use_mcp"))

    return RoutingDecision(
        selected_path=force_path,  # type: ignore[arg-type]
        reason=f"Forced by request.force_path={force_path}",
        confidence=1.0,
        requires_rag=requires_rag,
        requires_mcp=requires_mcp,
        rag_query_hint=task.prompt if requires_rag else None,
        mcp_intent="user_forced" if requires_mcp else None,
        preferred_server="filesystem" if requires_mcp else None,
        preferred_tool="list_files" if requires_mcp else None,
    )


def save_case_output(
    result: dict[str, Any],
    output_dir: Path | None = None,
    output_tag: str | None = None,
) -> Path:
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_tag = _sanitize_output_tag(output_tag)
    filename = f"full_{result['case_id']}.json"
    if safe_tag:
        filename = f"full_{result['case_id']}__{safe_tag}.json"

    file_path = out_dir / filename
    payload = CaseResult(**result).model_dump()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return file_path


async def run_single_task(
    task: TaskRequest,
    logger: TraceLogger,
    cost_tracker: CostTracker,
    model_settings: dict[str, str] | None = None,
) -> tuple[str, list[AgentOutput]]:
    model_settings = model_settings or {}
    agent = BaseAgent(
        agent_name="single_baseline",
        system_prompt="You are a helpful AI assistant. Answer the user's request directly.",
        provider=model_settings.get("provider"),
        model=model_settings.get("model"),
        api_key=model_settings.get("api_key"),
        base_url=model_settings.get("base_url"),
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
        operation_type="llm_completion",
    )

    cost_tracker.add(
        model=output.model,
        prompt_tokens=output.prompt_tokens,
        completion_tokens=output.completion_tokens,
        path="single",
        agent_name=output.agent_name,
        operation_type="llm_completion",
    )

    return output.content, [output]


async def run_moa_task(
    task: TaskRequest,
    logger: TraceLogger,
    cost_tracker: CostTracker,
    routing: RoutingDecision | None = None,
    model_settings: dict[str, dict[str, str]] | None = None,
) -> tuple[str, list[AgentOutput]]:
    start_index = len(logger.records)
    executor = MOAExecutor(model_overrides=model_settings)
    final_text, all_outputs = await executor.execute(task, logger, routing=routing)

    new_records = logger.records[start_index:]
    for record in new_records:
        cost_tracker.add(
            model=record["model"],
            prompt_tokens=record["prompt_tokens"],
            completion_tokens=record["completion_tokens"],
            path=record["path"],
            agent_name=record["agent_name"],
            operation_type=record.get("operation_type", "llm_completion"),
            metadata=record.get("metadata", {}),
            cost_override=record.get("cost_estimate", 0.0),
        )

    return final_text, all_outputs


def _build_context_metadata(
    *,
    decision: RoutingDecision,
    case_records: list[dict[str, Any]],
    selected_models: dict[str, Any],
    resolved_provider_map: dict[str, str],
    fallback_reasons: dict[str, str | None],
    session_id: str | None,
    preset_id: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    rag_records = [record for record in case_records if record.get("operation_type") == "rag"]
    mcp_records = [record for record in case_records if record.get("operation_type") == "mcp_tool"]
    failure_records = [record for record in case_records if record.get("operation_type") == "agent_failure"]

    retrieval_record = next(
        (
            record
            for record in reversed(rag_records)
            if record.get("metadata", {}).get("stage") == "retrieval"
        ),
        None,
    )
    context_build_record = next(
        (
            record
            for record in reversed(rag_records)
            if record.get("metadata", {}).get("stage") == "context_build"
        ),
        None,
    )
    mcp_record = next((record for record in reversed(mcp_records)), None)

    evaluation_context: dict[str, Any] = {}
    context_metadata = {
        "routing": {
            "requires_rag": decision.requires_rag,
            "requires_mcp": decision.requires_mcp,
            "rag_query_hint": decision.rag_query_hint,
            "mcp_intent": decision.mcp_intent,
            "preferred_server": decision.preferred_server,
            "preferred_tool": decision.preferred_tool,
        },
        "session": {"session_id": session_id},
        "model_selection": {
            "preset_id": preset_id,
            "selected_models": selected_models,
            "resolved_provider_map": resolved_provider_map,
            "fallback_reasons": fallback_reasons,
        },
    }

    if retrieval_record is not None:
        rag_retrieval_meta = dict(retrieval_record.get("metadata", {}))
        if "retriever" in rag_retrieval_meta and "retriever_type" not in rag_retrieval_meta:
            rag_retrieval_meta["retriever_type"] = rag_retrieval_meta["retriever"]
        context_metadata["rag_retrieval"] = rag_retrieval_meta
        graph_subgraph = rag_retrieval_meta.get("graph_subgraph") or {}
        context_metadata["graph"] = {
            "query": rag_retrieval_meta.get("query", ""),
            "graph_query": rag_retrieval_meta.get("graph_query", rag_retrieval_meta.get("query", "")),
            "highlighted_node_ids": rag_retrieval_meta.get("graph_highlighted_node_ids", []),
            "expansion_terms": rag_retrieval_meta.get("graph_expansion_terms", []),
            "subgraph": graph_subgraph,
        }
        evaluation_context["graph"] = context_metadata["graph"]
    if context_build_record is not None:
        rag_meta = dict(context_build_record.get("metadata", {}))
        rag_meta.setdefault("token_estimate", rag_meta.get("context_token_estimate", 0))
        rag_meta.setdefault("selected_count", len(rag_meta.get("selected_chunks", [])))
        rag_meta.setdefault("total_chunks", rag_meta.get("selected_count", 0))
        context_metadata["rag"] = rag_meta
        context_metadata["rag_sources"] = _extract_rag_sources(rag_meta.get("selected_chunks", []))
        context_metadata.setdefault("graph", {})
        context_metadata["graph"].update(
            {
                "highlighted_nodes": rag_meta.get("graph_highlighted_nodes", []),
                "highlighted_node_ids": rag_meta.get(
                    "graph_highlighted_node_ids",
                    context_metadata["graph"].get("highlighted_node_ids", []),
                ),
                "expansion_terms": rag_meta.get(
                    "graph_expansion_terms",
                    context_metadata["graph"].get("expansion_terms", []),
                ),
                "subgraph": rag_meta.get(
                    "graph_subgraph",
                    context_metadata["graph"].get("subgraph", {}),
                ),
            }
        )
        evaluation_context["retrieval_context"] = context_build_record.get("output_text", "")
        evaluation_context["selected_chunks"] = (
            rag_meta.get("selected_chunks", [])
        )
    if failure_records:
        context_metadata["failed_agents"] = [
            {
                "agent_name": record["agent_name"],
                "reason": record.get("metadata", {}).get("reason", "unknown"),
            }
            for record in failure_records
        ]

    if mcp_record is not None:
        context_metadata["mcp"] = mcp_record.get("metadata", {})
        evaluation_context["tool_trace"] = {
            "server_name": mcp_record.get("metadata", {}).get("server_name"),
            "tool_name": mcp_record.get("metadata", {}).get("tool_name"),
            "args": mcp_record.get("metadata", {}).get("args", {}),
            "success": mcp_record.get("metadata", {}).get("success"),
        }
        evaluation_context["tool_result_summary"] = (
            mcp_record.get("metadata", {}).get("normalized_result_summary", "")
        )

    return context_metadata, evaluation_context


async def run_chat_turn(
    request: ChatTurnRequest,
    *,
    output_dir: Path | None = None,
) -> ChatTurnResponse:
    task = _coerce_task_from_chat(request)
    execution_task = TaskRequest(**task.model_dump())
    execution_task.prompt = _build_execution_prompt(request.prompt, request.history)

    model_resolution = resolve_request_models(
        global_model=request.global_model,
        agent_overrides=request.agent_overrides,
        preset_id=request.preset_id,
    )
    model_settings = model_resolution["settings"]
    router = Router(model_settings=model_settings.get("router"))

    run_id = generate_run_id()
    logger = TraceLogger(run_id=run_id)
    cost_tracker = CostTracker()

    if request.force_path and request.force_path != "auto":
        decision = _build_forced_decision(task, request.force_path)
    else:
        decision = await router.route(task)

    logger.log(
        agent_name="runtime_config",
        model="runtime_config",
        input_prompt=request.prompt,
        output_text="",
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=0.0,
        cost_estimate=0.0,
        path=decision.selected_path,
        operation_type="runtime_config",
        metadata={
            "session_id": request.session_id,
            "force_path": request.force_path,
            "preset_id": request.preset_id,
            "selected_models": _serialize_selected_models(model_resolution["selected_models"]),
            "resolved_provider_map": model_resolution["resolved_provider_map"],
        },
    )

    start_index = len(logger.records)
    if decision.selected_path == "single":
        final_text, outputs = await run_single_task(
            execution_task,
            logger,
            cost_tracker,
            model_settings=model_settings.get("single_baseline"),
        )
    else:
        final_text, outputs = await run_moa_task(
            execution_task,
            logger,
            cost_tracker,
            routing=decision,
            model_settings=model_settings,
        )

    case_records = logger.records[start_index:]
    actual_path = case_records[-1]["path"] if case_records else decision.selected_path
    active_agents = {output.agent_name for output in outputs}
    response_selected_models = {
        agent_name: SelectedModelInfo(**payload)
        for agent_name, payload in _serialize_selected_models(
            model_resolution["selected_models"],
            active_agents=active_agents,
        ).items()
    }
    context_metadata, evaluation_context = _build_context_metadata(
        decision=decision,
        case_records=case_records,
        selected_models=_serialize_selected_models(
            model_resolution["selected_models"],
            active_agents=active_agents,
        ),
        resolved_provider_map=model_resolution["resolved_provider_map"],
        fallback_reasons=model_resolution["fallback_reasons"],
        session_id=request.session_id,
        preset_id=model_resolution["preset_id"],
    )

    evaluation: dict[str, Any] = {}
    if request.evaluate:
        last_err: Exception | None = None
        for _ in range(2):
            try:
                evaluation = await evaluate_single(
                    prompt=execution_task.prompt,
                    output=final_text,
                    constraints=execution_task.constraints,
                    path=actual_path,
                    evaluation_context=evaluation_context,
                    model_settings=model_settings.get("rubric_judge"),
                )
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        if last_err is not None:
            evaluation = {"error": str(last_err), "avg_score": None}

    trace_path = str(logger.save())
    result = {
        "case_id": task.task_id,
        "task_type": execution_task.task_type,
        "prompt": execution_task.prompt,
        "output": final_text,
        "path": actual_path,
        "routing_reason": decision.reason,
        "routing_confidence": decision.confidence,
        "agent_count": len(outputs),
        "agents": [output.agent_name for output in outputs],
        "prompt_tokens": sum(output.prompt_tokens for output in outputs),
        "completion_tokens": sum(output.completion_tokens for output in outputs),
        "latency_ms": round(sum(output.latency_ms for output in outputs), 2),
        "cost_estimate": round(sum(record["cost_estimate"] for record in case_records), 6),
        "constraints": execution_task.constraints,
        "evaluation": evaluation,
        "evaluation_context": evaluation_context,
        "context_metadata": context_metadata,
        "trace_path": trace_path,
        "session_id": request.session_id or "",
        "selected_models": _serialize_selected_models(
            model_resolution["selected_models"],
            active_agents=active_agents,
        ),
        "resolved_provider_map": model_resolution["resolved_provider_map"],
        "fallback_reasons": model_resolution["fallback_reasons"],
        "preset_id": model_resolution["preset_id"] or "",
    }

    output_path = ""
    if request.save_output:
        output_path = str(
            save_case_output(
                result,
                output_dir=output_dir,
                output_tag=request.output_tag,
            )
        )

    return ChatTurnResponse(
        session_id=request.session_id,
        run_id=run_id,
        prompt=execution_task.prompt,
        reply=final_text,
        path=actual_path,
        routing_reason=decision.reason,
        routing_confidence=decision.confidence,
        metrics=ChatMetrics(
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            latency_ms=result["latency_ms"],
            cost_estimate=result["cost_estimate"],
        ),
        trace_path=trace_path,
        output_path=output_path,
        agent_count=len(outputs),
        agents=result["agents"],
        evaluation=evaluation,
        evaluation_context=evaluation_context,
        context_metadata=context_metadata,
        selected_models=response_selected_models,
        resolved_provider_map=model_resolution["resolved_provider_map"],
        fallback_reasons=model_resolution["fallback_reasons"],
        preset_id=model_resolution["preset_id"],
    )


async def run_benchmark_pipeline(
    cases: list[dict[str, Any]],
    *,
    case_id: str | None = None,
    force_path: str | None = None,
    cost_report: bool = False,
    evaluate: bool = False,
    output_dir: Path | None = None,
    output_tag: str | None = None,
) -> list[dict[str, Any]]:
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            raise ValueError(f"case_id '{case_id}' was not found.")

    results: list[dict[str, Any]] = []
    total_tracker = CostTracker()
    print(f"[Full Pipeline] cases={len(cases)}")

    for case in cases:
        task = TaskRequest(
            task_id=case["id"],
            prompt=case["prompt"],
            task_type=case["type"],
            constraints=case.get("constraints", {}),
            metadata={
                "difficulty": case.get("difficulty", ""),
                "expected_moa_advantage": case.get("expected_moa_advantage", ""),
            },
        )

        request = ChatTurnRequest(
            prompt=task.prompt,
            force_path=force_path or "auto",
            evaluate=evaluate,
            task_type=task.task_type,
            constraints=task.constraints,
            metadata=task.metadata,
            save_output=True,
            output_tag=output_tag,
        )
        response = await run_chat_turn(request, output_dir=output_dir)

        result = {
            "case_id": task.task_id,
            "task_type": task.task_type,
            "prompt": response.prompt,
            "output": response.reply,
            "path": response.path,
            "routing_reason": response.routing_reason,
            "routing_confidence": response.routing_confidence,
            "agent_count": response.agent_count,
            "agents": response.agents,
            "prompt_tokens": response.metrics.prompt_tokens,
            "completion_tokens": response.metrics.completion_tokens,
            "latency_ms": response.metrics.latency_ms,
            "cost_estimate": response.metrics.cost_estimate,
            "constraints": task.constraints,
            "evaluation": response.evaluation,
            "evaluation_context": response.evaluation_context,
            "context_metadata": response.context_metadata,
            "trace_path": response.trace_path,
            "selected_models": {
                key: value.model_dump() for key, value in response.selected_models.items()
            },
            "resolved_provider_map": response.resolved_provider_map,
            "fallback_reasons": response.fallback_reasons,
            "preset_id": response.preset_id or "",
        }
        results.append(result)

        total_tracker.add(
            model="aggregate",
            prompt_tokens=response.metrics.prompt_tokens,
            completion_tokens=response.metrics.completion_tokens,
            path=response.path,
            agent_name="aggregate",
            operation_type="aggregate",
            cost_override=response.metrics.cost_estimate,
        )

        total_tokens = response.metrics.prompt_tokens + response.metrics.completion_tokens
        print(
            f"  [{task.task_id}] path={response.path} "
            f"{response.metrics.latency_ms:.0f}ms {total_tokens} tokens "
            f"${response.metrics.cost_estimate:.6f}"
        )

    if cost_report:
        summary = total_tracker.summary()
        print(f"\n{'=' * 50}")
        print("  Cost Report")
        print(f"{'=' * 50}")
        print(f"  Calls:            {summary['call_count']}")
        print(f"  Total tokens:     {summary['total_tokens']:,}")
        print(f"  Total cost:       ${summary['total_cost']:.6f}")
        print(f"{'=' * 50}")

    return results
