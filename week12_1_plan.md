# Week 12-1 Plan — 메타데이터 강화 RAG + 웹 UI 지식 패널

## 상태

| 항목 | 값 |
|------|-----|
| **주차** | 12주차 / Phase 1 |
| **상태** | 구현 대상 ✅ |
| **작성일** | 2026-05-01 |
| **목표** | RAG 문서에 메타데이터를 추가하고, 웹 UI에 "현재 RAG에 담긴 지식" 패널을 표시하여 사용자가 RAG와 관련된 질문을 할 수 있도록 안내한다. |

---

## 배경 및 문제

현재 RAG는 32개 문서(84 청크)를 보유하지만, 사용자는 **어떤 내용이 RAG에 있는지 전혀 알 수 없다**.  
결과적으로 RAG와 무관한 질문만 하게 되어 RAG 경로가 거의 실행되지 않는다.

**해결책**: 웹 UI 사이드바에 "RAG 지식 패널"을 추가하여 현재 인덱싱된 주제 목록과 예시 질문을 보여준다.

**현재 RAG 포함 내용 예시 (사용자에게 표시할 내용):**
- 프롬프트 엔지니어링: 퓨샷/제로샷 사용법, CoT, 역할 프롬프팅
- 컨텍스트 엔지니어링: 윈도우 관리, 메모리 계층, 지침 파일 구조
- 하네스 엔지니어링: 레이어 관리, 에이전트 루프, 맥락 유지법
- RAG/검색: 고급 RAG 설계, 벡터 DB, 청크 전략
- 멀티 에이전트: MOA 패턴, Critic-Revision, 오케스트레이션

---

## Week 12-1 원칙

- 백엔드에 `/api/rag-knowledge` 엔드포인트를 추가한다.
- 엔드포인트는 `data/rag_docs/`를 스캔해 YAML 프론트매터(있으면)와 파일명으로 카테고리를 파악한다.
- 웹 UI 사이드바에 **접을 수 있는 "📚 RAG 지식 베이스" 패널**을 추가한다.
- 각 카테고리별로 관련 문서 제목과 예시 질문 2~3개를 표시한다.
- 예시 질문 클릭 시 해당 질문이 입력창에 자동으로 채워진다(즉시 RAG 트리거 유도).
- 기존 백엔드(RAG 검색 로직, Chroma DB)는 변경하지 않는다.

---

## 데이터 흐름

```
GET /api/rag-knowledge
    ↓
server.py: scan data/rag_docs/*.txt
    ↓
각 파일에서 첫 번째 줄(제목) + 파일명으로 카테고리 추론
    ↓
JSON 응답: { categories: [ { name, docs: [{title, filename, example_questions}] } ] }
    ↓
app.js: renderKnowledgePanel(data)
    ↓
사이드바에 카테고리별 태그 + 예시 질문 렌더링
```

---

## 구현 범위

### C12-1-A. 백엔드: `/api/rag-knowledge` 엔드포인트

**파일**: `app/web/server.py`

추가 엔드포인트:
```python
@app.get("/api/rag-knowledge")
async def get_rag_knowledge():
    """현재 RAG에 인덱싱된 지식 목록 반환."""
    docs_dir = RAG_DOCS_DIR
    categories = _build_knowledge_catalog(docs_dir)
    return {"categories": categories, "total_docs": sum(len(c["docs"]) for c in categories)}
```

카탈로그 빌더 로직:
- `data/rag_docs/*.txt` 파일을 스캔
- 파일명 패턴으로 카테고리 분류:
  - `doc06~12` → 프롬프트 엔지니어링
  - `doc13~18`, `doc31` → 컨텍스트 엔지니어링
  - `doc19~24`, `doc28_harness` → 하네스 엔지니어링
  - `doc25~30` → 고급 기법 (RAG·MOA·평가·보안)
  - `doc01~05` → 기초 AI/검색
- 각 파일의 첫 번째 비어있지 않은 줄을 제목으로 추출
- 카테고리별 예시 질문 2~3개를 하드코딩 제공

### C12-1-B. 프론트엔드: RAG 지식 패널 (사이드바)

**파일**: `app/web/static/index.html`

사이드바에 추가:
```html
<!-- RAG 지식 베이스 패널 -->
<div class="sidebar-section" id="knowledge-section">
  <button class="sidebar-section-toggle" onclick="toggleKnowledge()">
    📚 RAG 지식 베이스 <span id="knowledge-toggle-icon">▼</span>
  </button>
  <div id="knowledge-panel" class="knowledge-panel">
    <div class="knowledge-loading">로딩 중...</div>
  </div>
</div>
```

**파일**: `app/web/static/app.js`

추가 함수:
```javascript
async function loadKnowledgePanel() { ... }
function renderKnowledgePanel(data) { ... }
function fillQuestionFromExample(question) {
  // 예시 질문 클릭 시 입력창에 자동 채워넣기
  inputEl.value = question;
  inputEl.focus();
}
function toggleKnowledge() { ... }
```

렌더링 결과 예시 (UI):
```
📚 RAG 지식 베이스                    ▼
┌────────────────────────────────────┐
│ 🔵 프롬프트 엔지니어링 (7개)        │
│   • 퓨샷/제로샷 프롬프팅            │
│   • Chain-of-Thought 기법           │
│   💬 "CoT 프롬프팅이란 무엇인가요?" │
│   💬 "Few-shot 예시 몇 개가 좋을까" │
├────────────────────────────────────┤
│ 🟢 컨텍스트 엔지니어링 (7개)        │
│   • 컨텍스트 윈도우 관리            │
│   • 메모리 계층 설계                │
│   💬 "컨텍스트 압축 기법 설명해줘"  │
├────────────────────────────────────┤
│ 🟠 하네스 엔지니어링 (7개)          │
│   ...                               │
└────────────────────────────────────┘
```

**파일**: `app/web/static/styles.css`

추가 스타일:
- `.knowledge-panel`: 접을 수 있는 패널 컨테이너
- `.knowledge-category`: 카테고리 헤더 (색상 코딩)
- `.knowledge-doc-item`: 문서 제목 항목
- `.knowledge-example-question`: 예시 질문 버튼 (클릭 → 입력창 채우기)
- `.knowledge-badge`: 문서 수 배지

### C12-1-C. YAML 메타데이터 스키마 도입 (선택적)

기존 `.txt` 파일 형식을 유지하면서, 첫 번째 줄을 제목으로, 두 번째 줄 이하를 본문으로 처리한다.  
향후 Phase 2에서 YAML 프론트매터(---로 감싸는 형식)로 확장할 수 있도록 파서를 준비한다.

```python
def parse_doc_metadata(file_path: Path) -> dict:
    """파일 첫 줄을 제목으로, 나머지를 본문으로 파싱. YAML 프론트매터가 있으면 추가 처리."""
    text = file_path.read_text(encoding="utf-8")
    lines = text.strip().split("\n")
    # YAML 프론트매터 체크 (---로 시작하면 파싱)
    if lines[0].strip() == "---":
        # Phase 2용 확장 포인트
        pass
    return {
        "title": lines[0].strip(),
        "filename": file_path.name,
        "word_count": len(text.split()),
    }
```

---

## 변경 대상 파일

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `app/web/server.py` | 수정 | `/api/rag-knowledge` 엔드포인트 추가 |
| `app/web/static/index.html` | 수정 | RAG 지식 패널 HTML 추가 |
| `app/web/static/app.js` | 수정 | 패널 로딩·렌더링·인터랙션 함수 추가 |
| `app/web/static/styles.css` | 수정 | 패널 스타일 추가 |

---

## 세부 구현 단계

| 단계 | 핵심 작업 | 커밋 제안 |
|------|-----------|-----------|
| A | `/api/rag-knowledge` 엔드포인트 구현 | `feat(rag): add rag-knowledge catalog API` |
| B | 사이드바 패널 HTML + JS 구현 | `feat(web): add RAG knowledge panel to sidebar` |
| C | 예시 질문 클릭 → 입력창 자동 채우기 | `feat(web): example question click-to-fill` |
| D | 스타일 + 카테고리 색상 코딩 | `style(web): knowledge panel category colors` |

---

## DoD

- [ ] GET `/api/rag-knowledge` 응답에 카테고리별 문서 목록 포함
- [ ] 사이드바에 "📚 RAG 지식 베이스" 패널 표시 (접기/펼치기 가능)
- [ ] 카테고리별 색상 구분
- [ ] 각 카테고리에 예시 질문 2~3개 표시
- [ ] 예시 질문 클릭 시 입력창에 자동 채워짐
- [ ] 총 문서 수 및 카테고리 수 상단에 요약 표시
- [ ] 기존 기능(RAG 검색, MCP, MOA 파이프라인)에 회귀 없음

---

## 리스크

| 상황 | 대응 |
|------|------|
| 파일명 패턴으로 카테고리 분류가 부정확할 수 있음 | 카테고리 매핑 테이블을 `server.py`에 하드코딩 |
| 문서 수가 많아 UI가 길어짐 | 카테고리별 접기/펼치기로 처리 |
| 새 문서 추가 시 카테고리 미분류 | 기본 카테고리("기타")로 폴백 |
