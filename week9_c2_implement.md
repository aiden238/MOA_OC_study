# Week 9 C9-2 Implement Guide — RAG/MCP Case Expansion

## 목표

현재 RAG/MCP 비교는 각 1건 기반이라 통계적 의미가 없다.  
`v1_rag_mcp.json`에 케이스를 추가해 각 3건으로 늘리고,  
Comparator의 `rag`, `mcp` 그룹 신뢰도를 확보한다.

---

## 범위

- `data/benchmarks/v1_rag_mcp.json` — **수정** (케이스 4건 추가)
- `scripts/run_full.py` — 실행만, 코드 변경 없음
- `data/outputs/` — 결과 파일 8건 추가 생성

---

## 선행 조건

- **C9-1이 완료**되어 `baseline` 그룹 `count=12`가 확인된 상태
- `.env`에 `OPENAI_API_KEY` 설정됨
- `node --version`, `npx.cmd --version` 정상 출력

---

## 구현 상세

### A. `v1_rag_mcp.json` 케이스 추가

`data/benchmarks/v1_rag_mcp.json` 파일을 아래 내용으로 교체한다.  
기존 `rag-001`, `mcp-001`은 **그대로 유지**하고 4건을 추가한다.

```json
{
  "version": "v1_rag_mcp",
  "cases": [
    {
      "id": "rag-001",
      "type": "explain",
      "prompt": "rag 자료를 참고해서 문서의 핵심 주제 3가지를 설명하라.",
      "constraints": {"source": "rag_docs"},
      "difficulty": "medium",
      "expected_moa_advantage": "rag_helps"
    },
    {
      "id": "rag-002",
      "type": "explain",
      "prompt": "RAG 문서를 바탕으로 벡터 데이터베이스의 역할과 대표 오픈소스 도구를 설명하라.",
      "constraints": {"source": "rag_docs"},
      "difficulty": "medium",
      "expected_moa_advantage": "rag_helps"
    },
    {
      "id": "rag-003",
      "type": "explain",
      "prompt": "RAG 자료를 참고해 자연어 처리에서 임베딩이 왜 중요한지 정리하라.",
      "constraints": {"source": "rag_docs"},
      "difficulty": "medium",
      "expected_moa_advantage": "rag_helps"
    },
    {
      "id": "mcp-001",
      "type": "explain",
      "prompt": "rag 자료 폴더의 파일 목록을 보여주고 어떤 파일들이 있는지 한 줄씩 정리해줘.",
      "constraints": {},
      "difficulty": "medium",
      "expected_moa_advantage": "mcp_helps"
    },
    {
      "id": "mcp-002",
      "type": "explain",
      "prompt": "docs 폴더의 파일 목록을 확인하고 각 파일이 어떤 내용을 담고 있을지 추론하라.",
      "constraints": {},
      "difficulty": "medium",
      "expected_moa_advantage": "mcp_helps"
    },
    {
      "id": "mcp-003",
      "type": "explain",
      "prompt": "data/outputs 폴더의 파일 목록을 확인하고 실험 결과가 몇 건 저장되어 있는지 정리하라.",
      "constraints": {},
      "difficulty": "medium",
      "expected_moa_advantage": "mcp_helps"
    }
  ]
}
```

**트리거 확인**:
- `rag-002`, `rag-003`: `constraints.source == "rag_docs"` → `requires_rag=True` 자동 트리거
- `mcp-002`, `mcp-003`: prompt에 "파일 목록" 키워드 → `requires_mcp=True` 자동 트리거  
  (`app/orchestrator/router.py` line 94의 `mcp_keywords` 목록 기준)

### B. RAG 추가 케이스 실행

```bash
# rag-002: moa+rag 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id rag-002 \
  --evaluate \
  --output-tag rag

# rag-002: plain moa 비교 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id rag-002 \
  --force-path moa \
  --evaluate \
  --output-tag rag_plain

# rag-003: moa+rag 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id rag-003 \
  --evaluate \
  --output-tag rag

# rag-003: plain moa 비교 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id rag-003 \
  --force-path moa \
  --evaluate \
  --output-tag rag_plain
```

### C. MCP 추가 케이스 실행

```bash
# mcp-002: moa+mcp 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id mcp-002 \
  --evaluate \
  --output-tag mcp

# mcp-002: plain moa 비교 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id mcp-002 \
  --force-path moa \
  --evaluate \
  --output-tag mcp_plain

# mcp-003: moa+mcp 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id mcp-003 \
  --evaluate \
  --output-tag mcp

# mcp-003: plain moa 비교 실행
python scripts/run_full.py \
  --benchmark v1_rag_mcp.json \
  --case-id mcp-003 \
  --force-path moa \
  --evaluate \
  --output-tag mcp_plain
```

---

## 검증 기준

### RAG 케이스 검증

각 `full_rag-00X__rag.json` 파일에서 아래를 확인한다.

| 항목 | 기준 |
|---|---|
| `path` | `"moa+rag"` |
| `context_metadata.rag_retrieval.retriever` | `"ChromaRetriever"` (SimpleRetriever 폴백 아님) |
| `context_metadata.rag_retrieval.fallback_reason` | `null` |
| `evaluation_context.selected_chunks` 길이 | `>= 1` |
| `selected_chunks[*].normalized_relevance` | `>= 0.20` |
| `evaluation.avg_score` | 숫자 |

### MCP 케이스 검증

각 `full_mcp-00X__mcp.json` 파일에서 아래를 확인한다.

| 항목 | 기준 |
|---|---|
| `path` | `"moa+mcp"` |
| `evaluation_context.tool_trace.success` | `true` |
| `evaluation_context.tool_result_summary` | 실제 파일 목록 텍스트 포함 |
| `context_metadata.mcp.server_name` | `"filesystem"` |
| `evaluation.avg_score` | 숫자 |

### Comparator 검증

```bash
python scripts/compare_runs.py --dir data/outputs --format table
```

기대 출력:

```
{'group': 'baseline', ..., 'count': 12, ...}
{'group': 'rag',      ..., 'count': 3,  ...}
{'group': 'mcp',      ..., 'count': 3,  ...}
```

빠른 검증 명령:

```bash
python -c "
import json, pathlib
for tag, path_val in [('rag', 'moa+rag'), ('mcp', 'moa+mcp')]:
    files = list(pathlib.Path('data/outputs').glob(f'*__{tag}.json'))
    print(f'{tag}: {len(files)}건')
    for f in files:
        d = json.loads(f.read_text(encoding='utf-8'))
        retriever = d.get('context_metadata', {}).get('rag_retrieval', {}).get('retriever', '-')
        success = d.get('evaluation_context', {}).get('tool_trace', {}).get('success', '-')
        score = d.get('evaluation', {}).get('avg_score', '-')
        print(f'  {f.name}: path={d[\"path\"]}, retriever/success={retriever or success}, score={score}')
"
```

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| ChromaRetriever 초기화 실패 (임베딩 API 오류) | `OPENAI_API_KEY` 확인. 실패 시 `fallback_reason`이 기록되므로 계속 진행하되 검증 기준에서 retriever 항목을 `SimpleRetriever`로 허용하고 사유를 기록 |
| MCP 세션 시작 실패 (`npx.cmd` 오류) | `node --version` 재확인. 첫 실행 시 패키지 다운로드 지연(30~60초) 정상. timeout은 `session_start_timeout_s=10` 기준이므로 재시도 |
| `normalized_relevance` 전부 0.20 미만 | `data/rag_docs/`에 문서 5건 존재하는지 확인. ChromaDB 재인덱싱 필요 시 `data/chroma/` 삭제 후 재실행 |
| mcp 케이스 `path == "moa"` (MCP 미트리거) | prompt에 "파일 목록" 키워드가 있는지 확인. 없으면 `router.py mcp_keywords` 목록과 대조 |

---

## 커밋

```bash
git add data/benchmarks/v1_rag_mcp.json
git commit -m "feat(eval): expand rag-mcp benchmark to 3 cases each"
```

`data/outputs/` 결과 파일은 C9-3에서 선별 커밋한다.

---

## 완료 기준 요약

- [ ] `v1_rag_mcp.json` 케이스 6건으로 확장
- [ ] RAG 결과 파일 `*__rag.json` 3건, 모두 `path=moa+rag`
- [ ] MCP 결과 파일 `*__mcp.json` 3건, 모두 `path=moa+mcp`, `success=true`
- [ ] Comparator `rag` 그룹 `count=3`, `mcp` 그룹 `count=3`
- [ ] `data/benchmarks/v1_rag_mcp.json` 커밋

---

## 권장 커밋 메시지

```
feat(eval): expand rag-mcp benchmark to 3 cases each
```
