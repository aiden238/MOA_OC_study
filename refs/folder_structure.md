# 폴더 구조

```
moa-orchestration-lab/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── claude.md                      # 프로젝트 전역 AI 인스트럭션
├── refs/                          # 세부 지침 (claude.md에서 분리)
│   ├── tech_stack.md
│   ├── folder_structure.md
│   └── eval_framework.md
├── week*_plan.md                  # 주차별 계획 컨텍스트
├── week*_implement.md             # 주차별 구현 상세
│
├── docs/                          # 기준 명세서 (코드보다 우선)
│   ├── 00_project_goal.md
│   ├── 01_scope_and_nongoals.md
│   ├── 02_architecture.md
│   ├── 03_agent_roles.md
│   ├── 04_routing_rules.md
│   ├── 05_eval_metrics.md
│   ├── 06_experiment_log.md
│   ├── 07_retrospective.md
│   └── 08_mcp_rag_integration.md
│
├── app/
│   ├── __init__.py
│   ├── core/                      # 공통 설정·유틸
│   │   ├── config.py              # dotenv 로딩, 모델 설정
│   │   ├── logger.py              # JSON trace 로거
│   │   ├── cost_tracker.py        # 토큰·비용 집계
│   │   └── timer.py               # 레이턴시 측정 데코레이터
│   │
│   ├── schemas/                   # Pydantic 모델
│   │   ├── task.py                # TaskRequest, TaskPlan
│   │   ├── agent_io.py            # AgentInput, AgentOutput
│   │   └── trace.py               # TraceRecord, RunSummary
│   │
│   ├── prompts/                   # 역할별 시스템 프롬프트 (.md)
│   │   ├── planner.md
│   │   ├── draft_analytical.md
│   │   ├── draft_creative.md
│   │   ├── draft_structured.md
│   │   ├── critic.md
│   │   ├── judge.md
│   │   ├── rewrite.md
│   │   └── synthesizer.md
│   │
│   ├── agents/                    # LLM 호출 최소 단위
│   │   ├── base_agent.py          # httpx + pydantic 래퍼
│   │   ├── draft_agent.py
│   │   ├── critic_agent.py
│   │   ├── judge_agent.py
│   │   ├── rewrite_agent.py
│   │   └── synthesizer_agent.py
│   │
│   ├── orchestrator/              # 에이전트 조율 로직
│   │   ├── router.py              # single / moa / rag / mcp 분기
│   │   ├── planner.py             # 태스크 분해
│   │   ├── executor.py            # 파이프라인 실행 엔진
│   │   ├── synthesizer.py         # 최종 조합
│   │   └── retry_policy.py        # 재시도·폴백 정책
│   │
│   ├── rag/                       # 6주차
│   │   ├── retriever.py
│   │   ├── chunker.py
│   │   └── embedder.py
│   │
│   ├── mcp_client/                # 6주차
│   │   └── client.py
│   │
│   └── eval/                      # 평가 로직
│       ├── metrics.py
│       ├── rubric.py
│       └── comparator.py
│
├── tests/
│   ├── test_schemas.py
│   ├── test_base_agent.py
│   ├── test_router.py
│   ├── test_critic.py
│   ├── test_synthesizer.py
│   ├── test_pipeline_single.py
│   ├── test_pipeline_moa.py
│   └── test_rag.py
│
├── scripts/
│   ├── run_single.py              # baseline 실행
│   ├── run_moa.py                 # MOA 파이프라인 실행
│   ├── run_full.py                # Router → 자동 분기 실행
│   └── compare_runs.py            # 결과 비교 스크립트
│
└── data/
    ├── benchmarks/v1.json
    ├── traces/                    # gitignore 대상
    ├── outputs/
    └── rag_docs/                  # 6주차
```
