# 06. Experiment Log

실험 결과와 실험 운영 기준의 변경 기록을 남긴다.

---

## 기록 원칙

- 실험 조건이 바뀌면 날짜와 이유를 남긴다.
- 모델, 프로바이더, CLI, 벤치마크 구조가 바뀌면 문서 정합성 변경도 함께 기록한다.
- 현재 실행 기준은 `AGENTS.md`와 `refs/tech_stack.md`를 우선한다.

---

## 2026-04-20 - OpenAI 기준 복구

### 배경

- OpenRouter + Gemma 기준으로 문서를 정렬했던 시도가 있었다.
- 사용 결정에 따라 해당 전환은 철회됐다.
- 이후 기본 런타임은 다시 OpenAI로 유지하고, Gemini/Grok는 선택 확장으로 다루기로 했다.

### 반영 내용

- 기본 provider를 OpenAI로 복구했다.
- Gemini와 Grok를 agent-level override로 혼합 사용할 수 있게 config 기준을 정리했다.
- OpenRouter 문구를 현재 기준에서 제외했다.

### 반영 문서

- `AGENTS.md`
- `claude.md`
- `refs/tech_stack.md`
- `README.md`
- `docs/02_architecture.md`
- `week7_plan.md`
- `week7_implement.md`
- `week7_Final_check_test.md`
- `week8_plan.md`

### 메모

- 과거 OpenRouter 관련 기록은 historical note로만 남기고 current runtime 해석에는 사용하지 않는다.

---

## 2026-04-20 - Week 8 실주행 착수 상태

### 확인 결과

- OpenAI 기본 런타임 복구 후 Week 8 실주행을 시작했다.
- `.env` 기준 모델은 `gpt-5-nano-2025-08-07`로 확인됐다.
- 초기 실행에서 GPT-5 계열이 `max_tokens`를 받지 않고, `temperature`도 기본값만 허용한다는 점을 확인했다.
- 이에 따라 `BaseAgent`를 GPT-5 chat completions 호환 payload로 수정했다.
- Judge와 Rubric, Router fallback에는 `response_format={"type":"json_object"}`를 추가했다.
- `compare_runs.py`의 `app` import 경로 버그도 수정했다.

### 현재 상태 판정

- 코드/문서 정렬: 완료
- 실주행 전제 확인: 완료
- Week 8 실주행: 완료
- 비교 실행: 완료

### 실주행 결과

- 초기 baseline 이후 운영 보강 플랜으로 GPT-5 pricing을 반영했다.
- `gpt-5-nano`가 rubric JSON을 불안정하게 내는 케이스가 있어 baseline evidence는 `EVAL_MODEL=gpt-4o-mini` override로 재생성했다.
- `rag-001`
  - output: `data/outputs/full_rag-001__rag.json`
  - trace: `data/traces/07b86f000d65.json`
  - path: `moa+rag`
  - evaluation avg_score: `5.0`
  - retriever: `ChromaRetriever`
  - cost_estimate: `0.002898`
- `mcp-001`
  - output: `data/outputs/full_mcp-001__mcp.json`
  - trace: `data/traces/93f21b91632d.json`
  - path: `moa+mcp`
  - tool: `filesystem:list_directory`
  - evaluation avg_score: `5.0`
  - cost_estimate: `0.000812`
- plain moa
  - `data/outputs/full_rag-001__rag_plain.json`
  - trace: `data/traces/18736d207748.json`
  - avg_score: `4.0`
  - cost_estimate: `0.002702`
  - judge_model: `gpt-4o-mini-2024-07-18`
  - `data/outputs/full_mcp-001__mcp_plain.json`
  - trace: `data/traces/ce8019b6d68f.json`
  - avg_score: `1.0`
  - cost_estimate: `0.002076`
  - judge_model: `gpt-4o-mini-2024-07-18`

### 비교표 요약

- rag: `avg_score_delta=1.0`, `avg_cost_delta=0.000196`, `avg_latency_delta=152.23`, `avg_tokens_delta=768.0`
- mcp: `avg_score_delta=4.0`, `avg_cost_delta=-0.001264`, `avg_latency_delta=-12806.22`, `avg_tokens_delta=-5964.0`

### 해석 메모

- 현재 상태는 Week 8 baseline snapshot으로 쓸 수 있다.
- mixed-provider는 아직 실행하지 않았고 현재 `.env`에는 관련 provider key가 없다.
- GPT-5 비용 계산은 반영 완료 상태다.
- 구조화 evaluation은 현재 기준으로 `gpt-4o-mini` override가 더 안정적이었다.

### 다음 실행 순서

1. 산출물 검토 후 필요 시 mixed-provider 실험 분기 추가
2. 결과를 커밋 단위로 정리

---

## Week 9 실험 결과 (2026-04-20)

### 실험 환경

- 기본 모델: `.env`의 `DEFAULT_MODEL` (`gpt-5-nano-2025-08-07`)
- 임베딩: `text-embedding-3-small`
- 벤치마크: `v1.json` (12케이스, baseline용), `v1_rag_mcp.json` (6케이스, RAG/MCP용)
- 평가 모델: `EVAL_MODEL` (`gpt-4o-mini`)
- 비교표: `data/outputs/comparison_w9_final.csv`

### Baseline 비교 (single vs moa, n=12)

| 지표 | 값 |
|---|---|
| avg_score_delta | -0.277778 |
| avg_cost_delta | +0.001538 |
| avg_latency_delta | +20539.32 ms |
| avg_tokens_delta | +7293.08 |

해석: 12케이스 평균에서 MOA가 single 대비 품질 점수가 약 -0.28 낮고 비용은 약 25배, 지연은 +20초 가까이 증가했다. 단순 요약/설명/아이디에이션처럼 짧은 응답이 충분한 케이스에서는 MOA의 critic→rewrite 루프가 비용 대비 이득을 내지 못한다는 경향이 관찰된다. (n=12, 통계적 단정은 불가)

### RAG 비교 (moa vs moa+rag, n=3)

| 지표 | 값 |
|---|---|
| avg_score_delta | +0.125 |
| avg_cost_delta | +0.000143 |
| avg_latency_delta | -1919.56 ms |

해석: RAG 주입은 평균 점수를 소폭 끌어올리고(+0.13), 비용 증가도 미미하다. 모든 3건이 `ChromaRetriever`로 정상 검색되었고 fallback은 발생하지 않았다. 다만 plain moa가 동일 프롬프트에서도 일부 점수를 받아 격차가 작게 나타났다. (n=3, 경향 관찰)

### MCP 비교 (moa vs moa+mcp, n=3)

| 지표 | 값 |
|---|---|
| avg_score_delta | +2.75 |
| avg_cost_delta | -0.000021 |
| avg_latency_delta | -1720.11 ms |

해석: 파일 목록 조회와 같이 외부 사실이 필요한 케이스에서 MCP 경로가 plain moa 대비 평균 +2.75점의 큰 격차로 우위를 보였다. plain moa는 데이터 부재로 judge가 escalate→채점 실패 사례가 많았고, MCP는 3건 모두 `success=true`로 안정 동작했다. (n=3, 경향 관찰)

### 핵심 발견

1. MOA의 단순 우위는 자동 보장되지 않는다 — baseline 12케이스에서는 single이 비용·지연·품질 모두에서 더 효율적이었다.
2. RAG는 비용 대비 품질 향상이 작지만 안정적이며, ChromaRetriever fallback이 한 번도 발생하지 않을 만큼 인덱스가 안정적으로 동작했다.
3. MCP는 외부 사실이 응답 품질을 좌우하는 케이스에서 가장 큰 효과(+2.75)를 보였고, 도구 부재 시 judge escalate가 빈번해 plain moa는 사실상 응답 불가에 가까웠다.

### 한계

- 케이스 수: baseline 12, rag/mcp 각 3 — 통계적 결론 단정 불가, 경향 관찰 수준.
- 단일 도메인 벤치마크 (범용 텍스트, 파일 목록) — 코드/수학/장문 등은 미포함.
- 평가 모델(`gpt-4o-mini`)과 생성 모델(`gpt-5-nano`)이 OpenAI 동일 계열 — 평가 편향 가능성.
- baseline 12건 중 일부 케이스에서 judge가 `clarity=null/not_evaluable`로 응답해 `avg_score=None`으로 기록됨. comparator는 양측 모두 점수가 있는 페어만 평균에 반영.
- MCP 케이스가 plain moa에서 데이터 부재로 escalate되는 비율이 높아 점수 격차가 다소 과대 평가됐을 수 있음.

### 운영 변경 메모

- `scripts/run_full.py`에 judge 채점 실패 시 1회 재시도 + 실패해도 케이스를 `evaluation={error,...}`로 기록하고 sweep을 계속 진행하도록 보강했다.
- `data/benchmarks/v1_rag_mcp.json`을 6케이스로 확장했다(rag-002/003, mcp-002/003 추가).
- 대표 증거: `data/outputs/full_rag-001__rag.json`, `data/outputs/full_mcp-001__mcp.json`, 비교표 CSV `data/outputs/comparison_w9_final.csv`를 git에 force-add 했다.


