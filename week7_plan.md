# Week 7 Plan

## 목적

Week 7의 목적은 mock 단계의 RAG/MCP를 실제 실행 가능한 구조로 연결하고, 그 결과를 MOA 비교 실험에 포함시키는 것이다.

---

## 현재 해석 기준

- 이 문서는 2026-04-20 기준으로 정합성 보정된 버전이다.
- 현재 기본 런타임은 `OpenAI`다.
- `Gemini`, `Grok(xAI)`는 선택 provider로 취급한다.
- 실제 모델명은 `.env`의 `DEFAULT_MODEL`을 따른다.
- 과거 OpenRouter + Gemma 문구는 철회된 시도로 본다.

---

## Week 7 범위

### C7-1

- routing 정보의 실제 전달
- 평가 컨텍스트 구조 정리
- comparator, cost tracking, trace metadata 정비

### C7-2

- `ChromaRetriever` 기반 RAG 연결
- retrieval metadata와 context injection 기록
- `SimpleRetriever` fallback 유지

### C7-3

- 공식 `mcp` Python SDK 기반 Filesystem MCP 연결
- stdio transport 사용
- whitelist + read-only 정책 유지
- tool trace / fallback trace 기록

---

## 실행 기준

### 벤치마크

- `data/benchmarks/v1.json`
- `data/benchmarks/v1_rag_mcp.json`

### CLI

- `run_single.py --benchmark ...`
- `run_moa.py --benchmark ...`
- `run_full.py --benchmark ... --evaluate --output-tag ...`

---

## 구현 해석 규칙

- Planner는 현재 코드베이스에서 독립 필수 모듈이 아니다.
- 문서의 Planner는 planning stage 또는 향후 확장 지점으로 해석한다.
- 문서 우선순위는 `AGENTS.md -> refs/tech_stack.md -> 현재 주차 문서`다.

---

## DoD

- `requires_rag=True` 케이스에서 retrieval metadata가 남는다.
- `requires_mcp=True` 케이스에서 tool trace가 남는다.
- `run_full.py --evaluate` 경로에서 `evaluation`이 비어 있지 않다.
- 문서가 current runtime과 충돌하지 않는다.

---

## 변경 기록

### 2026-04-20

- OpenAI 기본 기준으로 문서를 재정렬했다.
- Gemini/Grok 선택 확장 해석을 추가했다.
- OpenRouter + Gemma 문구를 현재 기준에서 제외했다.
