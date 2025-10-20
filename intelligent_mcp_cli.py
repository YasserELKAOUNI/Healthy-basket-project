#!/usr/bin/env python3
"""
Intelligent MCP-based Email Phishing Analysis CLI
Uses Claude to decide which MCP tools to call based on user queries
"""

import argparse
import json
from src.core.config import get_settings
from src.core.mcp_client import MCPClient
from src.core.llm_client import BedrockLLMClient
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
    
    mcp_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    client = MCPClient(elastic_url=config['elastic_url'], api_key=config['elastic_api_key'])
    return client.call_tool(tool_name, arguments)

def get_available_tools(config: Dict[str, str]) -> List[Dict[str, Any]]:
    """Get list of available MCP tools"""
    
    mcp_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/list'
    }
    
    client = MCPClient(elastic_url=config['elastic_url'], api_key=config['elastic_api_key'])
    try:
        return client.list_tools()
    except Exception:
        return []

def let_claude_decide_tools(user_query: str, available_tools: List[Dict[str, Any]], config: Dict[str, str]) -> str:
    """Let Claude decide which MCP tools to call based on the user query"""
    
    try:
        llm = BedrockLLMClient(region_name=config['bedrock_region'])
        
        # Create tools description for Claude
        tools_description = ""
        for tool in available_tools:
            tools_description += f"- {tool['name']}: {tool['description']}\n"
            if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                params = list(tool['inputSchema']['properties'].keys())
                tools_description += f"  Parameters: {params}\n"
            tools_description += "\n"
        
        # Create decision prompt
        decision_prompt = f"""
You are an intelligent assistant that helps users analyze phishing emails using MCP (Model Context Protocol) tools. 

USER QUERY: "{user_query}"

AVAILABLE MCP TOOLS:
{tools_description}

Based on the user's query, you need to:
1. Determine which MCP tool(s) would be most appropriate to use
2. Decide on the parameters for each tool
3. Execute the tool calls
4. Analyze the results and provide a comprehensive response

Please respond with a JSON object in this exact format:
{{
    "reasoning": "Explain why you chose these tools and parameters",
    "tools_to_call": [
        {{
            "tool_name": "platform_core_search",
            "arguments": {{"query": "phishing", "index": "fishfish"}},
            "purpose": "Search for phishing emails"
        }}
    ],
    "analysis_approach": "Describe how you will analyze the results"
}}

IMPORTANT:
- Always use the "fishfish" index for email searches
- For search queries, use platform_core_search
- For specific documents, use platform_core_get_document_by_id
- For listing indices, use platform_core_list_indices
- For mappings, use platform_core_get_index_mapping
- Be specific about what you're looking for based on the user query
"""
        
        # Call Claude for tool selection
        return llm.invoke_text(
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            messages=[{"role": "user", "content": decision_prompt}],
            max_tokens=2000,
        )
        
    except Exception as e:
        return f"Tool selection failed: {str(e)}"

def execute_tool_calls(tool_calls: List[Dict[str, Any]], config: Dict[str, str]) -> List[Dict[str, Any]]:
    """Execute the MCP tool calls decided by Claude"""
    
    results = []
    
    for tool_call in tool_calls:
        tool_name = tool_call.get('tool_name')
        arguments = tool_call.get('arguments', {})
        purpose = tool_call.get('purpose', '')
        
        print(f"🔧 Executing: {tool_name}")
        print(f"   Purpose: {purpose}")
        print(f"   Arguments: {arguments}")
        
        result = call_mcp_tool(tool_name, arguments, config)
        results.append({
            'tool_name': tool_name,
            'arguments': arguments,
            'purpose': purpose,
            'result': result
        })
        
        print(f"   ✅ Completed\n")
    
    return results

def analyze_results_with_claude(user_query: str, tool_results: List[Dict[str, Any]], config: Dict[str, str]) -> str:
    """Use Claude to analyze the MCP tool results and provide comprehensive response"""
    
    try:
        llm = BedrockLLMClient(region_name=config['bedrock_region'])
        
        # Prepare results summary for Claude
        results_summary = ""
        for i, result in enumerate(tool_results, 1):
            results_summary += f"Tool {i}: {result['tool_name']}\n"
            results_summary += f"Purpose: {result['purpose']}\n"
            results_summary += f"Arguments: {result['arguments']}\n"
            results_summary += f"Result: {json.dumps(result['result'], indent=2)}\n\n"
        
        # Create analysis prompt
        analysis_prompt = f"""
You are an expert cybersecurity analyst. A user asked: "{user_query}"

I executed the following MCP tools and got these results:

{results_summary}

Please provide a comprehensive analysis that includes:

## 1. QUERY RESPONSE
- Direct answer to the user's question
- Summary of what was found

## 2. TECHNICAL ANALYSIS
- Detailed analysis of the MCP tool results
- Key findings and insights
- Patterns or trends identified

## 3. PHISHING INSIGHTS
- Specific phishing techniques or patterns found
- Risk assessment based on the data
- Threat level evaluation

## 4. RECOMMENDATIONS
- Immediate actions to take
- Security improvements needed
- User training priorities

## 5. NEXT STEPS
- Additional analysis that might be helpful
- Follow-up questions or investigations
- Tools or methods to consider

Provide a thorough, professional response that directly addresses the user's query using the MCP tool results. Be specific and actionable.
"""
        
        # Call Claude for analysis
        return llm.invoke_text(
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=4000,
        )
        
    except Exception as e:
        return f"Analysis failed: {str(e)}"

def intelligent_query(user_query: str, config: Dict[str, str]) -> str:
    """Main function that lets Claude decide which tools to use"""
    
    print(f"🤖 Intelligent MCP Analysis")
    print(f"User Query: {user_query}")
    print("=" * 80)
    
    # Get available tools
    print("📋 Getting available MCP tools...")
    available_tools = get_available_tools(config)
    print(f"Found {len(available_tools)} available tools\n")
    
    # Let Claude decide which tools to use
    print("🧠 Letting Claude decide which tools to use...")
    claude_decision = let_claude_decide_tools(user_query, available_tools, config)
    
    try:
        # Clean the response and extract JSON
        import re
        
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', claude_decision, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            # Clean control characters
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            decision_data = json.loads(json_str)
        else:
            # Fallback: try to parse the entire response
            decision_data = json.loads(claude_decision)
        
        print(f"💭 Claude's Reasoning: {decision_data.get('reasoning', 'No reasoning provided')}")
        print(f"🎯 Analysis Approach: {decision_data.get('analysis_approach', 'No approach specified')}")
        print()
        
        # Execute the tool calls
        tool_calls = decision_data.get('tools_to_call', [])
        if not tool_calls:
            return "No tools were selected for execution."
        
        print(f"🔧 Executing {len(tool_calls)} tool call(s)...")
        tool_results = execute_tool_calls(tool_calls, config)
        
        # Analyze results with Claude
        print("🧠 Analyzing results with Claude...")
        analysis = analyze_results_with_claude(user_query, tool_results, config)
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse Claude's decision: {e}")
        print("🔄 Attempting to extract and execute tools manually...")
        
        # Fallback: try to extract tool calls manually
        try:
            # Look for tool calls in the text
            if "platform_core_search" in claude_decision:
                # Default search for urgent phishing
                tool_calls = [{
                    "tool_name": "platform_core_search",
                    "arguments": {"query": "urgent phishing", "index": "fishfish"},
                    "purpose": "Search for urgent phishing emails"
                }]
                
                print(f"🔧 Executing fallback search...")
                tool_results = execute_tool_calls(tool_calls, config)
                
                print("🧠 Analyzing results with Claude...")
                analysis = analyze_results_with_claude(user_query, tool_results, config)
                return analysis
            else:
                return f"Could not determine appropriate tools from Claude's response.\n\nClaude's response:\n{claude_decision}"
        except Exception as fallback_error:
            return f"Fallback execution failed: {fallback_error}\n\nClaude's response:\n{claude_decision}"
    except Exception as e:
        return f"Error in intelligent query processing: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="Intelligent MCP-based Email Phishing Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python intelligent_mcp_cli.py "Find all urgent phishing emails"
  python intelligent_mcp_cli.py "Show me phishing campaigns targeting banks"
  python intelligent_mcp_cli.py "What are the most common phishing techniques?"
  python intelligent_mcp_cli.py "Get details about document 6_ZV3JkBYed92zFcRQrW"
  python intelligent_mcp_cli.py "List all available indices"
        """
    )
    
    parser.add_argument('query', help='Your question or request about phishing emails')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if not config['elastic_url'] or not config['elastic_api_key']:
        print("Error: Missing ELASTIC_URL or ELASTIC_API_KEY environment variables")
        return
    
    # Process the intelligent query
    result = intelligent_query(args.query, config)
    
    print("\n" + "=" * 80)
    print("🤖 CLAUDE'S COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    print(result)
    print("=" * 80)

if __name__ == "__main__":
    main()
