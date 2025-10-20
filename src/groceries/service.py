"""Groceries domain service: orchestrates intent, MCP calls, enrichment, and LLM analysis.

This module implements the groceries workflow using centralized clients
from src.core (MCP and LLM), decoupling UI/CLI from protocol details.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
import json
import re

from src.core.config import get_settings
from src.core.mcp_client import MCPClient, parse_mcp_content_text
from src.core.llm_client import BedrockLLMClient
from src.adapters.tool_invoker import ToolInvoker
from src.adapters.llm_client import LLMClient as LLMClientProtocol


_INTENT_CACHE: Dict[str, Dict[str, Any]] = {}


def _analyze_query_intent_rule_based(user_query: str) -> Dict[str, Any]:
    q = user_query.lower()
    patterns = {
        'search_products': {
            'keywords': ['find', 'search', 'show me', 'look for', 'groceries', 'food', 'products', 'items', 'catalog'],
            'action': 'search_products',
            'tool': 'catalog_products_search',
            'pattern': r'(find|search|show me|look for)\s+(.*(groceries|food|products|items))',
            'exclude_keywords': ['indices', 'indexes', 'categories', 'nutrition', 'promotions'],
        },
        'nutrition_search': {
            'keywords': ['healthy', 'health', 'nutrition', 'nutritious', 'recommend', 'suggest', 'good for', 'diet', 'calories', 'vitamins'],
            'action': 'nutrition_search',
            'tool': 'catalog_nutrition_search',
            'pattern': r'(healthy|health|nutrition|nutritious|recommend|suggest|diet|calories|vitamins)\s+(.*)'
        },
        'promotions_search': {
            'keywords': ['promotions', 'promo', 'deals', 'discounts', 'offers', 'sale', 'special'],
            'action': 'promotions_search',
            'tool': 'catalog_promotions_search',
            'pattern': r'(promotions|promo|deals|discounts|offers|sale|special)\s+(.*)'
        },
        'get_product': {
            'keywords': ['get product', 'retrieve product', 'show product', 'product id', 'id'],
            'action': 'get_product',
            'tool': 'platform_core_get_document_by_id',
            'pattern': r'(get|retrieve|show)\s+(product|item)\s+([a-zA-Z0-9_-]+)'
        },
        'basket_analysis': {
            'keywords': ['basket', 'cart', 'shopping list', 'meal plan', 'diet', 'nutritional'],
            'action': 'analyze_basket',
            'tool': 'catalog_products_search'
        },
        'list_categories': {
            'keywords': ['indices', 'indexes', 'list indices', 'show indices', 'list all indices', 'categories', 'category', 'list categories', 'show categories', 'types', 'show me indices'],
            'action': 'list_categories',
            'tool': 'platform_core_list_indices',
            'pattern': r'(list|show)\s+(me\s+)?(all\s+)?(indices|indexes|categories)'
        },
        'get_schema': {
            'keywords': ['schema', 'structure', 'fields', 'mapping'],
            'action': 'get_schema',
            'tool': 'platform_core_get_index_mapping'
        },
        'index_explorer': {
            'keywords': ['explore', 'discover', 'find indices', 'what indices', 'available data'],
            'action': 'index_explorer',
            'tool': 'platform_core_index_explorer',
            'pattern': r'(explore|discover|find indices|what indices|available data)\s+(.*)'
        },
    }

    candidates: List[Dict[str, Any]] = []
    for name, cfg in patterns.items():
        if 'exclude_keywords' in cfg and any(x in q for x in cfg['exclude_keywords']):
            continue
        matches = [kw for kw in cfg['keywords'] if kw in q]
        if matches:
            max_len = max(len(k) for k in matches)
            conf = min(0.6 + max_len / 20.0, 0.95)
            if any(k in q for k in ['indices', 'indexes', 'list indices', 'show indices']):
                conf = 0.95
            candidates.append({'intent': name, 'action': cfg['action'], 'tool': cfg['tool'], 'confidence': conf})
        if 'pattern' in cfg and re.search(cfg['pattern'], user_query):
            candidates.append({'intent': name, 'action': cfg['action'], 'tool': cfg['tool'], 'confidence': 0.8})

    if candidates:
        return max(candidates, key=lambda x: x['confidence'])
    return {'intent': 'search_groceries', 'action': 'search_groceries', 'tool': 'platform_core_search', 'confidence': 0.5}


def _analyze_query_intent_with_llm(user_query: str, llm: LLMClientProtocol | None = None) -> Dict[str, Any]:
    cache_key = user_query.lower().strip()
    if cache_key in _INTENT_CACHE:
        return _INTENT_CACHE[cache_key]

    cfg = get_settings()
    llm = llm or BedrockLLMClient(region_name=cfg.bedrock_region)
    tools_descr = [
        {"name": "platform_core_search", "description": "General search across indices"},
        {"name": "catalog_products_search", "description": "Search grocery products"},
        {"name": "catalog_nutrition_search", "description": "Nutrition rows filtered by health score"},
        {"name": "catalog_promotions_search", "description": "Promotions and deals"},
        {"name": "platform_core_get_document_by_id", "description": "Fetch full document by id"},
        {"name": "platform_core_list_indices", "description": "List indices"},
        {"name": "platform_core_get_index_mapping", "description": "Get index mappings"},
        {"name": "platform_core_index_explorer", "description": "Find relevant indices by NL query"},
    ]
    prompt = f"""
Analyze the following user query and pick the most appropriate tool.
USER QUERY: "{user_query}"
AVAILABLE TOOLS:\n{json.dumps(tools_descr, indent=2)}
Return strict JSON: {{"intent": str, "action": str, "tool": str, "confidence": float, "reasoning": str}}
Guidelines: prefer platform_core_search for general product search; nutrition -> catalog_nutrition_search; promotions -> catalog_promotions_search; by ID -> platform_core_get_document_by_id; listing -> platform_core_list_indices; explorer -> platform_core_index_explorer; mapping -> platform_core_get_index_mapping.
"""
    text = llm.invoke_text(
        model_id=cfg.claude_primary_model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        retries=3,
    )
    try:
        start, end = text.find('{'), text.rfind('}') + 1
        data = json.loads(text[start:end]) if start != -1 and end != -1 else {}
        if all(k in data for k in ('intent', 'action', 'tool', 'confidence')):
            _INTENT_CACHE[cache_key] = data
            return data
    except Exception:
        pass
    # Fallback
    return {'intent': 'search_products', 'action': 'search_products', 'tool': 'catalog_products_search', 'confidence': 0.5, 'reasoning': 'Fallback'}


def _build_arguments(tool: str, user_query: str, products_index: str) -> Dict[str, Any]:
    if tool == 'platform_core_search':
        return {'query': user_query, 'index': products_index}
    if tool in ('catalog_products_search', 'catalog_nutrition_search', 'catalog_promotions_search'):
        return {'nlQuery': user_query}
    if tool == 'platform_core_get_document_by_id':
        m = re.search(r'(get|retrieve|show)\s+(product|item)\s+([a-zA-Z0-9_-]+)', user_query.lower())
        if m:
            return {'index': products_index, 'id': m.group(3)}
        return {}
    if tool == 'platform_core_list_indices':
        return {}
    if tool == 'platform_core_get_index_mapping':
        return {'indices': [products_index]}
    if tool == 'platform_core_index_explorer':
        return {'query': user_query}
    return {}


def _enrich_search_results_with_content(raw: Dict[str, Any], client: MCPClient) -> Dict[str, Any]:
    parsed = parse_mcp_content_text(raw)
    if not parsed or 'results' not in parsed:
        return raw
    hits = parsed['results']
    enriched_hits: List[Dict[str, Any]] = []
    for hit in hits[:5]:
        ref = hit.get('data', {}).get('reference', {})
        doc_id = ref.get('id')
        index_name = ref.get('index')
        if not (doc_id and index_name):
            continue
        doc_raw = client.platform_core_get_document_by_id(index=index_name, id=doc_id)
        enriched_hits.append({
            'id': doc_id,
            'index': index_name,
            'search_highlights': hit.get('data', {}).get('content', {}).get('highlights', []),
            'full_content': doc_raw,
        })
    out = dict(raw)
    out['enriched_content'] = {'total_hits': len(hits), 'enriched_hits': enriched_hits}
    return out


def _generate_llm_analysis(user_query: str, mcp_result: Dict[str, Any], llm: LLMClientProtocol | None = None) -> str:
    cfg = get_settings()
    llm = llm or BedrockLLMClient(region_name=cfg.bedrock_region)
    # Summarize results similarly to CLI implementation
    summary = ""
    if 'enriched_content' in mcp_result:
        data = mcp_result['enriched_content']
        summary = f"Found {data['total_hits']} results, analyzed top {len(data['enriched_hits'])}:\n\n"
        for i, hit in enumerate(data['enriched_hits'], 1):
            summary += f"Product {i}:\n  ID: {hit['id']}\n  Index: {hit['index']}\n\n"
    else:
        parsed = parse_mcp_content_text(mcp_result)
        if parsed and 'results' in parsed:
            hits = parsed['results']
            summary = f"Found {len(hits)} grocery products:\n\n"
            for i, h in enumerate(hits[:5], 1):
                ref = h.get('data', {}).get('reference', {})
                content = h.get('data', {}).get('content', {})
                summary += f"Product {i}:\n  ID: {ref.get('id')}\n"
                if 'name' in content:
                    summary += f"  Name: {content['name']}\n"
                if 'category' in content:
                    summary += f"  Category: {content['category']}\n"
                if 'price' in content:
                    summary += f"  Price: {content['price']}\n"
                summary += "\n"
        else:
            summary = "No results found or error in MCP response."

    analysis_prompt = f"""
You are an expert nutritionist and grocery shopping advisor. A user asked: "{user_query}"

Here is the data gathered from MCP tools:\n\n{summary}

Produce a comprehensive French analysis with the following sections:
1. DIRECT ANSWER\n2. NUTRITIONAL ANALYSIS\n3. HEALTH RECOMMENDATIONS\n4. SHOPPING GUIDANCE\n5. MEAL PLANNING INSIGHTS\n6. HEALTHY LIFESTYLE TIPS\n7. HEALTHY SCORE INDEX\n+"""
    return llm.invoke_text(
        model_id=cfg.claude_primary_model_id,
        messages=[{"role": "user", "content": analysis_prompt}],
        max_tokens=4000,
        retries=3,
    )


def execute(
    query: str,
    *,
    use_llm: bool = True,
    tool_invoker: ToolInvoker | None = None,
    llm_client: LLMClientProtocol | None = None,
) -> Dict[str, Any]:
    cfg = get_settings()
    client = tool_invoker or MCPClient()

    # Intent
    intent = _analyze_query_intent_with_llm(query, llm_client) if use_llm else _analyze_query_intent_rule_based(query)

    # Build args and call tool
    args = _build_arguments(intent['tool'], query, cfg.products_index)
    raw = client.call_tool(intent['tool'], args)

    # Enrich if applicable
    if intent['action'] in ['search_products', 'nutrition_search', 'promotions_search', 'analyze_basket'] or intent['tool'] == 'platform_core_search':
        raw = _enrich_search_results_with_content(raw, client)

    out: Dict[str, Any] = {
        'query': query,
        'intent': intent,
        'mcp_result': raw,
    }

    if use_llm:
        out['llm_analysis'] = _generate_llm_analysis(query, raw, llm_client)

    return out
