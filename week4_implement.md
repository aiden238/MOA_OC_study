# Week 4 Implement — 구현 상세

## MOA 파이프라인 흐름

```
Input (TaskRequest)
  → Draft Agent A (analytical, temp=0.4)  ─┐
  → Draft Agent B (creative, temp=0.9)     ├─ asyncio.gather() 비동기 병렬
  → Draft Agent C (structured, temp=0.6)  ─┘
  → Critic Agent (3개 draft 비교 분석, 강점/약점 정리)
  → Synthesizer Agent (critic 피드백 + drafts → 최종 결과)
  → Trace Save (모든 에이전트 호출 기록)
```

---

## Draft Agent 구현

```python
# app/agents/draft_agent.py

class DraftAgent(BaseAgent):
    """특정 관점의 초안을 생성하는 에이전트"""
    
    VARIANTS = {
        "analytical": {"prompt": "draft_analytical", "temperature": 0.4},
        "creative": {"prompt": "draft_creative", "temperature": 0.9},
        "structured": {"prompt": "draft_structured", "temperature": 0.6},
    }
    
    def __init__(self, variant: str):
        config = self.VARIANTS[variant]
        prompt = self.load_prompt(config["prompt"])
        super().__init__(agent_name=f"draft_{variant}", system_prompt=prompt)
        self.temperature = config["temperature"]

async def run_all_drafts(task: TaskRequest) -> list[AgentOutput]:
    """3개 Draft Agent를 비동기 병렬 실행"""
    agents = [DraftAgent(v) for v in DraftAgent.VARIANTS]
    results = await asyncio.gather(*[a.run(...) for a in agents])
    return results
```

---

## API Rate Limit 대응

- **`asyncio.Semaphore(3)`** — 동시 호출 수 제한
- **tenacity exponential backoff** — API 429 에러 시 재시도
- **graceful degradation** — 연속 3회 실패 시 해당 draft skip, 2개로 진행

```python
semaphore = asyncio.Semaphore(3)

async def rate_limited_call(agent, input):
    async with semaphore:
        return await agent.run(input)
```

---

## Critic Agent

```python
# app/agents/critic_agent.py

class CriticAgent(BaseAgent):
    """3개 draft를 비교 분석하는 에이전트"""
    
    def __init__(self):
        prompt = self.load_prompt("critic")
        super().__init__(agent_name="critic", system_prompt=prompt)
    
    async def critique(self, drafts: list[AgentOutput]) -> AgentOutput:
        """3개 draft의 강점/약점을 비교 분석"""
        # user_message에 3개 draft를 [Draft A], [Draft B], [Draft C]로 포맷
        ...
```

**Critic 출력 구조 (프롬프트에서 강제):**
```json
{
  "draft_analyses": [
    {"draft": "A", "strengths": ["..."], "weaknesses": ["..."]},
    {"draft": "B", "strengths": ["..."], "weaknesses": ["..."]},
    {"draft": "C", "strengths": ["..."], "weaknesses": ["..."]}
  ],
  "recommendation": "A와 C의 장점을 조합하되, B의 창의적 비유를 포함",
  "key_improvements": ["..."]
}
```

---

## Synthesizer

```python
# app/orchestrator/synthesizer.py

class SynthesizerAgent(BaseAgent):
    """Critic 피드백과 drafts를 기반으로 최종 결과 생성"""
    
    def __init__(self):
        prompt = self.load_prompt("synthesizer")
        super().__init__(agent_name="synthesizer", system_prompt=prompt)
    
    async def synthesize(self, drafts: list[AgentOutput], critique: AgentOutput) -> AgentOutput:
        """drafts + critic 피드백 → 최종 조합"""
        ...
```

---

## Executor (파이프라인 실행 엔진)

```python
# app/orchestrator/executor.py

class MOAExecutor:
    """Draft → Critic → Synthesizer 파이프라인 실행"""
    
    async def execute(self, task: TaskRequest, run_id: str) -> RunSummary:
        # 1. Draft 3종 병렬 실행
        drafts = await run_all_drafts(task)
        
        # 2. Critic 분석
        critic = CriticAgent()
        critique = await critic.critique(drafts)
        
        # 3. Synthesizer 조합
        synthesizer = SynthesizerAgent()
        final = await synthesizer.synthesize(drafts, critique)
        
        # 4. Trace 저장 (모든 에이전트 호출 기록)
        # 5. RunSummary 반환
        ...
```

---

## `scripts/run_moa.py` CLI

```bash
python scripts/run_moa.py                      # 전체 12건 MOA 실행
python scripts/run_moa.py --case-id ide-001     # 특정 케이스만
python scripts/run_moa.py --repeat 3            # 3회 반복
python scripts/run_moa.py --compare             # single 결과와 나란히 비교 출력
```

---

## 다양성 테스트 (test_draft_diversity.py)

동일 입력에 대해 3개 draft의 **유사도가 충분히 낮은지** 검증:
- 단순 문자열 유사도 (SequenceMatcher)로 측정
- 3쌍(A-B, A-C, B-C)의 평균 유사도가 **0.7 이하**면 통과
- 유사도가 너무 높으면 temperature/프롬프트 조정 필요

---

## 참고 컨텍스트

### pytest-asyncio 사용 (4주차~)

```python
import pytest

@pytest.mark.asyncio
async def test_parallel_drafts():
    results = await run_all_drafts(task)
    assert len(results) == 3
```

`requirements.txt`에서 `pytest-asyncio>=0.23.0`이 이미 포함되어 있음.

### 비용 추정 (4주차 분)

| 항목 | 호출 수 | 추정 비용 |
|------|---------|-----------|
| Draft ×3 × 12건 × 3회 | 108 | ~$0.16 |
| Critic × 12건 × 3회 | 36 | ~$0.05 |
| Synthesizer × 12건 × 3회 | 36 | ~$0.05 |
| 루브릭 평가 (MOA 결과) | 36 | ~$0.05 |
| **4주차 합계** | **~216** | **~$0.31** |

### 이번 주 포함하지 않는 것

- ❌ Judge Agent — 5주차로 이동
- ❌ Rewrite Agent — 5주차로 이동
- ❌ Router — 5주차로 이동
- ❌ RAG / MCP — 6주차로 이동
