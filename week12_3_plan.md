# Week 12-3 Plan — Self-Updating LLM Wiki

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 12주차 / Phase 3 |
| **상태** | 장기 기획 🗓️ (Phase 1·2 완료 후 착수) |
| **작성일** | 2026-05-02 |
| **목표** | 새로운 LLM 기법·논문·모델 정보가 등장할 때 자동으로 RAG 지식 베이스를 갱신하는 Self-Updating Wiki 파이프라인을 구축한다. |

---

## 배경

현재 RAG의 구조적 한계:
- 지식이 정적(Static): 새 논문·모델이 나와도 반영 불가
- 수동 업데이트 필요: 사람이 직접 `.txt` 파일을 추가해야 함
- 버전 관리 없음: 기존 문서의 변경 이력 추적 불가

Self-Updating Wiki의 목표:
- 주 1회 자동으로 새 LLM 기법·논문을 검색·수집
- LLM이 수집된 정보를 평가하고 Wiki 형식으로 변환
- 자동 재인덱싱으로 검색에 즉시 반영
- 사람은 최종 승인만 담당 (Human-in-the-Loop)

---

## 시스템 아키텍처

```
[스케줄러: 주 1회 실행]
         ↓
[수집 에이전트 (Collector Agent)]
  - 웹 검색: "LLM 최신 기법", "prompt engineering 2026"
  - arXiv RSS 피드 모니터링
  - GitHub trending repositories
         ↓
[평가 에이전트 (Evaluator Agent)]
  - 수집된 정보의 신뢰성·관련성 평가
  - 중복 감지: 기존 Wiki와 유사도 비교
  - 점수 < 0.6이면 제외
         ↓
[변환 에이전트 (Writer Agent)]
  - 원문 → Wiki 형식 문서로 변환
  - YAML 프론트매터 자동 생성
  - 기존 노드와의 관계 추론
         ↓
[검토 단계 (Human-in-the-Loop)]
  - 관리자 UI에서 새 문서 목록 확인
  - 승인/거부/수정 후 적용
         ↓
[업데이트 에이전트 (Updater Agent)]
  - 승인된 문서를 data/rag_docs/에 저장
  - Chroma DB 재인덱싱
  - 지식 그래프 노드/에지 자동 업데이트
  - 변경 이력 git commit
```

---

## 핵심 컴포넌트 설계

### 1. 수집 에이전트 (Collector Agent)

```python
class CollectorAgent(BaseAgent):
    """새로운 LLM 지식을 웹에서 수집."""
    
    async def collect(self, topics: list[str]) -> list[CollectedItem]:
        """지정된 주제에 대한 최신 정보를 수집."""
        items = []
        for topic in topics:
            # arXiv API 쿼리
            arxiv_results = await self._query_arxiv(topic)
            # 웹 검색 (MCP filesystem 활용)
            web_results = await self._web_search(topic)
            items.extend(arxiv_results + web_results)
        return items
```

수집 대상:
- arXiv: cs.AI, cs.LG, cs.CL 카테고리 최신 논문
- GitHub: awesome-prompt-engineering 등 curated list
- 블로그: Anthropic, OpenAI 공식 블로그

### 2. 평가 에이전트 (Evaluator Agent)

```python
class EvaluatorAgent(BaseAgent):
    """수집된 정보의 품질을 평가."""
    
    EVALUATION_PROMPT = """
    다음 기준으로 수집된 정보를 평가하세요:
    1. 관련성 (0-1): LLM 기법/엔지니어링 주제인가?
    2. 신뢰성 (0-1): 출처가 신뢰할 수 있는가?
    3. 참신성 (0-1): 기존 Wiki와 얼마나 다른 내용인가?
    4. 품질 (0-1): 내용이 충분히 상세하고 정확한가?
    
    종합 점수가 0.6 미만이면 exclude, 이상이면 include.
    """
```

### 3. 변환 에이전트 (Writer Agent)

```python
class WikiWriterAgent(BaseAgent):
    """수집된 정보를 Wiki 문서 형식으로 변환."""
    
    WRITER_PROMPT = """
    수집된 정보를 다음 형식의 Wiki 문서로 변환하세요:
    
    ---
    title: [문서 제목]
    category: [prompt_engineering|context_engineering|harness_engineering|advanced]
    tags: [태그1, 태그2]
    related: [연관 문서 파일명 목록]
    source_url: [원본 URL]
    confidence: [0-1, 정보 신뢰도]
    created_date: [YYYY-MM-DD]
    ---
    
    [본문: 핵심 개념 설명, 사용 방법, 예시 코드]
    """
```

### 4. YAML 프론트매터 스키마

Phase 2부터 모든 새 문서에 적용:
```yaml
---
id: doc_uuid_or_sequence
title: "문서 제목"
category: prompt_engineering  # context_engineering | harness_engineering | advanced | basics
tags:
  - CoT
  - reasoning
  - few-shot
related:
  - doc08_chain_of_thought.txt
  - doc07_zero_few_shot.txt
difficulty: beginner  # intermediate | advanced
source_url: https://arxiv.org/...  # 선택적
confidence: 0.9  # 정보 신뢰도
created_date: 2026-05-03
last_updated: 2026-05-03
---
[본문]
```

---

## 버전 관리 및 변경 이력

### Git 기반 문서 이력 추적

```
data/rag_docs/
  wiki_versions/
    v1/  ← 초기 32개 문서
    v2/  ← Phase 3 첫 번째 업데이트
    v3/  ← ...
  changelog.json  ← 변경 이력 메타데이터
```

### 변경 이력 스키마

```json
{
  "version": "2.1",
  "updated_at": "2026-05-10",
  "changes": [
    {
      "action": "added",
      "filename": "doc32_qwen3_prompting.txt",
      "title": "Qwen3 모델 프롬프팅 기법",
      "category": "prompt_engineering",
      "source": "arxiv:2506.xxxxx"
    }
  ]
}
```

---

## 웹 UI 업데이트 알림

Phase 3가 완료되면 웹 UI에 다음 기능 추가:
- 사이드바의 "📚 RAG 지식 베이스" 패널에 "마지막 업데이트: N일 전" 표시
- 새 문서 추가 시 패널에 🆕 배지 표시
- 관리자가 웹 UI에서 업데이트 결과 검토·승인

---

## 기술 스택 및 의존성

| 컴포넌트 | 기술 | 라이선스 |
|---------|------|---------|
| arXiv 수집 | arxiv Python SDK | MIT ✅ |
| 웹 스케줄링 | APScheduler | MIT ✅ |
| HTML 파싱 | BeautifulSoup4 | MIT ✅ |
| 중복 감지 | 기존 Chroma 임베딩 활용 | — |
| 문서 변환 | 기존 LLM 에이전트 재사용 | — |

---

## 구현 우선순위 및 리스크

### 높은 리스크
- 웹 수집 시 저작권 문제 → 공개 API(arXiv, GitHub)만 사용, 원본 URL 기록
- LLM 변환 품질 불안정 → Human-in-the-Loop로 보완
- 자동 업데이트로 인한 품질 저하 → 엄격한 점수 기준(0.6) 적용

### 구현 순서
1. 수동 모드 먼저: 사람이 트리거하는 수동 업데이트 파이프라인
2. 반자동 모드: 스케줄러가 수집, 사람이 승인
3. 완전 자동 모드: 신뢰도 높은 소스는 자동 승인

---

## DoD (Phase 3)

- [ ] `CollectorAgent`가 arXiv에서 최신 논문을 수집
- [ ] `EvaluatorAgent`가 관련성·품질 점수를 산출
- [ ] `WikiWriterAgent`가 YAML 프론트매터 포함 문서를 생성
- [ ] 관리자 검토 인터페이스 (CLI 또는 웹 UI)
- [ ] 승인 후 자동 재인덱싱 및 그래프 업데이트
- [ ] `changelog.json`에 변경 이력 기록
- [ ] 웹 UI에 "마지막 업데이트" 및 🆕 배지 표시
