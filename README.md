# moa-orchestration-lab

> 단일 LLM 호출(Baseline)과 Multi-Agent Orchestration(MOA)을 비교 실험하는 6주 프로젝트

## 프로젝트 목표

- 단일 호출 baseline과 MOA 파이프라인의 품질·비용·속도 차이를 정량적으로 비교
- Router → Planner → Draft → Critic → Judge → Synthesizer 구조를 직접 설계·구현
- 6주차에 RAG·MCP를 통합하여 종합 오케스트레이션 검증
- 모든 실행을 trace/logging으로 추적하고 재현 가능하게 유지

## Non-Goals

- 범용 에이전트 완성, UI 개발, 대규모 배포
- LangChain/CrewAI 등 고수준 프레임워크 사용
- 6주 전까지 RAG/MCP/Tool Calling 도입

## 아키텍처

```
[Single Path]
  Input → LLM → Output → Trace

[MOA Path]
  Input → Router → Planner
    → Draft Agent ×3 (async)
    → Critic Agent
    → Judge Agent → (Rewrite Agent)
    → Synthesizer
    → Output → Trace

[Full Path — 6주차]
  Input → Router
    → [RAG Retriever] / [MCP Tool Call]
    → MOA Pipeline
    → Output → Trace
```

## 디렉토리 구조

```
├── docs/          # 기준 명세서 (코드보다 우선)
├── app/
│   ├── core/      # config, logger, cost_tracker
│   ├── schemas/   # Pydantic 입출력 모델
│   ├── prompts/   # 역할별 시스템 프롬프트 (.md)
│   ├── agents/    # LLM API 호출 단위
│   ├── orchestrator/  # 에이전트 조율 로직
│   ├── eval/      # 평가 루브릭·비교 엔진
│   ├── rag/       # 6주차: 문서 검색
│   └── mcp_client/# 6주차: MCP 도구 호출
├── tests/         # pytest
├── scripts/       # CLI 실행 스크립트
└── data/          # 벤치마크, 결과, trace
```

## 실행 방법

### 환경 설정
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env에 API 키 설정
```

### Baseline 실행
```bash
python scripts/run_single.py --input data/benchmarks/v1.json
```

### MOA 실행
```bash
python scripts/run_moa.py --input data/benchmarks/v1.json
```

### 결과 비교
```bash
python scripts/compare_runs.py --baseline data/traces/single/ --moa data/traces/moa/
```

## 주차별 진행

| 주차 | 주제 | 핵심 산출물 |
|------|------|------------|
| 1 | 프로젝트 뼈대 + 명세 | docs, logger, config |
| 2 | 스키마 + Base Agent + 프롬프트 | schemas, base_agent, prompts |
| 3 | Baseline 파이프라인 | run_single.py, 벤치마크, 루브릭 |
| 4 | MOA 파이프라인 (Draft+Critic+Synth) | run_moa.py, executor |
| 5 | Router + Judge/Rewrite + 분기 | router, retry_policy, run_full.py |
| 6 | MCP·RAG 통합 + 비교 실험 + 회고 | rag, mcp_client, retrospective |

## 기술 스택

- Python 3.10+
- Pydantic v2 (MIT)
- httpx (BSD-3)
- pytest (MIT)
- tenacity (Apache 2.0)
- tiktoken (MIT)
- chromadb (Apache 2.0) — 6주차
- mcp Python SDK (MIT) — 6주차

## 라이선스

MIT
