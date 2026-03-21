"""공식 MCP Python SDK 기반 Filesystem MCP 클라이언트."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT

try:  # pragma: no cover - 설치 여부는 런타임에서 확인
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
except ImportError:  # pragma: no cover
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
    types = None


WORKSPACE_ROOT = PROJECT_ROOT.resolve()
BLOCKED_PARTS = {".git", ".venv"}
ALLOWED_DIRECTORY_ROOTS = {
    "docs",
    "refs",
    "data/rag_docs",
    "data/outputs",
    "data/traces",
}
READ_ONLY_TOOLS = {
    "read_file",
    "read_text_file",
    "read_media_file",
    "read_multiple_files",
    "list_directory",
    "list_directory_with_sizes",
    "directory_tree",
    "search_files",
    "get_file_info",
    "list_allowed_directories",
}
TOOL_ALIASES = {
    "list_files": "list_allowed_directories",
}
WEEK_FILE_PATTERN = re.compile(r"(week\d+(?:_c\d+)?_(?:plan|implement)\.md)", re.IGNORECASE)


@dataclass
class MCPToolRequest:
    server_name: str
    tool_name: str
    args: dict[str, Any]


class MCPClient:
    """Filesystem MCP 서버에 읽기 전용으로 연결하는 클라이언트."""

    def __init__(
        self,
        project_root: Path | None = None,
        session_start_timeout_s: int = 10,
        tool_timeout_s: int = 8,
        max_tool_result_chars: int = 4000,
    ):
        self.project_root = Path(project_root or WORKSPACE_ROOT).resolve()
        self.session_start_timeout_s = session_start_timeout_s
        self.tool_timeout_s = tool_timeout_s
        self.max_tool_result_chars = max_tool_result_chars

    def _ensure_sdk_available(self):
        if ClientSession is None or StdioServerParameters is None or stdio_client is None:
            raise RuntimeError("mcp Python SDK가 설치되지 않았습니다.")

    def _filesystem_server_params(self):
        self._ensure_sdk_available()
        command = "npx.cmd" if os.name == "nt" else "npx"
        return StdioServerParameters(
            command=command,
            args=["-y", "@modelcontextprotocol/server-filesystem", "."],
            cwd=str(self.project_root),
        )

    @staticmethod
    def _looks_like_week_file(prompt: str) -> str | None:
        match = WEEK_FILE_PATTERN.search(prompt)
        if match:
            return match.group(1)
        return None

    def plan_filesystem_request(self, prompt: str, preferred_tool: str | None = None) -> MCPToolRequest:
        """프롬프트를 기준으로 안전한 Filesystem MCP 호출을 계획한다."""
        lowered = prompt.lower()
        if "readme.md" in lowered or "readme" in lowered:
            return MCPToolRequest("filesystem", "read_text_file", {"path": "README.md"})

        week_file = self._looks_like_week_file(prompt)
        if week_file:
            return MCPToolRequest("filesystem", "read_text_file", {"path": week_file})

        canonical_tool = TOOL_ALIASES.get(preferred_tool or "", preferred_tool)
        directory_tool = canonical_tool if canonical_tool and canonical_tool != "list_allowed_directories" else "list_directory"
        if "refs" in lowered:
            return MCPToolRequest("filesystem", directory_tool, {"path": "refs"})
        if "docs" in lowered or "문서" in prompt:
            return MCPToolRequest("filesystem", directory_tool, {"path": "docs"})
        if "trace" in lowered or "로그" in prompt:
            return MCPToolRequest("filesystem", directory_tool, {"path": "data/traces"})
        if "output" in lowered or "결과" in prompt:
            return MCPToolRequest("filesystem", directory_tool, {"path": "data/outputs"})
        if "rag_docs" in lowered or "rag" in lowered:
            return MCPToolRequest("filesystem", directory_tool, {"path": "data/rag_docs"})

        return MCPToolRequest("filesystem", canonical_tool or "list_allowed_directories", {})

    def _validate_resolved_path(self, raw_path: str, *, allow_workspace_root: bool = False) -> str:
        candidate = Path(raw_path)
        resolved = (self.project_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

        try:
            resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError(f"워크스페이스 외부 경로는 허용되지 않습니다: {raw_path}") from exc

        if any(part in BLOCKED_PARTS for part in resolved.parts):
            raise ValueError(f"차단된 경로입니다: {raw_path}")
        if resolved.name == ".env":
            raise ValueError(f"차단된 파일입니다: {raw_path}")

        if allow_workspace_root and resolved == self.project_root:
            return "."

        relative = resolved.relative_to(self.project_root)
        relative_str = str(relative)
        relative_posix = relative.as_posix()

        if relative_posix == "README.md":
            return relative_str
        if WEEK_FILE_PATTERN.fullmatch(relative.name):
            return relative_str
        if any(
            relative_posix == allowed or relative_posix.startswith(f"{allowed}/")
            for allowed in ALLOWED_DIRECTORY_ROOTS
        ):
            return relative_str

        raise ValueError(f"허용된 whitelist 경로가 아닙니다: {raw_path}")

    def validate_tool_request(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """읽기 전용 도구와 whitelist 경로만 허용한다."""
        canonical_tool = TOOL_ALIASES.get(tool_name, tool_name)
        if canonical_tool not in READ_ONLY_TOOLS:
            raise ValueError(f"읽기 전용이 아닌 도구는 허용되지 않습니다: {tool_name}")

        validated_args = dict(args)
        if canonical_tool == "list_allowed_directories":
            return validated_args

        if canonical_tool in {
            "read_file",
            "read_text_file",
            "read_media_file",
            "list_directory",
            "list_directory_with_sizes",
            "directory_tree",
            "search_files",
            "get_file_info",
        }:
            allow_workspace_root = canonical_tool in {"search_files"}
            validated_args["path"] = self._validate_resolved_path(
                str(validated_args.get("path", "")),
                allow_workspace_root=allow_workspace_root,
            )
            return validated_args

        if canonical_tool == "read_multiple_files":
            paths = validated_args.get("paths", [])
            validated_args["paths"] = [
                self._validate_resolved_path(str(path))
                for path in paths
            ]
            return validated_args

        return validated_args

    def _extract_result_text(self, result: Any) -> str:
        if result is None:
            return ""

        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict) and structured:
            try:
                return json.dumps(structured, ensure_ascii=False, indent=2)
            except TypeError:
                return str(structured)

        content = getattr(result, "content", None)
        if isinstance(content, list):
            texts = []
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    texts.append(text)
                else:
                    texts.append(str(item))
            return "\n".join(texts)

        return str(result)

    def normalize_tool_result(self, tool_name: str, args: dict[str, Any], result: Any) -> str:
        body = self._extract_result_text(result).strip()
        summary = (
            f"[MCP Server] filesystem\n"
            f"[Tool] {tool_name}\n"
            f"[Args] {json.dumps(args, ensure_ascii=False)}\n"
            f"[Result]\n{body}"
        ).strip()
        if len(summary) <= self.max_tool_result_chars:
            return summary
        return summary[: self.max_tool_result_chars - 16].rstrip() + "\n...[truncated]"

    async def _run_tool_request(self, request: MCPToolRequest) -> dict[str, Any]:
        """공식 SDK로 세션을 열고 tool 호출을 수행한다."""
        if request.server_name != "filesystem":
            raise ValueError(f"지원하지 않는 MCP 서버입니다: {request.server_name}")

        validated_args = self.validate_tool_request(request.tool_name, request.args)
        params = self._filesystem_server_params()
        started_at = time.perf_counter()

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=self.session_start_timeout_s)
                tools_result = await asyncio.wait_for(session.list_tools(), timeout=self.tool_timeout_s)
                available_tools = [tool.name for tool in tools_result.tools]

                canonical_tool = TOOL_ALIASES.get(request.tool_name, request.tool_name)
                if canonical_tool not in available_tools:
                    raise RuntimeError(f"Filesystem MCP 서버에 도구가 없습니다: {canonical_tool}")

                call_result = await asyncio.wait_for(
                    session.call_tool(canonical_tool, arguments=validated_args),
                    timeout=self.tool_timeout_s,
                )

        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        normalized_result_summary = self.normalize_tool_result(canonical_tool, validated_args, call_result)
        return {
            "server_name": request.server_name,
            "tool_name": canonical_tool,
            "args": validated_args,
            "available_tools": available_tools,
            "success": not bool(getattr(call_result, "isError", False)),
            "latency_ms": latency_ms,
            "normalized_result_summary": normalized_result_summary,
            "result_text": self._extract_result_text(call_result),
        }

    async def execute_filesystem_lookup(self, prompt: str, preferred_tool: str | None = None) -> dict[str, Any]:
        request = self.plan_filesystem_request(prompt, preferred_tool=preferred_tool)
        return await self._run_tool_request(request)
