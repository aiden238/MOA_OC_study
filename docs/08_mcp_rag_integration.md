# MCP & RAG 통합 명세

이 문서는 6주차에서 추가된 MCP 클라이언트와 RAG 파이프라인의 통합 방식을 설명합니다.

요약:
- `app/rag`: 문서 청킹, 간이 임베더, 간이 리트리버 제공
- `app/mcp_client`: MCP 서버 호출을 위한 최소 클라이언트 (mock 시뮬레이션 포함)
- `Router`는 `requires_rag`/`requires_mcp` 플래그를 반환할 수 있으며, `MOAExecutor`는 해당 플래그에 따라 컨텍스트를 주입합니다.

운영 원칙:
- 로컬/테스트 환경에서는 `SimpleRetriever`와 `mock://local` MCP 서버를 사용하여 외부 의존성을 최소화합니다.
- 실제 배포 시에는 ChromaDB, Milvus 등의 벡터 DB와 실제 MCP 서버 URL을 설정하여 사용합니다.
