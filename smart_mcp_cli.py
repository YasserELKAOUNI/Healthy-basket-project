#!/usr/bin/env python3
"""
Smart MCP-based Email Phishing Analysis CLI
Uses intelligent rules to decide which MCP tools to call based on user queries
"""

import argparse
import json
from src.core.config import get_settings
from src.core.mcp_client import MCPClient, parse_mcp_content_text
from src.core.llm_client import BedrockLLMClient
import re
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

def load_config():
    """Load configuration from centralized settings"""
    s = get_settings()
    return {
        'elastic_url': s.elastic_url,
        'elastic_api_key': s.elastic_api_key,
        'bedrock_region': s.bedrock_region,
    }

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], config: Dict[str, str]) -> Dict[str, Any]:
    """Call an MCP tool directly"""
    
    client = MCPClient(elastic_url=config['elastic_url'], api_key=config['elastic_api_key'])
    return client.call_tool(tool_name, arguments)

def analyze_query_intent(user_query: str) -> Dict[str, Any]:
    """Analyze user query to determine intent and required tools"""
    
    query_lower = user_query.lower()
    
    # Define patterns and their corresponding actions
    patterns = {
        'search_phishing': {
            'keywords': ['find', 'search', 'look for', 'show me', 'get', 'list'],
            'phishing_terms': ['phishing', 'phish', 'scam', 'fraud', 'suspicious', 'malicious'],
            'action': 'search_emails',
            'tool': 'platform_core_search'
        },
        'urgent_emails': {
            'keywords': ['urgent', 'immediate', 'asap', 'critical', 'emergency'],
            'action': 'search_urgent',
            'tool': 'platform_core_search'
        },
        'specific_document': {
            'keywords': ['document', 'email id', 'get email', 'show document'],
            'pattern': r'[a-zA-Z0-9_-]{10,}',
            'action': 'get_document',
            'tool': 'platform_core_get_document_by_id'
        },
        'campaign_analysis': {
            'keywords': ['campaign', 'campaigns', 'attack', 'attacks', 'pattern', 'patterns'],
            'action': 'analyze_campaigns',
            'tool': 'platform_core_search'
        },
        'list_indices': {
            'keywords': ['indices', 'indexes', 'list indices', 'show indices', 'list all indices'],
            'action': 'list_indices',
            'tool': 'platform_core_list_indices'
        },
        'get_mapping': {
            'keywords': ['mapping', 'schema', 'structure', 'fields'],
            'action': 'get_mapping',
            'tool': 'platform_core_get_index_mapping'
        }
    }
    
    # Analyze the query
    detected_intents = []
    
    for intent, config in patterns.items():
        # Check for keywords with higher priority for exact matches
        keyword_matches = [keyword for keyword in config['keywords'] if keyword in query_lower]
        if keyword_matches:
            # Higher confidence for longer/more specific keywords
            max_keyword_len = max(len(keyword) for keyword in keyword_matches)
            confidence = 0.6 + (max_keyword_len / 20)  # Scale confidence based on keyword length
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
                    'confidence': 0.9
                })
    
    # Determine the best action
    if not detected_intents:
        # Default to search
        return {
            'action': 'search_emails',
            'tool': 'platform_core_search',
            'arguments': {'query': user_query, 'index': 'fishfish'},
            'confidence': 0.5
        }
    
    # Sort by confidence and return the best match
    best_intent = max(detected_intents, key=lambda x: x['confidence'])
    
    # Generate arguments based on intent
    arguments = {'index': 'fishfish'}
    
    if best_intent['action'] == 'search_emails':
        arguments['query'] = user_query
    elif best_intent['action'] == 'search_urgent':
        arguments['query'] = 'urgent phishing'
    elif best_intent['action'] == 'get_document':
        # Extract document ID from query
        doc_id_match = re.search(r'[a-zA-Z0-9_-]{10,}', user_query)
        if doc_id_match:
            arguments['id'] = doc_id_match.group(0)
        else:
            arguments['id'] = 'unknown'
    elif best_intent['action'] == 'analyze_campaigns':
        arguments['query'] = 'phishing campaign'
    elif best_intent['action'] == 'list_indices':
        arguments = {}
    elif best_intent['action'] == 'get_mapping':
        arguments = {'indices': ['fishfish']}
    
    return {
        'action': best_intent['action'],
        'tool': best_intent['tool'],
        'arguments': arguments,
        'confidence': best_intent['confidence']
    }

def execute_smart_query(user_query: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Execute the query using intelligent tool selection"""
    
    print(f"🧠 Analyzing query intent...")
    intent = analyze_query_intent(user_query)
    
    print(f"🎯 Detected intent: {intent['action']}")
    print(f"🔧 Selected tool: {intent['tool']}")
    print(f"📊 Confidence: {intent['confidence']:.2f}")
    print(f"⚙️ Arguments: {intent['arguments']}")
    print()
    
    # Execute the tool
    print(f"🔧 Executing {intent['tool']}...")
    result = call_mcp_tool(intent['tool'], intent['arguments'], config)
    
    return {
        'intent': intent,
        'result': result,
        'query': user_query
    }

def format_search_results(result: Dict[str, Any]) -> str:
    """Format search results for display"""
    
    if not result:
        return "No results found."
    
    try:
        parsed_results = parse_mcp_content_text(result)
        if parsed_results is None:
            return "No search results found."
        
        if 'results' not in parsed_results:
            return "No search results found."
        
        hits = parsed_results['results']
        formatted = f"Found {len(hits)} results:\n\n"
        
        for i, hit in enumerate(hits[:10], 1):  # Show top 10
            if 'data' in hit and 'reference' in hit['data']:
                doc_id = hit['data']['reference']['id']
                content = hit['data'].get('content', {})
                
                formatted += f"{i}. Document ID: {doc_id}\n"
                if 'category' in content:
                    formatted += f"   Category: {content['category']}\n"
                if 'subject' in content:
                    formatted += f"   Subject: {content['subject']}\n"
                if 'date' in content:
                    formatted += f"   Date: {content['date']}\n"
                formatted += "\n"
        
        return formatted
        
    except Exception as e:
        return f"Error formatting results: {str(e)}"

def format_document_result(result: Dict[str, Any]) -> str:
    """Format document result for display"""
    
    if not result:
        return "Document not found."
    
    try:
        parsed_results = parse_mcp_content_text(result)
        if parsed_results is None:
            return "Document not found."
        
        if 'results' not in parsed_results or not parsed_results['results']:
            return "Document not found."
        
        doc_data = parsed_results['results'][0]
        content = doc_data.get('data', {}).get('content', {})
        
        formatted = "Document Details:\n\n"
        formatted += f"ID: {doc_data.get('data', {}).get('reference', {}).get('id', 'Unknown')}\n"
        formatted += f"Index: {doc_data.get('data', {}).get('reference', {}).get('index', 'Unknown')}\n"
        
        if 'category' in content:
            formatted += f"Category: {content['category']}\n"
        if 'subject' in content:
            formatted += f"Subject: {content['subject']}\n"
        if 'from' in content:
            formatted += f"From: {content['from']}\n"
        if 'date' in content:
            formatted += f"Date: {content['date']}\n"
        
        return formatted
        
    except Exception as e:
        return f"Error formatting document: {str(e)}"

def generate_llm_analysis(user_query: str, mcp_result: Dict[str, Any], config: Dict[str, str]) -> str:
    """Generate comprehensive LLM analysis of MCP results"""
    
    try:
        llm = BedrockLLMClient(region_name=config['bedrock_region'])
        
        # Prepare results summary for Claude
        results_summary = ""
        
        if mcp_result and 'content' in mcp_result:
            try:
                content_text = mcp_result['content'][0]['text']
                parsed_results = json.loads(content_text)
                
                if 'results' in parsed_results:
                    hits = parsed_results['results']
                    results_summary = f"Found {len(hits)} results:\n\n"
                    
                    for i, hit in enumerate(hits[:5], 1):  # Show top 5 for analysis
                        if 'data' in hit and 'reference' in hit['data']:
                            doc_id = hit['data']['reference']['id']
                            content = hit['data'].get('content', {})
                            
                            results_summary += f"Result {i}:\n"
                            results_summary += f"  Document ID: {doc_id}\n"
                            if 'category' in content:
                                results_summary += f"  Category: {content['category']}\n"
                            if 'subject' in content:
                                results_summary += f"  Subject: {content['subject']}\n"
                            if 'from' in content:
                                results_summary += f"  From: {content['from']}\n"
                            if 'date' in content:
                                results_summary += f"  Date: {content['date']}\n"
                            results_summary += "\n"
                
                elif 'indices' in parsed_results:
                    indices = parsed_results['indices']
                    results_summary = f"Available indices: {len(indices)}\n"
                    for idx in indices:
                        results_summary += f"- {idx.get('name', 'Unknown')} ({idx.get('type', 'Unknown')})\n"
                
            except Exception as e:
                results_summary = f"Error parsing results: {str(e)}"
        else:
            results_summary = "No results found or error in MCP response."
        
        # Create comprehensive analysis prompt
        analysis_prompt = f"""
You are an expert cybersecurity analyst and technical writer. A user asked: "{user_query}"

I executed MCP tools to gather data and got these results:

{results_summary}

Please provide a comprehensive, professional analysis that includes:

## 1. DIRECT ANSWER
- Direct response to the user's question
- Summary of what was found

## 2. TECHNICAL ANALYSIS
- Detailed analysis of the MCP tool results
- Key findings and insights from the data
- Patterns or trends identified

## 3. PHISHING INSIGHTS
- Specific phishing techniques or patterns found
- Risk assessment based on the data
- Threat level evaluation

## 4. SECURITY IMPLICATIONS
- What these findings mean for security
- Potential risks and vulnerabilities
- Impact assessment

## 5. RECOMMENDATIONS
- Immediate actions to take
- Security improvements needed
- User training priorities
- Technical controls and monitoring

## 6. NEXT STEPS
- Additional analysis that might be helpful
- Follow-up questions or investigations
- Tools or methods to consider

Provide a thorough, professional response that directly addresses the user's query using the MCP tool results. Be specific, actionable, and use examples from the data to support your analysis.
"""
        
        # Call Claude
        return llm.invoke_text(
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=4000,
        )
        
    except Exception as e:
        return f"LLM analysis failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="Smart MCP-based Email Phishing Analysis CLI with LLM Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python smart_mcp_cli.py "Find all urgent phishing emails"
  python smart_mcp_cli.py "Show me phishing campaigns"
  python smart_mcp_cli.py "Get document 6_ZV3JkBYed92zFcRQrW"
  python smart_mcp_cli.py "List all indices"
  python smart_mcp_cli.py "Show me suspicious emails"
        """
    )
    
    parser.add_argument('query', help='Your question or request about phishing emails')
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM analysis and show raw results only')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if not config['elastic_url'] or not config['elastic_api_key']:
        print("Error: Missing ELASTIC_URL or ELASTIC_API_KEY environment variables")
        return
    
    print(f"🤖 Smart MCP Analysis")
    print(f"User Query: {args.query}")
    print("=" * 80)
    
    # Execute the smart query
    result = execute_smart_query(args.query, config)
    
    if args.no_llm:
        # Show raw results only
        print("\n" + "=" * 80)
        print("📊 RAW RESULTS")
        print("=" * 80)
        
        # Format and display results based on the action
        if result['intent']['action'] in ['search_emails', 'search_urgent', 'analyze_campaigns']:
            print(format_search_results(result['result']))
        elif result['intent']['action'] == 'get_document':
            print(format_document_result(result['result']))
        elif result['intent']['action'] == 'list_indices':
            if result['result'] and 'content' in result['result']:
                content_text = result['result']['content'][0]['text']
                parsed_results = json.loads(content_text)
                indices = parsed_results.get('indices', [])
                print(f"Available indices: {len(indices)}")
                for idx in indices:
                    print(f"- {idx.get('name', 'Unknown')} ({idx.get('type', 'Unknown')})")
            else:
                print("No indices found.")
        elif result['intent']['action'] == 'get_mapping':
            print("Index mapping retrieved successfully.")
            print(json.dumps(result['result'], indent=2))
        else:
            print("Results:")
            print(json.dumps(result['result'], indent=2))
    else:
        # Generate LLM analysis
        print("\n🧠 Generating comprehensive LLM analysis...")
        llm_analysis = generate_llm_analysis(args.query, result['result'], config)
        
        print("\n" + "=" * 80)
        print("🤖 CLAUDE'S COMPREHENSIVE ANALYSIS")
        print("=" * 80)
        print(llm_analysis)
    
    print("=" * 80)

if __name__ == "__main__":
    main()
