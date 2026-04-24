# Week 10 C10-4 Implement Guide - Validation, Docs, and Operator Hardening

## 목표

Week 10 구현 결과를 테스트, 문서, 운영 기준까지 포함해 닫는다.  
이 단계는 기능을 더 넣는 단계가 아니라, 이미 만든 기능이

- 재현 가능하고
- 회귀 없이 동작하며
- 제3자가 읽고 실행할 수 있도록

정리하는 마감 단계다.

---

## 범위

- `tests/` - 신규 테스트 추가
- `README.md` - 웹 실행 방법 및 모델 선택 문서화
- `refs/tech_stack.md` - 의존성, provider 정책, UI 관련 제한 반영
- `AGENTS.md` - 현재 주차 구현 반영 필요 시 갱신
- `claude.md` - Week 10 상태 갱신
- `week10_plan.md` - DoD 체크 상태 갱신
- `week10_c1_implement.md` ~ `week10_c4_implement.md` - 최종 정합성 점검
- 필요 시 `docs/06_experiment_log.md` - Week 10 검증 기록 추가

---

## 선행 조건

- **C10-1 완료**
- **C10-2 완료**
- **C10-3 완료**
- 웹 UI와 API가 실제로 동작
- 모델 선택 및 preset이 최소 1회 이상 실주행 검증됨

---

## 구현 원칙

- 코드만 끝내지 않고 실행 방법을 반드시 문서화한다.
- 테스트는 service/api/model selection/session의 4축을 최소 포함한다.
- 문서는 현재 런타임 정책과 실제 구현이 어긋나지 않아야 한다.
- known limitation은 감추지 않고 명시한다.

---

## 구현 상세

### A. 테스트 추가

최소 권장 테스트 묶음:

- `tests/test_chat_service.py`
- `tests/test_web_api.py`
- `tests/test_session_store.py`
- `tests/test_model_registry.py`

테스트 범위:

- 자유 입력 1턴 실행
- 세션 생성 / 조회 / 초기화
- `/api/chat`, `/api/sessions`, `/api/models`
- global model 선택
- agent override 적용
- preset 적용
- selected_models metadata 확인

### B. 회귀 테스트 실행

```bash
python -m pytest -q
```

가능하면 아래도 추가 확인:

```bash
python scripts/run_full.py --benchmark v1.json --case-id sum-001
python scripts/run_full.py --benchmark v1_rag_mcp.json --case-id rag-001 --evaluate --output-tag rag
```

핵심 확인:

- 기존 CLI가 안 깨졌는지
- web 관련 코드가 기존 평가/trace 구조를 망치지 않았는지

### C. 수동 검증 시나리오 정리

아래 시나리오를 실제로 실행하고 결과를 문서 또는 로그로 남긴다.

1. OpenAI only, `auto`
2. OpenAI only, `single`
3. OpenAI only, `moa`
4. OpenAI + Z.AI creative override
5. RAG 질문
6. MCP 질문
7. 세션 2턴 대화
8. preset 적용 후 응답/trace 확인

기록할 항목:

- prompt
- selected path
- selected models
- latency
- cost
- trace path
- 실패 시 오류 메시지

### D. README 갱신

최소 포함 내용:

- 웹 서버 실행 방법
- 의존성 설치 방법
- 브라우저 접속 방법
- `auto/single/moa` 설명
- 글로벌 모델 선택과 agent override 설명
- preset 개념 설명
- known limitations

### E. 기술 문서 동기화

`refs/tech_stack.md`에 아래를 반영한다.

- `fastapi`, `uvicorn` 추가
- 웹 UI는 보조 인터페이스이고 기준은 CLI + JSON trace라는 점 유지
- provider/model selection 정책
- request-level override 정책

`AGENTS.md`, `claude.md`에는 아래를 반영한다.

- Week 10 진행 상태
- web chat UI 범위
- 모델 선택 기능 추가 여부
- Z.AI / Gemini / OpenAI 현재 해석 기준

### F. Week 10 문서 정합성 점검

확인 대상:

- `week10_plan.md`
- `week10_c1_implement.md`
- `week10_c2_implement.md`
- `week10_c3_implement.md`
- `week10_c4_implement.md`

체크 포인트:

- 파일명과 단계 명칭 일치
- provider 표기가 `Z.AI` 기준으로 정리됨
- commit message와 실제 범위가 어긋나지 않음

### G. 운영 가드레일 명시

최소 명시 항목:

- 세션은 메모리 기반이라 서버 재시작 시 유실
- 1차 버전은 비스트리밍
- provider key가 없으면 UI에서 비활성 또는 요청 거절
- quota 초과는 key 존재와 별도로 runtime failure 가능
- trace/output evidence는 gitignored 상태일 수 있음

---

## 검증 기준

| 항목 | 기준 |
|---|---|
| pytest | 신규 테스트 포함 전체 통과 |
| CLI 회귀 | `run_full.py` 기존 명령 정상 동작 |
| 웹 검증 | 주요 시나리오 수동 검증 완료 |
| 문서 정합성 | README, refs, AGENTS, claude, week10 문서 일치 |
| 운영 가드레일 | known limitation 명시 완료 |

문서 점검 체크 예시:

```bash
rg -n "Grok|xai|streamlit|gradio" README.md refs/tech_stack.md AGENTS.md claude.md week10_*.md
```

의도:

- stale wording 제거
- 금지 스택 재도입 여부 확인

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| 테스트 작성 중 mocking 복잡도 과대 | service/API 테스트를 우선하고 UI는 수동 검증으로 대체 |
| README와 실제 실행법 불일치 | 서버 실행 명령과 API 예제를 먼저 고정한 뒤 문서 갱신 |
| provider 상태가 문서와 다름 | `.env`, `AGENTS.md`, `claude.md` 기준을 맞추고 변경 기록 남김 |
| session/model selection 검증이 flaky | deterministic test doubles 도입 후 실호출 검증은 수동 시나리오로 분리 |

---

## 마무리 커밋

```bash
git add tests README.md refs/tech_stack.md AGENTS.md claude.md week10_plan.md week10_c1_implement.md week10_c2_implement.md week10_c3_implement.md week10_c4_implement.md
git commit -m "docs(core): document web chat workflow and validation"
```

테스트 코드 변경 비중이 크면 아래처럼 2개 커밋으로 나눌 수 있다.

```bash
git commit -m "test(core): add web chat and model selection coverage"
git commit -m "docs(core): document web chat workflow and validation"
```

---

## 완료 기준 요약

- [ ] service / web / model selector 테스트 추가
- [ ] `python -m pytest -q` 통과
- [ ] 웹 주요 시나리오 수동 검증 완료
- [ ] README / refs / AGENTS / claude / week10 문서 동기화 완료
- [ ] known limitations 및 운영 가드레일 명시

---

## 권장 커밋 메시지

```text
docs(core): document web chat workflow and validation
```
