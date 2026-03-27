# Week 9 Plan — Baseline Sweep · Comparison Hardening · Retrospective

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 9주차 |
| **상태** | ✅ 완료 (2026-04-20) |
| **작성일** | 2026-04-20 |
| **목표** | baseline 12케이스 sweep → RAG/MCP 3건 확장 → 3-group 비교표 완성 → 회고 마감 |

---

## 선행 완료 항목

| 항목 | 커밋 |
|---|---|
| C7-1 routing trace + --evaluate 플래그 | `3df7374` |
| C7-2 ChromaRetriever + RAG 경로 | `d0e4c69` |
| C7-3 공식 mcp SDK + Filesystem whitelist | `b4cef10` |
| OpenAI 런타임 복구 + GPT-5 호환 | `a6d700c` |
| moa+rag 실주행 1건, moa+mcp 실주행 1건 | `data/outputs/` |
| 143 tests passed | — |

---

## 3단계 커밋 구조

| 단계 | 지침 파일 | 커밋 메시지 | 핵심 작업 |
|---|---|---|---|
| C9-1 | `week9_c1_implement.md` | `feat(eval): add baseline sweep single-vs-moa` | v1.json 12케이스 × 2경로 실행 |
| C9-2 | `week9_c2_implement.md` | `feat(eval): expand rag-mcp benchmark to 3 cases` | v1_rag_mcp.json 확장 + 추가 실행 |
| C9-3 | `week9_c3_implement.md` | `docs(retrospective): finalize comparison and week9 log` | 비교표 CSV + 증거 커밋 + 회고 |

각 단계의 구현 세부사항은 위 지침 파일을 참고한다.  
C9-1 → C9-2 → C9-3 순서로 진행한다. 앞 단계가 DoD를 충족해야 다음 단계로 넘어간다.

---

## DoD (전체)

- [x] Comparator `baseline` 그룹 `count=12` 출력
- [x] Comparator `rag` 그룹 `count=3` 출력, 모든 케이스 `retriever=ChromaRetriever`
- [x] Comparator `mcp` 그룹 `count=3` 출력, 모든 케이스 `success=true`
- [x] `data/outputs/comparison_w9_final.csv` 존재
- [x] 대표 증거 2건 git 추적됨
- [x] `docs/06_experiment_log.md` Week 9 섹션 완성
- [x] `claude.md` 9주차 ✅ 완료 표시

---

## 예상 비용 / 소요 시간

| 단계 | 시간 | API 비용 |
|---|---|---|
| C9-1 | ~30분 | ~$0.035 |
| C9-2 | ~30분 | ~$0.020 |
| C9-3 | ~20분 | $0 |
| **합계** | **~80분** | **~$0.055** |

---

## 변경 기록

### 2026-04-20

- Week 9 계획 최초 작성.
- 세부 구현은 week9_c1/c2/c3_implement.md로 분리.
