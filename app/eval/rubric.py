"""LLM Judge 기반 루브릭 채점 — 기본 4항목 + 경로별 추가 항목."""

import json

from app.agents.base_agent import BaseAgent


RUBRIC_SYSTEM_PROMPT = """당신은 텍스트 품질 평가 전문가입니다.
주어진 [원래 요청]과 [생성된 결과]를 분석하고, 기본 4가지 항목에 대해 1~5점으로 채점하세요.

기본 채점 기준:
- clarity (명확성): 1=혼란스럽고 이해 어려움, 3=대체로 이해 가능, 5=매우 명확하고 읽기 쉬움
- structure (구조): 1=두서없고 구조 없음, 3=기본 구조 존재, 5=체계적이고 논리적 흐름
- constraint_following (제약 준수): 1=제약 조건 무시, 3=일부 준수, 5=모든 제약 조건 완벽 준수
- usefulness (유용성): 1=무의미하거나 부정확, 3=보통 수준으로 유용, 5=매우 유용하고 실용적

추가 평가 항목이 함께 요청되면 같이 응답하세요.
추가 평가 항목을 판단할 정보가 부족하면 "not_evaluable"로 표기하세요.

반드시 JSON 형식으로만 응답하세요 (다른 텍스트 없이)."""


RUBRIC_DIMENSIONS = ["clarity", "structure", "constraint_following", "usefulness"]
PATH_SPECIFIC_DIMENSIONS = {
    "moa+rag": ["groundedness", "citation_traceability"],
    "moa+mcp": ["tool_use_correctness", "tool_result_faithfulness"],
}


def build_judge_message(
    prompt: str,
    output: str,
    constraints: dict | None = None,
    path: str = "single",
    evaluation_context: dict | None = None,
) -> str:
    """Judge에게 전달할 채점 요청 메시지를 구성."""
    constraint_text = ""
    if constraints:
        constraint_text = f"\n\n[제약 조건]\n{json.dumps(constraints, ensure_ascii=False)}"

    extra_metrics = PATH_SPECIFIC_DIMENSIONS.get(path, [])
    extra_metric_text = ""
    if extra_metrics:
        extra_metric_text = (
            "\n\n[추가 평가 항목]\n"
            f"{', '.join(extra_metrics)}\n"
            '추가 항목을 판단할 정보가 부족하면 "not_evaluable"로 응답하세요.'
        )

    context_text = ""
    if evaluation_context:
        context_text = (
            "\n\n[평가 컨텍스트]\n"
            f"{json.dumps(evaluation_context, ensure_ascii=False)}"
        )

    return f"""[실행 경로]
{path}

[원래 요청]
{prompt}{constraint_text}

[생성된 결과]
{output}{extra_metric_text}{context_text}"""


def parse_judge_response(response_text: str, path: str = "single") -> dict:
    """Judge의 JSON 응답을 파싱하고 검증."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            if line.strip() == "```" and in_block:
                break
            if in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)

    data = json.loads(text)

    scores = {}
    for dim in RUBRIC_DIMENSIONS:
        score = data.get(dim)
        if score is None or not isinstance(score, (int, float)):
            raise ValueError(f"'{dim}' 점수가 누락되었거나 유효하지 않습니다: {score}")
        score = int(score)
        if not 1 <= score <= 5:
            raise ValueError(f"'{dim}' 점수가 범위(1~5)를 벗어났습니다: {score}")
        scores[dim] = score

    for dim in PATH_SPECIFIC_DIMENSIONS.get(path, []):
        value = data.get(dim, "not_evaluable")
        if value == "not_evaluable":
            scores[dim] = "not_evaluable"
            continue
        if not isinstance(value, (int, float)):
            raise ValueError(f"'{dim}' 점수가 유효하지 않습니다: {value}")
        value = int(value)
        if not 1 <= value <= 5:
            raise ValueError(f"'{dim}' 점수가 범위(1~5)를 벗어났습니다: {value}")
        scores[dim] = value

    scores["reasoning"] = data.get("reasoning", "")
    scores["avg_score"] = round(sum(scores[d] for d in RUBRIC_DIMENSIONS) / len(RUBRIC_DIMENSIONS), 2)
    return scores


async def evaluate_single(
    prompt: str,
    output: str,
    constraints: dict | None = None,
    path: str = "single",
    evaluation_context: dict | None = None,
) -> dict:
    """단일 케이스를 LLM Judge로 채점."""
    judge = BaseAgent(
        agent_name="rubric_judge",
        system_prompt=RUBRIC_SYSTEM_PROMPT,
    )

    message = build_judge_message(prompt, output, constraints, path, evaluation_context)
    agent_output = await judge.run(
        message,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    scores = parse_judge_response(agent_output.content, path=path)
    scores["judge_model"] = agent_output.model
    scores["judge_tokens"] = agent_output.prompt_tokens + agent_output.completion_tokens
    scores["judge_cost"] = agent_output.cost_estimate
    scores["path"] = path

    return scores


async def evaluate_batch(results: list[dict]) -> list[dict]:
    """여러 케이스 결과를 순차적으로 채점."""
    evaluations = []
    for result in results:
        scores = await evaluate_single(
            prompt=result["prompt"],
            output=result["output"],
            constraints=result.get("constraints"),
            path=result.get("path", "single"),
            evaluation_context=result.get("evaluation_context"),
        )
        scores["case_id"] = result.get("case_id", "")
        evaluations.append(scores)
    return evaluations
