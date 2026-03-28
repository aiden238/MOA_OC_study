# Week 7 Implement Notes

## 목적

Week 7 구현의 초점은 mock이 아니라 실제 동작하는 RAG와 Filesystem MCP 경로를 `run_full.py`에 연결하는 것이다.

---

## 현재 런타임 기준

- 기본 provider: `OpenAI`
- 선택 provider: `Gemini`, `Grok(xAI)`
- 기본 embedding: `text-embedding-3-small`
- 실제 기본 모델: `.env`의 `DEFAULT_MODEL`

OpenRouter + Gemma 문구는 현재 구현 기준이 아니다.

---

## 구현 메모

### RAG

- `ChromaRetriever`가 실제 검색 경로를 담당한다.
- retrieval metadata와 selected chunks를 trace 및 evaluation context에 남긴다.
- 실패 시 `SimpleRetriever` fallback을 유지한다.

### MCP

- Filesystem MCP는 공식 `mcp` Python SDK + stdio 기반이다.
- read-only whitelist와 경로 검증을 적용한다.
- tool success/failure 모두 trace에 남긴다.

### Evaluation

- `--evaluate` 사용 시 path-aware rubric을 호출한다.
- RAG는 groundedness, citation traceability를 본다.
- MCP는 tool_use_correctness, tool_result_faithfulness를 본다.

### Runtime Config

- BaseAgent는 agent name별 env override를 읽는다.
- 따라서 Draft, Critic, Judge, Eval에 서로 다른 provider/model을 줄 수 있다.

---

## 실행 기준

```bash
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id mcp-001 --evaluate --output-tag mcp
```

---

## 변경 기록

### 2026-04-20

- OpenAI 기본 구성으로 구현 메모를 정리했다.
- Gemini/Grok 혼합 사용 가능성을 runtime config 기준에 반영했다.
