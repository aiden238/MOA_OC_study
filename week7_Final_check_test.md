# Week 7 Final Check

## 확인 항목

| 항목 | 상태 | 기준 |
|------|------|------|
| RAG 연결 | 완료 | `ChromaRetriever` 실제 연결 |
| MCP 연결 | 완료 | 공식 `mcp` SDK + stdio |
| 평가 후크 | 완료 | `--evaluate` 경로 사용 |
| 문서 정합성 | 보정 완료 | OpenAI 기본 기준으로 갱신 |

---

## 현재 기준

- 기본 provider: `OpenAI`
- 선택 provider: `Gemini`, `Grok(xAI)`
- 기본 embedding: `text-embedding-3-small`
- 실제 모델명: `.env`의 `DEFAULT_MODEL`

OpenRouter + Gemma 관련 표기는 current runtime으로 보지 않는다.

---

## 검증 포인트

1. `rag-001` 실행 시 retrieval metadata가 남는가
2. `mcp-001` 실행 시 tool trace가 남는가
3. `--evaluate` 결과가 비어 있지 않은가
4. 동일 `case_id` 재실행 시 `--output-tag`로 결과 분리가 되는가
5. 문서가 OpenAI 기본 + 선택 provider 확장 기준과 일치하는가

---

## 변경 기록

### 2026-04-20

- OpenAI 기준으로 final check 문서를 다시 정리했다.
- Gemini/Grok 선택 확장 정책을 반영했다.
