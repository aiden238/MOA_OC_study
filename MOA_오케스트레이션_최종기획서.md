# MOA 오케스트레이션 실험 프로젝트 — 최종 기획서

> **프로젝트 한 줄 정의:** 단일 LLM 호출(Baseline)부터 Multi-Agent Orchestration, API·MCP·RAG 통합까지 단계적으로 확장하는 6주 실험 프로젝트

---

## 0. 프로젝트 개요

### 0.1 왜 이 프로젝트를 하는가

- 멀티 에이전트 오케스트레이션(MOA)이 단일 호출보다 **실제로** 나은지 검증
- Router → Planner → Draft → Critic → Synthesizer 파이프라인의 최소 구조를 직접 설계·구현
- 6주차까지 API 연동, MCP 서버 통합, RAG 파이프라인을 **점진적으로** 추가하여 종합 오케스트레이션 완성
- 모든 과정을 trace/logging으로 추적하고, baseline 대비 개선 여부를 정량적으로 비교

### 0.2 최종 목표 아키텍처 (6주차 완성 시)

```
User Input
  → Router (단순/복합 판별, MCP/RAG 필요 여부 판별)
  → Planner (태스크 분해)
  → [RAG Retriever] (필요 시 외부 문서 검색)
  → [MCP Tool Call] (필요 시 외부 서비스 호출)
  → Draft Agent ×3 (병렬 생성, 다양성 보장)
  → Critic Agent (약점 분석)
  → Judge Agent (best draft 선택 또는 재생성 판정)
  → Rewrite Agent (조건부)
  → Synthesizer (최종 조합)
  → Final Output + Trace Save
```

### 0.3 Non-Goals (6주 범위 밖)

- 범용 초거대 에이전트 완성
- 자체 파운데이션 모델 개발
- 복잡한 프론트엔드 UI 완성
- 대규모 배포 인프라 / 운영 수준 비용 최적화
- 브라우저 자동화

---

## 1. 기술 스택 및 라이선스 정책

### 1.1 라이선스 원칙

> **MIT 또는 Apache 2.0 라이선스만 사용한다. GPL 계열은 사용하지 않는다.**

### 1.2 핵심 의존성 (최소화)

| 패키지 | 용도 | 라이선스 | 주차 |
|--------|------|----------|------|
| `pydantic` (v2) | 스키마 유효성 검증 | MIT | 1주차~ |
| `httpx` | LLM API 호출 (async 지원) | BSD-3 | 1주차~ |
| `python-dotenv` | 환경변수 관리 | BSD-3 | 1주차~ |
| `pytest` | 테스트 프레임워크 | MIT | 1주차~ |
| `pytest-asyncio` | async 테스트 | MIT | 4주차~ |
| `tenacity` | 재시도 로직 | Apache 2.0 | 3주차~ |
| `tiktoken` | 토큰 수 추정 | MIT | 3주차~ |
| `chromadb` | 벡터 DB (RAG용) | Apache 2.0 | 6주차 |
| `mcp` (Python SDK) | MCP 서버 연동 | MIT | 6주차 |

### 1.3 사용하지 않는 것

| 패키지 | 이유 |
|--------|------|
| LangChain / LangGraph | 내부 마법에 의존하면 오케스트레이션 구조를 이해 못 함 |
| CrewAI / AutoGen | 같은 이유 |
| Streamlit / Gradio | 6주 내 UI 불필요 |
| SQLAlchemy | JSON/SQLite 직접 사용으로 충분 |

### 1.4 LLM API 선택

- **1~5주차:** 단일 모델 고정 (예: `gpt-4o-mini` 또는 `claude-3-5-haiku`)
  - 이유: 모델 차이 vs 구조 차이를 분리하기 위해
- **6주차:** 멀티 모델 실험 도입 (Router가 모델도 선택)

---

## 2. 폴더 구조

```
moa-orchestration-lab/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── docs/                          # 기준 명세서 (코드보다 우선)
│   ├── 00_project_goal.md
│   ├── 01_scope_and_nonggoals.md
│   ├── 02_architecture.md
│   ├── 03_agent_roles.md
│   ├── 04_routing_rules.md
│   ├── 05_eval_metrics.md
│   ├── 06_experiment_log.md
│   ├── 07_retrospective.md
│   └── 08_mcp_rag_integration.md   # 6주차 추가
│
├── app/
│   ├── __init__.py
│   ├── core/                       # 공통 설정·유틸
│   │   ├── __init__.py
│   │   ├── config.py               # dotenv 로딩, 모델 설정
│   │   ├── logger.py               # JSON trace 로거
│   │   ├── cost_tracker.py         # 토큰·비용 집계
│   │   └── timer.py                # 레이턴시 측정 데코레이터
│   │
│   ├── schemas/                    # Pydantic 모델 (입출력 구조 강제)
│   │   ├── __init__.py
│   │   ├── task.py                 # TaskRequest, TaskPlan
│   │   ├── agent_io.py             # AgentInput, AgentOutput
│   │   └── trace.py                # TraceRecord, RunSummary
│   │
│   ├── prompts/                    # 역할별 시스템 프롬프트
│   │   ├── planner.md
│   │   ├── draft_analytical.md     # Draft 변이 A
│   │   ├── draft_creative.md       # Draft 변이 B
│   │   ├── draft_structured.md     # Draft 변이 C
│   │   ├── critic.md
│   │   ├── judge.md
│   │   ├── rewrite.md
│   │   └── synthesizer.md
│   │
│   ├── agents/                     # LLM 호출 최소 단위
│   │   ├── __init__.py
│   │   ├── base_agent.py           # httpx + pydantic 래퍼
│   │   ├── draft_agent.py
│   │   ├── critic_agent.py
│   │   ├── judge_agent.py
│   │   ├── rewrite_agent.py
│   │   └── synthesizer_agent.py
│   │
│   ├── orchestrator/               # 에이전트 조율 로직
│   │   ├── __init__.py
│   │   ├── router.py               # single / moa / rag / mcp 분기
│   │   ├── planner.py              # 태스크 분해
│   │   ├── executor.py             # 파이프라인 실행 엔진
│   │   ├── synthesizer.py          # 최종 조합
│   │   └── retry_policy.py         # 재시도·폴백 정책
│   │
│   ├── rag/                        # 6주차 추가
│   │   ├── __init__.py
│   │   ├── retriever.py            # 문서 검색
│   │   ├── chunker.py              # 문서 분할
│   │   └── embedder.py             # 임베딩 생성
│   │
│   ├── mcp_client/                 # 6주차 추가
│   │   ├── __init__.py
│   │   └── client.py               # MCP 서버 호출 래퍼
│   │
│   └── eval/                       # 평가 로직
│       ├── __init__.py
│       ├── metrics.py              # 정량 지표 계산
│       ├── rubric.py               # 루브릭 기반 LLM 평가
│       └── comparator.py           # single vs moa 비교 엔진
│
├── tests/
│   ├── test_schemas.py
│   ├── test_base_agent.py
│   ├── test_router.py
│   ├── test_critic.py
│   ├── test_synthesizer.py
│   ├── test_pipeline_single.py
│   ├── test_pipeline_moa.py
│   └── test_rag.py                 # 6주차 추가
│
├── scripts/                        # CLI 엔트리포인트
│   ├── run_single.py               # baseline 실행
│   ├── run_moa.py                  # MOA 파이프라인 실행
│   ├── run_full.py                 # 6주차: Router → 자동 분기 실행
│   └── compare_runs.py             # 결과 비교 스크립트
│
└── data/
    ├── benchmarks/                 # 실험 입력 데이터
    │   └── v1.json
    ├── traces/                     # 실행 로그 (gitignore 대상)
    ├── outputs/                    # 생성 결과물
    └── rag_docs/                   # 6주차: RAG용 샘플 문서
```

---

## 3. 1~6주차 계획표 (주당 커밋 3회)

---

### 🔷 1주차: 프로젝트 뼈대 + 명세 확정

**만드는 것:** 프로젝트 환경, 기획 문서, JSON trace 로거

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C1-1 | Day 1~2 | 프로젝트 초기화, venv, requirements.txt, .env.example, .gitignore | `README.md`, `requirements.txt`, `.env.example` |
| C1-2 | Day 3~4 | 기획 문서 작성 (goal, scope, architecture) | `docs/00~02.md` |
| C1-3 | Day 5~7 | JSON trace 로거 구현 + 테스트 | `app/core/logger.py`, `app/core/config.py`, `app/core/timer.py`, `tests/test_logger.py` |

**완료 기준 (DoD):**
- `python -m pytest tests/test_logger.py` 통과
- logger가 `data/traces/`에 JSON 파일을 정상 생성
- docs/00~02.md의 뼈대가 채워져 있음

**세부 설명:**

`logger.py`는 이 프로젝트의 근간이다. 모든 LLM 호출은 이 로거를 거쳐야 하며, 아래 필드를 기록한다:
- `run_id`: 실행 식별자 (UUID)
- `agent_name`: 어떤 에이전트가 호출했는지
- `model`: 사용 모델
- `input_prompt`: 입력 프롬프트 (전체 또는 해시)
- `output_text`: 출력 텍스트
- `prompt_tokens`, `completion_tokens`: 토큰 수
- `latency_ms`: 응답 시간
- `cost_estimate`: 추정 비용
- `timestamp`: 호출 시각
- `path`: single / moa / rag 등 어떤 경로를 탔는지

---

### 🔷 2주차: 스키마 + 에이전트 기반 + 프롬프트 분리

**만드는 것:** Pydantic 스키마, Base Agent 클래스, 역할별 프롬프트 파일

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C2-1 | Day 1~2 | Pydantic 스키마 3종 정의 + validation 테스트 | `app/schemas/task.py`, `agent_io.py`, `trace.py`, `tests/test_schemas.py` |
| C2-2 | Day 3~4 | Base Agent 클래스 (httpx + pydantic + tenacity) | `app/agents/base_agent.py`, `tests/test_base_agent.py` |
| C2-3 | Day 5~7 | 역할별 프롬프트 파일 분리 + 에이전트 역할 문서 | `app/prompts/*.md`, `docs/03_agent_roles.md` |

**완료 기준:**
- `TaskRequest(prompt="test")` 등 스키마 validation 통과
- Base Agent가 실제 LLM API를 호출하고 Pydantic 모델로 파싱
- 프롬프트 파일이 `.md`로 분리되어 있고, 에이전트가 파일에서 읽어 사용

**핵심 스키마 설계:**

```python
# app/schemas/task.py
class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str
    task_type: Literal["summarize", "explain", "ideate", "critique_rewrite"]
    constraints: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

class TaskPlan(BaseModel):
    original_request: TaskRequest
    subtasks: list[str] = []           # Planner가 분해한 하위 작업
    selected_path: Literal["single", "moa"]
    requires_rag: bool = False         # 6주차
    requires_mcp: bool = False         # 6주차
```

```python
# app/schemas/agent_io.py
class AgentInput(BaseModel):
    agent_name: str
    system_prompt: str
    user_message: str
    temperature: float = 0.7
    max_tokens: int = 1024

class AgentOutput(BaseModel):
    agent_name: str
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    cost_estimate: float
    raw_response: dict[str, Any] = {}
```

**Draft 다양성 확보 전략 (2주차에 확정):**

| Draft Agent | 관점 지시 | temperature | 출력 스타일 |
|-------------|-----------|-------------|-------------|
| draft_analytical | "분석적이고 논리적인 관점에서" | 0.4 | 구조화된 설명 |
| draft_creative | "창의적이고 비유를 활용하는 관점에서" | 0.9 | 자유로운 서술 |
| draft_structured | "비전공자도 이해할 수 있게 단계적으로" | 0.6 | 단계별 정리 |

---

### 🔷 3주차: Baseline (Single Path) 파이프라인

**만드는 것:** 단일 호출 파이프라인, 벤치마크 데이터, 평가 루브릭

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C3-1 | Day 1~2 | 벤치마크 입력 데이터 v1 작성 (4종 × 3건 = 12건) | `data/benchmarks/v1.json`, `docs/05_eval_metrics.md` |
| C3-2 | Day 3~4 | `run_single.py` 구현 — input 읽기 → 단일 호출 → trace 저장 | `scripts/run_single.py`, `tests/test_pipeline_single.py` |
| C3-3 | Day 5~7 | 평가 루브릭 구현 (LLM Judge + 수동 5건 교차 검증) | `app/eval/rubric.py`, `app/eval/metrics.py` |

**완료 기준:**
- `python scripts/run_single.py` 실행 시 12건 입력에 대한 결과가 `data/outputs/`에 저장
- 각 실행의 trace가 `data/traces/`에 JSON으로 저장
- 루브릭이 clarity / structure / constraint_following / usefulness 4항목을 1~5점으로 채점

**벤치마크 데이터 v1 구조:**

```json
{
  "version": "v1",
  "cases": [
    {
      "id": "sum-001",
      "type": "summarize",
      "prompt": "다음 텍스트를 3문장으로 요약하세요: [300자 텍스트]",
      "constraints": {"max_sentences": 3},
      "difficulty": "low",
      "expected_moa_advantage": "minimal"
    },
    {
      "id": "exp-001",
      "type": "explain",
      "prompt": "양자 컴퓨팅의 큐비트 개념을 중학생에게 설명하세요.",
      "constraints": {"audience": "middle_school"},
      "difficulty": "medium",
      "expected_moa_advantage": "planner_helps"
    },
    {
      "id": "ide-001",
      "type": "ideate",
      "prompt": "도시의 교통 혼잡을 줄이기 위한 창의적인 아이디어 5가지를 제시하세요.",
      "constraints": {"count": 5, "novelty": "high"},
      "difficulty": "medium",
      "expected_moa_advantage": "multi_draft_helps"
    },
    {
      "id": "crw-001",
      "type": "critique_rewrite",
      "prompt": "다음 이메일을 개선하세요: [비즈니스 이메일 초안]",
      "constraints": {"tone": "professional"},
      "difficulty": "high",
      "expected_moa_advantage": "critique_rewrite_helps"
    }
  ]
}
```

**평가 프로토콜 (3주차에 확정):**
1. LLM Judge가 루브릭 기반 1~5점 채점 (자동)
2. 본인이 12건 중 5건을 수동 채점 (교차 검증)
3. LLM 점수와 수동 점수의 상관관계가 0.7 이상이면 LLM Judge 신뢰
4. 0.7 미만이면 루브릭 재조정

---

### 🔷 4주차: MOA 파이프라인 (Draft + Critic + Trace)

**만드는 것:** 병렬 Draft 생성, Critic 평가, Trace 저장 (이번 주는 Synthesizer까지만, Judge/Rewrite는 5주차)

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C4-1 | Day 1~2 | Draft Agent 3종 구현 (async 병렬) + 다양성 테스트 | `app/agents/draft_agent.py`, `tests/test_draft_diversity.py` |
| C4-2 | Day 3~5 | Critic Agent + Synthesizer 구현 | `app/agents/critic_agent.py`, `app/orchestrator/synthesizer.py` |
| C4-3 | Day 6~7 | MOA 실행 스크립트 + trace 통합 저장 + single vs moa 첫 비교 | `scripts/run_moa.py`, `app/orchestrator/executor.py` |

**완료 기준:**
- `python scripts/run_moa.py` 실행 시 3개 draft가 생성되고 critic 평가를 거쳐 synthesized 결과 출력
- trace에 각 에이전트별 호출 정보가 모두 기록
- 동일 입력에 대해 single vs moa 결과가 나란히 비교 가능

**4주차 MOA 파이프라인 흐름:**

```
Input
  → Draft Agent A (analytical, temp=0.4)  ─┐
  → Draft Agent B (creative, temp=0.9)     ├─ 비동기 병렬
  → Draft Agent C (structured, temp=0.6)  ─┘
  → Critic Agent (3개 draft 비교 분석, 강점/약점 정리)
  → Synthesizer Agent (critic 피드백 + drafts → 최종 결과)
  → Trace Save
```

**API Rate Limit 대응 (4주차 필수):**
- 병렬 3개 호출 시 `asyncio.Semaphore(3)` 사용
- API 429 에러 시 tenacity의 exponential backoff 적용
- 연속 3회 실패 시 해당 draft를 skip하고 2개로 진행 (graceful degradation)

---

### 🔷 5주차: Router + Judge/Rewrite + 조건부 분기

**만드는 것:** Router (경로 판별), Judge (재생성 판정), Rewrite (조건부), Retry/Fallback

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C5-1 | Day 1~2 | Judge Agent + Rewrite Agent 구현 | `app/agents/judge_agent.py`, `app/agents/rewrite_agent.py` |
| C5-2 | Day 3~5 | Router 구현 (rule-based + LLM hybrid) + 테스트 | `app/orchestrator/router.py`, `app/orchestrator/retry_policy.py`, `tests/test_router.py` |
| C5-3 | Day 6~7 | cost_tracker + 통합 실행 스크립트 (`run_full.py`) | `app/core/cost_tracker.py`, `scripts/run_full.py`, `docs/04_routing_rules.md` |

**완료 기준:**
- Router가 입력을 분석하여 single/moa 경로를 자동 선택
- Judge가 "pass/rewrite/escalate" 판정을 내리고, rewrite 시 Rewrite Agent가 개선
- `run_full.py`가 Router → 자동 분기 → 결과 저장까지 end-to-end 실행
- cost_tracker가 총 토큰, 추정 비용, 경로별 비용 집계

**Router 판별 기준 (5주차에 확정):**

```python
class RoutingDecision(BaseModel):
    selected_path: Literal["single", "moa"]
    reason: str
    confidence: float  # 0.0 ~ 1.0
    requires_rag: bool = False    # 6주차 활성화
    requires_mcp: bool = False    # 6주차 활성화

# Rule-based 1차 필터 (빠르고 저렴)
# - task_type == "summarize" and difficulty == "low" → single
# - task_type == "ideate" → moa
# - prompt 길이 > 500자 → moa
# - constraints에 "novelty" 포함 → moa

# LLM 2차 판별 (1차 필터 통과 후 애매한 경우)
# - LLM에게 "이 요청은 단일 답변으로 충분한가, 다중 관점이 필요한가?" 질문
```

**Judge → Rewrite 흐름:**

```
Synthesized Output
  → Judge Agent
     ├─ "pass" → 최종 출력으로 확정
     ├─ "rewrite" → Rewrite Agent → 재평가 (최대 2회)
     └─ "escalate" → 로그 기록 + 사람 검토 플래그
```

---

### 🔷 6주차: MCP·RAG 통합 + 비교 실험 + 회고

**만드는 것:** RAG 파이프라인, MCP 클라이언트, 최종 비교 실험, 회고 문서

| 커밋 | 날짜 기준 | 작업 내용 | 산출물 |
|------|-----------|-----------|--------|
| C6-1 | Day 1~3 | RAG 파이프라인 (chunker → embedder → retriever → context injection) | `app/rag/*.py`, `data/rag_docs/`, `tests/test_rag.py` |
| C6-2 | Day 4~5 | MCP 클라이언트 + Router에 rag/mcp 분기 추가 | `app/mcp_client/client.py`, `docs/08_mcp_rag_integration.md` |
| C6-3 | Day 6~7 | 전체 비교 실험 실행 + 결과 분석 + 회고 문서 작성 | `scripts/compare_runs.py`, `docs/06_experiment_log.md`, `docs/07_retrospective.md` |

**완료 기준:**
- RAG: 샘플 문서 5건을 ChromaDB에 저장 → 질의 시 관련 청크 검색 → Draft Agent에 컨텍스트 주입
- MCP: 최소 1개 MCP 서버(예: 파일시스템 또는 웹검색)에 연결하여 도구 호출 성공
- `compare_runs.py`가 single / moa / moa+rag / moa+mcp 4가지 경로의 결과를 비교 테이블로 출력
- 회고 문서에 "어떤 태스크에서 MOA가 유리했는지"가 데이터와 함께 기록

**6주차 RAG 최소 구현:**

```python
# app/rag/retriever.py
class SimpleRetriever:
    """ChromaDB 기반 최소 검색기"""
    
    def __init__(self, collection_name: str):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)
    
    def add_documents(self, docs: list[str], metadatas: list[dict]):
        """문서 청크를 벡터 DB에 저장"""
        ...
    
    def query(self, query_text: str, n_results: int = 3) -> list[str]:
        """질의에 관련된 청크 반환"""
        ...
```

**6주차 MCP 최소 구현:**

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

**Router 확장 (6주차):**

```
Router 판별 결과:
  ├─ path: single          → 단일 호출
  ├─ path: moa             → 기존 MOA 파이프라인
  ├─ path: moa + rag       → RAG 검색 → 컨텍스트 포함 MOA
  ├─ path: moa + mcp       → MCP 도구 호출 결과 → MOA
  └─ path: moa + rag + mcp → 풀 파이프라인
```

---

## 4. 전체 비교 프레임워크

### 4.1 비교 축 (4가지 경로)

| 경로 | 설명 | 도입 시점 |
|------|------|-----------|
| **Single** | 단일 LLM 호출 (baseline) | 3주차 |
| **MOA** | Draft×3 → Critic → Synthesizer | 4주차 |
| **MOA + RAG** | 외부 문서 검색 후 MOA | 6주차 |
| **MOA + MCP** | 외부 도구 호출 후 MOA | 6주차 |

### 4.2 평가 지표

**품질 지표 (루브릭 1~5점):**
- clarity: 읽기 쉬운가
- structure: 논리 구조가 명확한가
- constraint_following: 제약 조건을 지켰는가
- usefulness: 실제로 도움이 되는가

**시스템 지표 (자동 측정):**
- total_latency_ms: 전체 응답 시간
- total_tokens: 사용 토큰 수
- total_cost_estimate: 추정 비용 ($)
- retry_count: 재시도 횟수
- failure_count: 실패 횟수

**오케스트레이션 효과 (비교):**
- quality_delta: single 대비 품질 개선폭
- cost_ratio: single 대비 비용 배수
- latency_ratio: single 대비 시간 배수
- draft_diversity_score: 3개 draft 간 유사도 (낮을수록 다양)

### 4.3 최종 비교 테이블 (6주차 산출물)

```
| case_id | type      | single_score | moa_score | delta | single_cost | moa_cost | cost_ratio | single_latency | moa_latency |
|---------|-----------|-------------|-----------|-------|-------------|----------|------------|----------------|-------------|
| sum-001 | summarize | 4.2         | 4.0       | -0.2  | $0.002      | $0.012   | 6.0x       | 1.2s           | 3.8s        |
| ide-001 | ideate    | 3.1         | 4.5       | +1.4  | $0.003      | $0.018   | 6.0x       | 1.5s           | 5.2s        |
```

---

## 5. 벤치마크 태스크 설계

### 5.1 태스크 유형 4종

| 유형 | 왜 테스트하는가 | MOA 기대 효과 |
|------|----------------|--------------|
| **단순 요약** | MOA가 불필요할 수 있는 케이스 확인 | 최소 (비용만 낭비할 수 있음) |
| **구조화 설명** | Planner의 태스크 분해 효과 측정 | 중간 (Planner가 도움) |
| **창의적 아이디어** | 다중 Draft의 다양성 효과 측정 | 높음 (Draft 변이가 핵심) |
| **비판-재작성** | Critic → Rewrite 루프 효과 측정 | 높음 (피드백 루프가 핵심) |

### 5.2 각 유형별 3건씩, 총 12건

- 모든 케이스는 도메인 지식 불필요 (범용 주제)
- 정답이 명확한 것이 아니라 루브릭 기반 평가에 적합한 주제
- 6주차에 RAG용 케이스 4건 추가 (문서 기반 질의)

---

## 6. 가드레일 (과도한 확장 방지)

| # | 제약 조건 | 이유 |
|---|----------|------|
| 1 | LangChain / CrewAI / AutoGen 사용 금지 | 내부 동작을 이해하지 못한 채 의존하면 학습 목적 상실 |
| 2 | 1~5주차 동안 모델 단일화 (하나만 사용) | 모델 차이 vs 구조 차이를 분리하기 위해 |
| 3 | UI 개발 금지 (CLI + JSON 로그만) | 6주 내 집중도 유지 |
| 4 | 도메인 데이터 지양 (범용 벤치마크만) | 도메인 환각 vs 오케스트레이션 실패를 분리하기 위해 |
| 5 | RAG·MCP는 6주차에만 (그 전에 도입 금지) | 파이프라인 기본 구조가 안정된 후에 추가 |
| 6 | 한 주에 3커밋 초과 금지 | 무리한 진행 방지, 커밋 품질 유지 |
| 7 | 새 의존성 추가 시 라이선스 확인 필수 | MIT / Apache 2.0만 허용 |
| 8 | 문서 없이 코드만 커밋하지 않기 | 문서가 기준, 코드가 증명 |

---

## 7. 커밋 컨벤션

```
<type>(<scope>): <subject>

type:
  docs     - 문서 추가/수정
  feat     - 기능 구현
  test     - 테스트 추가
  fix      - 버그 수정
  refactor - 구조 변경
  chore    - 환경 설정, 의존성

scope:
  core / schemas / agents / orchestrator / eval / rag / mcp / scripts

예시:
  docs(project): add project goal and scope documents
  feat(agents): implement base agent with httpx and pydantic
  test(schemas): add validation tests for TaskRequest
  feat(orchestrator): implement async parallel draft execution
  feat(rag): add chromadb retriever with simple chunking
  docs(retrospective): write week 6 experiment analysis
```

---

## 8. 비용 추정 (6주 전체)

> gpt-4o-mini 기준 추정 (가장 저렴한 옵션)

| 항목 | 호출 수 | 추정 비용 |
|------|---------|-----------|
| Baseline 실험 (12건 × 3회 반복) | 36 | ~$0.05 |
| MOA 실험 (12건 × 에이전트 5~7개 × 3회) | ~250 | ~$0.50 |
| Router/Judge/Rewrite 실험 | ~100 | ~$0.20 |
| RAG 실험 (6주차) | ~50 | ~$0.10 |
| 루브릭 평가 (LLM Judge) | ~100 | ~$0.15 |
| **합계** | **~536** | **~$1.00** |

> claude-3-5-haiku 사용 시 약 $2~3 예상. 비용은 제약 요인이 아님.

---

## 9. 주차별 각 구성 요소가 하는 일 요약

| 구성 요소 | 역할 | 도입 | 무엇을 검증하는가 |
|-----------|------|------|-------------------|
| **Logger/Tracer** | 모든 호출 기록 | 1주차 | 재현 가능성, 비교 가능성 |
| **Pydantic Schema** | 입출력 구조 강제 | 2주차 | 데이터 무결성 |
| **Base Agent** | LLM API 래퍼 | 2주차 | 단일 호출의 안정성 |
| **Draft Agent ×3** | 다양한 관점의 초안 생성 | 4주차 | 다중 생성의 품질 향상 효과 |
| **Critic Agent** | 초안 비교 분석·약점 지적 | 4주차 | 자기 평가의 유용성 |
| **Synthesizer** | 여러 초안의 장점 조합 | 4주차 | 합성 결과의 품질 |
| **Judge Agent** | 최종 품질 판정·재생성 결정 | 5주차 | 반복 개선의 한계점 |
| **Rewrite Agent** | 피드백 기반 재작성 | 5주차 | 피드백 루프의 실효성 |
| **Router** | 경로 자동 선택 | 5주차 | 태스크별 최적 경로 존재 여부 |
| **Retry/Fallback** | 실패 대응 | 5주차 | 시스템 안정성 |
| **RAG Retriever** | 외부 문서 검색·주입 | 6주차 | 외부 지식이 품질에 미치는 영향 |
| **MCP Client** | 외부 도구 호출 | 6주차 | 도구 사용이 결과에 미치는 영향 |
| **Comparator** | 경로별 결과 비교 | 6주차 | 최종 검증 |

---

## 10. 이 기획서 활용 방법

1. **이 문서를 `docs/00_project_goal.md`의 원본으로 사용한다.**
2. **각 주차 시작 시** 해당 주차의 커밋 계획을 확인하고, 코드 작성 전에 관련 docs를 먼저 업데이트한다.
3. **Copilot Code에 작업을 넘길 때** 이 문서의 해당 섹션 + 스키마 정의를 함께 컨텍스트로 제공한다.
4. **6주차 완료 후** `docs/07_retrospective.md`에 실제 결과 대비 이 기획의 차이를 기록한다.

---

*마지막 업데이트: 2026-04-16*
