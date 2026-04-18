# Week 7 C7-3 Implement Guide

## 목표

Week 7의 세 번째 단계로 실동작 MCP를 연결하고, 이후 UI 문서를 새 구조에 맞게 정리한다.

- 공식 `mcp` SDK 기반 stdio 세션 도입
- Filesystem MCP를 1차 실제 서버로 연결
- tool trace / fallback / whitelist 정책 구현
- `week7_implement.md`를 C7-3 전용 UI 명세로 재작성

## 범위

- `app/mcp_client/`
- `app/orchestrator/executor.py`
- MCP 관련 테스트
- `week7_implement.md`

## 선행 조건

- C7-1과 C7-2가 먼저 완료되어야 한다.
- `executor.py`는 이미 `execute(task, logger, routing=None)` 시그니처를 가져야 한다. (C7-1 구현 결과)
- `TraceRecord`, `TraceLogger`는 이미 `operation_type`, `metadata` 필드를 지원해야 한다. (C7-1 구현 결과)
- Windows 환경에서 `node --version`, `npx.cmd --version`이 동작해야 한다.

## 핵심 결정

### 1. 사전 확인

구현 전에 아래를 먼저 확인한다.

- `node --version`
- `npx.cmd --version`

Windows PowerShell에서는 `npx` 대신 `npx.cmd`를 사용한다.

### 2. 전송 방식

- 공식 `mcp` SDK
- `stdio` transport 우선

stdio 연결 테스트를 먼저 성공시킨 후 executor 통합으로 넘어간다.

### 3. v1 서버 범위

1차 구현은 Filesystem MCP만 실제화한다.

### 4. 보안 경계

- read-only only
- whitelist 경로만 허용
- workspace 외부, `.env`, `.git`, `.venv` 차단

## 구현 상세

### A. registry / session manager

- 서버 이름
- command / args
- timeout
- 허용 tool 목록

### B. Filesystem MCP 정책

허용 루트:

- `docs/`
- `refs/`
- `data/rag_docs/`
- `data/outputs/`
- `data/traces/`
- `README.md`
- `week*_plan.md`
- `week*_implement.md`

차단:

- `.env`
- `.git/`
- `.venv/`
- workspace 외부 경로
- Windows system path
- 사용자 홈 디렉토리 외부 경로

### C. tool trace

trace metadata에 아래를 남긴다.

- `server_name`
- `tool_name`
- `args`
- `latency`
- `success`
- `normalized_result_summary`

### D. fallback

- MCP 세션 시작 실패
- tool timeout
- tool call 실패

위 경우에는 MOA-only로 폴백하고 trace에 실패 사유를 남긴다.

### E. UI 문서 재작성

`week7_implement.md`는 이 단계에서만 수정한다.

- 기존 웹 래퍼 중심 문서 정리
- 새 trace / result schema 기준 반영
- C7-3 전용 UI 명세로 재작성

## 테스트 계획

- `node --version`, `npx.cmd --version` 확인
- stdio MCP 연결 smoke test
- whitelist / path validation 테스트
- tool trace 기록 테스트
- timeout / failure fallback 테스트
- 3개 비교 테이블 생성 가능 여부 확인

## DoD

- MCP tests 통과
- tool trace 기록
- fallback 동작
- 3개 비교 테이블 생성 가능
- `week7_implement.md`가 C7-3 전용 UI 문서로 재작성됨

## 중단 조건

- `node` 또는 `npx.cmd`가 실제 구현 셸에서 실패할 때
- stdio MCP 세션을 안정적으로 시작할 수 없을 때
- Filesystem whitelist 경계를 안전하게 강제할 수 없을 때
- `mcp` SDK 설치 또는 라이선스가 정책과 충돌할 때

## 권장 커밋 메시지

```text
feat(mcp): implement filesystem mcp and rewrite week7 ui spec
```
