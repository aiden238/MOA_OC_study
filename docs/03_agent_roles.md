# 03. 에이전트 역할 명세

## 역할 개요

| 역할 | 목적 | 입력 | 출력 | 도입 주차 |
|------|------|------|------|-----------|
| Planner | 태스크를 하위 작업으로 분해 | TaskRequest | subtasks 리스트 | 5주차 |
| Draft (Analytical) | 분석적 관점의 초안 | user_message + system_prompt | 구조화된 텍스트 | 4주차 |
| Draft (Creative) | 창의적 관점의 초안 | user_message + system_prompt | 자유로운 텍스트 | 4주차 |
| Draft (Structured) | 단계별 설명 초안 | user_message + system_prompt | 번호 매긴 텍스트 | 4주차 |
| Critic | 3개 draft의 강점/약점 분석 | 3개 draft 텍스트 | 비교 분석 | 4주차 |
| Judge | 최종 품질 판정 | synthesized output | pass/rewrite/escalate | 5주차 |
| Rewrite | 피드백 기반 재작성 | original + feedback | 개선된 텍스트 | 5주차 |
| Synthesizer | 여러 draft의 장점 조합 | drafts + critic feedback | 최종 결과 | 4주차 |

## Draft 다양성 확보 전략

| Draft Agent | 관점 지시 | temperature | 출력 스타일 |
|-------------|-----------|-------------|-------------|
| draft_analytical | 분석적이고 논리적인 관점 | 0.4 | 구조화된 설명 |
| draft_creative | 창의적이고 비유를 활용하는 관점 | 0.9 | 자유로운 서술 |
| draft_structured | 비전공자도 이해할 수 있게 단계적으로 | 0.6 | 단계별 정리 |

## 프롬프트 파일 위치

모든 프롬프트는 `app/prompts/` 디렉토리에 `.md` 파일로 관리됩니다.

| 파일명 | 역할 |
|--------|------|
| `planner.md` | Planner |
| `draft_analytical.md` | Draft (Analytical) |
| `draft_creative.md` | Draft (Creative) |
| `draft_structured.md` | Draft (Structured) |
| `critic.md` | Critic |
| `judge.md` | Judge |
| `rewrite.md` | Rewrite |
| `synthesizer.md` | Synthesizer |

## 프롬프트 파일 작성 규칙

- 파일 최상단에 `# Role: {역할명}` 헤더
- `## 지시사항` 섹션에 역할의 핵심 행동 지침
- `## 출력 형식` 섹션에 기대하는 출력 구조
- Markdown 포맷, 한국어 작성
- 변수 치환이 필요한 부분은 `{{variable}}` 형식 사용
