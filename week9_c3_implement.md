# Week 9 C9-3 Implement Guide — Comparison · Evidence · Retrospective

## 목표

C9-1과 C9-2에서 확보된 실주행 결과를 토대로  
3-group 최종 비교표를 완성하고, 핵심 증거를 git에 보존하고,  
실험 회고 문서로 Week 9를 마감한다.

---

## 범위

- `data/outputs/comparison_w9_final.csv` — 신규 생성
- `data/outputs/full_rag-001__rag.json` — git force-add (대표 증거)
- `data/outputs/full_mcp-001__mcp.json` — git force-add (대표 증거)
- `data/benchmarks/v1_rag_mcp.json` — 이미 C9-2에서 커밋됨
- `docs/06_experiment_log.md` — Week 9 섹션 추가
- `claude.md` — 9주차 상태 갱신
- `week9_plan.md` — DoD 체크 완료 표시

코드(`.py`) 변경은 없다.

---

## 선행 조건

- **C9-1 완료**: Comparator `baseline` 그룹 `count=12`
- **C9-2 완료**: Comparator `rag`, `mcp` 그룹 각 `count=3`
- 아래 명령으로 선행 조건을 먼저 확인한다.

```bash
python scripts/compare_runs.py --dir data/outputs --format table
# 기대: baseline(12), rag(3), mcp(3) 모두 출력
```

---

## 구현 상세

### A. 최종 비교표 CSV 생성

```bash
python scripts/compare_runs.py --dir data/outputs --format csv \
  > data/outputs/comparison_w9_final.csv

# 내용 확인
cat data/outputs/comparison_w9_final.csv
```

기대 출력 형태:

```
group,left_path,right_path,count,avg_score_delta,avg_cost_delta,avg_latency_delta,avg_tokens_delta
baseline,single,moa,12,[값],[값],[값],[값]
rag,moa,moa+rag,3,[값],[값],[값],[값]
mcp,moa,moa+mcp,3,[값],[값],[값],[값]
```

---

### B. 비교 결과 해석 (docs/06_experiment_log.md 작성 기준)

비교표 수치를 읽어 아래 해석 기준을 적용한다.

**baseline (single vs moa)**

| 조건 | 해석 |
|---|---|
| `avg_score_delta > 0` | MOA가 품질 우위 — 실험 가설 지지 |
| `avg_score_delta == 0` | 동등 — 비용 대비 효과 없음 |
| `avg_score_delta < 0` | single 우위 — 예상 밖 결과, 원인 분석 필요 |
| `avg_cost_delta` | moa 비용이 single 대비 증가량 (예상: 10배 내외) |
| `avg_latency_delta` | moa 지연이 single 대비 증가량 (예상: 양수) |

**rag (moa vs moa+rag)**

| 조건 | 해석 |
|---|---|
| `avg_score_delta > 0` | RAG 주입이 품질을 올림 |
| `avg_groundedness_delta > 0` | 근거 기반 응답 향상 (있으면 기재) |
| `avg_cost_delta` | 임베딩 + 추가 토큰 비용 (예상: 소폭 증가) |

**mcp (moa vs moa+mcp)**

| 조건 | 해석 |
|---|---|
| `avg_score_delta > 0` | 도구 결과가 품질에 기여 |
| `avg_cost_delta < 0` | mcp+moa가 plain moa보다 저렴할 수 있음 (케이스 특성) |
| count=3, 편차 큰 경우 | 도구 호출 특성상 케이스별 편차 크다고 명시 |

**단정 금지 조건**: 어떤 그룹이든 `count < 5`이면 "경향 관찰"로만 표현한다.

---

### C. 증거 파일 git 커밋

`data/outputs/`는 `.gitignore` 대상이므로 선택 파일만 `force-add`한다.

```bash
# 대표 증거 2건 + 비교표 CSV
git add -f data/outputs/full_rag-001__rag.json
git add -f data/outputs/full_mcp-001__mcp.json
git add -f data/outputs/comparison_w9_final.csv

# 커밋
git commit -m "feat(eval): add baseline sweep results and final 3-group comparison"
```

---

### D. docs/06_experiment_log.md 갱신

`docs/06_experiment_log.md` 파일에 아래 섹션을 추가한다.  
`[실측값]` 자리에는 CSV에서 읽은 실제 수치를 기입한다.

```markdown
## Week 9 실험 결과 (2026-04-20)

### 실험 환경

- 기본 모델: `.env`의 `DEFAULT_MODEL`
- 임베딩: `text-embedding-3-small`
- 벤치마크: `v1.json` (12케이스), `v1_rag_mcp.json` (6케이스)
- 평가 모델: `EVAL_MODEL` (기본 gpt-4o-mini)

### Baseline 비교 (single vs moa, n=12)

| 지표 | 값 |
|---|---|
| avg_score_delta | [실측값] |
| avg_cost_delta | [실측값] |
| avg_latency_delta | [실측값] |
| avg_tokens_delta | [실측값] |

해석: [baseline 해석 기준 적용하여 1~2문장 서술]

### RAG 비교 (moa vs moa+rag, n=3)

| 지표 | 값 |
|---|---|
| avg_score_delta | [실측값] |
| avg_cost_delta | [실측값] |
| avg_latency_delta | [실측값] |

해석: [rag 해석 기준 적용하여 1~2문장 서술]

### MCP 비교 (moa vs moa+mcp, n=3)

| 지표 | 값 |
|---|---|
| avg_score_delta | [실측값] |
| avg_cost_delta | [실측값] |
| avg_latency_delta | [실측값] |

해석: [mcp 해석 기준 적용하여 1~2문장 서술]

### 핵심 발견

1. [가장 중요한 발견 — 수치 기반]
2. [두 번째 발견]
3. [세 번째 발견]

### 한계

- 케이스 수: baseline 12, rag/mcp 각 3 — 통계적 결론 단정 불가
- 단일 도메인 벤치마크 (범용 텍스트 위주)
- 평가 모델과 생성 모델이 동일 계열 — 평가 편향 가능성
- MCP 케이스의 편차가 RAG 대비 높을 수 있음 (도구 결과 특성)
```

---

### E. claude.md 상태 갱신

`claude.md`의 진행 상태 테이블에서 9주차 행을 추가 또는 갱신한다.

```markdown
| 9주차 | ✅ 완료 | baseline sweep 12건, RAG/MCP 각 3건, 비교표 3-group | 2026-04-20 |
```

---

### F. week9_plan.md DoD 체크 완료

`week9_plan.md`의 DoD 체크박스를 실제 완료 여부에 맞게 갱신한다.

---

## 검증 기준

| 항목 | 확인 방법 |
|---|---|
| CSV 존재 | `ls data/outputs/comparison_w9_final.csv` |
| CSV 3개 그룹 | `cat` 결과에 baseline, rag, mcp 행 존재 |
| 대표 증거 git 추적 | `git status` 또는 `git show --stat HEAD` |
| 실험 로그 | `docs/06_experiment_log.md` Week 9 섹션 존재 |
| claude.md | 9주차 ✅ 표시 |

---

## 마무리 커밋

```bash
git add docs/06_experiment_log.md
git add claude.md
git add week9_plan.md

git commit -m "docs(retrospective): finalize comparison and week9 log"
```

---

## 완료 기준 요약

- [ ] `data/outputs/comparison_w9_final.csv` 3행 (baseline, rag, mcp)
- [ ] `full_rag-001__rag.json`, `full_mcp-001__mcp.json`, CSV git 추적됨
- [ ] `docs/06_experiment_log.md` Week 9 섹션 수치 채워짐
- [ ] `claude.md` 9주차 ✅ 완료 표시
- [ ] `week9_plan.md` DoD 체크 완료

---

## 권장 커밋 메시지

```
# 커밋 1 (증거 파일)
feat(eval): add baseline sweep results and final 3-group comparison

# 커밋 2 (회고 문서)
docs(retrospective): finalize comparison and week9 log
```
