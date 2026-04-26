# Week 11 C11-1 Implement Guide — 백엔드 소스 노출 검증

## 목표

`/api/chat` 응답의 `context_metadata`에서 프론트엔드가 쉽게 파싱할 수 있도록  
RAG 청크의 **소스 파일명**과 **유사도 점수**가 포함되어 있는지 확인하고 보완한다.

---

## 선행 조건

- `python -m pytest -q` 통과 상태
- `uvicorn app.web.server:app --reload` 정상 기동
- Week 10 웹 UI에서 `moa` 경로로 최소 1턴 대화 가능

---

## 확인해야 할 사실

### A. `selected_chunks`에 source 포함 여부

`context_metadata.rag.selected_chunks` 배열의 각 원소 구조를 확인한다.

```python
# 직접 확인 스크립트
import asyncio, json
from app.schemas.chat import ChatTurnRequest
from app.services.chat_service import run_chat_turn

async def check():
    req = ChatTurnRequest(
        prompt="문서에서 MOA에 대해 설명해줘",   # rag_docs/에 있는 내용
        force_path="auto",
    )
    resp = await run_chat_turn(req)
    print("path:", resp.path)
    rag = resp.context_metadata.get("rag", {})
    print("rag keys:", list(rag.keys()))
    chunks = rag.get("selected_chunks", [])
    print("chunks sample:", chunks[:2] if chunks else "EMPTY")

asyncio.run(check())
```

**예상 결과 A — chunks에 source 포함:**
```json
[
  { "source": "doc1.txt", "score": 0.87, "text": "..." },
  { "source": "doc3.txt", "score": 0.74, "text": "..." }
]
```
→ 추가 작업 불필요. C11-2로 진행.

**예상 결과 B — chunks가 빈 배열 또는 source 없음:**
```json
[] 또는 [{ "text": "..." }]   ← source 없음
```
→ 아래 보완 작업 수행.

---

## 보완 작업: source 추출 추가

`context_metadata.rag`가 `ContextBuilder`의 `context_build` 레코드에서 옵니다.  
`app/rag/context_builder.py`와 `app/orchestrator/executor.py`의 로깅 부분을 확인합니다.

### 확인 경로

```
app/rag/context_builder.py  → build() 메서드 반환값
app/orchestrator/executor.py → _run_rag() 내 trace_logger.log() 호출부
app/services/chat_service.py → _build_context_metadata()의 rag 필드
```

### executor.py에서 source 목록 추가 (필요 시)

`executor.py`의 RAG 로깅 부분에서 `selected_chunks`에 source를 포함시킨다:

```python
# executor.py — RAG context_build 로그 기록 시
trace_logger.log(
    agent_name="rag_retriever",
    operation_type="rag",
    input_text=query,
    output_text=context_text,
    metadata={
        "stage": "context_build",
        "retriever_type": retriever_type,
        "selected_chunks": [
            {
                "source": chunk.get("source", chunk.get("metadata", {}).get("source", "unknown")),
                "score": round(chunk.get("score", 0.0), 3),
                "text_preview": chunk.get("text", "")[:80],   # 80자 미리보기
            }
            for chunk in selected
        ],
        "token_estimate": token_estimate,
        "total_chunks": len(results),
    },
)
```

### _build_context_metadata 보완 (선택 사항)

`selected_chunks`에서 source만 뽑은 `rag_sources` 리스트를 `context_metadata`에 추가하면  
프론트 파싱이 단순해진다:

```python
# chat_service.py — _build_context_metadata 내부
if context_build_record is not None:
    context_metadata["rag"] = context_build_record.get("metadata", {})

    # 프론트 편의용: source 파일명 목록 추출
    chunks = context_build_record.get("metadata", {}).get("selected_chunks", [])
    context_metadata["rag_sources"] = [
        {
            "source": c.get("source", "unknown"),
            "score":  c.get("score", 0.0),
        }
        for c in chunks
    ]
```

---

## MCP 결과 품질 확인

```python
mcp = resp.context_metadata.get("mcp", {})
print("mcp keys:", list(mcp.keys()))
print("tool_name:", mcp.get("tool_name"))
print("success:", mcp.get("success"))
summary = mcp.get("normalized_result_summary", "")
print("summary length:", len(summary))
print("summary[:200]:", summary[:200])
```

**확인 항목:**
- `tool_name`, `server_name`, `success`, `normalized_result_summary` 모두 존재 → C11-3으로 진행
- 없으면 `executor.py`의 MCP 로깅 레코드 `metadata` 키 점검

---

## 검증 기준

| 항목 | 기준 |
|------|------|
| RAG 트리거 | RAG 관련 질문으로 `path == "moa+rag"` 확인 |
| source 포함 | `context_metadata.rag_sources[].source`에 파일명 존재 |
| score 포함 | `context_metadata.rag_sources[].score`에 0~1 실수 존재 |
| MCP 구조 | `context_metadata.mcp.tool_name` 존재 |
| pytest | `python -m pytest tests/test_rag.py -q` 통과 |

---

## 완료 기준

- [ ] `context_metadata.rag_sources` 또는 `context_metadata.rag.selected_chunks[].source` 보장
- [ ] `context_metadata.mcp` 키 구조 확인 완료
- [ ] 변경한 경우 pytest 회귀 없음

---

## 커밋 (변경 사항이 있을 경우만)

```
fix(rag): expose source filenames in context_metadata for frontend
```
