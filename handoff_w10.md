# Copilot Code 인수인계 — Week 10 착수 전 완료 필수 작업

작성일: 2026-04-20  
작성자: Claude (검토 세션)

---

## 현재 상태 요약

### 완료된 작업 (이번 세션)

| 파일 | 변경 내용 |
|---|---|
| `app/core/config.py` | Z.AI(Zhipu) 프로바이더 완전 추가 (`_normalize_provider`, `_default_api_base`, `_provider_api_key`, `_provider_api_base`, 모듈 상수) |
| `app/core/cost_tracker.py` | GLM-4.x, Gemini 2.x/3.x 모델 가격 추가 |
| `env.example` | xAI → Z.AI 섹션 교체, 모델명 정정 |
| `.env` | 실제 키 입력 완료 + 에이전트 분배 설정 활성화 |

### 현재 `.env` 에이전트 구성

```
DRAFT_ANALYTICAL_MODEL_PROVIDER=openai
DRAFT_ANALYTICAL_MODEL=gpt-4o-mini
DRAFT_CREATIVE_MODEL_PROVIDER=zai          ← Z.AI GLM-4.7-flash (정상 동작 확인)
DRAFT_CREATIVE_MODEL=glm-4.7-flash
DRAFT_STRUCTURED_MODEL_PROVIDER=openai
DRAFT_STRUCTURED_MODEL=gpt-4o-mini
EVAL_MODEL_PROVIDER=openai
EVAL_MODEL=gpt-4o-mini
```

### API 키 상태

| 프로바이더 | 상태 | 비고 |
|---|---|---|
| OpenAI | ✅ 정상 | gpt-5-nano가 DEFAULT_MODEL |
| Z.AI (Zhipu GLM) | ✅ 정상 | `glm-4.7-flash` 응답 확인 |
| Gemini | ❌ 사용 불가 | free tier quota=0 (billing 미설정) |

---

## 즉시 실행해야 할 작업 (Week 10 전에 완료)

### STEP 1 — 전체 12케이스 MOA 실행

아래 명령을 순서대로 실행한다.

```bash
# sum-001 단일 케이스는 이미 성공 확인됨 (32s, 6 agents, $0.000685)
# 전체 12케이스 실행
python scripts/run_full.py \
  --benchmark v1.json \
  --force-path moa \
  --evaluate \
  --output-tag moa_w10
```

완료 후 확인:

```bash
python -c "
import pathlib, json
files = list(pathlib.Path('data/outputs').glob('*__moa_w10.json'))
print(f'생성 파일: {len(files)}건')
for f in files[:2]:
    d = json.loads(f.read_text(encoding='utf-8'))
    score = d.get('evaluation', {}).get('avg_score')
    path = d.get('path')
    print(f'  {f.name}: path={path}, avg_score={score}')
"
```

기대: 12건 생성, 각 파일에 `evaluation.avg_score` 숫자 존재.

---

### STEP 2 — GLM 실동작 증거 확인

```bash
python -c "
import pathlib, json
files = list(pathlib.Path('data/outputs').glob('*__moa_w10.json'))
for f in files[:1]:
    d = json.loads(f.read_text(encoding='utf-8'))
    drafts = d.get('trace', {}).get('drafts', [])
    for dr in drafts:
        print(f'  agent={dr.get(\"agent_name\")}, model={dr.get(\"model\")}, tokens={dr.get(\"completion_tokens\")}')
"
```

기대: `draft_creative`의 model이 `glm-4.7-flash`임을 확인.

---

### STEP 3 — 커밋

실행 결과 파일은 `.gitignore` 대상이므로 코드 변경만 커밋한다.

```bash
git add app/core/config.py app/core/cost_tracker.py env.example
git commit -m "feat(core): add Z.AI/Zhipu provider and update model pricing"
```

---

## Week 10 착수 전 주의사항

1. **Gemini 비활성화 상태 유지**: Gemini API key quota 소진. Week 10 코드에서 Gemini provider는 `available=false`로 처리해야 한다.

2. **4커밋 구조 → 3커밋으로 조정 필요**: week10_plan.md에 C10-1~C10-4 4단계가 있으나 가드레일 #6(한 주 3커밋 초과 금지) 위반. C10-3+C10-4를 병합하거나 C10-4를 다음 주로 이관한다.

3. **plan의 `grok-4` 잔재 수정**: week10_plan.md 244행 API 초안에 `"model": "grok-4"` 잔재가 있음. `glm-4.7-flash`로 수정할 것.

4. **모델 선택 원칙 반영**: `DRAFT_CREATIVE`는 Z.AI (GLM), Analytical/Structured는 OpenAI가 현재 구성. plan의 preset 예시도 이에 맞게 업데이트할 것.

---

## 참고 파일

- `week10_plan.md` — 10주차 전체 계획
- `app/core/config.py` — Z.AI 지원 포함 최신 버전
- `app/core/cost_tracker.py` — GLM/Gemini 가격 포함 최신 버전
