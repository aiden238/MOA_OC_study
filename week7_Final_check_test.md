# Week 7 — Final Check & Test Report

> 작성일: 2026-04-18  
> 목적: 1~6주차 전체 구현 상태 점검 + 실제 테스트에 필요한 사항 정리

---

## 1. 전체 테스트 결과 요약

```
pytest tests/ -v
====== 116 passed in 0.34s ======
```

| 테스트 파일 | 테스트 수 | 상태 | 대상 모듈 |
|------------|----------|------|----------|
| `test_logger.py` | 8 | ✅ 전체 통과 | config, logger, timer |
| `test_schemas.py` | 10 | ✅ 전체 통과 | task.py, agent_io.py, trace.py |
| `test_base_agent.py` | 7 | ✅ 전체 통과 | base_agent.py |
| `test_draft_diversity.py` | 6 | ✅ 전체 통과 | draft_agent.py |
| `test_critic.py` | 4 | ✅ 전체 통과 | critic_agent.py |
| `test_synthesizer.py` | 4 | ✅ 전체 통과 | synthesizer.py |
| `test_judge.py` | 11 | ✅ 전체 통과 | judge_agent.py, rewrite_agent.py |
| `test_eval.py` | 10 | ✅ 전체 통과 | metrics.py, rubric.py |
| `test_router.py` | 14 | ✅ 전체 통과 | router.py, retry_policy.py |
| `test_pipeline_single.py` | 9 | ✅ 전체 통과 | run_single.py |
| `test_pipeline_moa.py` | 7 | ✅ 전체 통과 | executor.py, run_moa.py |
| `test_rag.py` | 3 | ✅ 전체 통과 | chunker, embedder, retriever |
| `test_run_full.py` | 8 | ✅ 전체 통과 | run_full.py (Mock 시범 실행) |

---

## 2. 주차별 구현 상태 점검

### 1주차 — 프로젝트 인프라

| 산출물 | 파일 | 상태 |
|--------|------|------|
| 전역 설정 | `app/core/config.py` | ✅ .env 로딩, 환경변수 관리 |
| JSON 트레이스 로거 | `app/core/logger.py` | ✅ run_id 생성, 레코드 기록, JSON 저장 |
| 레이턴시 타이머 | `app/core/timer.py` | ✅ sync/async measure_time 데코레이터 |
| 프로젝트 문서 | `docs/00~02` | ✅ 목표, 범위, 아키텍처 명세 |

### 2주차 — 스키마 & 에이전트 기반

| 산출물 | 파일 | 상태 |
|--------|------|------|
| TaskRequest / TaskPlan | `app/schemas/task.py` | ✅ pydantic v2 스키마 |
| AgentInput / AgentOutput | `app/schemas/agent_io.py` | ✅ LLM 입출력 정형화 |
| TraceRecord / RunSummary | `app/schemas/trace.py` | ✅ 실행 추적 스키마 |
| BaseAgent | `app/agents/base_agent.py` | ✅ httpx + OpenAI API 래퍼 |
| 시스템 프롬프트 | `app/prompts/*.md` | ✅ 역할별 8개 프롬프트 파일 |

### 3주차 — 벤치마크 & 평가

| 산출물 | 파일 | 상태 |
|--------|------|------|
| 벤치마크 v1 | `data/benchmarks/v1.json` | ✅ 12건 (4유형 × 3난이도) |
| Single 실행기 | `scripts/run_single.py` | ✅ CLI + 결과 JSON 저장 |
| 평가 메트릭 | `app/eval/metrics.py` | ✅ 품질·시스템 지표 |
| LLM 루브릭 | `app/eval/rubric.py` | ✅ LLM 기반 자동 평가 |
| 재시도 정책 | `app/orchestrator/retry_policy.py` | ✅ 지수 백오프 + 폴백 |

### 4주차 — MOA 파이프라인

| 산출물 | 파일 | 상태 |
|--------|------|------|
| Draft Agent × 3 | `app/agents/draft_agent.py` | ✅ analytical/creative/structured |
| Critic Agent | `app/agents/critic_agent.py` | ✅ 비교 분석 |
| Synthesizer | `app/orchestrator/synthesizer.py` | ✅ 최종 종합 |
| MOA Executor | `app/orchestrator/executor.py` | ✅ 파이프라인 실행 엔진 |
| MOA 실행기 | `scripts/run_moa.py` | ✅ CLI + 비교 출력 |

### 5주차 — Router & Judge

| 산출물 | 파일 | 상태 |
|--------|------|------|
| Router | `app/orchestrator/router.py` | ✅ 2단계 하이브리드 (Rule + LLM) |
| Judge Agent | `app/agents/judge_agent.py` | ✅ pass/rewrite/escalate 판정 |
| Rewrite Agent | `app/agents/rewrite_agent.py` | ✅ 피드백 기반 개선 |
| CostTracker | `app/core/cost_tracker.py` | ✅ 토큰·비용 집계 |
| Full Pipeline | `scripts/run_full.py` | ✅ Router → single/moa 자동 분기 |

### 6주차 — RAG & MCP

| 산출물 | 파일 | 상태 |
|--------|------|------|
| Chunker | `app/rag/chunker.py` | ✅ 고정 크기 문자 분할 |
| Embedder | `app/rag/embedder.py` | ✅ SHA256 해시 기반 (플레이스홀더) |
| Retriever | `app/rag/retriever.py` | ✅ 단어 중복 기반 검색 |
| MCP Client | `app/mcp_client/client.py` | ✅ mock:// 시뮬레이션 지원 |
| Router 확장 | `app/orchestrator/router.py` | ✅ requires_rag / requires_mcp 플래그 |
| Executor 확장 | `app/orchestrator/executor.py` | ✅ RAG/MCP 컨텍스트 주입 |
| Comparator | `app/eval/comparator.py` | ✅ 경로별 비교 분석 |
| compare_runs | `scripts/compare_runs.py` | ✅ CLI 비교 도구 |
| 샘플 문서 | `data/rag_docs/doc1~5.txt` | ✅ 한국어 5개 문서 |

---

## 3. 이번 세션(Week 7)에서 수행한 작업

### 3-1. Mock 기반 시범 실행 테스트 작성 (`tests/test_run_full.py`)

API 키 없이 전체 파이프라인 흐름을 검증하는 8개 테스트를 작성:

| 테스트명 | 검증 내용 |
|---------|----------|
| `test_single_path` | single 경로 BaseAgent 단일 호출 동작 |
| `test_moa_path` | moa 경로 Draft×3 → Critic → Synth → Judge 흐름 |
| `test_save_full_output` | 결과 JSON 파일 저장/로드 |
| `test_router_single_case` | summarize + low difficulty → single 라우팅 |
| `test_router_moa_case` | ideate → moa 라우팅 |
| `test_router_rag_case` | source:rag_docs → requires_rag=True |
| `test_router_mcp_case` | MCP 키워드 → requires_mcp=True |
| `test_full_pipeline_3_cases` | sum-001(single), ide-001/crw-001(moa) 3건 E2E |

### 3-2. 전체 테스트 재실행

- 기존 108개 + 새 8개 = **총 116개 테스트 모두 통과**
- 실행 시간: 0.34초

---

## 4. 실제 API 테스트에 필요한 사항

### 4-1. 필요한 API 키

현재 코드베이스는 **OpenAI API만 사용**합니다.

| 항목 | 값 | 설명 |
|------|-----|------|
| **API 키** | `OPENAI_API_KEY` | OpenAI 플랫폼에서 발급 |
| **기본 모델** | `gpt-4o-mini` | 1~5주차 단일 모델로 고정 |
| **대체 모델** | `gpt-4o` | 비용이 높지만 품질 비교용 |
| **API 엔드포인트** | `https://api.openai.com/v1/chat/completions` | `base_agent.py`에 하드코딩 |

### 4-2. API 키 설정 방법

```bash
# 1. 프로젝트 루트에 .env 파일 생성
cp env.example .env

# 2. .env 파일 편집 — API 키 입력
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
DEFAULT_MODEL=gpt-4o-mini
```

> **주의:** `.env` 파일은 `.gitignore`에 포함되어 있어 커밋되지 않습니다.

### 4-3. API 키 발급 방법

1. https://platform.openai.com 접속 → 로그인
2. 좌측 메뉴에서 **API keys** 선택
3. **Create new secret key** 클릭
4. 키를 복사하여 `.env` 파일에 붙여넣기

### 4-4. 비용 예상

| 모델 | 입력 단가 | 출력 단가 | 12건 벤치마크 예상 비용 |
|------|----------|----------|---------------------|
| `gpt-4o-mini` | $0.15 / 1M tokens | $0.60 / 1M tokens | ~$0.01~0.05 |
| `gpt-4o` | $2.50 / 1M tokens | $10.00 / 1M tokens | ~$0.20~0.80 |

- Single 경로: 에이전트 1회 호출
- MOA 경로: 에이전트 5~7회 호출 (Draft×3 + Critic + Synth + Judge + Rewrite)
- 12건 전체 실행 시 gpt-4o-mini 기준 약 **$0.05 이하**

### 4-5. 실제 실행 명령어

```bash
# 1) 단일 케이스 테스트
python scripts/run_full.py --case-id sum-001

# 2) 전체 12건 실행
python scripts/run_full.py --cost-report

# 3) 경로 강제 지정
python scripts/run_full.py --case-id ide-001 --force-path moa

# 4) Single baseline만 실행
python scripts/run_single.py

# 5) MOA 파이프라인만 실행
python scripts/run_moa.py

# 6) 결과 비교
python scripts/compare_runs.py data/outputs/ --format table
```

### 4-6. 향후 멀티모델 테스트 시 필요 사항

6주차 명세에 따르면 멀티모델 실험이 가능하도록 설계되어 있지만, 현재 코드는 `base_agent.py`에서 OpenAI API만 호출합니다. 다른 모델을 테스트하려면:

| 모델 | 필요 API 키 | 환경변수 | 추가 구현 필요 |
|------|------------|---------|--------------|
| Claude 3.5 Haiku | Anthropic API Key | `ANTHROPIC_API_KEY` | `base_agent.py`에 Anthropic 엔드포인트 추가 |
| Gemini | Google AI API Key | `GOOGLE_API_KEY` | 별도 호출 로직 추가 |
| 로컬 Ollama | 없음 (로컬) | `OLLAMA_BASE_URL` | 엔드포인트 URL 변경 |

> 현재 구현에서는 `OPENAI_API_KEY` 하나만 있으면 모든 파이프라인을 실행할 수 있습니다.

---

## 5. 웹 UI 지원 현황

### 결론: ❌ 웹 UI 미구현

현재 프로젝트에는 웹 UI가 **전혀 없습니다.** 모든 실행은 CLI(명령줄)로만 가능합니다.

| 현재 구조 | 입력 방식 | 출력 방식 |
|----------|----------|----------|
| `run_single.py` | CLI args + `v1.json` 벤치마크 파일 | JSON 파일 저장 |
| `run_moa.py` | CLI args + `v1.json` 벤치마크 파일 | JSON 파일 저장 |
| `run_full.py` | CLI args + `v1.json` 벤치마크 파일 | JSON 파일 저장 |

**사용자가 직접 프롬프트를 입력하여 MOA 파이프라인을 실행하는 인터페이스가 없습니다.**

- 가드레일 #3에서 "UI 개발 금지 (CLI + JSON 로그만)" → 6주차까지는 설계 의도대로
- 그러나 7주차 이후 실제 활용을 위해서는 웹 UI 구현이 필요함
- 구현 지침은 `week7_implement.md`에 별도 작성

---

## 6. 프로젝트 파일 트리 (최종 상태)

```
MOA_OC_study/
├── app/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # LLM API 호출 래퍼
│   │   ├── draft_agent.py         # Draft × 3 (analytical/creative/structured)
│   │   ├── critic_agent.py        # 비교 분석
│   │   ├── judge_agent.py         # 품질 판정 (pass/rewrite/escalate)
│   │   └── rewrite_agent.py       # 피드백 기반 개선
│   ├── core/
│   │   ├── config.py              # .env 로딩, 전역 설정
│   │   ├── cost_tracker.py        # 토큰·비용 집계
│   │   ├── logger.py              # JSON trace 로거
│   │   └── timer.py               # 레이턴시 데코레이터
│   ├── eval/
│   │   ├── comparator.py          # 경로별 비교 분석
│   │   ├── metrics.py             # 품질·시스템 지표
│   │   └── rubric.py              # LLM 기반 루브릭 평가
│   ├── mcp_client/
│   │   ├── __init__.py
│   │   └── client.py              # MCP 도구 호출 (mock:// 지원)
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── executor.py            # MOA 파이프라인 실행 엔진
│   │   ├── retry_policy.py        # 재시도·폴백 정책
│   │   ├── router.py              # 2단계 하이브리드 라우팅
│   │   └── synthesizer.py         # 최종 종합 에이전트
│   ├── prompts/                   # 역할별 시스템 프롬프트 (.md)
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── chunker.py             # 텍스트 분할
│   │   ├── embedder.py            # 임베딩 (SHA256 플레이스홀더)
│   │   └── retriever.py           # 단어 중복 기반 검색
│   └── schemas/
│       ├── task.py                # TaskRequest, TaskPlan
│       ├── agent_io.py            # AgentInput, AgentOutput
│       └── trace.py               # TraceRecord, RunSummary
├── data/
│   ├── benchmarks/v1.json         # 12건 벤치마크
│   ├── rag_docs/doc1~5.txt        # RAG 샘플 문서
│   ├── outputs/                   # 실행 결과 저장
│   └── traces/                    # trace 로그 저장
├── scripts/
│   ├── run_single.py              # Baseline CLI
│   ├── run_moa.py                 # MOA CLI
│   ├── run_full.py                # Full Pipeline CLI
│   └── compare_runs.py            # 결과 비교 CLI
├── tests/                         # 116개 테스트
│   ├── test_base_agent.py
│   ├── test_critic.py
│   ├── test_draft_diversity.py
│   ├── test_eval.py
│   ├── test_judge.py
│   ├── test_logger.py
│   ├── test_pipeline_moa.py
│   ├── test_pipeline_single.py
│   ├── test_rag.py
│   ├── test_router.py
│   ├── test_run_full.py
│   ├── test_schemas.py
│   └── test_synthesizer.py
├── docs/                          # 명세 문서 9개
├── refs/                          # 기술 스택·구조·평가 지침
├── requirements.txt
├── env.example
└── claude.md                      # AI 인스트럭션
```

---

## 7. 핵심 아키텍처 흐름

```
사용자 입력
    │
    ▼
  Router (rule_based_route → llm_route)
    │
    ├─ single ──► BaseAgent 단일 호출 ──► 결과 JSON
    │
    └─ moa ──► Draft×3 (병렬)
                  │
                  ▼
              Critic (비교 분석)
                  │
                  ▼
              Synthesizer (종합)
                  │
                  ▼
              Judge (pass/rewrite/escalate)
                  │
                  ├─ pass ──► 결과 JSON
                  └─ rewrite ──► Rewrite Agent → Judge (최대 2회 루프)
```

**RAG/MCP 주입 (6주차):**
- Router가 `requires_rag=True` → Executor가 RAG 문서 검색 후 프롬프트에 추가
- Router가 `requires_mcp=True` → Executor가 MCP 도구 호출 후 결과를 프롬프트에 추가
