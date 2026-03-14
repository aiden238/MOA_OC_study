"""MCP 클라이언트 패키지.

최소 기능의 MCP 호출 래퍼를 제공하며, 테스트/로컬 실행을 위해
`mock://` 스킴을 통해 간단한 시뮬레이션을 지원합니다.
"""

from .client import MCPClient

__all__ = ["MCPClient"]
