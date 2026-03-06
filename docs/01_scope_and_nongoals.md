# 01. 범위 및 Non-Goals

## 6주 범위

| 주차 | 핵심 산출물 |
|------|------------|
| 1주차 | 프로젝트 뼈대, config, logger, timer, docs/00~02 |
| 2주차 | Pydantic 스키마 3종, BaseAgent, 프롬프트 파일 |
| 3주차 | 벤치마크 v1, run_single.py, 루브릭 평가 |
| 4주차 | Draft×3, Critic, Synthesizer, run_moa.py |
| 5주차 | Router, Judge, Rewrite, run_full.py |
| 6주차 | RAG, MCP, compare_runs.py, 회고 |

## 가드레일 (8항목)

| # | 제약 조건 |
|---|----------|
| 1 | LangChain / CrewAI / AutoGen 사용 금지 |
| 2 | 1~5주차 동안 모델 단일화 (하나만 사용) |
| 3 | UI 개발 금지 (CLI + JSON 로그만) |
| 4 | 도메인 데이터 지양 (범용 벤치마크만) |
| 5 | RAG·MCP는 6주차에만 (그 전에 도입 금지) |
| 6 | 한 주에 3커밋 초과 금지 |
| 7 | 새 의존성 추가 시 라이선스 확인 필수 (MIT / Apache 2.0만) |
| 8 | 문서 없이 코드만 커밋하지 않기 (문서가 기준, 코드가 증명) |

## Non-Goals (6주 범위 밖)

- 범용 초거대 에이전트 완성
- 자체 파운데이션 모델 개발
- 복잡한 프론트엔드 UI 완성
- 대규모 배포 인프라 / 운영 수준 비용 최적화
- 브라우저 자동화
