"""MCP 서버에 도구 호출을 보내는 최소 클라이언트 구현.

이 모듈은 실제 MCP 서버가 없을 때를 대비한 `mock://` 스킴 시뮬레이션을 제공하며,
HTTP 기반 MCP 서버에 대해서는 `httpx`를 이용해 요청을 보낼 수 있습니다.
"""

import json
from typing import List

import httpx


class MCPClient:
    """간단한 MCP 클라이언트.

    실제 서버가 없을 때는 server_url로 "mock://local"을 주어
    내부 시뮬레이션을 수행할 수 있습니다.
    """

    async def list_tools(self, server_url: str) -> List[dict]:
        if server_url.startswith("mock://"):
            # 로컬 시뮬레이션 도구 목록
            return [{"name": "list_files", "description": "List files in workspace"}]

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{server_url.rstrip('/')}/tools")
            resp.raise_for_status()
            return resp.json()

    async def call_tool(self, server_url: str, tool_name: str, args: dict) -> dict:
        if server_url.startswith("mock://"):
            # 간단한 mock 동작: list_files 도구는 cwd의 파일 리스트 반환
            if tool_name == "list_files":
                import os

                files = [f for f in os.listdir('.') if os.path.isfile(f)]
                return {"status": "ok", "result": files}
            # 기본적으로 입력을 그대로 반환
            return {"status": "ok", "tool": tool_name, "args": args}

        async with httpx.AsyncClient() as client:
            url = f"{server_url.rstrip('/')}/call/{tool_name}"
            resp = await client.post(url, json=args)
            resp.raise_for_status()
            return resp.json()
