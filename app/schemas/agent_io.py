"""에이전트 입출력 스키마 — AgentInput, AgentOutput.

AgentInput:  LLM 호출 전 구성하는 입력 모델
AgentOutput: LLM 호출 후 반환하는 결과 모델
"""

from typing import Any

from pydantic import BaseModel


class AgentInput(BaseModel):
    """LLM 호출에 필요한 입력 데이터."""
    agent_name: str       # 호출하는 에이전트 이름
    system_prompt: str    # 시스템 프롬프트 (역할 지정)
    user_message: str     # 사용자 메시지
    temperature: float = 0.7   # 생성 온도 (0: 결정적, 1: 창의적)
    max_tokens: int = 1024     # 최대 생성 토큰 수


class AgentOutput(BaseModel):
    """LLM 호출 결과를 정형화한 출력 데이터."""
    agent_name: str            # 응답한 에이전트 이름
    content: str               # LLM이 생성한 텍스트
    model: str                 # 실제 사용된 모델명
    prompt_tokens: int         # 입력 토큰 수
    completion_tokens: int     # 출력 토큰 수
    latency_ms: float          # 응답 지연 시간 (ms)
    cost_estimate: float = 0.0            # 추정 비용 (USD)
    raw_response: dict[str, Any] = {}     # 원본 API 응답
