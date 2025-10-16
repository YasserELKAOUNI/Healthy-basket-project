import os
import json
import boto3
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PhishingAnalysisResult:
    """Result of phishing analysis"""
    is_phishing: bool
    confidence_score: float
    risk_factors: List[str]
    suspicious_urls: List[str]
    suspicious_domains: List[str]
    suspicious_keywords: List[str]
    sender_analysis: Dict[str, Any]
    content_analysis: Dict[str, Any]
    recommendations: List[str]

class ElasticMCPServer:
    """Client for Elastic MCP Server using MCP protocol"""
    
    def __init__(self, mcp_server_url: str, api_key: Optional[str] = None):
        self.mcp_server_url = mcp_server_url
        self.api_key = api_key
        self.session = requests.Session()
        
        # Check for AUTH_HEADER environment variable first
        auth_header = os.getenv('AUTH_HEADER')
        if auth_header:
            self.session.headers.update({
                'Authorization': auth_header,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        elif self.api_key:
            # Use ApiKey format for Elastic
            self.session.headers.update({
                'Authorization': f'ApiKey {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
    
    def search_emails(self, query: str, size: int = 10) -> Dict[str, Any]:
        """Search emails using MCP tools"""
        
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "platform_core_search",
                "arguments": {
                    "query": query,
                    "index": "fishfish"
                }
            }
        }
        
        try:
            response = self.session.post(self.mcp_server_url, json=mcp_payload)
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result:
                # Parse MCP response format
                mcp_result = result['result']
                if 'content' in mcp_result and mcp_result['content']:
                    # Extract the JSON string from the content
                    content_text = mcp_result['content'][0]['text']
                    import json
                    parsed_results = json.loads(content_text)
                    
                    # Convert to Elasticsearch-like format
                    hits = []
                    if 'results' in parsed_results:
                        for item in parsed_results['results']:
                            if 'data' in item and 'reference' in item['data']:
                                hit = {
                                    '_id': item['data']['reference']['id'],
                                    '_index': item['data']['reference']['index'],
                                    '_source': item['data'].get('content', {}),
                                    '_score': 1.0
                                }
                                hits.append(hit)
                    
                    return {
                        'hits': {
                            'hits': hits,
                            'total': {'value': len(hits)}
                        }
                    }
                else:
                    return {"hits": {"hits": []}}
            else:
                logger.error(f"MCP search failed: {result}")
                return {"hits": {"hits": []}}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Elastic MCP search failed: {e}")
            return {"hits": {"hits": []}}
        except Exception as e:
            logger.error(f"Error parsing MCP search results: {e}")
            return {"hits": {"hits": []}}
    
    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get specific email by ID using MCP tools"""
        
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "platform_core_get_document_by_id",
                "arguments": {
                    "id": email_id,
                    "index": "fishfish"
                }
            }
        }
        
        try:
            response = self.session.post(self.mcp_server_url, json=mcp_payload)
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result:
                return result['result']
            else:
                logger.error(f"MCP get document failed: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Elastic MCP get document failed: {e}")
            return None
    
    def index_email(self, email_data: Dict[str, Any]) -> bool:
        """Index an email using MCP tools (placeholder implementation)"""
        
        # Note: The MCP server doesn't have a direct indexing tool
        # This would need to be implemented using Elasticsearch REST API
        # or through a different MCP tool if available
        
        logger.warning("Indexing not available through MCP tools. Use direct Elasticsearch API.")
        return False
    
    def get_phishing_statistics(self) -> Dict[str, Any]:
        """Get phishing analysis statistics using MCP tools"""
        
        # Use the search tool to get statistics
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "platform_core_search",
                "arguments": {
                    "query": "phishing analysis statistics",
                    "index": "fishfish"
                }
            }
        }
        
        try:
            response = self.session.post(self.mcp_server_url, json=mcp_payload)
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result:
                return result['result']
            else:
                logger.error(f"MCP statistics failed: {result}")
                return {}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Elastic MCP statistics failed: {e}")
            return {}
    
    def analyze_search_results(self, query: str, hits: List[Dict[str, Any]]) -> str:
        """Use Claude 4.5 to analyze search results and draft a comprehensive response"""
        
        # Prepare the search results for analysis
        search_context = {
            "query": query,
            "total_results": len(hits),
            "documents": []
        }
        
        for i, hit in enumerate(hits[:5], 1):  # Limit to top 5 for analysis
            doc = {
                "id": hit.get('_id', f'doc_{i}'),
                "score": hit.get('_score', 0),
                "highlights": hit.get('_source', {}).get('highlights', [])
            }
            search_context["documents"].append(doc)
        
        # Create analysis prompt
        analysis_prompt = f"""
You are an expert email phishing analyst. I've searched a phishing email database with the query: "{query}"

Here are the search results:
- Total documents found: {len(hits)}
- Top {min(5, len(hits))} most relevant documents:

{chr(10).join([f"Document {i+1}: ID {doc['id']}, Score: {doc['score']}, Highlights: {doc['highlights'][:2] if doc['highlights'] else 'None'}" for i, doc in enumerate(search_context['documents'])])}

Please provide a comprehensive analysis that includes:

1. **Search Summary**: What patterns or themes emerge from these results?
2. **Phishing Indicators**: What common phishing techniques are present in these emails?
3. **Risk Assessment**: How serious are these threats based on the content?
4. **Recommendations**: What actions should be taken based on these findings?
5. **Pattern Analysis**: Are there any recurring tactics or target types?

Format your response clearly with headers and bullet points where appropriate.
"""
        
        try:
            # Use Claude 4.5 for analysis
            response = self.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude 4.5 analysis failed: {e}")
            return f"Analysis failed: {str(e)}"

class BedrockClaudeClient:
    """Client for AWS Bedrock Claude 4.5"""
    
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name=region
        )
        self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet
    
    def analyze_email_for_phishing(self, email_content: str, sender_info: Dict[str, Any]) -> PhishingAnalysisResult:
        """Analyze email content for phishing indicators using Claude"""
        
        prompt = f"""
        You are an expert email phishing analyst. Analyze the following email for phishing indicators:

        EMAIL CONTENT:
        {email_content}

        SENDER INFORMATION:
        {json.dumps(sender_info, indent=2)}

        Please analyze this email and provide:
        1. Is this likely a phishing email? (true/false)
        2. Confidence score (0.0 to 1.0)
        3. Risk factors identified
        4. Suspicious URLs found
        5. Suspicious domains found
        6. Suspicious keywords/phrases
        7. Sender analysis (reputation, spoofing indicators)
        8. Content analysis (urgency, grammar, requests)
        9. Recommendations for handling

        Respond in JSON format with the following structure:
        {{
            "is_phishing": boolean,
            "confidence_score": float,
            "risk_factors": ["factor1", "factor2"],
            "suspicious_urls": ["url1", "url2"],
            "suspicious_domains": ["domain1", "domain2"],
            "suspicious_keywords": ["keyword1", "keyword2"],
            "sender_analysis": {{
                "reputation_score": float,
                "spoofing_indicators": ["indicator1"],
                "domain_analysis": "analysis"
            }},
            "content_analysis": {{
                "urgency_level": "high/medium/low",
                "grammar_quality": "good/poor",
                "request_type": "description"
            }},
            "recommendations": ["rec1", "rec2"]
        }}
        """
        
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            analysis_text = response_body['content'][0]['text']
            
            # Parse the JSON response
            analysis_data = json.loads(analysis_text)
            
            return PhishingAnalysisResult(
                is_phishing=analysis_data.get('is_phishing', False),
                confidence_score=analysis_data.get('confidence_score', 0.0),
                risk_factors=analysis_data.get('risk_factors', []),
                suspicious_urls=analysis_data.get('suspicious_urls', []),
                suspicious_domains=analysis_data.get('suspicious_domains', []),
                suspicious_keywords=analysis_data.get('suspicious_keywords', []),
                sender_analysis=analysis_data.get('sender_analysis', {}),
                content_analysis=analysis_data.get('content_analysis', {}),
                recommendations=analysis_data.get('recommendations', [])
            )
            
        except Exception as e:
            logger.error(f"Bedrock analysis failed: {e}")
            # Return a default result
            return PhishingAnalysisResult(
                is_phishing=False,
                confidence_score=0.0,
                risk_factors=["Analysis failed"],
                suspicious_urls=[],
                suspicious_domains=[],
                suspicious_keywords=[],
                sender_analysis={},
                content_analysis={},
                recommendations=["Manual review required due to analysis failure"]
            )

class EmailPhishingAnalyzer:
    """Main email phishing analysis agent"""
    
    def __init__(self, elastic_url: str, elastic_api_key: Optional[str] = None, bedrock_region: str = "us-east-1"):
        self.elastic_client = ElasticMCPServer(elastic_url, elastic_api_key)
        self.claude_client = BedrockClaudeClient(bedrock_region)
        
        # Common phishing indicators
        self.phishing_keywords = [
            "urgent", "immediately", "verify", "confirm", "suspended", "locked",
            "expired", "click here", "act now", "limited time", "free money",
            "congratulations", "winner", "prize", "lottery", "inheritance"
        ]
        
        self.suspicious_domains = [
            "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly"
        ]
    
    def extract_email_content(self, email_data: Dict[str, Any]) -> str:
        """Extract text content from email"""
        content = ""
        
        # Extract from body
        if 'body' in email_data:
            body = email_data['body']
            if isinstance(body, str):
                content += body
            elif isinstance(body, dict):
                # Handle multipart emails
                if 'text' in body:
                    content += body['text']
                if 'html' in body:
                    # Strip HTML tags
                    soup = BeautifulSoup(body['html'], 'html.parser')
                    content += soup.get_text()
        
        # Add subject
        if 'subject' in email_data:
            content += f"\nSubject: {email_data['subject']}"
        
        return content
    
    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text"""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    def extract_domains(self, urls: List[str]) -> List[str]:
        """Extract domains from URLs"""
        domains = []
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if domain:
                    domains.append(domain)
            except:
                continue
        return domains
    
    def analyze_email(self, email_data: Dict[str, Any]) -> PhishingAnalysisResult:
        """Perform comprehensive phishing analysis on an email"""
        
        # Extract email content
        email_content = self.extract_email_content(email_data)
        
        # Extract sender information
        sender_info = {
            'email': email_data.get('sender', ''),
            'name': email_data.get('sender_name', ''),
            'domain': email_data.get('sender', '').split('@')[-1] if '@' in email_data.get('sender', '') else ''
        }
        
        # Use Claude for AI analysis
        claude_result = self.claude_client.analyze_email_for_phishing(email_content, sender_info)
        
        # Perform additional rule-based analysis
        urls = self.extract_urls(email_content)
        domains = self.extract_domains(urls)
        
        # Check for suspicious patterns
        additional_risk_factors = []
        
        # Check for suspicious domains
        for domain in domains:
            if any(suspicious in domain for suspicious in self.suspicious_domains):
                additional_risk_factors.append(f"Suspicious URL shortener domain: {domain}")
        
        # Check for phishing keywords
        content_lower = email_content.lower()
        found_keywords = [keyword for keyword in self.phishing_keywords if keyword in content_lower]
        if found_keywords:
            additional_risk_factors.append(f"Suspicious keywords found: {', '.join(found_keywords)}")
        
        # Combine results
        combined_risk_factors = claude_result.risk_factors + additional_risk_factors
        
        # Update confidence score based on additional factors
        confidence_adjustment = len(additional_risk_factors) * 0.1
        final_confidence = min(1.0, claude_result.confidence_score + confidence_adjustment)
        
        return PhishingAnalysisResult(
            is_phishing=claude_result.is_phishing or len(additional_risk_factors) > 2,
            confidence_score=final_confidence,
            risk_factors=combined_risk_factors,
            suspicious_urls=claude_result.suspicious_urls + urls,
            suspicious_domains=claude_result.suspicious_domains + domains,
            suspicious_keywords=claude_result.suspicious_keywords + found_keywords,
            sender_analysis=claude_result.sender_analysis,
            content_analysis=claude_result.content_analysis,
            recommendations=claude_result.recommendations
        )
    
    def search_similar_emails(self, email_data: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """Search for similar emails in the database using MCP tools"""
        query_terms = []
        
        if 'subject' in email_data:
            query_terms.append(email_data['subject'])
        
        if 'sender' in email_data:
            query_terms.append(email_data['sender'])
        
        # Extract key phrases from body
        body_text = self.extract_email_content(email_data)
        # Simple keyword extraction (in production, use more sophisticated NLP)
        words = re.findall(r'\b\w+\b', body_text.lower())
        common_words = [word for word in words if len(word) > 4 and word not in ['this', 'that', 'with', 'from', 'they', 'have', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'will', 'about', 'would', 'there', 'could', 'other']]
        query_terms.extend(common_words[:5])  # Add top 5 uncommon words
        
        query = ' '.join(query_terms)
        results = self.elastic_client.search_emails(query, size=limit)
        
        return results.get('hits', {}).get('hits', [])
    
    def index_email_for_analysis(self, email_data: Dict[str, Any], analysis_result: PhishingAnalysisResult) -> bool:
        """Index email and analysis results for future reference"""
        
        indexed_data = {
            **email_data,
            'analysis_result': {
                'is_phishing': analysis_result.is_phishing,
                'confidence_score': analysis_result.confidence_score,
                'risk_factors': analysis_result.risk_factors,
                'suspicious_urls': analysis_result.suspicious_urls,
                'suspicious_domains': analysis_result.suspicious_domains,
                'suspicious_keywords': analysis_result.suspicious_keywords,
                'timestamp': email_data.get('timestamp', ''),
                'analyzed_at': str(datetime.now())
            }
        }
        
        return self.elastic_client.index_email(indexed_data)
    
    def analyze_search_results(self, query: str, hits: List[Dict[str, Any]]) -> str:
        """Use Claude 4.5 to analyze search results and draft a comprehensive response"""
        
        # Prepare the search results for analysis
        search_context = {
            "query": query,
            "total_results": len(hits),
            "documents": []
        }
        
        for i, hit in enumerate(hits[:5], 1):  # Limit to top 5 for analysis
            doc = {
                "id": hit.get('_id', f'doc_{i}'),
                "score": hit.get('_score', 0),
                "highlights": hit.get('_source', {}).get('highlights', [])
            }
            search_context["documents"].append(doc)
        
        # Create analysis prompt
        analysis_prompt = f"""
You are an expert email phishing analyst. I've searched a phishing email database with the query: "{query}"

Here are the search results:
- Total documents found: {len(hits)}
- Top {min(5, len(hits))} most relevant documents:

{chr(10).join([f"Document {i+1}: ID {doc['id']}, Score: {doc['score']}, Highlights: {doc['highlights'][:2] if doc['highlights'] else 'None'}" for i, doc in enumerate(search_context['documents'])])}

Please provide a comprehensive analysis that includes:

1. **Search Summary**: What patterns or themes emerge from these results?
2. **Phishing Indicators**: What common phishing techniques are present in these emails?
3. **Risk Assessment**: How serious are these threats based on the content?
4. **Recommendations**: What actions should be taken based on these findings?
5. **Pattern Analysis**: Are there any recurring tactics or target types?

Format your response clearly with headers and bullet points where appropriate.
"""
        
        try:
            # Use Claude 3.5 Sonnet for analysis
            response = self.claude_client.bedrock.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude 4.5 analysis failed: {e}")
            return f"Analysis failed: {str(e)}"
    
    def comprehensive_analysis(self, query: str, hits: List[Dict[str, Any]]) -> str:
        """Use Claude 3.5 Sonnet to provide a comprehensive, detailed analysis of search results"""
        
        # Prepare the search results for analysis
        search_context = {
            "query": query,
            "total_results": len(hits),
            "documents": []
        }
        
        for i, hit in enumerate(hits[:5], 1):  # Limit to top 5 for analysis
            doc = {
                "id": hit.get('_id', f'doc_{i}'),
                "score": hit.get('_score', 0),
                "highlights": hit.get('_source', {}).get('highlights', [])
            }
            search_context["documents"].append(doc)
        
        # Create comprehensive analysis prompt
        analysis_prompt = f"""
You are a world-class email phishing analyst and cybersecurity expert. I've searched a comprehensive phishing email database with the query: "{query}"

DATABASE SEARCH RESULTS:
- Total documents found: {len(hits)}
- Top {min(5, len(hits))} most relevant documents analyzed:

{chr(10).join([f"Document {i+1}: ID {doc['id']}, Score: {doc['score']}, Highlights: {doc['highlights'][:2] if doc['highlights'] else 'None'}" for i, doc in enumerate(search_context['documents'])])}

Please provide a COMPREHENSIVE, DETAILED analysis that includes:

## 1. EXECUTIVE SUMMARY
- Brief overview of what was found
- Key insights and immediate concerns
- Overall threat level assessment

## 2. DETAILED SEARCH ANALYSIS
- What specific patterns, themes, and tactics emerge from these results?
- How do these results relate to current phishing trends?
- What makes these particular emails effective or concerning?

## 3. PHISHING INDICATORS & TECHNIQUES
- Detailed breakdown of phishing techniques present
- Sophistication level of the attacks
- Technical indicators (URLs, domains, content structure)
- Psychological manipulation tactics used

## 4. RISK ASSESSMENT & IMPACT
- Severity of threats based on content analysis
- Potential impact on victims
- Likelihood of success for attackers
- Target demographics and attack vectors

## 5. THREAT INTELLIGENCE INSIGHTS
- Attribution patterns (if any)
- Campaign characteristics
- Evolution of techniques over time
- Connection to known threat groups or patterns

## 6. DEFENSIVE RECOMMENDATIONS
- Immediate actions to take
- Long-term security improvements
- User training priorities
- Technical controls and monitoring

## 7. PATTERN ANALYSIS & TRENDS
- Recurring tactics and target types
- Geographic or demographic patterns
- Temporal patterns (if applicable)
- Industry-specific targeting

## 8. FORENSIC DETAILS
- Technical analysis of suspicious elements
- URL and domain analysis
- Content structure examination
- Metadata and header analysis

Provide a thorough, professional analysis that would be suitable for a cybersecurity report. Use specific examples from the search results to support your analysis. Be detailed and actionable in your recommendations.
"""
        
        try:
            # Use Claude 3.5 Sonnet for comprehensive analysis
            response = self.claude_client.bedrock.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,  # Increased token limit for comprehensive analysis
                    "messages": [
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude comprehensive analysis failed: {e}")
            return f"Comprehensive analysis failed: {str(e)}"

def main():
    """Example usage of the email phishing analyzer"""
    
    # Configuration
    ELASTIC_URL = os.getenv('ELASTIC_URL', 'https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud')
    ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
    BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')
    
    # Initialize analyzer
    analyzer = EmailPhishingAnalyzer(ELASTIC_URL, ELASTIC_API_KEY, BEDROCK_REGION)
    
    # Example email data
    sample_email = {
        'sender': 'noreply@bank-security.com',
        'sender_name': 'Bank Security Team',
        'subject': 'URGENT: Verify Your Account Immediately',
        'body': {
            'text': 'Dear Customer,\n\nYour account has been suspended due to suspicious activity. Click here to verify your identity immediately: http://bit.ly/verify-now\n\nThis is urgent - act now or your account will be permanently locked.\n\nBest regards,\nBank Security Team'
        },
        'recipient': 'user@example.com',
        'timestamp': '2024-01-15T10:30:00Z'
    }
    
    # Analyze the email
    print("Analyzing email for phishing indicators...")
    result = analyzer.analyze_email(sample_email)
    
    # Print results
    print(f"\n=== PHISHING ANALYSIS RESULTS ===")
    print(f"Is Phishing: {result.is_phishing}")
    print(f"Confidence Score: {result.confidence_score:.2f}")
    print(f"Risk Factors: {', '.join(result.risk_factors)}")
    print(f"Suspicious URLs: {', '.join(result.suspicious_urls)}")
    print(f"Suspicious Domains: {', '.join(result.suspicious_domains)}")
    print(f"Suspicious Keywords: {', '.join(result.suspicious_keywords)}")
    print(f"Recommendations: {', '.join(result.recommendations)}")
    
    # Search for similar emails
    print(f"\n=== SEARCHING FOR SIMILAR EMAILS ===")
    similar_emails = analyzer.search_similar_emails(sample_email)
    print(f"Found {len(similar_emails)} similar emails")
    
    # Index the email for future reference
    print(f"\n=== INDEXING EMAIL ===")
    indexed = analyzer.index_email_for_analysis(sample_email, result)
    print(f"Email indexed successfully: {indexed}")

if __name__ == "__main__":
    from datetime import datetime
    main()
