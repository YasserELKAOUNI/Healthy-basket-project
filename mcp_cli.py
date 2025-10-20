#!/usr/bin/env python3
"""
MCP-based Email Phishing Analysis CLI
Uses MCP tools directly for all operations
"""

import argparse
import json
from typing import Dict, Any, List
from src.core.config import get_settings
from src.core.mcp_client import MCPClient, parse_mcp_content_text
from src.core.llm_client import BedrockLLMClient

def load_config():
    """Load configuration from centralized settings."""
    s = get_settings()
    return {
        'elastic_url': s.elastic_url,
        'elastic_api_key': s.elastic_api_key,
        'bedrock_region': s.bedrock_region,
    }

def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], config: Dict[str, str]) -> Dict[str, Any]:
    """Call an MCP tool via MCPClient facade."""
    client = MCPClient(elastic_url=config['elastic_url'], api_key=config['elastic_api_key'])
    return client.call_tool(tool_name, arguments)

def search_emails_mcp(query: str, config: Dict[str, str], size: int = 10) -> List[Dict[str, Any]]:
    """Search emails using MCP platform_core_search tool"""
    
    print(f"🔍 Searching with MCP tool: platform_core_search")
    print(f"Query: {query}")
    print(f"Index: fishfish")
    
    result = call_mcp_tool("platform_core_search", {
        "query": query,
        "index": "fishfish"
    }, config)
    
    if not result:
        return []
    
    # Parse MCP response format
    hits = []
    parsed_results = parse_mcp_content_text(result)
    if parsed_results:
        
        if 'results' in parsed_results:
            for item in parsed_results['results'][:size]:
                if 'data' in item and 'reference' in item['data']:
                    hit = {
                        '_id': item['data']['reference']['id'],
                        '_index': item['data']['reference']['index'],
                        '_source': item['data'].get('content', {}),
                        '_score': 1.0
                    }
                    hits.append(hit)
    
    return hits

def get_email_by_id_mcp(email_id: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Get specific email using MCP platform_core_get_document_by_id tool"""
    
    print(f"📧 Getting email with MCP tool: platform_core_get_document_by_id")
    print(f"ID: {email_id}")
    print(f"Index: fishfish")
    
    result = call_mcp_tool("platform_core_get_document_by_id", {
        "id": email_id,
        "index": "fishfish"
    }, config)
    
    if not result:
        return {}
    
    # Parse MCP response format
    parsed = parse_mcp_content_text(result)
    if parsed:
        return parsed
    
    return {}

def list_indices_mcp(config: Dict[str, str]) -> List[Dict[str, Any]]:
    """List indices using MCP platform_core_list_indices tool"""
    
    print(f"📋 Listing indices with MCP tool: platform_core_list_indices")
    
    result = call_mcp_tool("platform_core_list_indices", {}, config)
    
    if not result:
        return []
    
    # Parse MCP response format
    indices = []
    parsed_results = parse_mcp_content_text(result)
    if parsed_results:
        indices = parsed_results.get('indices', [])
    
    return indices

def get_index_mapping_mcp(index_name: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Get index mapping using MCP platform_core_get_index_mapping tool"""
    
    print(f"🗺️ Getting mapping with MCP tool: platform_core_get_index_mapping")
    print(f"Index: {index_name}")
    
    result = call_mcp_tool("platform_core_get_index_mapping", {
        "indices": [index_name]
    }, config)
    
    if not result:
        return {}
    
    # Parse MCP response format
    parsed = parse_mcp_content_text(result)
    if parsed:
        return parsed
    
    return {}

def analyze_with_claude(query: str, hits: List[Dict[str, Any]], config: Dict[str, str]) -> str:
    """Analyze search results using Claude via Bedrock"""
    
    try:
        llm = BedrockLLMClient(region_name=config['bedrock_region'])
        
        # Prepare analysis prompt
        analysis_prompt = f"""
You are a world-class email phishing analyst. I've searched a phishing email database with the query: "{query}"

Here are the search results:
- Total documents found: {len(hits)}
- Top {min(5, len(hits))} most relevant documents:

{chr(10).join([f"Document {i+1}: ID {hit['_id']}, Score: {hit['_score']}, Highlights: {hit['_source'].get('highlights', [])[:2] if hit['_source'].get('highlights') else 'None'}" for i, hit in enumerate(hits[:5])])}

Please provide a comprehensive analysis including:
1. **Search Summary**: What patterns emerge from these results?
2. **Phishing Indicators**: What techniques are present?
3. **Risk Assessment**: How serious are these threats?
4. **Recommendations**: What actions should be taken?
5. **Pattern Analysis**: Any recurring tactics or target types?

Format your response clearly with headers and bullet points.
"""
        
        # Call Claude
        return llm.invoke_text(
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=2000,
        )
        
    except Exception as e:
        return f"Analysis failed: {str(e)}"

def generate_text_from_document(email_data: Dict[str, Any], config: Dict[str, str]) -> str:
    """Generate comprehensive text analysis from email document using Claude"""
    
    try:
        llm = BedrockLLMClient(region_name=config['bedrock_region'])
        
        # Extract key information from the document structure
        if 'results' in email_data and email_data['results']:
            result = email_data['results'][0]
            document_id = result.get('data', {}).get('reference', {}).get('id', 'Unknown')
            content = result.get('data', {}).get('content', {})
        else:
            document_id = 'Unknown'
            content = {}
        
        # Extract parsed data
        extracted_data = {}
        if 'output' in content:
            try:
                extracted_data = json.loads(content['output'])
            except:
                extracted_data = {}
        
        # Prepare comprehensive text generation prompt
        text_prompt = f"""
You are an expert cybersecurity analyst and technical writer. I've retrieved a phishing email document from our database.

DOCUMENT INFORMATION:
- Document ID: {document_id}
- Category: {extracted_data.get('category', 'Unknown')}
- Date: {extracted_data.get('date', content.get('date', 'Unknown'))}
- Subject: {content.get('subject', 'Unknown')}
- From: {content.get('from', 'Unknown')}

EMAIL CONTENT ANALYSIS:
{content.get('content', 'No content available')}

EXTRACTED DATA:
- URLs: {extracted_data.get('urls', [])}
- Reasoning: {extracted_data.get('reasoning', 'No reasoning provided')}

Please generate a comprehensive, professional text analysis that includes:

## 1. EXECUTIVE SUMMARY
- Brief overview of the email and its threat level
- Key findings and immediate concerns

## 2. TECHNICAL ANALYSIS
- Detailed breakdown of the email structure and content
- Analysis of URLs, domains, and technical elements
- Identification of suspicious patterns and techniques

## 3. PHISHING INDICATORS
- Specific phishing techniques used in this email
- Sophistication level and effectiveness assessment
- Comparison to known phishing patterns

## 4. THREAT ASSESSMENT
- Risk level and potential impact
- Target audience and attack vector analysis
- Likelihood of success for attackers

## 5. FORENSIC DETAILS
- Technical analysis of suspicious elements
- URL and domain analysis
- Content structure examination
- Metadata and header analysis

## 6. RECOMMENDATIONS
- Immediate actions to take
- Long-term security improvements
- User training priorities
- Technical controls and monitoring

## 7. INCIDENT RESPONSE
- Steps to take if this email is encountered
- Reporting procedures
- Containment and mitigation strategies

Generate a thorough, professional analysis suitable for a cybersecurity report. Use specific examples from the email content to support your analysis. Be detailed and actionable in your recommendations.
"""
        
        # Call Claude
        return llm.invoke_text(
            model_id='anthropic.claude-3-5-sonnet-20240620-v1:0',
            messages=[{"role": "user", "content": text_prompt}],
            max_tokens=4000,
        )
        
    except Exception as e:
        return f"Text generation failed: {str(e)}"

def main():
    parser = argparse.ArgumentParser(
        description="MCP-based Email Phishing Analysis CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mcp_cli.py search "urgent verify account"
  python mcp_cli.py search "phishing" --analyze
  python mcp_cli.py get-email 6_ZV3JkBYed92zFcRQrW --analyze
  python mcp_cli.py generate-text 6_ZV3JkBYed92zFcRQrW
  python mcp_cli.py list-indices
  python mcp_cli.py get-mapping fishfish
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search emails using MCP tools')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--size', type=int, default=10, help='Number of results to return')
    search_parser.add_argument('--analyze', action='store_true', help='Analyze results with Claude')
    
    # Get email command
    get_parser = subparsers.add_parser('get-email', help='Get specific email by ID using MCP tools')
    get_parser.add_argument('email_id', help='Email document ID')
    get_parser.add_argument('--analyze', action='store_true', help='Generate comprehensive text analysis with Claude')
    
    # List indices command
    list_parser = subparsers.add_parser('list-indices', help='List all indices using MCP tools')
    
    # Get mapping command
    mapping_parser = subparsers.add_parser('get-mapping', help='Get index mapping using MCP tools')
    mapping_parser.add_argument('index_name', help='Index name')
    
    # Generate text command
    text_parser = subparsers.add_parser('generate-text', help='Generate comprehensive text analysis from email document')
    text_parser.add_argument('email_id', help='Email document ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = load_config()
    
    if not config['elastic_url'] or not config['elastic_api_key']:
        print("Error: Missing ELASTIC_URL or ELASTIC_API_KEY environment variables")
        return
    
    if args.command == 'search':
        hits = search_emails_mcp(args.query, config, args.size)
        
        print(f"\n=== MCP SEARCH RESULTS ===")
        print(f"Found {len(hits)} results")
        
        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            print(f"\n{i}. Document ID: {hit.get('_id', 'N/A')}")
            print(f"   Index: {hit.get('_index', 'N/A')}")
            print(f"   Score: {hit.get('_score', 'N/A')}")
            
            if 'highlights' in source:
                print(f"   Highlights: {source['highlights'][:2]}")
        
        if args.analyze and hits:
            print(f"\n=== CLAUDE ANALYSIS ===")
            analysis = analyze_with_claude(args.query, hits, config)
            print(f"\n🤖 Claude Analysis:")
            print("=" * 80)
            print(analysis)
            print("=" * 80)
    
    elif args.command == 'get-email':
        email_data = get_email_by_id_mcp(args.email_id, config)
        
        print(f"\n=== EMAIL DETAILS ===")
        if email_data:
            print(f"Document ID: {args.email_id}")
            if args.analyze:
                print(f"\n=== GENERATING COMPREHENSIVE TEXT ANALYSIS ===")
                text_analysis = generate_text_from_document(email_data, config)
                print(f"\n🤖 Claude Text Analysis:")
                print("=" * 80)
                print(text_analysis)
                print("=" * 80)
            else:
                print(f"Content: {json.dumps(email_data, indent=2)}")
        else:
            print("Email not found")
    
    elif args.command == 'generate-text':
        email_data = get_email_by_id_mcp(args.email_id, config)
        
        if email_data:
            print(f"\n=== GENERATING COMPREHENSIVE TEXT ANALYSIS ===")
            print(f"Document ID: {args.email_id}")
            text_analysis = generate_text_from_document(email_data, config)
            print(f"\n🤖 Claude Text Analysis:")
            print("=" * 80)
            print(text_analysis)
            print("=" * 80)
        else:
            print("Email not found")
    
    elif args.command == 'list-indices':
        indices = list_indices_mcp(config)
        
        print(f"\n=== AVAILABLE INDICES ===")
        for index in indices:
            print(f"- {index.get('name', 'Unknown')} ({index.get('type', 'Unknown')})")
    
    elif args.command == 'get-mapping':
        mapping = get_index_mapping_mcp(args.index_name, config)
        
        print(f"\n=== INDEX MAPPING FOR {args.index_name.upper()} ===")
        print(json.dumps(mapping, indent=2))

if __name__ == "__main__":
    main()
