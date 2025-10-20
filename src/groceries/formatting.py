from __future__ import annotations

import json
from typing import Any, Dict


def format_search_results(mcp_result: Dict[str, Any]) -> str:
    try:
        if 'error' in mcp_result:
            return f"Error: {mcp_result['error']}"

        if 'enriched_content' in mcp_result:
            enriched_data = mcp_result['enriched_content']
            formatted = f"Found {enriched_data['total_hits']} results, showing top {len(enriched_data['enriched_hits'])} with full details:\n\n"
            for i, hit in enumerate(enriched_data['enriched_hits'], 1):
                formatted += f"{i}. Product ID: {hit.get('id')} (Index: {hit.get('index')})\n"
                if 'full_content' in hit and 'content' in hit['full_content']:
                    try:
                        doc_content_text = hit['full_content']['content'][0]['text']
                        doc_data = json.loads(doc_content_text)
                        if 'results' in doc_data and doc_data['results']:
                            doc_result = doc_data['results'][0]
                            if 'data' in doc_result and 'content' in doc_result['data']:
                                content = doc_result['data']['content']
                                for key, value in content.items():
                                    if key not in ['highlights']:
                                        formatted += f"   {key.title()}: {value}\n"
                    except Exception as e:
                        formatted += f"   Content parsing error: {str(e)}\n"
                formatted += "\n"
            return formatted

        if 'content' not in mcp_result:
            return "No content in MCP result"
        content_text = mcp_result['content'][0]['text']
        parsed_results = json.loads(content_text)
        if 'results' not in parsed_results:
            return "No results found"
        hits = parsed_results['results']
        formatted = f"Found {len(hits)} grocery products:\n\n"
        for i, hit in enumerate(hits[:10], 1):
            if 'data' in hit and 'reference' in hit['data']:
                product_id = hit['data']['reference']['id']
                content = hit['data'].get('content', {})
                formatted += f"{i}. Product ID: {product_id}\n"
                if 'name' in content:
                    formatted += f"   Name: {content['name']}\n"
                if 'category' in content:
                    formatted += f"   Category: {content['category']}\n"
                if 'price' in content:
                    formatted += f"   Price: {content['price']}\n"
                if 'nutrition_score' in content:
                    formatted += f"   Nutrition Score: {content['nutrition_score']}\n"
                formatted += "\n"
        return formatted
    except Exception as e:
        return f"Error formatting results: {str(e)}"


def format_product_result(mcp_result: Dict[str, Any]) -> str:
    try:
        if 'error' in mcp_result:
            return f"Error: {mcp_result['error']}"
        if 'content' not in mcp_result:
            return "No content in MCP result"
        content_text = mcp_result['content'][0]['text']
        parsed_results = json.loads(content_text)
        if 'results' not in parsed_results or not parsed_results['results']:
            return "Product not found"
        result = parsed_results['results'][0]
        if 'data' not in result:
            return "No product data found"
        data = result['data']
        content = data.get('content', {})
        formatted = f"Product Details:\n"
        formatted += f"ID: {data.get('reference', {}).get('id', 'Unknown')}\n"
        if 'name' in content:
            formatted += f"Name: {content['name']}\n"
        if 'category' in content:
            formatted += f"Category: {content['category']}\n"
        if 'price' in content:
            formatted += f"Price: {content['price']}\n"
        if 'nutrition_score' in content:
            formatted += f"Nutrition Score: {content['nutrition_score']}\n"
        if 'ingredients' in content:
            formatted += f"Ingredients: {content['ingredients']}\n"
        if 'allergens' in content:
            formatted += f"Allergens: {content['allergens']}\n"
        if 'health_benefits' in content:
            formatted += f"Health Benefits: {content['health_benefits']}\n"
        return formatted
    except Exception as e:
        return f"Error formatting product: {str(e)}"

