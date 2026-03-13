# 04. 라우팅 규칙 명세

## 개요

Router는 입력 태스크를 분석하여 **single**(단일 LLM 호출) 또는 **moa**(Multi-Agent Orchestration 파이프라인) 중 최적 경로를 자동 선택한다.

## 2단계 하이브리드 라우팅

### 1단계: Rule-based 필터 (LLM 호출 없음)

명확한 패턴은 규칙 기반으로 즉시 분류하여 LLM 호출 비용을 절약한다.

| 조건 | 경로 | 확신도 | 근거 |
|------|------|--------|------|
| `task_type == "summarize"` + `difficulty == "low"` | single | 0.9 | 단순 요약은 단일 호출 충분 |
| `task_type == "ideate"` | moa | 0.85 | 창의적 과제 → 다중 관점 필요 |
| `task_type == "critique_rewrite"` | moa | 0.9 | 비평+재작성 → MOA 파이프라인 필요 |
| `len(prompt) > 500` | moa | 0.7 | 긴 프롬프트 → 복합 과제 가능성 |
| `"novelty" in constraints` | moa | 0.8 | novelty 요구 → 다양성 필요 |
| 그 외 | None | — | 2단계 LLM 판별로 위임 |

### 2단계: LLM 판별 (1단계 미결정 시)

1단계에서 `None`을 반환하면, LLM에게 태스크 유형·프롬프트·제약 조건을 전달하여 경로를 판정한다.

- **temperature:** 0.2 (일관된 판정)
- **응답 형식:** JSON (`selected_path`, `reason`, `confidence`)
- **파싱 실패 폴백:** moa (더 안전한 선택)

## 경로별 파이프라인

### single 경로
```
Input → BaseAgent 단일 호출 → Output
```

### moa 경로
```
Input → Draft×3 (병렬) → Critic → Synthesizer → Judge
  ├─ pass     → Output
  ├─ rewrite  → Rewrite → Judge (최대 2회)
  └─ escalate → 로그 + 사람 검토 플래그
```

## 6주차 확장 예고

| 현재 (5주차) | 6주차 확장 |
|-------------|-----------|
| `single \| moa` | `single \| moa \| moa+rag \| moa+mcp \| moa+rag+mcp` |
| `requires_rag = False` | RAG 컨텍스트 주입 활성화 |
| `requires_mcp = False` | MCP 도구 호출 활성화 |

## 비용 최적화

- Rule-based 필터가 ~60% 케이스를 처리 → LLM 라우팅 호출 절약
- Rule-based가 확실한 경우만 처리하므로 오분류 최소화
- 애매한 케이스에서만 LLM을 호출하여 비용 대비 정확도 극대화
