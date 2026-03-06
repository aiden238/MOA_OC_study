# 00. 프로젝트 목표

## 한 줄 정의

단일 LLM 호출(Baseline)부터 Multi-Agent Orchestration, MCP·RAG 통합까지 6주 단계적 확장 실험

## 왜 이 프로젝트를 하는가

1. 멀티 에이전트 오케스트레이션(MOA)이 단일 호출보다 **실제로** 나은지 정량적으로 검증한다.
2. Router → Planner → Draft → Critic → Synthesizer 파이프라인을 프레임워크 없이 직접 설계·구현한다.
3. 6주차까지 MCP 서버 통합, RAG 파이프라인을 **점진적으로** 추가하여 종합 오케스트레이션을 완성한다.
4. 모든 과정을 trace/logging으로 추적하고, baseline 대비 개선 여부를 정량적으로 비교한다.

## 핵심 질문

> "멀티 에이전트 오케스트레이션이 단일 호출보다 **실제로** 나은가?"

## 최종 목표 아키텍처 (6주차 완성)

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

## 비교 경로 (4가지)

| 경로 | 설명 | 도입 시점 |
|------|------|-----------|
| Path A: Single | 단일 LLM 호출 baseline | 3주차 |
| Path B: MOA | Draft×3 → Critic → Synthesizer | 4주차 |
| Path C: Full | Router → Judge → Rewrite 포함 전체 파이프라인 | 5주차 |
| Path D: RAG+MCP | Full + 외부 도구·문서 통합 | 6주차 |
