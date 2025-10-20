from __future__ import annotations

import json
from typing import Any, Dict, List

from src.groceries import service
from src.adapters.tool_invoker import ToolInvoker
from src.adapters.llm_client import LLMClient


class FakeToolInvoker(ToolInvoker):
    def list_tools(self) -> List[Dict[str, Any]]:
        return [{"name": "platform_core_search"}, {"name": "platform_core_get_document_by_id"}]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name in ("platform_core_search", "catalog_products_search"):
            payload = {
                "results": [
                    {
                        "data": {
                            "reference": {"id": "DOC1", "index": arguments.get("index", "products")},
                            "content": {"name": "Apple", "category": "Fruit", "price": 1.5},
                        }
                    },
                    {
                        "data": {
                            "reference": {"id": "DOC2", "index": arguments.get("index", "products")},
                            "content": {"name": "Banana", "category": "Fruit", "price": 1.0},
                        }
                    },
                ]
            }
            return {"content": [{"type": "text", "text": json.dumps(payload)}]}
        if name == "platform_core_get_document_by_id":
            doc_payload = {
                "results": [
                    {
                        "data": {
                            "reference": {"id": arguments.get("id"), "index": arguments.get("index")},
                            "content": {"name": "Apple", "nutrition_score": 90},
                        }
                    }
                ]
            }
            return {"content": [{"type": "text", "text": json.dumps(doc_payload)}]}
        if name == "platform_core_list_indices":
            return {"content": [{"type": "text", "text": json.dumps({"results": [{"data": {"indices": [{"name": "products"}]}}]})}]}
        return {"content": [{"type": "text", "text": json.dumps({"ok": True})}]}


class FakeLLM(LLMClient):
    def invoke(self, *, model_id: str, messages: List[Dict[str, Any]], max_tokens: int = 1000, retries: int = 3, base_delay_s: int = 2) -> Dict[str, Any]:
        return {"content": [{"type": "text", "text": "ok"}]}

    def invoke_text(self, *, model_id: str, messages: List[Dict[str, Any]], max_tokens: int = 2000, retries: int = 3, base_delay_s: int = 2) -> str:
        return "FAKE LLM ANALYSIS"


def test_rule_based_intent_search():
    res = service.execute("find healthy groceries", use_llm=False, tool_invoker=FakeToolInvoker())
    assert res["intent"]["action"] in {"search_products", "nutrition_search"}
    assert "mcp_result" in res


def test_enrichment_with_fake_invoker():
    res = service.execute("find apples", use_llm=False, tool_invoker=FakeToolInvoker(), limit=1, offset=0, top_n=1)
    m = res["mcp_result"]
    assert "enriched_content" in m
    assert len(m["enriched_content"]["enriched_hits"]) == 1
    assert res.get("pagination", {}).get("limit") == 1
    assert res.get("pagination", {}).get("has_more") in (True, False)


def test_llm_injection():
    res = service.execute("find bananas", use_llm=True, tool_invoker=FakeToolInvoker(), llm_client=FakeLLM())
    assert "llm_analysis" in res
    assert res["llm_analysis"].startswith("FAKE LLM ANALYSIS")
