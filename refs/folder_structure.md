# 폴더 구조

```text
MOA_OC_study/
├── AGENTS.md
├── claude.md
├── README.md
├── requirements.txt
├── env.example
├── refs/
│   ├── tech_stack.md
│   ├── folder_structure.md
│   └── eval_framework.md
├── docs/
│   ├── 00_project_goal.md
│   ├── 01_scope_and_nongoals.md
│   ├── 02_architecture.md
│   ├── 03_agent_roles.md
│   ├── 04_routing_rules.md
│   ├── 05_eval_metrics.md
│   ├── 06_experiment_log.md
│   ├── 07_retrospective.md
│   └── 08_mcp_rag_integration.md
├── week*_plan.md
├── week*_implement.md
├── app/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── critic_agent.py
│   │   ├── draft_agent.py
│   │   ├── judge_agent.py
│   │   ├── rewrite_agent.py
│   │   └── synthesizer_agent.py
│   ├── core/
│   │   ├── config.py
│   │   ├── cost_tracker.py
│   │   ├── logger.py
│   │   └── timer.py
│   ├── eval/
│   │   ├── comparator.py
│   │   ├── metrics.py
│   │   └── rubric.py
│   ├── mcp_client/
│   │   └── client.py
│   ├── orchestrator/
│   │   ├── executor.py
│   │   ├── retry_policy.py
│   │   ├── router.py
│   │   └── synthesizer.py
│   ├── prompts/
│   ├── rag/
│   │   ├── chunker.py
│   │   ├── context_builder.py
│   │   ├── embedder.py
│   │   └── retriever.py
│   └── schemas/
├── scripts/
│   ├── compare_runs.py
│   ├── run_full.py
│   ├── run_moa.py
│   └── run_single.py
├── tests/
└── data/
    ├── benchmarks/
    │   ├── v1.json
    │   └── v1_rag_mcp.json
    ├── outputs/
    ├── rag_docs/
    └── traces/
```

---

## 주의할 점

- `.env`는 로컬 전용이며 git 추적 대상이 아니다.
- `data/outputs/`, `data/traces/`, `data/chroma/`는 기본적으로 gitignore 대상이다.
- 현재 코드베이스에는 독립 `app/orchestrator/planner.py`가 없다. 문서의 Planner는 planning stage 또는 향후 확장 포인트로 해석한다.
- 실행 스크립트는 `--benchmark`를 사용한다.

---

## 변경 기록

### 2026-04-20

- 실제 폴더 구조 기준으로 정리했다.
- `v1_rag_mcp.json`를 벤치마크 구조에 추가했다.
- planner 관련 과거 문서 해석 규칙을 명시했다.
