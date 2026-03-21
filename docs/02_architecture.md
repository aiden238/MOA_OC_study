# 02. 아키텍처

## 실행 경로별 비교

### Path A: Single (3주차~)

```
Input → LLM 단일 호출 → Output + Trace
```

### Path B: MOA (4주차~)

```
Input → Draft Agent ×3 (병렬)
      → Critic Agent (약점 분석)
      → Synthesizer (최종 조합)
      → Output + Trace
```

### Path C: Full (5주차~)

```
Input → Router (단순/복합 분기)
      → Planner 또는 Router 통합형 계획 단계
      → Draft Agent ×3
      → Critic Agent
      → Judge Agent (best draft 선택 / 재생성 판정)
      → [Rewrite Agent] (조건부)
      → Synthesizer
      → Output + Trace
```

### Path D: RAG+MCP (6주차)

```
Input → Router (MCP/RAG 필요 여부 판별 포함)
      → Planner 또는 Router 통합형 계획 단계
      → [RAG Retriever] (필요 시)
      → [MCP Tool Call] (필요 시)
      → Draft ×3 → Critic → Judge → [Rewrite] → Synthesizer
      → Output + Trace
```

## 모듈 구조

| 모듈 | 역할 | 위치 |
|------|------|------|
| **core** | config, logger, timer 등 공통 인프라 | `app/core/` |
| **schemas** | Pydantic으로 입출력 구조 강제 | `app/schemas/` |
| **prompts** | 역할별 시스템 프롬프트 (Markdown) | `app/prompts/` |
| **agents** | LLM 호출 최소 단위 (BaseAgent 상속) | `app/agents/` |
| **orchestrator** | 에이전트 조율 (Router, Executor, 향후 필요 시 Planner) | `app/orchestrator/` |
| **eval** | 루브릭 평가, 지표 계산, 경로 비교 | `app/eval/` |
| **rag** | 문서 검색·분할·임베딩 (6주차) | `app/rag/` |
| **mcp_client** | MCP 서버 호출 래퍼 (6주차) | `app/mcp_client/` |

## 기술 스택 요약

- **언어:** Python 3.11+
- **LLM 호출:** httpx (async)
- **스키마:** pydantic v2
- **환경변수:** python-dotenv
- **테스트:** pytest + pytest-asyncio
- **모델:** 1~5주차 단일 모델 고정 (gpt-4o-mini 또는 claude-3-5-haiku)
