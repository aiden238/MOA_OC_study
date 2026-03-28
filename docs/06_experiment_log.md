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

- `rag-001`
  - output: `data/outputs/full_rag-001__rag.json`
  - trace: `data/traces/2cd3a598934c.json`
  - path: `moa+rag`
  - evaluation avg_score: `4.0`
  - retriever: `ChromaRetriever`
- `mcp-001`
  - output: `data/outputs/full_mcp-001__mcp.json`
  - trace: `data/traces/6750c520220f.json`
  - path: `moa+mcp`
  - tool: `filesystem:list_directory`
  - evaluation avg_score: `4.0`
- plain moa
  - `data/outputs/full_rag-001__rag_plain.json`
  - `data/outputs/full_mcp-001__mcp_plain.json`

### 비교표 요약

- rag: `avg_score_delta=2.25`, `avg_latency_delta=9434.95`, `avg_tokens_delta=5759.0`
- mcp: `avg_score_delta=0.25`, `avg_latency_delta=-5101.43`, `avg_tokens_delta=-1516.0`

### 해석 메모

- 현재 상태는 Week 8 baseline snapshot으로 쓸 수 있다.
- mixed-provider는 아직 실행하지 않았으므로 결과 비교 대상에 포함하지 않는다.
- GPT-5 비용 계산은 미정이므로 현재 cost 숫자는 운영용 참고값이 아니다.

### 다음 실행 순서

1. 산출물 검토 후 필요 시 mixed-provider 실험 분기 추가
2. 결과를 커밋 단위로 정리
