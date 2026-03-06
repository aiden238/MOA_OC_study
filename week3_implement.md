# Week 3 Implement — 구현 상세

## 벤치마크 데이터 v1 구조

```json
{
  "version": "v1",
  "cases": [
    {
      "id": "sum-001",
      "type": "summarize",
      "prompt": "다음 텍스트를 3문장으로 요약하세요: [300자 텍스트]",
      "constraints": {"max_sentences": 3},
      "difficulty": "low",
      "expected_moa_advantage": "minimal"
    },
    {
      "id": "exp-001",
      "type": "explain",
      "prompt": "양자 컴퓨팅의 큐비트 개념을 중학생에게 설명하세요.",
      "constraints": {"audience": "middle_school"},
      "difficulty": "medium",
      "expected_moa_advantage": "planner_helps"
    },
    {
      "id": "ide-001",
      "type": "ideate",
      "prompt": "도시의 교통 혼잡을 줄이기 위한 창의적인 아이디어 5가지를 제시하세요.",
      "constraints": {"count": 5, "novelty": "high"},
      "difficulty": "medium",
      "expected_moa_advantage": "multi_draft_helps"
    },
    {
      "id": "crw-001",
      "type": "critique_rewrite",
      "prompt": "다음 이메일을 개선하세요: [비즈니스 이메일 초안]",
      "constraints": {"tone": "professional"},
      "difficulty": "high",
      "expected_moa_advantage": "critique_rewrite_helps"
    }
  ]
}
```

> 총 12건: 위 4종 각 3건 (001, 002, 003). 범용 주제, 도메인 지식 불필요.

---

## `scripts/run_single.py` 흐름

```
1. data/benchmarks/v1.json 로딩
2. 각 case를 TaskRequest로 변환
3. BaseAgent로 단일 LLM 호출
4. AgentOutput → TraceRecord 변환
5. RunSummary 집계
6. data/traces/{run_id}.json 저장
7. data/outputs/single_{case_id}.json 저장
8. 콘솔에 요약 출력
```

**CLI 인터페이스:**
```bash
python scripts/run_single.py                    # 전체 12건 실행
python scripts/run_single.py --case-id sum-001   # 특정 케이스만 실행
python scripts/run_single.py --repeat 3          # 3회 반복 (분산 측정)
```

---

## 평가 루브릭

### `app/eval/rubric.py`

LLM을 Judge로 사용하여 출력 품질을 1~5점으로 채점.

**채점 항목 (4항목):**

| 항목 | 설명 | 채점 기준 |
|------|------|----------|
| `clarity` | 읽기 쉬운가 | 1: 혼란스러움 → 5: 매우 명확 |
| `structure` | 논리 구조가 명확한가 | 1: 두서없음 → 5: 체계적 |
| `constraint_following` | 제약 조건을 지켰는가 | 1: 무시 → 5: 완벽 준수 |
| `usefulness` | 실제로 도움이 되는가 | 1: 무의미 → 5: 매우 유용 |

**Judge 프롬프트 구조:**
```
당신은 텍스트 품질 평가자입니다.
다음 [원래 요청]과 [생성된 결과]를 보고, 4가지 항목에 대해 1~5점으로 채점하세요.
반드시 JSON 형식으로 응답하세요: {"clarity": N, "structure": N, "constraint_following": N, "usefulness": N, "reasoning": "..."}
```

### `app/eval/metrics.py`

시스템 지표 자동 계산:

| 지표 | 계산 방법 |
|------|----------|
| `total_latency_ms` | trace의 latency_ms 합계 |
| `total_tokens` | prompt_tokens + completion_tokens 합계 |
| `total_cost_estimate` | cost_estimate 합계 |
| `avg_quality_score` | 4항목 평균 |

---

## 평가 프로토콜 (교차 검증)

1. LLM Judge가 12건 전부 자동 채점
2. 본인이 12건 중 5건을 수동 채점
3. LLM 점수와 수동 점수의 상관관계 계산
4. **상관계수 ≥ 0.7** → LLM Judge 신뢰, 이후 자동 채점만 사용
5. **상관계수 < 0.7** → 루브릭 재조정 후 재실행

---

## 참고 컨텍스트

### 벤치마크 설계 원칙

- 도메인 지식 불필요 (범용 주제만)
- 정답이 명확한 것이 아니라 **루브릭 기반 평가에 적합한** 주제
- 각 유형별 **MOA의 기대 효과가 다름** (이것이 실험의 핵심)

| 유형 | 왜 테스트하는가 | MOA 기대 효과 |
|------|----------------|--------------|
| 단순 요약 | MOA가 불필요할 수 있는 케이스 확인 | 최소 (비용만 낭비할 수 있음) |
| 구조화 설명 | Planner의 태스크 분해 효과 측정 | 중간 (Planner가 도움) |
| 창의적 아이디어 | 다중 Draft의 다양성 효과 측정 | 높음 (Draft 변이가 핵심) |
| 비판-재작성 | Critic → Rewrite 루프 효과 측정 | 높음 (피드백 루프가 핵심) |

### 비용 추정 (3주차 분)

| 항목 | 호출 수 | 추정 비용 |
|------|---------|-----------|
| Baseline 실험 (12건 × 3회) | 36 | ~$0.05 |
| 루브릭 평가 (12건) | 12 | ~$0.02 |
| **3주차 합계** | **48** | **~$0.07** |
