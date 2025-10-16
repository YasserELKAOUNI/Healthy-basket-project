#!/usr/bin/env python3
"""
Smart MCP-based Groceries Health Basket Analysis CLI
Intelligent grocery recommendations and nutritional analysis using MCP tools and Claude AI
"""

import argparse
import json
import os
import re
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def load_config() -> Dict[str, str]:
    """Load configuration from environment variables"""
    return {
        'elastic_url': os.getenv('ELASTIC_URL', ''),
        'elastic_api_key': os.getenv('ELASTIC_API_KEY', ''),
        'bedrock_region': os.getenv('BEDROCK_REGION', 'us-east-1')
    }

# Simple cache for intent analysis to avoid repeated LLM calls
_intent_cache = {}

def analyze_query_intent_with_llm(user_query: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Use Claude to analyze user query intent and select appropriate MCP tool"""
    
    # Check cache first
    cache_key = user_query.lower().strip()
    if cache_key in _intent_cache:
        print("Using cached intent analysis...")
        return _intent_cache[cache_key]
    
    try:
        import boto3
        import time
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name=config['bedrock_region'])
        
        # Available MCP tools
        available_tools = [
            {
                "name": "platform_core_search",
                "description": "General search across Elasticsearch indices with flexible querying",
                "use_case": "General product searches, finding specific items, browsing catalog, wine searches"
            },
            {
                "name": "catalog_products_search",
                "description": "Search grocery products by text and return name/price/category",
                "use_case": "Specialized grocery product searches (may have limited data)"
            },
            {
                "name": "catalog_nutrition_search", 
                "description": "Retrieve nutrition rows filtered by health_score",
                "use_case": "Health and nutrition queries, dietary requirements, nutritional analysis"
            },
            {
                "name": "catalog_promotions_search",
                "description": "Fetch SKUs with active promotions and promo payload",
                "use_case": "Finding deals, discounts, promotional offers, sales"
            },
            {
                "name": "platform_core_get_document_by_id",
                "description": "Retrieve the full content of an Elasticsearch document based on its ID",
                "use_case": "Getting specific product details by ID"
            },
            {
                "name": "platform_core_list_indices",
                "description": "List the indices, aliases and datastreams from the Elasticsearch cluster",
                "use_case": "Listing available data sources, indices, categories"
            },
            {
                "name": "platform_core_get_index_mapping",
                "description": "Retrieve mappings for the specified index or indices",
                "use_case": "Getting schema information, field structures"
            },
            {
                "name": "platform_core_index_explorer",
                "description": "List relevant indices based on a natural language query",
                "use_case": "Exploring available data, discovering what data is available"
            }
        ]
        
        # Create prompt for Claude to analyze intent
        intent_prompt = f"""
You are an expert at analyzing user queries and selecting the most appropriate tool for grocery and health-related searches.

USER QUERY: "{user_query}"

AVAILABLE TOOLS:
{json.dumps(available_tools, indent=2)}

Please analyze the user's query and determine:
1. What is the user's primary intent?
2. Which tool would be most appropriate?
3. What confidence level do you have in this choice (0.0 to 1.0)?

Respond with a JSON object in this exact format:
{{
    "intent": "descriptive_intent_name",
    "action": "action_name", 
    "tool": "tool_name",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this tool was chosen"
}}

Guidelines:
- For general product searches (groceries, food items, wine, beverages), use platform_core_search
- For specialized grocery product searches, use catalog_products_search (fallback if platform_core_search fails)
- For health/nutrition queries (healthy, diet, calories, vitamins), use catalog_nutrition_search  
- For deals/promotions/sales, use catalog_promotions_search
- For getting specific product by ID, use platform_core_get_document_by_id
- For listing available data sources, use platform_core_list_indices
- For exploring what data is available, use platform_core_index_explorer
- For schema/mapping info, use platform_core_get_index_mapping

Be precise and choose the most specific tool that matches the user's intent. Prefer platform_core_search for general product queries as it has broader data access.
"""
        
        # Call Claude with retry logic
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = bedrock.invoke_model(
                    modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [
                            {
                                "role": "user",
                                "content": intent_prompt
                            }
                        ]
                    })
                )
                break  # Success, exit retry loop
                
            except Exception as e:
                if "ThrottlingException" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                    continue
                else:
                    raise e  # Re-raise if not throttling or final attempt
        
        response_body = json.loads(response['body'].read())
        claude_response = response_body['content'][0]['text']
        
        # Parse Claude's JSON response
        try:
            # Extract JSON from Claude's response (it might have extra text)
            json_start = claude_response.find('{')
            json_end = claude_response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = claude_response[json_start:json_end]
                intent_result = json.loads(json_str)
                
                # Validate the response has required fields
                required_fields = ['intent', 'action', 'tool', 'confidence']
                if all(field in intent_result for field in required_fields):
                    # Cache the result
                    _intent_cache[cache_key] = intent_result
                    return intent_result
                else:
                    raise ValueError("Missing required fields in Claude response")
            else:
                raise ValueError("No JSON found in Claude response")
                
        except Exception as e:
            print(f"Failed to parse Claude's intent analysis: {e}")
            print(f"Claude response: {claude_response}")
            # Fallback to default
            return {
                'intent': 'search_products',
                'action': 'search_products', 
                'tool': 'catalog_products_search',
                'confidence': 0.5,
                'reasoning': 'Fallback due to parsing error'
            }
        
    except Exception as e:
        print(f"LLM intent analysis failed: {e}")
        # Fallback to rule-based analysis
        print("Falling back to rule-based intent analysis...")
        return analyze_query_intent_rule_based(user_query)

def analyze_query_intent_rule_based(user_query: str) -> Dict[str, Any]:
    """Analyze user query to determine intent and select appropriate MCP tool"""
    query_lower = user_query.lower()
    
    patterns = {
        'search_products': {
            'keywords': ['find', 'search', 'show me', 'look for', 'groceries', 'food', 'products', 'items', 'catalog'],
            'action': 'search_products',
            'tool': 'catalog_products_search',
            'pattern': r'(find|search|show me|look for)\s+(.*(groceries|food|products|items))',
            'exclude_keywords': ['indices', 'indexes', 'categories', 'nutrition', 'promotions']
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
            'pattern': r'(list|show)\s+(me\s+)?(all\s+)?(indices|indexes|categories)',
            'priority': 1  # Higher priority
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
        }
    }
    
    # Analyze the query
    detected_intents = []
    
    for intent, config in patterns.items():
        # Check for exclude keywords first
        if 'exclude_keywords' in config:
            if any(exclude_keyword in query_lower for exclude_keyword in config['exclude_keywords']):
                continue  # Skip this intent if exclude keywords are present
        
        # Check for keywords with higher priority for exact matches
        keyword_matches = [keyword for keyword in config['keywords'] if keyword in query_lower]
        if keyword_matches:
            # Higher confidence for longer/more specific keywords
            max_keyword_len = max(len(keyword) for keyword in keyword_matches)
            confidence = 0.6 + (max_keyword_len / 20)  # Scale confidence based on keyword length
            
            # Boost confidence for specific high-priority keywords
            if any(keyword in query_lower for keyword in ['indices', 'indexes', 'list indices', 'show indices']):
                confidence = 0.95
            
            detected_intents.append({
                'intent': intent,
                'action': config['action'],
                'tool': config['tool'],
                'confidence': min(confidence, 0.95)  # Cap at 0.95
            })
        
        # Check for specific patterns
        if 'pattern' in config:
            if re.search(config['pattern'], user_query):
                detected_intents.append({
                    'intent': intent,
                    'action': config['action'],
                    'tool': config['tool'],
                    'confidence': 0.8  # Base confidence for pattern match
                })
    
    # Prioritize based on confidence
    if detected_intents:
        best_intent = max(detected_intents, key=lambda x: x['confidence'])
        return best_intent
    
    # Default to search if no specific intent is detected
    return {
        'intent': 'search_groceries',
        'action': 'search_groceries',
        'tool': 'platform_core_search',
        'confidence': 0.5
    }

def get_document_content(doc_id: str, index_name: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Get full document content by ID"""
    arguments = {
        'id': doc_id,
        'index': index_name
    }
    return call_mcp_tool('platform_core_get_document_by_id', arguments, config)

def enrich_search_results_with_content(search_result: Dict[str, Any], config: Dict[str, str]) -> Dict[str, Any]:
    """Enrich search results by fetching full document content for each result"""
    try:
        if 'error' in search_result:
            return search_result
        
        if 'content' not in search_result:
            return search_result
        
        content_text = search_result['content'][0]['text']
        parsed_results = json.loads(content_text)
        
        if 'results' not in parsed_results:
            return search_result
        
        hits = parsed_results['results']
        enriched_hits = []
        
        for hit in hits[:5]:  # Limit to top 5 to avoid too many API calls
            if 'data' in hit and 'reference' in hit['data']:
                doc_id = hit['data']['reference']['id']
                index_name = hit['data']['reference']['index']
                
                # Get full document content
                doc_content = get_document_content(doc_id, index_name, config)
                
                # Create enriched hit with full content
                enriched_hit = {
                    'id': doc_id,
                    'index': index_name,
                    'search_highlights': hit['data'].get('content', {}).get('highlights', []),
                    'full_content': doc_content
                }
                enriched_hits.append(enriched_hit)
        
        # Return enriched results
        enriched_result = search_result.copy()
        enriched_result['enriched_content'] = {
            'total_hits': len(hits),
            'enriched_hits': enriched_hits
        }
        
        return enriched_result
        
    except Exception as e:
        # Return original result if enrichment fails
        enriched_result = search_result.copy()
        enriched_result['enrichment_error'] = str(e)
        return enriched_result

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], config: Dict[str, str]) -> Dict[str, Any]:
    """Call MCP tool with given arguments"""
    
    # Prepare MCP payload
    mcp_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/call',
        'params': {
            'name': tool_name,
            'arguments': arguments
        }
    }
    
    headers = {
        'Authorization': f'ApiKey {config["elastic_api_key"]}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.post(config['elastic_url'], json=mcp_payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        if 'result' in result:
            return result['result']
        else:
            return {'error': 'No result in MCP response', 'raw_response': result}
            
    except Exception as e:
        return {'error': f'MCP tool call failed: {str(e)}'}

def execute_smart_query(user_query: str, config: Dict[str, str], verbose: bool = True, use_llm: bool = True) -> Dict[str, Any]:
    """Execute smart query with LLM-based intent analysis and MCP tool selection"""
    
    if use_llm:
        if verbose:
            print("🧠 Analyzing query intent with Claude...")
        intent = analyze_query_intent_with_llm(user_query, config)
    else:
        if verbose:
            print("🧠 Analyzing query intent with rule-based system...")
        intent = analyze_query_intent_rule_based(user_query)
    
    if verbose:
        print(f"🎯 Detected intent: {intent['intent']}")
        print(f"🔧 Selected tool: {intent['tool']}")
        print(f"📊 Confidence: {intent['confidence']:.2f}")
        print(f"💭 Reasoning: {intent.get('reasoning', 'No reasoning provided')}")
    
    # Prepare arguments based on selected tool
    arguments = {}
    
    if intent['tool'] == 'platform_core_search':
        arguments = {
            'query': user_query,
            'index': 'products'  # Default to products index
        }
    elif intent['tool'] in ['catalog_products_search', 'catalog_nutrition_search', 'catalog_promotions_search']:
        arguments = {
            'nlQuery': user_query
        }
    elif intent['tool'] == 'platform_core_get_document_by_id':
        # Extract product ID from query
        match = re.search(r'(get|retrieve|show)\s+(product|item)\s+([a-zA-Z0-9_-]+)', user_query.lower())
        if match:
            product_id = match.group(3)
            arguments = {
                'index': 'products',
                'id': product_id
            }
        else:
            return {'error': 'Could not extract product ID from query'}
    elif intent['tool'] == 'platform_core_list_indices':
        arguments = {}
    elif intent['tool'] == 'platform_core_get_index_mapping':
        arguments = {
            'indices': ['products']
        }
    elif intent['tool'] == 'platform_core_index_explorer':
        arguments = {
            'query': user_query
        }
    
    if verbose:
        print(f"⚙️ Arguments: {arguments}")
    
    if verbose:
        print(f"\n🔧 Executing {intent['tool']}...")
    result = call_mcp_tool(intent['tool'], arguments, config)
    
    # Enrich search results with full document content
    if intent['action'] in ['search_products', 'nutrition_search', 'promotions_search', 'analyze_basket'] or intent['tool'] == 'platform_core_search':
        if verbose:
            print("📄 Enriching results with full document content...")
        result = enrich_search_results_with_content(result, config)
    
    return {
        'intent': intent,
        'result': result
    }

def format_search_results(mcp_result: Dict[str, Any]) -> str:
    """Format search results for display"""
    
    try:
        if 'error' in mcp_result:
            return f"Error: {mcp_result['error']}"
        
        # Check if we have enriched content
        if 'enriched_content' in mcp_result:
            enriched_data = mcp_result['enriched_content']
            formatted = f"Found {enriched_data['total_hits']} results, showing top {len(enriched_data['enriched_hits'])} with full details:\n\n"
            
            for i, hit in enumerate(enriched_data['enriched_hits'], 1):
                formatted += f"{i}. Product ID: {hit['id']} (Index: {hit['index']})\n"
                
                # Extract and display full content
                if 'full_content' in hit and 'content' in hit['full_content']:
                    try:
                        doc_content_text = hit['full_content']['content'][0]['text']
                        doc_data = json.loads(doc_content_text)
                        
                        if 'results' in doc_data and doc_data['results']:
                            doc_result = doc_data['results'][0]
                            if 'data' in doc_result and 'content' in doc_result['data']:
                                content = doc_result['data']['content']
                                
                                # Display all available fields
                                for key, value in content.items():
                                    if key not in ['highlights']:  # Skip highlights
                                        formatted += f"   {key.title()}: {value}\n"
                    except Exception as e:
                        formatted += f"   Content parsing error: {str(e)}\n"
                
                formatted += "\n"
            
            return formatted
        
        # Fallback to original formatting
        if 'content' not in mcp_result:
            return "No content in MCP result"
        
        content_text = mcp_result['content'][0]['text']
        parsed_results = json.loads(content_text)
        
        if 'results' not in parsed_results:
            return "No results found"
        
        hits = parsed_results['results']
        formatted = f"Found {len(hits)} grocery products:\n\n"
        
        for i, hit in enumerate(hits[:10], 1):  # Show top 10
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
    """Format single product result for display"""
    
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

def generate_llm_analysis(user_query: str, mcp_result: Dict[str, Any], config: Dict[str, str]) -> str:
    """Generate comprehensive LLM analysis of grocery/health results"""
    
    try:
        import boto3
        import time
        
        # Initialize Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name=config['bedrock_region'])
        
        # Prepare results summary for Claude
        results_summary = ""
        
        # Check if we have enriched content
        if mcp_result and 'enriched_content' in mcp_result:
            enriched_data = mcp_result['enriched_content']
            results_summary = f"Found {enriched_data['total_hits']} results, analyzed top {len(enriched_data['enriched_hits'])}:\n\n"
            
            for i, hit in enumerate(enriched_data['enriched_hits'], 1):
                results_summary += f"Product {i}:\n"
                results_summary += f"  ID: {hit['id']}\n"
                results_summary += f"  Index: {hit['index']}\n"
                
                # Extract content from full document
                if 'full_content' in hit and 'content' in hit['full_content']:
                    try:
                        doc_content_text = hit['full_content']['content'][0]['text']
                        doc_data = json.loads(doc_content_text)
                        
                        if 'results' in doc_data and doc_data['results']:
                            doc_result = doc_data['results'][0]
                            if 'data' in doc_result and 'content' in doc_result['data']:
                                content = doc_result['data']['content']
                                
                                # Add all available fields
                                for key, value in content.items():
                                    if key not in ['highlights']:  # Skip highlights
                                        results_summary += f"  {key.title()}: {value}\n"
                    except Exception as e:
                        results_summary += f"  Content parsing error: {str(e)}\n"
                
                results_summary += "\n"
        
        elif mcp_result and 'content' in mcp_result:
            try:
                content_text = mcp_result['content'][0]['text']
                parsed_results = json.loads(content_text)
                
                if 'results' in parsed_results:
                    hits = parsed_results['results']
                    results_summary = f"Found {len(hits)} grocery products:\n\n"
                    
                    for i, hit in enumerate(hits[:5], 1):  # Show top 5 for analysis
                        if 'data' in hit and 'reference' in hit['data']:
                            product_id = hit['data']['reference']['id']
                            content = hit['data'].get('content', {})
                            
                            results_summary += f"Product {i}:\n"
                            results_summary += f"  ID: {product_id}\n"
                            if 'name' in content:
                                results_summary += f"  Name: {content['name']}\n"
                            if 'category' in content:
                                results_summary += f"  Category: {content['category']}\n"
                            if 'price' in content:
                                results_summary += f"  Price: {content['price']}\n"
                            if 'nutrition_score' in content:
                                results_summary += f"  Nutrition Score: {content['nutrition_score']}\n"
                            results_summary += "\n"
                
                elif 'indices' in parsed_results:
                    indices = parsed_results['indices']
                    results_summary = f"Available categories: {len(indices)}\n"
                    for idx in indices:
                        results_summary += f"- {idx.get('name', 'Unknown')} ({idx.get('type', 'Unknown')})\n"
                
            except Exception as e:
                results_summary = f"Error parsing results: {str(e)}"
        else:
            results_summary = "No results found or error in MCP response."
        
        # Create comprehensive analysis prompt for groceries/health
        analysis_prompt = f"""
You are an expert nutritionist and grocery shopping advisor. A user asked: "{user_query}"

I executed MCP tools to gather grocery and health data and got these results:

{results_summary}

Please provide a comprehensive, professional analysis that includes:

## 1. DIRECT ANSWER
- Direct response to the user's grocery/health question
- Summary of what was found

## 2. NUTRITIONAL ANALYSIS
- Detailed analysis of the nutritional value of found products
- Health benefits and potential concerns
- Nutritional density and quality assessment

## 3. HEALTH RECOMMENDATIONS
- Specific health benefits of recommended products
- Dietary considerations and restrictions
- Optimal consumption patterns

## 4. SHOPPING GUIDANCE
- Best products for the user's health goals
- Value for money analysis
- Quality indicators to look for

## 5. MEAL PLANNING INSIGHTS
- How these products fit into a balanced diet
- Complementary food suggestions
- Recipe ideas and preparation tips

## 6. HEALTHY LIFESTYLE TIPS
- Additional dietary recommendations
- Lifestyle factors to consider
- Long-term health benefits
- Use index healthy score

Provide a thorough, professional response that directly addresses the user's grocery/health query using the MCP tool results. Be specific, actionable, and use examples from the data to support your analysis. Focus on practical, evidence-based nutrition advice.

Always uses French language
"""
        
        # Call Claude with retry logic
        max_retries = 3
        base_delay = 5  # Increased delay for rate limiting
        
        for attempt in range(max_retries):
            try:
                response = bedrock.invoke_model(
                    modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 4000,
                        "messages": [
                            {
                                "role": "user",
                                "content": analysis_prompt
                            }
                        ]
                    })
                )
                break  # Success, exit retry loop
                
            except Exception as e:
                if "ThrottlingException" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Rate limited, waiting {delay} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)
                    continue
                else:
                    raise e  # Re-raise if not throttling or final attempt
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        if "ThrottlingException" in str(e):
            return f"""LLM analysis temporarily unavailable due to rate limiting. 

The system successfully analyzed your query and found results, but Claude is currently experiencing high demand. 

To get immediate results without LLM analysis, you can:
1. Use the --no-llm flag: `python smart_grocery_cli.py "your query" --no-llm`
2. Wait a few minutes and try again
3. Check the raw results above for the data found

The search and data retrieval worked correctly - only the final analysis step is affected by rate limiting."""
        else:
            return f"LLM analysis failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="Smart MCP-based Groceries Health Basket Analysis CLI with LLM Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smart_grocery_cli.py "Find healthy breakfast options"
  python smart_grocery_cli.py "Show me organic vegetables"
  python smart_grocery_cli.py "Get product PROD_12345"
  python smart_grocery_cli.py "List all indices"
  python smart_grocery_cli.py "Search for nutrition data"
  python smart_grocery_cli.py "Find current promotions"
  python smart_grocery_cli.py "Explore available data"
        """
    )
    
    parser.add_argument('query', help='Your question or request about groceries and health')
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM analysis and show raw results only')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if not config['elastic_url'] or not config['elastic_api_key']:
        print("Error: Missing ELASTIC_URL or ELASTIC_API_KEY environment variables")
        return
    
    print(f"🛒 Smart Grocery Health Analysis")
    print(f"User Query: {args.query}")
    print("=" * 80)
    
    # Execute the smart query
    result = execute_smart_query(args.query, config, use_llm=not args.no_llm)
    
    if args.no_llm:
        # Show raw results only
        print("\n" + "=" * 80)
        print("📊 RAW RESULTS")
        print("=" * 80)
        
        # Format and display results based on the action
        if result['intent']['action'] in ['search_products', 'nutrition_search', 'promotions_search', 'analyze_basket']:
            print(format_search_results(result['result']))
        elif result['intent']['action'] == 'get_product':
            print(format_product_result(result['result']))
        elif result['intent']['action'] == 'list_categories':
            if result['result'] and 'content' in result['result']:
                content_text = result['result']['content'][0]['text']
                parsed_results = json.loads(content_text)
                
                # Parse the nested structure
                if 'results' in parsed_results and parsed_results['results']:
                    data = parsed_results['results'][0].get('data', {})
                    indices = data.get('indices', [])
                    print(f"Available indices: {len(indices)}")
                    for idx in indices:
                        print(f"- {idx.get('name', 'Unknown')}")
                else:
                    print("No indices found.")
            else:
                print("No categories found.")
        elif result['intent']['action'] == 'get_schema':
            print("Product schema retrieved successfully.")
            print(json.dumps(result['result'], indent=2))
        else:
            print("Results:")
            print(json.dumps(result['result'], indent=2))
    else:
        # Generate LLM analysis
        print("\n🧠 Generating comprehensive LLM analysis...")
        llm_analysis = generate_llm_analysis(args.query, result['result'], config)
        
        print("\n" + "=" * 80)
        print("🤖 CLAUDE'S COMPREHENSIVE HEALTH ANALYSIS")
        print("=" * 80)
        print(llm_analysis)
    
    print("=" * 80)

if __name__ == "__main__":
    main()
