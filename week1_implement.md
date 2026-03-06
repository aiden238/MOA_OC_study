# Week 1 Implement — 구현 상세

## `app/core/config.py`

`python-dotenv`로 `.env` 파일을 로딩하고, 프로젝트 전역 설정을 관리하는 모듈.

**핵심 설정값:**
- `DEFAULT_MODEL` — 사용할 LLM 모델명
- `DEFAULT_TEMPERATURE` — 기본 temperature
- `MAX_TOKENS` — 최대 토큰 수
- `MAX_RETRIES` — 재시도 횟수
- `TRACE_DIR` — trace 저장 경로 (`data/traces/`)
- `OUTPUT_DIR` — 출력 저장 경로 (`data/outputs/`)
- `OPENAI_API_KEY` 또는 `ANTHROPIC_API_KEY`

**설계 원칙:**
- 환경변수가 없으면 합리적인 기본값 사용
- 경로는 프로젝트 루트 기준 상대 경로
- API 키가 없으면 명확한 에러 메시지 출력

---

## `app/core/logger.py`

모든 LLM 호출을 JSON 파일로 기록하는 trace 로거. 이 프로젝트의 **근간**이다.

**기록 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `run_id` | str | 실행 식별자 (UUID) |
| `agent_name` | str | 호출한 에이전트 이름 |
| `model` | str | 사용 모델명 |
| `input_prompt` | str | 입력 프롬프트 (전체 또는 해시) |
| `output_text` | str | 출력 텍스트 |
| `prompt_tokens` | int | 프롬프트 토큰 수 |
| `completion_tokens` | int | 완성 토큰 수 |
| `latency_ms` | float | 응답 시간 (ms) |
| `cost_estimate` | float | 추정 비용 ($) |
| `timestamp` | str | 호출 시각 (ISO 8601) |
| `path` | str | 경로 (single / moa / rag 등) |

**동작 방식:**
- `data/traces/` 디렉토리에 `{run_id}.json` 형태로 저장
- 하나의 run_id에 여러 에이전트 호출이 배열로 저장
- JSON Lines가 아닌 **단일 JSON 파일** (run 단위)
- 디렉토리가 없으면 자동 생성

---

## `app/core/timer.py`

함수 실행 시간을 밀리초 단위로 측정하는 데코레이터.

**사용 방식:**
```python
@measure_time
async def call_llm(...):
    ...
# 반환값: (result, latency_ms)
```

---

## `.gitignore` 포함 항목

```
.env
__pycache__/
*.pyc
data/traces/
data/outputs/
.venv/
*.egg-info/
dist/
build/
```

---

## 참고 컨텍스트

### 환경변수 구조 (env.example)

```env
OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=sk-ant-your-key-here
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.7
MAX_TOKENS=1024
MAX_RETRIES=3
TRACE_DIR=data/traces
OUTPUT_DIR=data/outputs
BENCHMARK_DIR=data/benchmarks
```

### 의존성 (1주차에 필요한 것만)

```
pydantic>=2.0,<3.0
httpx>=0.25.0
python-dotenv>=1.0.0
pytest>=7.0
```
