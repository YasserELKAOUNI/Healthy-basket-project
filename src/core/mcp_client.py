"""MCP client facade for Elastic-based MCP servers.

This module encapsulates JSON-RPC requests to the MCP endpoint and
provides convenience methods for common operations used by the
groceries domain (search, get document by id, list indices, etc.).

All business code should call this facade instead of issuing raw
HTTP requests or handling JSON-RPC envelopes directly.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import get_settings
from src.adapters.tool_invoker import ToolInvoker


class MCPError(RuntimeError):
    pass


class MCPClient(ToolInvoker):
    def __init__(self, *, elastic_url: Optional[str] = None, api_key: Optional[str] = None, timeout_s: Optional[int] = None):
        cfg = get_settings()
        self.base_url = elastic_url or cfg.elastic_url
        self.api_key = api_key or cfg.elastic_api_key
        self.timeout_s = timeout_s or cfg.http_timeout_seconds

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            resp = self._session.post(self.base_url, json=payload, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise MCPError(f"MCP request failed for {method}: {e}") from e

        if "error" in data:
            raise MCPError(f"MCP error for {method}: {data['error']}")
        if "result" not in data:
            raise MCPError(f"MCP invalid response for {method}: missing result")
        return data["result"]

    # Low-level primitives
    def list_tools(self) -> List[Dict[str, Any]]:
        result = self._rpc("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return result

    # Convenience methods for common tools
    def platform_core_search(self, *, index: str, query: str) -> Dict[str, Any]:
        return self.call_tool("platform_core_search", {"index": index, "query": query})

    def platform_core_get_document_by_id(self, *, index: str, id: str) -> Dict[str, Any]:
        return self.call_tool("platform_core_get_document_by_id", {"index": index, "id": id})

    def platform_core_list_indices(self) -> Dict[str, Any]:
        return self.call_tool("platform_core_list_indices", {})

    def platform_core_get_index_mapping(self, *, indices: List[str]) -> Dict[str, Any]:
        return self.call_tool("platform_core_get_index_mapping", {"indices": indices})


def parse_mcp_content_text(mcp_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract and parse the JSON payload embedded in `result.content[0].text`.

    Returns the parsed dict or None if missing/malformed.
    """
    try:
        content = mcp_result.get("content", [])
        if not content:
            return None
        text = content[0].get("text")
        if not text:
            return None
        return json.loads(text)
    except Exception:
        return None


def search_and_parse(client: MCPClient, *, index: str, query: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Run `platform_core_search` and return the raw MCP result and parsed payload.
    Parsed payload typically has a `results` list with data/reference/content.
    """
    raw = client.platform_core_search(index=index, query=query)
    parsed = parse_mcp_content_text(raw)
    return raw, parsed


def get_document_and_parse(client: MCPClient, *, index: str, id: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    raw = client.platform_core_get_document_by_id(index=index, id=id)
    parsed = parse_mcp_content_text(raw)
    return raw, parsed
