# Week 5 Implement — 구현 상세

## Judge → Rewrite 흐름

```
Synthesized Output
  → Judge Agent
     ├─ "pass"     → 최종 출력으로 확정
     ├─ "rewrite"  → Rewrite Agent → 재평가 (최대 2회 루프)
     └─ "escalate" → 로그 기록 + 사람 검토 플래그
```

---

## Judge Agent

```python
# app/agents/judge_agent.py

class JudgeAgent(BaseAgent):
    """최종 출력의 품질을 판정하는 에이전트"""
    
    def __init__(self):
        prompt = self.load_prompt("judge")
        super().__init__(agent_name="judge", system_prompt=prompt)
    
    async def judge(self, task: TaskRequest, output: AgentOutput) -> JudgeDecision:
        """pass / rewrite / escalate 판정"""
        ...
```

**Judge 출력 구조 (프롬프트에서 강제):**
```json
{
  "decision": "rewrite",
  "confidence": 0.65,
  "reasoning": "제약 조건(3문장)을 4문장으로 초과했고, 두 번째 문단의 논리 흐름이 약함",
  "improvement_hints": [
    "3문장 제한을 준수할 것",
    "두 번째 포인트의 근거를 보강할 것"
  ]
}
```

**JudgeDecision 스키마:**
```python
class JudgeDecision(BaseModel):
    decision: Literal["pass", "rewrite", "escalate"]
    confidence: float  # 0.0 ~ 1.0
    reasoning: str
    improvement_hints: list[str] = []
```

---

## Rewrite Agent

```python
# app/agents/rewrite_agent.py

class RewriteAgent(BaseAgent):
    """Judge 피드백을 기반으로 출력을 개선하는 에이전트"""
    
    def __init__(self):
        prompt = self.load_prompt("rewrite")
        super().__init__(agent_name="rewrite", system_prompt=prompt)
    
    async def rewrite(self, original: AgentOutput, feedback: JudgeDecision) -> AgentOutput:
        """원본 + Judge 피드백 → 개선된 텍스트"""
        ...
```

**Rewrite 루프 정책:**
- 최대 2회까지만 rewrite (무한 루프 방지)
- 2회 rewrite 후에도 "rewrite" 판정이면 마지막 결과를 채택하고 경고 로그
- escalate 시 즉시 중단, 사람 검토 플래그 기록

---

## Router 구현

```python
# app/orchestrator/router.py

class RoutingDecision(BaseModel):
    selected_path: Literal["single", "moa"]
    reason: str
    confidence: float  # 0.0 ~ 1.0
    requires_rag: bool = False    # 6주차 활성화
    requires_mcp: bool = False    # 6주차 활성화
```

**2단계 라우팅 전략:**

### 1단계: Rule-based 필터 (빠르고 저렴, LLM 호출 불필요)

```python
def rule_based_route(task: TaskRequest) -> RoutingDecision | None:
    # 확실한 케이스만 처리, 애매하면 None 반환
    
    if task.task_type == "summarize" and task.constraints.get("difficulty") == "low":
        return RoutingDecision(selected_path="single", reason="단순 요약", confidence=0.9)
    
    if task.task_type == "ideate":
        return RoutingDecision(selected_path="moa", reason="창의적 과제 → 다중 관점 필요", confidence=0.85)
    
    if len(task.prompt) > 500:
        return RoutingDecision(selected_path="moa", reason="긴 프롬프트 → 복합 과제 가능성", confidence=0.7)
    
    if "novelty" in str(task.constraints):
        return RoutingDecision(selected_path="moa", reason="novelty 요구 → 다양성 필요", confidence=0.8)
    
    return None  # 애매한 경우 → LLM 2차 판별
```

### 2단계: LLM 판별 (1단계에서 결정 못 한 경우만)

```python
async def llm_route(task: TaskRequest) -> RoutingDecision:
    # LLM에게 질문: "이 요청은 단일 답변으로 충분한가, 다중 관점이 필요한가?"
    # JSON 형식 응답 파싱 → RoutingDecision
    ...
```

---

## Retry Policy

```python
# app/orchestrator/retry_policy.py

class RetryPolicy:
    """API 실패·Judge escalate 등의 재시도/폴백 정책"""
    
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 30.0
    
    def should_retry(self, error: Exception, attempt: int) -> bool: ...
    def get_delay(self, attempt: int) -> float: ...
    def on_final_failure(self, error: Exception, context: dict) -> None: ...
```

---

## cost_tracker

```python
# app/core/cost_tracker.py

class CostTracker:
    """실행 비용을 토큰·달러로 집계하는 트래커"""
    
    PRICING = {
        "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
        "claude-3-5-haiku-20241022": {"prompt": 0.001, "completion": 0.005},
    }
    
    def add(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """비용 추가, 추정 비용 반환"""
        ...
    
    def summary(self) -> dict:
        """총 토큰, 총 비용, 경로별 집계 반환"""
        ...
```

---

## `scripts/run_full.py` 흐름

```
1. data/benchmarks/v1.json 로딩
2. 각 case를 TaskRequest로 변환
3. Router.route(task) → single 또는 moa 경로 결정
4-A. single → BaseAgent 단일 호출
4-B. moa → Draft×3 → Critic → Synthesizer → Judge → (Rewrite)
5. cost_tracker로 비용 집계
6. trace + output 저장
7. 경로별 요약 출력
```

**CLI 인터페이스:**
```bash
python scripts/run_full.py                     # 전체 12건, Router 자동 분기
python scripts/run_full.py --case-id exp-002    # 특정 케이스
python scripts/run_full.py --force-path moa     # 경로 강제 지정 (Router 무시)
python scripts/run_full.py --cost-report        # 비용 요약 출력
```

---

## 참고 컨텍스트

### Executor 확장 포인트 (5주차에서 준비)

4주차의 `executor.py`에 Judge/Rewrite 단계를 삽입:

```
[기존 4주차 흐름]
Draft×3 → Critic → Synthesizer

[5주차 확장]
Draft×3 → Critic → Synthesizer → Judge
  ├─ pass → 최종 출력
  ├─ rewrite → Rewrite → Judge (최대 2회)
  └─ escalate → 로그 + 플래그
```

### Router 확장 예고 (6주차)

```
[5주차: 2가지 경로]
Router → single | moa

[6주차 확장: 5가지 경로]
Router → single | moa | moa+rag | moa+mcp | moa+rag+mcp
```

### 비용 추정 (5주차 분)

| 항목 | 호출 수 | 추정 비용 |
|------|---------|-----------|
| Router (LLM 2차 판별) | ~20 | ~$0.03 |
| Judge × 12건 × 3회 | 36 | ~$0.05 |
| Rewrite (조건부, ~30%) | ~12 | ~$0.02 |
| 기존 MOA 파이프라인 | ~180 | ~$0.26 |
| **5주차 합계** | **~248** | **~$0.36** |
