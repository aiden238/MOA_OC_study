"""MOA 파이프라인 실행 엔진 — Draft → Critic → Synthesizer → Judge → (Rewrite).

전체 MOA 파이프라인을 관리하는 실행 엔진.
1) Draft Agent 3종 비동기 병렬 실행
2) Critic Agent가 3개 draft 비교 분석
3) Synthesizer Agent가 최종 결과 생성
4) Judge Agent가 품질 판정 (pass/rewrite/escalate)
5) Rewrite Agent가 피드백 기반 개선 (최대 2회 루프)
6) 모든 에이전트 호출을 trace로 기록
"""

from app.agents.critic_agent import CriticAgent
from app.agents.draft_agent import run_all_drafts
from app.agents.judge_agent import JudgeAgent
from app.agents.rewrite_agent import RewriteAgent
from app.core.logger import TraceLogger
from app.orchestrator.synthesizer import SynthesizerAgent
from app.schemas.agent_io import AgentOutput, JudgeDecision
from app.schemas.task import TaskRequest
from app.schemas.trace import RunSummary, TraceRecord

# Judge → Rewrite 루프 최대 횟수 (무한 루프 방지)
MAX_REWRITE_LOOPS = 2


def _log_output(logger: TraceLogger, output: AgentOutput, input_prompt: str, path: str = "moa"):
    """AgentOutput을 TraceLogger에 기록하는 헬퍼."""
    logger.log(
        agent_name=output.agent_name,
        model=output.model,
        input_prompt=input_prompt,
        output_text=output.content,
        prompt_tokens=output.prompt_tokens,
        completion_tokens=output.completion_tokens,
        latency_ms=output.latency_ms,
        cost_estimate=output.cost_estimate,
        path=path,
        operation_type="llm_completion",
    )


class MOAExecutor:
    """Draft → Critic → Synthesizer → Judge → (Rewrite) 파이프라인을 실행.

    `execute`는 선택적으로 `routing`을 받아 RAG/MCP 컨텍스트를 주입할 수 있습니다.
    backward-compatible하게 기존 호출 시에도 동작합니다.
    """

    async def execute(self, task: TaskRequest, logger: TraceLogger, routing=None, run_id: str | None = None) -> tuple[str, list[AgentOutput]]:
        """MOA 파이프라인 전체 실행.

        Args:
            task: 처리할 태스크 요청
            logger: trace 기록용 로거
            routing: (선택) Router의 RoutingDecision. RAG/MCP 주입을 위해 사용.
            run_id: (선택) 실행 식별자

        Returns:
            (최종 출력 텍스트, 모든 에이전트 출력 리스트)
        """
        # 지연 import로 순환 의존성 방지
        from app.rag.context_builder import ContextBuilder
        from app.rag.retriever import ChromaRetriever, SimpleRetriever
        from app.mcp_client.client import MCPClient

        all_outputs: list[AgentOutput] = []

        # RAG / MCP 컨텍스트 수집
        context_parts: list[str] = []
        path_suffix = ""
        if routing is not None:
            if getattr(routing, "requires_rag", False):
                rag_query = getattr(routing, "rag_query_hint", None) or task.prompt
                rag_items = []
                fallback_reason = None
                retriever_name = "ChromaRetriever"
                embedding_model = "text-embedding-3-small"

                try:
                    retriever = ChromaRetriever()
                    index_info = await retriever.ensure_indexed()
                    embedding_model = getattr(retriever.embedder, "model_name", embedding_model)
                    if index_info.get("indexed_count", 0) > 0:
                        logger.log(
                            agent_name="rag_retriever",
                            model=embedding_model,
                            input_prompt=f"index:{retriever.collection_name}",
                            output_text=f"indexed {index_info['indexed_count']} chunks",
                            prompt_tokens=index_info.get("embedding_tokens", 0),
                            completion_tokens=0,
                            latency_ms=0.0,
                            cost_estimate=index_info.get("embedding_cost_estimate", 0.0),
                            path="moa",
                            operation_type="rag",
                            metadata={
                                "stage": "indexing",
                                "indexed_count": index_info.get("indexed_count", 0),
                                "source_count": index_info.get("source_count", 0),
                            },
                        )
                    rag_items = await retriever.query_items(rag_query, n_results=5)
                except Exception as exc:
                    fallback_reason = str(exc)
                    retriever_name = "SimpleRetriever"
                    retriever = SimpleRetriever.from_directory()
                    rag_items = retriever.query_items(rag_query, n_results=5)
                    embedding_model = getattr(retriever, "collection_name", "simple-retriever")

                logger.log(
                    agent_name="rag_retriever",
                    model=embedding_model,
                    input_prompt=rag_query,
                    output_text="",
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=0.0,
                    cost_estimate=0.0,
                    path="moa",
                    operation_type="rag",
                    metadata={
                        "stage": "retrieval",
                        "retriever": retriever_name,
                        "query": rag_query,
                        "hit_count": len(rag_items),
                        "fallback_reason": fallback_reason,
                        "results": [
                            {
                                "doc_id": item.get("doc_id"),
                                "source_path": item.get("source_path"),
                                "chunk_id": item.get("chunk_id"),
                                "raw_distance": item.get("raw_distance"),
                                "normalized_relevance": item.get("normalized_relevance"),
                            }
                            for item in rag_items
                        ],
                    },
                )

                eligible_items = [
                    item for item in rag_items
                    if item.get("normalized_relevance", 0.0) >= 0.20
                ]
                builder = ContextBuilder(injection_top_k=3, max_context_tokens=1200)
                rag_context, context_meta = builder.build(eligible_items)
                rag_hit = bool(rag_context)

                logger.log(
                    agent_name="rag_retriever",
                    model=embedding_model,
                    input_prompt=rag_query,
                    output_text=rag_context,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=0.0,
                    cost_estimate=0.0,
                    path="moa+rag" if rag_hit else "moa",
                    operation_type="rag",
                    metadata={
                        "stage": "context_build",
                        "retriever": retriever_name,
                        "rag_miss": not rag_hit,
                        "fallback_reason": fallback_reason,
                        "query": rag_query,
                        **context_meta,
                    },
                )

                if rag_hit:
                    context_parts.append("[참고 문서]\n" + rag_context)
                    path_suffix += "+rag"
            if getattr(routing, "requires_mcp", False):
                mcp = MCPClient()
                try:
                    tool_result = await mcp.execute_filesystem_lookup(
                        task.prompt,
                        preferred_tool=getattr(routing, "preferred_tool", None),
                    )
                    normalized_summary = tool_result["normalized_result_summary"]
                    logger.log(
                        agent_name="mcp_filesystem",
                        model="filesystem",
                        input_prompt=task.prompt,
                        output_text=normalized_summary,
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=tool_result["latency_ms"],
                        cost_estimate=0.0,
                        path="moa+mcp",
                        operation_type="mcp_tool",
                        metadata={
                            "server_name": tool_result["server_name"],
                            "tool_name": tool_result["tool_name"],
                            "args": tool_result["args"],
                            "success": tool_result["success"],
                            "available_tools": tool_result.get("available_tools", []),
                            "normalized_result_summary": normalized_summary,
                            "result_text": tool_result.get("result_text", ""),
                        },
                    )
                    context_parts.append("[도구 호출 결과]\n" + normalized_summary)
                    path_suffix += "+mcp"
                except Exception as e:
                    logger.log(
                        agent_name="mcp_filesystem",
                        model="filesystem",
                        input_prompt=task.prompt,
                        output_text="",
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=0.0,
                        cost_estimate=0.0,
                        path="moa",
                        operation_type="mcp_tool",
                        metadata={
                            "server_name": getattr(routing, "preferred_server", "filesystem"),
                            "tool_name": getattr(routing, "preferred_tool", None),
                            "args": {},
                            "success": False,
                            "fallback_reason": str(e),
                            "normalized_result_summary": "",
                        },
                    )
                    context_parts.append(f"[도구 호출 실패]\n{e}")

        # enriched task 생성 (원본 TaskRequest를 변경하지 않음)
        enriched_prompt = task.prompt
        if context_parts:
            enriched_prompt = task.prompt + "\n\n" + "\n\n".join(context_parts)

        enriched_task = TaskRequest(**task.model_dump())
        enriched_task.prompt = enriched_prompt

        # ── 1단계: Draft 3종 비동기 병렬 실행 ──
        drafts = await run_all_drafts(enriched_task)
        for draft in drafts:
            _log_output(logger, draft, enriched_task.prompt, path="moa" + path_suffix)
            all_outputs.append(draft)

        # ── 2단계: Critic이 draft 비교 분석 ──
        critic = CriticAgent()
        critique = await critic.critique(drafts, original_prompt=enriched_task.prompt)
        _log_output(logger, critique, enriched_task.prompt, path="moa" + path_suffix)
        all_outputs.append(critique)

        # ── 3단계: Synthesizer가 최종 결과 생성 ──
        synthesizer = SynthesizerAgent()
        final = await synthesizer.synthesize(drafts, critique, original_prompt=enriched_task.prompt)
        _log_output(logger, final, enriched_task.prompt, path="moa" + path_suffix)
        all_outputs.append(final)

        # ── 4단계: Judge가 품질 판정 ──
        judge = JudgeAgent()
        current_output = final
        decision = None

        for loop in range(MAX_REWRITE_LOOPS + 1):
            decision = await judge.judge(enriched_task, current_output)
            # Judge 호출도 trace에 기록 (AgentOutput 생성)
            judge_output = AgentOutput(
                agent_name="judge",
                content=decision.model_dump_json(),
                model="gpt-4o-mini",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0.0,
            )
            _log_output(logger, judge_output, enriched_task.prompt, path="moa" + path_suffix)
            all_outputs.append(judge_output)

            if decision.decision == "pass":
                break
            elif decision.decision == "escalate":
                print(f"  [ESCALATE] 사람 검토 필요: {decision.reasoning}")
                break
            elif decision.decision == "rewrite" and loop < MAX_REWRITE_LOOPS:
                # ── 5단계: Rewrite Agent가 피드백 반영 ──
                rewriter = RewriteAgent()
                current_output = await rewriter.rewrite(current_output, decision)
                _log_output(logger, current_output, enriched_task.prompt, path="moa" + path_suffix)
                all_outputs.append(current_output)
            else:
                # 최대 rewrite 횟수 초과 → 마지막 결과 채택
                print(f"  [WARNING] 최대 rewrite 횟수({MAX_REWRITE_LOOPS}) 초과 → 마지막 결과 채택")
                break

        return current_output.content, all_outputs


def build_moa_summary(
    run_id: str,
    task: TaskRequest,
    final_output: str,
    logger: TraceLogger,
    path: str = "moa",
) -> RunSummary:
    """MOA 실행 결과를 RunSummary로 집계."""
    traces = [TraceRecord(**record) for record in logger.records]
    total_tokens = sum(r["prompt_tokens"] + r["completion_tokens"] for r in logger.records)
    total_cost = sum(r["cost_estimate"] for r in logger.records)
    total_latency = sum(r["latency_ms"] for r in logger.records)
    agents = {r["agent_name"] for r in logger.records}

    return RunSummary(
        run_id=run_id,
        task_id=task.task_id,
        path=path,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 6),
        total_latency_ms=round(total_latency, 2),
        agent_count=len(agents),
        traces=traces,
        final_output=final_output,
    )
