# Week 9 C9-1 Implement Guide — Baseline Sweep

## 목표

`v1.json` 12케이스를 `single`과 `moa` 두 경로로 각각 실행해  
Comparator의 `baseline` 그룹을 활성화한다.

이것이 프로젝트의 핵심 질문  
**"멀티 에이전트 오케스트레이션이 단일 호출보다 실제로 나은가?"**  
에 답하는 유일한 데이터다.

---

## 범위

- `data/benchmarks/v1.json` — 읽기 전용 (수정하지 않는다)
- `scripts/run_full.py` — 실행만, 코드 변경 없음
- `data/outputs/` — 결과 파일 24건 생성
- `data/traces/` — trace 파일 자동 생성

코드 변경은 없다. 명령어 실행과 출력 검증만 수행한다.

---

## 선행 조건

- `week9_plan.md` 숙지
- `.env`에 `OPENAI_API_KEY` 설정됨
- `python -c "from app.core.config import OPENAI_API_KEY; print(bool(OPENAI_API_KEY))"` → `True`
- `python -m pytest -q` → `143 passed` (또는 그 이상)
- `data/outputs/` 디렉토리 존재 (없으면 자동 생성됨)

---

## 사전 점검

아래를 먼저 실행해 현재 상태를 확인한다.

```bash
# 현재 비교표 확인 — baseline 그룹이 없어야 정상
python scripts/compare_runs.py --dir data/outputs --format table

# 현재 outputs 파일 목록 확인
ls data/outputs/
```

기대 출력:
- `rag`, `mcp` 그룹만 출력되고 `baseline` 없음
- `data/outputs/`에 `full_rag-001__*`, `full_mcp-001__*` 파일 4건만 존재

---

## 구현 상세

### A. single 경로 12케이스 전체 실행

```bash
python scripts/run_full.py \
  --benchmark v1.json \
  --force-path single \
  --evaluate \
  --output-tag single
```

- `--force-path single`: Router를 무시하고 단일 LLM 호출 강제
- `--evaluate`: rubric 평가 실행 (evaluation 필드 채움)
- `--output-tag single`: 결과 파일명에 `__single` 태그 추가

완료 후 생성 파일 확인:

```bash
ls data/outputs/ | grep "__single"
# 기대: 12개 파일
# full_sum-001__single.json, full_sum-002__single.json, ...
```

### B. moa 경로 12케이스 전체 실행

```bash
python scripts/run_full.py \
  --benchmark v1.json \
  --force-path moa \
  --evaluate \
  --output-tag moa
```

완료 후 생성 파일 확인:

```bash
ls data/outputs/ | grep "__moa"
# 기대: 12개 파일
```

### C. 비교표 확인

```bash
python scripts/compare_runs.py --dir data/outputs --format table
```

기대 출력:

```
{'group': 'baseline', 'left_path': 'single', 'right_path': 'moa', 'count': 12, ...}
{'group': 'rag', ...}
{'group': 'mcp', ...}
```

---

## 검증 기준

아래를 모두 충족해야 C9-1 DoD 달성으로 본다.

| 검증 항목 | 기준 |
|---|---|
| single 결과 파일 수 | `ls data/outputs/ \| grep "__single" \| wc -l` → `12` |
| moa 결과 파일 수 | `ls data/outputs/ \| grep "__moa" \| wc -l` → `12` |
| baseline count | Comparator 출력 `count=12` |
| evaluation 채워짐 | 임의 파일 1건 열어 `evaluation.avg_score` 숫자 확인 |
| path 필드 | single 파일 → `"path": "single"`, moa 파일 → `"path": "moa"` |

빠른 검증 명령:

```bash
python -c "
import json, pathlib
singles = list(pathlib.Path('data/outputs').glob('*__single.json'))
moas = list(pathlib.Path('data/outputs').glob('*__moa.json'))
print(f'single: {len(singles)}건, moa: {len(moas)}건')
for f in singles[:1]:
    d = json.loads(f.read_text(encoding='utf-8'))
    print(f'  path={d[\"path\"]}, avg_score={d[\"evaluation\"].get(\"avg_score\")}')
"
```

---

## 블로커 조건

| 상황 | 조치 |
|---|---|
| `OPENAI_API_KEY` 미설정 | `.env` 확인 후 재시작 |
| 일부 케이스만 실행됨 (count < 12) | 누락 case-id 확인 후 `--case-id` 개별 재실행 |
| `evaluation.avg_score == None` 전체 | rubric 호출 실패 — `EVAL_MODEL` env 확인 |
| Comparator `baseline` 여전히 없음 | `path` 필드 값 확인 (single/moa가 정확히 매칭되는지) |

---

## 커밋

C9-1 DoD 달성 후 아래 커밋을 생성한다.  
`data/outputs/`는 `.gitignore` 대상이므로 **결과 파일은 이 커밋에 포함하지 않는다.**  
결과 파일 커밋은 C9-3에서 수행한다.

```bash
# v1.json은 변경하지 않으므로 커밋할 파일이 없을 수 있음
# 이 경우 C9-1은 실행 단계만으로 완료 처리한다
# 만약 run_full.py나 scripts에 버그 수정이 발생했다면 그것만 커밋한다

git commit -m "feat(eval): run baseline sweep single-vs-moa on v1 benchmark"
```

실행 결과만 있고 코드 변경이 없으면 커밋 없이 C9-2로 넘어간다.

---

## 완료 기준 요약

- [ ] single 12건 생성
- [ ] moa 12건 생성
- [ ] Comparator baseline `count=12`
- [ ] 모든 파일 `evaluation.avg_score` 숫자

---

## 권장 커밋 메시지

```
feat(eval): run baseline sweep single-vs-moa on v1 benchmark
```
