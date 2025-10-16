#!/usr/bin/env python3
"""
Quick Start Script for Email Phishing Analysis Agent

This script provides a guided setup and demonstration of the agent.
"""

import os
import sys
import json
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'boto3', 'requests', 'fastapi', 'uvicorn', 
        'pydantic', 'beautifulsoup4', 'python-dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def check_api_keys():
    """Check if API keys are configured"""
    print("\n🔑 Checking API key configuration...")
    
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    optional_vars = ['ELASTIC_URL', 'ELASTIC_API_KEY']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"  ✅ {var}")
        else:
            print(f"  ❌ {var}")
            missing_required.append(var)
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"  ✅ {var}")
        else:
            print(f"  ⚠️  {var} (optional)")
            missing_optional.append(var)
    
    if missing_required:
        print(f"\n❌ Missing required API keys: {', '.join(missing_required)}")
        print("Run: python setup_api_keys.py")
        return False
    
    print("✅ API keys are configured!")
    return True

def run_demo():
    """Run a demonstration of the agent"""
    print("\n🚀 Running Email Phishing Analysis Demo")
    print("=" * 50)
    
    try:
        from email_phishing_analyzer import EmailPhishingAnalyzer
        
        # Initialize analyzer
        elastic_url = os.getenv('ELASTIC_URL', 'https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud')
        elastic_api_key = os.getenv('ELASTIC_API_KEY')
        bedrock_region = os.getenv('BEDROCK_REGION', 'us-east-1')
        
        print("Initializing analyzer...")
        analyzer = EmailPhishingAnalyzer(elastic_url, elastic_api_key, bedrock_region)
        
        # Load test emails
        test_files = ['test_phishing_email.json', 'test_legitimate_email.json']
        
        for test_file in test_files:
            if Path(test_file).exists():
                print(f"\n📧 Analyzing {test_file}...")
                
                with open(test_file, 'r') as f:
                    email_data = json.load(f)
                
                # Analyze email
                result = analyzer.analyze_email(email_data)
                
                print(f"  From: {email_data.get('sender')}")
                print(f"  Subject: {email_data.get('subject')}")
                print(f"  Is Phishing: {result.is_phishing}")
                print(f"  Confidence: {result.confidence_score:.2f}")
                print(f"  Risk Factors: {len(result.risk_factors)} found")
                
                if result.risk_factors:
                    print(f"    - {result.risk_factors[0]}")
                    if len(result.risk_factors) > 1:
                        print(f"    - ... and {len(result.risk_factors) - 1} more")
        
        print("\n✅ Demo completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return False

def show_next_steps():
    """Show next steps for using the agent"""
    print("\n🎯 Next Steps")
    print("=" * 20)
    
    print("\n1. Start the API server:")
    print("   python mcp_server.py")
    print("   # Then visit: http://localhost:8000/docs")
    
    print("\n2. Use the command line interface:")
    print("   python cli.py analyze test_phishing_email.json")
    print("   python cli.py search 'urgent verify'")
    
    print("\n3. Test the API with curl:")
    print("   curl -X POST 'http://localhost:8000/analyze' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d @test_phishing_email.json")
    
    print("\n4. View interactive API documentation:")
    print("   http://localhost:8000/docs")

def main():
    """Main quick start function"""
    print("🚀 Email Phishing Analysis Agent - Quick Start")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install dependencies first:")
        print("   pip install -r requirements.txt")
        return
    
    # Check API keys
    if not check_api_keys():
        print("\n❌ Please configure API keys first:")
        print("   python setup_api_keys.py")
        return
    
    # Run demo
    if not run_demo():
        print("\n❌ Demo failed. Please check your configuration.")
        return
    
    # Show next steps
    show_next_steps()
    
    print("\n🎉 Quick start completed successfully!")
    print("Your Email Phishing Analysis Agent is ready to use!")

if __name__ == "__main__":
    main()
