from __future__ import annotations

from typing import Protocol, Dict, Any, List


class ToolInvoker(Protocol):
    """Abstract interface for invoking MCP tools.

    Implementations may call out to MCP servers over JSON-RPC/HTTP, stdio, or other transports.
    """

    def list_tools(self) -> List[Dict[str, Any]]:
        ...

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ...

