# Week 8 Plan

## 목표

Week 8의 목적은 Week 7에서 구현된 RAG/MCP 경로를 실제로 실행해 증거를 남기고, 평가와 문서 정합성을 current runtime 기준으로 마무리하는 것이다.

---

## 현재 기준

- 기본 provider: `OpenAI`
- 선택 provider: `Gemini`, `Grok(xAI)`
- 호출 방식: chat completions 기반 OpenAI-compatible API
- 실제 기본 모델명: `.env`의 `DEFAULT_MODEL`
- 기본 임베딩 경로: OpenAI `text-embedding-3-small`

OpenRouter + Gemma 관련 문구는 철회된 시도로 보고 현재 기준에 사용하지 않는다.

---

## Week 8 작업 축

### W8-1. 실주행 검증

- `rag-001` 실행
- `mcp-001` 실행
- output / trace 확보

### W8-2. 평가 확인

- `--evaluate` 경로에서 `evaluation`이 비어 있지 않은지 검증
- RAG/MCP path-specific metric이 결과 JSON에 반영되는지 확인

### W8-3. 비교 실험 준비

- plain `moa`와 `moa+rag`, `moa`와 `moa+mcp`를 비교할 수 있게 결과 파일을 분리 저장
- `--output-tag` 사용

### W8-4. 문서 정합성 마감

- AGENTS, claude, refs, README, week 문서의 현재 기준 정렬
- 이후 Claude가 과거 OpenRouter 문구를 현재 기준으로 오해하지 않게 유지

---

## 권장 실행 명령

### RAG

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --force-path moa --evaluate --output-tag rag_plain
```

### MCP

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --evaluate --output-tag mcp
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --force-path moa --evaluate --output-tag mcp_plain
```

### 비교

```bash
python scripts/compare_runs.py --dir data/outputs --format table
```

---

## 혼합 provider 실험 메모

- 기본 경로는 OpenAI로 둔다.
- Draft 일부를 Gemini나 Grok로 바꾸려면 agent-level env override를 사용한다.
- 평가와 최종 판단은 OpenAI에 두고, 초안 생성만 다중 provider로 실험하는 구성이 가장 해석이 쉽다.

---

## 현재 진행 상태

기준 시각: 2026-04-20

- OpenRouter 기준 복구 작업은 완료됐다.
- 현재 런타임 기준 문서는 OpenAI 기본 + Gemini/Grok 선택 확장으로 정렬됐다.
- `data/benchmarks/v1_rag_mcp.json`은 준비돼 있다.
- `OPENAI_API_KEY` 확인 후 Week 8 실주행 4건을 완료했다.
- `data/outputs/`에 실주행 결과 4건이 저장됐다.
- `data/traces/`에 현재 기준 trace 4건이 저장됐다.
- GPT-5 계열 chat completions 호환성 패치를 적용했다.
- `compare_runs.py` import 경로 버그를 수정했다.

### 현재 블로커

- 없음

### 확보된 산출물

- `data/outputs/full_rag-001__rag.json`
- `data/outputs/full_mcp-001__mcp.json`
- `data/outputs/full_rag-001__rag_plain.json`
- `data/outputs/full_mcp-001__mcp_plain.json`

### 실주행 검증 결과

- `rag-001`
  - path: `moa+rag`
  - retriever: `ChromaRetriever`
  - fallback: 없음
  - evaluation avg_score: `4.0`
- `mcp-001`
  - path: `moa+mcp`
  - server: `filesystem`
  - tool: `list_directory`
  - success: `true`
  - evaluation avg_score: `4.0`

### 비교 결과

- rag group
  - `avg_score_delta=2.25`
  - `avg_latency_delta=9434.95`
  - `avg_tokens_delta=5759.0`
- mcp group
  - `avg_score_delta=0.25`
  - `avg_latency_delta=-5101.43`
  - `avg_tokens_delta=-1516.0`

### 현재 구현 범위 해석

이미 구현 및 검증됨:

- OpenAI 기본 런타임
- Gemini/Grok override 구성
- GPT-5 chat completions 호환성
- `moa+rag` 실주행
- `moa+mcp` 실주행
- plain `moa` 비교
- 비교표 산출

아직 후속 작업으로 남음:

- mixed-provider 실험 실제 수행
- GPT-5 pricing 반영
- evidence를 git에 포함할지 정책 결정

### 현재 선택지

1. 현재 결과를 Week 8 baseline으로 고정하고 커밋/푸시
2. mixed-provider 실험을 추가 수행
3. 비용/운영 정합성 보강

### 블로커 해소 후 즉시 실행할 명령

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --evaluate --output-tag mcp
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --force-path moa --evaluate --output-tag rag_plain
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --force-path moa --evaluate --output-tag mcp_plain
python scripts/compare_runs.py --dir data/outputs --format table
```

---

## DoD

- `moa+rag` 실주행 output/trace 1건 이상 확보
- `moa+mcp` 실주행 output/trace 1건 이상 확보
- 평가 결과가 비어 있지 않음
- 문서가 OpenAI 기본 + Gemini/Grok 선택 확장 기준으로 정리됨

---

## 변경 기록

### 2026-04-20

- Week 8 계획 문서를 OpenAI 기본 기준으로 복구했다.
- Gemini/Grok 혼합 사용 메모를 추가했다.
- OpenRouter + Gemma 기준 문구를 제거했다.
- OpenAI 키 확인 후 Week 8 실주행 4건과 비교 결과를 반영했다.
- 현재 구현 범위와 후속 선택지를 추가했다.
