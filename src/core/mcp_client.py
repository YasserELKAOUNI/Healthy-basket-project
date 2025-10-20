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
import logging
import time

import requests

from .config import get_settings
from src.adapters.tool_invoker import ToolInvoker


class MCPError(RuntimeError):
    pass


class MCPClient(ToolInvoker):
    def __init__(
        self,
        *,
        elastic_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_s: Optional[int] = None,
        identity: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ):
        cfg = get_settings()
        self.base_url = elastic_url or cfg.elastic_url
        self.api_key = api_key or cfg.elastic_api_key
        self.timeout_s = timeout_s or cfg.http_timeout_seconds
        self.identity = identity

        self._session = requests.Session()
        headers: Dict[str, str] = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if identity:
            headers["X-Agent-Id"] = identity
        if extra_headers:
            headers.update(extra_headers)
        self._session.headers.update(headers)

        self._logger = logging.getLogger(__name__)

    def initialize(self, *, client_name: str = "healthy-basket-client", client_version: str = "1.0.0", protocol_version: Optional[str] = None) -> Dict[str, Any]:
        """Perform MCP initialize handshake and store server info/capabilities.

        Returns the raw 'result' object from the initialize call.
        """
        from .constants import PROTOCOL_VERSION

        params = {
            "protocolVersion": protocol_version or PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": client_version},
        }
        result = self._rpc("initialize", params)
        # Cache some fields for later debugging/inspection
        self.server_info = result.get("serverInfo")  # type: ignore[attr-defined]
        self.capabilities = result.get("capabilities")  # type: ignore[attr-defined]
        return result

    def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            payload["params"] = params
        # Audit-style log (stderr)
        self._logger.info("mcp.rpc call", extra={"method": method, "has_params": bool(params)})

        retries = 3
        backoff = 1.5
        for attempt in range(retries):
            try:
                resp = self._session.post(self.base_url, json=payload, timeout=self.timeout_s)
                if resp.status_code == 429 and attempt < retries - 1:
                    sleep_s = backoff ** attempt
                    self._logger.warning("mcp.rpc 429 throttled; backing off", extra={"sleep": sleep_s})
                    time.sleep(sleep_s)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(backoff ** attempt)
                    continue
                raise MCPError(
                    f"MCP request failed for {method}: {e}. "
                    f"If this is rate limiting, try again later or reduce request volume."
                ) from e

        if "error" in data:
            raise MCPError(
                f"MCP error for {method}: {data['error']}. "
                f"Check tool name/arguments and permissions."
            )
        if "result" not in data:
            raise MCPError(f"MCP invalid response for {method}: missing result")
        return data["result"]

    # Low-level primitives
    def list_tools(self) -> List[Dict[str, Any]]:
        result = self._rpc("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        # Surface tool-level errors per MCP guidance
        try:
            if result.get("isError"):
                # Try to extract a human-friendly message from content
                msg = None
                content = result.get("content", [])
                if isinstance(content, list) and content:
                    first = content[0]
                    if isinstance(first, dict):
                        msg = first.get("text") or first.get("error")
                if msg:
                    result["error"] = f"Tool '{name}' error: {msg}"
                else:
                    result["error"] = f"Tool '{name}' reported an error. Check arguments/permissions."
        except Exception:
            # Don't disrupt normal flow on error surfacing
            pass
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

    def ping(self) -> Dict[str, Any]:
        """Lightweight connectivity check measuring roundtrip time.

        Tries a 'ping' tool if available; otherwise uses tools/list.
        Returns: { okay: bool, duration_ms: float, method: str }
        """
        import time as _t
        try:
            start = _t.perf_counter()
            self.list_tools()
            dur_ms = (_t.perf_counter() - start) * 1000.0
            return {"okay": True, "duration_ms": dur_ms, "method": "tools/list"}
        except Exception:
            return {"okay": False, "duration_ms": 0.0, "method": "tools/list"}


def parse_mcp_content_text(mcp_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON payload from MCP CallToolResult.content.

    Preference order:
    1) content items with JSON mimeType (e.g., application/json) and 'text' body
    2) first content item with 'json' field (if present)
    3) first content item with 'text' that contains JSON
    Returns parsed dict or None.
    """
    try:
        content = mcp_result.get("content", [])
        if not isinstance(content, list) or not content:
            return None

        # 1) Prefer JSON mimeType
        for item in content:
            if isinstance(item, dict):
                mime = item.get("mimeType") or item.get("mime")
                if mime and "json" in str(mime).lower():
                    txt = item.get("text")
                    if isinstance(txt, str):
                        return json.loads(txt)

        # 2) A 'json' field in item
        for item in content:
            if isinstance(item, dict) and "json" in item:
                data = item.get("json")
                if isinstance(data, dict):
                    return data
                if isinstance(data, str):
                    return json.loads(data)

        # 3) Fallback to first text
        first = content[0]
        if isinstance(first, dict):
            txt = first.get("text")
            if isinstance(txt, str):
                return json.loads(txt)
        return None
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
