# Week 6 Implement — 구현 상세

## RAG 파이프라인

### 전체 흐름

```
샘플 문서 (data/rag_docs/)
  → Chunker (문서 분할, ~500자 단위)
  → Embedder (임베딩 생성)
  → ChromaDB (벡터 저장)

사용자 질의
  → Retriever (ChromaDB에서 관련 청크 검색, top-k=3)
  → 검색된 컨텍스트를 Draft Agent의 user_message에 주입
  → 기존 MOA 파이프라인 실행
```

### `app/rag/chunker.py`

```python
class SimpleChunker:
    """문서를 고정 크기 청크로 분할"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> list[str]:
        """텍스트를 겹치는 청크로 분할"""
        ...
```

### `app/rag/embedder.py`

```python
class Embedder:
    """텍스트를 임베딩 벡터로 변환"""
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """LLM API의 임베딩 엔드포인트 호출"""
        ...
```

> ChromaDB의 내장 임베딩 함수를 사용하면 별도 임베딩 호출 불필요. 구현 시 판단.

### `app/rag/retriever.py`

```python
class SimpleRetriever:
    """ChromaDB 기반 최소 검색기"""
    
    def __init__(self, collection_name: str = "rag_docs"):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def add_documents(self, docs: list[str], metadatas: list[dict] | None = None):
        """문서 청크를 벡터 DB에 저장"""
        ...
    
    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """질의에 관련된 청크 반환"""
        ...
```

### RAG용 벤치마크 추가 (4건)

기존 v1.json의 12건에 RAG가 필요한 케이스 4건 추가:

```json
{
  "id": "rag-001",
  "type": "explain",
  "prompt": "제공된 문서를 기반으로 [특정 개념]을 설명하세요.",
  "constraints": {"source": "rag_docs", "must_cite": true},
  "difficulty": "medium",
  "expected_moa_advantage": "rag_context_helps",
  "requires_rag": true
}
```

### 샘플 문서 (data/rag_docs/)

5건의 간단한 텍스트 문서:
- 범용 주제 (도메인 지식 불필요)
- 각 문서 500~1000자
- RAG 벤치마크의 질의에 관련된 내용 포함

---

## MCP 클라이언트

```python
# app/mcp_client/client.py

class MCPClient:
    """MCP 서버에 도구 호출을 보내는 최소 클라이언트"""
    
    async def list_tools(self, server_url: str) -> list[dict]:
        """서버에서 사용 가능한 도구 목록 조회"""
        ...
    
    async def call_tool(self, server_url: str, tool_name: str, args: dict) -> dict:
        """특정 도구 실행"""
        ...
```

**최소 연결 목표:** 1개 MCP 서버(예: 파일시스템 또는 웹검색)에 연결하여 도구 호출 성공

---

## Router 확장 (5경로)

**라우팅 분기 (6주차 최종):**

```
Router 판별 결과:
  ├─ path: single              → 단일 호출
  ├─ path: moa                 → 기존 MOA 파이프라인
  ├─ path: moa + rag           → RAG 검색 → 컨텍스트 포함 MOA
  ├─ path: moa + mcp           → MCP 도구 호출 결과 → MOA
  └─ path: moa + rag + mcp     → 풀 파이프라인
```

**RAG 필요 판별 기준 (Rule-based):**
- `constraints`에 `"source": "rag_docs"` 포함 → `requires_rag = True`
- prompt에 "문서 기반", "자료를 참고하여" 등 키워드 → LLM에게 확인

**MCP 필요 판별 기준 (Rule-based):**
- prompt에 "현재 날씨", "파일 목록", "웹 검색" 등 외부 도구 필요 키워드 → `requires_mcp = True`

---

## Executor 확장 (RAG/MCP 주입 포인트)

```python
# executor.py 확장

async def execute(self, task: TaskRequest, routing: RoutingDecision, run_id: str):
    context_parts = []
    
    # RAG 컨텍스트 주입
    if routing.requires_rag:
        retriever = SimpleRetriever()
        rag_chunks = retriever.query(task.prompt, n_results=3)
        context_parts.append(f"[참고 문서]\n{''.join(rag_chunks)}")
    
    # MCP 도구 결과 주입
    if routing.requires_mcp:
        mcp = MCPClient()
        tool_result = await mcp.call_tool(...)
        context_parts.append(f"[도구 호출 결과]\n{tool_result}")
    
    # 기존 파이프라인에 enriched context 전달
    enriched_message = task.prompt + "\n\n" + "\n".join(context_parts)
    ...
```

---

## 비교 실험 프레임워크

### `app/eval/comparator.py`

```python
class Comparator:
    """경로별 결과를 비교하는 엔진"""
    
    def compare(self, runs: dict[str, list[RunSummary]]) -> ComparisonTable:
        """
        runs = {
            "single": [...],
            "moa": [...],
            "moa_rag": [...],
            "moa_mcp": [...]
        }
        → 비교 테이블 생성
        """
        ...
```

### `scripts/compare_runs.py`

```bash
python scripts/compare_runs.py                  # 전체 비교 테이블 출력
python scripts/compare_runs.py --format csv      # CSV로 내보내기
python scripts/compare_runs.py --type ideate     # 특정 유형만 비교
```

### 최종 비교 테이블 (산출물)

```
| case_id | type      | single | moa  | delta | single_cost | moa_cost | cost_ratio | latency_ratio |
|---------|-----------|--------|------|-------|-------------|----------|------------|---------------|
| sum-001 | summarize | 4.2    | 4.0  | -0.2  | $0.002      | $0.012   | 6.0x       | 3.2x          |
| ide-001 | ideate    | 3.1    | 4.5  | +1.4  | $0.003      | $0.018   | 6.0x       | 3.5x          |
| crw-001 | critique  | 3.5    | 4.3  | +0.8  | $0.003      | $0.020   | 6.7x       | 4.1x          |
| rag-001 | explain   | —      | 4.1  | —     | —           | $0.025   | —          | —             |
```

---

## 회고 문서 (`docs/07_retrospective.md`)

필수 포함 항목:
1. **가설 검증 결과** — "어떤 태스크에서 MOA가 유리했는가"를 데이터로 증명
2. **비용 대비 효과** — MOA의 품질 개선이 비용 증가를 정당화하는가
3. **아키텍처 평가** — Router/Planner/Draft/Critic/Judge 각 단계의 기여도
4. **실패 사례 분석** — MOA가 오히려 나빴던 케이스와 원인
5. **개선 방향** — 6주 이후 확장 시 우선순위
6. **기획서 대비 실제** — 기획서의 예측과 실제 결과의 차이
