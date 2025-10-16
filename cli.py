#!/usr/bin/env python3
"""
Email Phishing Analysis Agent - CLI Tool

This script provides a command-line interface for the email phishing analysis agent.
"""

import argparse
import json
import sys
from email_phishing_analyzer import EmailPhishingAnalyzer
import os
from dotenv import load_dotenv

def load_config():
    """Load configuration from environment variables"""
    load_dotenv()
    
    return {
        'elastic_url': os.getenv('ELASTIC_URL', 'https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud'),
        'elastic_api_key': os.getenv('ELASTIC_API_KEY'),
        'bedrock_region': os.getenv('BEDROCK_REGION', 'us-east-1')
    }

def analyze_email_file(file_path: str, config: dict):
    """Analyze an email from a JSON file"""
    try:
        with open(file_path, 'r') as f:
            email_data = json.load(f)
        
        analyzer = EmailPhishingAnalyzer(
            config['elastic_url'],
            config['elastic_api_key'],
            config['bedrock_region']
        )
        
        result = analyzer.analyze_email(email_data)
        
        print(f"\n=== PHISHING ANALYSIS RESULTS ===")
        print(f"Is Phishing: {result.is_phishing}")
        print(f"Confidence Score: {result.confidence_score:.2f}")
        print(f"Risk Factors: {', '.join(result.risk_factors)}")
        print(f"Suspicious URLs: {', '.join(result.suspicious_urls)}")
        print(f"Suspicious Domains: {', '.join(result.suspicious_domains)}")
        print(f"Suspicious Keywords: {', '.join(result.suspicious_keywords)}")
        print(f"Recommendations: {', '.join(result.recommendations)}")
        
        return result
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{file_path}'")
        return None
    except Exception as e:
        print(f"Error analyzing email: {e}")
        return None

def search_emails(query: str, config: dict, size: int = 10, analyze: bool = False):
    """Search for emails and optionally analyze with Claude 4.5"""
    try:
        analyzer = EmailPhishingAnalyzer(
            config['elastic_url'],
            config['elastic_api_key'],
            config['bedrock_region']
        )
        
        results = analyzer.elastic_client.search_emails(query, size=size)
        hits = results.get('hits', {}).get('hits', [])
        
        print(f"\n=== SEARCH RESULTS ===")
        print(f"Query: {query}")
        print(f"Found {len(hits)} results")
        
        # Display basic results
        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            print(f"\n{i}. Document ID: {hit.get('_id', 'N/A')}")
            print(f"   Index: {hit.get('_index', 'N/A')}")
            print(f"   Score: {hit.get('_score', 'N/A')}")
            
            # Show highlights if available
            if 'highlights' in source:
                print(f"   Highlights: {source['highlights'][:2]}")  # Show first 2 highlights
        
        # If analyze flag is set, use Claude 3.5 Sonnet to analyze the results
        if analyze and hits:
            print(f"\n=== COMPREHENSIVE AI ANALYSIS WITH CLAUDE 3.5 SONNET ===")
            try:
                analysis = analyzer.comprehensive_analysis(query, hits)
                print(f"\n🤖 Claude 3.5 Sonnet Comprehensive Analysis:")
                print("=" * 80)
                print(f"{analysis}")
                print("=" * 80)
                
                # Also provide a summary of key findings
                print(f"\n📊 QUICK SUMMARY:")
                print(f"   • Query: '{query}'")
                print(f"   • Documents analyzed: {min(5, len(hits))}")
                print(f"   • Total results found: {len(hits)}")
                print(f"   • Analysis completed successfully")
                
            except Exception as e:
                print(f"Error in AI analysis: {e}")
                print("Continuing with basic search results...")
        
        return hits
        
    except Exception as e:
        print(f"Error searching emails: {e}")
        return []

def create_sample_email():
    """Create a sample email JSON file"""
    sample_email = {
        "sender": "noreply@bank-security.com",
        "sender_name": "Bank Security Team",
        "subject": "URGENT: Verify Your Account Immediately",
        "body": {
            "text": "Dear Customer,\n\nYour account has been suspended due to suspicious activity. Click here to verify your identity immediately: http://bit.ly/verify-now\n\nThis is urgent - act now or your account will be permanently locked.\n\nBest regards,\nBank Security Team"
        },
        "recipient": "user@example.com",
        "timestamp": "2024-01-15T10:30:00Z"
    }
    
    with open('sample_email.json', 'w') as f:
        json.dump(sample_email, f, indent=2)
    
    print("Sample email created: sample_email.json")
    return sample_email

def main():
    parser = argparse.ArgumentParser(
        description="Email Phishing Analysis Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py analyze sample_email.json
  python cli.py search "urgent verify account"
  python cli.py search "phishing" --analyze
  python cli.py create-sample
  python cli.py analyze sample_email.json --index
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze an email for phishing')
    analyze_parser.add_argument('file', help='JSON file containing email data')
    analyze_parser.add_argument('--index', action='store_true', help='Index the email after analysis')
    analyze_parser.add_argument('--similar', action='store_true', help='Search for similar emails')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search emails in database')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--size', type=int, default=10, help='Number of results to return')
    search_parser.add_argument('--analyze', action='store_true', help='Use Claude 4.5 to analyze search results')
    
    # Create sample command
    sample_parser = subparsers.add_parser('create-sample', help='Create a sample email JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = load_config()
    
    if args.command == 'analyze':
        result = analyze_email_file(args.file, config)
        
        if result and args.index:
            print("\n=== INDEXING EMAIL ===")
            analyzer = EmailPhishingAnalyzer(
                config['elastic_url'],
                config['elastic_api_key'],
                config['bedrock_region']
            )
            
            with open(args.file, 'r') as f:
                email_data = json.load(f)
            
            indexed = analyzer.index_email_for_analysis(email_data, result)
            print(f"Email indexed successfully: {indexed}")
        
        if result and args.similar:
            print("\n=== SEARCHING FOR SIMILAR EMAILS ===")
            analyzer = EmailPhishingAnalyzer(
                config['elastic_url'],
                config['elastic_api_key'],
                config['bedrock_region']
            )
            
            with open(args.file, 'r') as f:
                email_data = json.load(f)
            
            similar_emails = analyzer.search_similar_emails(email_data)
            print(f"Found {len(similar_emails)} similar emails")
    
    elif args.command == 'search':
        search_emails(args.query, config, args.size, args.analyze)
    
    elif args.command == 'create-sample':
        create_sample_email()

if __name__ == "__main__":
    main()
