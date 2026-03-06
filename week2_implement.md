# Week 2 Implement — 구현 상세

## Pydantic 스키마 설계

### `app/schemas/task.py`

```python
class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    task_type: Literal["summarize", "explain", "ideate", "critique_rewrite"]
    constraints: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

class TaskPlan(BaseModel):
    original_request: TaskRequest
    subtasks: list[str] = []           # Planner가 분해한 하위 작업
    selected_path: Literal["single", "moa"]
    requires_rag: bool = False         # 6주차 활성화
    requires_mcp: bool = False         # 6주차 활성화
```

### `app/schemas/agent_io.py`

```python
class AgentInput(BaseModel):
    agent_name: str
    system_prompt: str
    user_message: str
    temperature: float = 0.7
    max_tokens: int = 1024

class AgentOutput(BaseModel):
    agent_name: str
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float
    raw_response: dict[str, Any] = {}
```

### `app/schemas/trace.py`

```python
class TraceRecord(BaseModel):
    run_id: str
    agent_name: str
    model: str
    input_prompt: str
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float
    timestamp: str
    path: str  # "single" | "moa" | "rag" | "mcp"

class RunSummary(BaseModel):
    run_id: str
    task_id: str
    path: str
    total_tokens: int
    total_cost: float
    total_latency_ms: float
    agent_count: int
    traces: list[TraceRecord]
    final_output: str
```

---

## Base Agent 클래스

```python
class BaseAgent:
    """httpx + pydantic 기반 LLM API 호출 래퍼"""
    
    def __init__(self, agent_name: str, system_prompt: str):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
    
    async def run(self, input: AgentInput) -> AgentOutput:
        """LLM API 호출 → AgentOutput 반환"""
        # 1. httpx로 API 호출 (config에서 모델/키 로딩)
        # 2. timer로 레이턴시 측정
        # 3. 응답을 AgentOutput으로 파싱
        # 4. logger로 trace 기록
        ...
    
    @staticmethod
    def load_prompt(prompt_file: str) -> str:
        """app/prompts/{prompt_file}.md에서 시스템 프롬프트 로딩"""
        ...
```

**설계 원칙:**
- 모든 에이전트가 `BaseAgent`를 상속
- `run()` 메서드 하나로 호출 → 응답 → trace 기록까지 일관된 흐름
- 프롬프트는 하드코딩 금지, 반드시 `.md` 파일에서 로딩
- API 호출 실패 시 명확한 에러 (이번 주는 재시도 없이 단순 실패)

---

## Draft 다양성 확보 전략

| Draft Agent | 관점 지시 | temperature | 출력 스타일 |
|-------------|-----------|-------------|-------------|
| draft_analytical | "분석적이고 논리적인 관점에서" | 0.4 | 구조화된 설명 |
| draft_creative | "창의적이고 비유를 활용하는 관점에서" | 0.9 | 자유로운 서술 |
| draft_structured | "비전공자도 이해할 수 있게 단계적으로" | 0.6 | 단계별 정리 |

---

## 참고 컨텍스트

### 에이전트 역할 요약 (프롬프트 작성 시 참조)

| 역할 | 목적 | 입력 | 출력 |
|------|------|------|------|
| Planner | 태스크를 하위 작업으로 분해 | TaskRequest | subtasks 리스트 |
| Draft (Analytical) | 분석적 관점의 초안 | user_message + system_prompt | 구조화된 텍스트 |
| Draft (Creative) | 창의적 관점의 초안 | user_message + system_prompt | 자유로운 텍스트 |
| Draft (Structured) | 단계별 설명 초안 | user_message + system_prompt | 번호 매긴 텍스트 |
| Critic | 3개 draft의 강점/약점 분석 | 3개 draft 텍스트 | 비교 분석 |
| Judge | 최종 품질 판정 | synthesized output | pass/rewrite/escalate |
| Rewrite | 피드백 기반 재작성 | original + feedback | 개선된 텍스트 |
| Synthesizer | 여러 draft의 장점 조합 | drafts + critic feedback | 최종 결과 |

### 프롬프트 파일 작성 규칙

- 파일 최상단에 `# Role: {역할명}` 헤더
- `## 지시사항` 섹션에 역할의 핵심 행동 지침
- `## 출력 형식` 섹션에 기대하는 출력 구조
- Markdown 포맷, 한국어 작성
- 변수 치환이 필요한 부분은 `{{variable}}` 형식 사용
