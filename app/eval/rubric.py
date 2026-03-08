"""LLM Judge 기반 루브릭 채점 — 4항목 1~5점 자동 평가."""

import json

from app.agents.base_agent import BaseAgent


RUBRIC_SYSTEM_PROMPT = """당신은 텍스트 품질 평가 전문가입니다.
주어진 [원래 요청]과 [생성된 결과]를 분석하고, 아래 4가지 항목에 대해 1~5점으로 채점하세요.

채점 기준:
- clarity (명확성): 1=혼란스럽고 이해 어려움, 3=대체로 이해 가능, 5=매우 명확하고 읽기 쉬움
- structure (구조): 1=두서없고 구조 없음, 3=기본 구조 존재, 5=체계적이고 논리적 흐름
- constraint_following (제약 준수): 1=제약 조건 무시, 3=일부 준수, 5=모든 제약 조건 완벽 준수
- usefulness (유용성): 1=무의미하거나 부정확, 3=보통 수준으로 유용, 5=매우 유용하고 실용적

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"clarity": N, "structure": N, "constraint_following": N, "usefulness": N, "reasoning": "간단한 채점 근거"}"""


RUBRIC_DIMENSIONS = ["clarity", "structure", "constraint_following", "usefulness"]


def build_judge_message(prompt: str, output: str, constraints: dict | None = None) -> str:
    """Judge에게 전달할 채점 요청 메시지를 구성."""
    constraint_text = ""
    if constraints:
        constraint_text = f"\n\n[제약 조건]\n{json.dumps(constraints, ensure_ascii=False)}"

    return f"""[원래 요청]
{prompt}{constraint_text}

[생성된 결과]
{output}"""


def parse_judge_response(response_text: str) -> dict:
    """Judge의 JSON 응답을 파싱하고 검증."""
    # JSON 블록 추출 (```json ... ``` 감싸기 대응)
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```") and not in_block:
                in_block = True
                continue
            elif line.strip() == "```" and in_block:
                break
            elif in_block:
                json_lines.append(line)
        text = "\n".join(json_lines)

    data = json.loads(text)

    # 점수 범위 검증
    scores = {}
    for dim in RUBRIC_DIMENSIONS:
        score = data.get(dim)
        if score is None or not isinstance(score, (int, float)):
            raise ValueError(f"'{dim}' 점수가 누락되었거나 유효하지 않습니다: {score}")
        score = int(score)
        if not 1 <= score <= 5:
            raise ValueError(f"'{dim}' 점수가 범위(1~5)를 벗어났습니다: {score}")
        scores[dim] = score

    scores["reasoning"] = data.get("reasoning", "")
    scores["avg_score"] = round(sum(scores[d] for d in RUBRIC_DIMENSIONS) / len(RUBRIC_DIMENSIONS), 2)
    return scores


async def evaluate_single(
    prompt: str,
    output: str,
    constraints: dict | None = None,
) -> dict:
    """단일 케이스를 LLM Judge로 채점."""
    judge = BaseAgent(
        agent_name="rubric_judge",
        system_prompt=RUBRIC_SYSTEM_PROMPT,
    )

    message = build_judge_message(prompt, output, constraints)
    agent_output = await judge.run(message, temperature=0.1)

    scores = parse_judge_response(agent_output.content)
    scores["judge_model"] = agent_output.model
    scores["judge_tokens"] = agent_output.prompt_tokens + agent_output.completion_tokens
    scores["judge_cost"] = agent_output.cost_estimate

    return scores


async def evaluate_batch(results: list[dict]) -> list[dict]:
    """여러 케이스 결과를 순차적으로 채점."""
    evaluations = []
    for result in results:
        scores = await evaluate_single(
            prompt=result["prompt"],
            output=result["output"],
            constraints=result.get("constraints"),
        )
        scores["case_id"] = result.get("case_id", "")
        evaluations.append(scores)
    return evaluations
