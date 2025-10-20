#!/usr/bin/env python3
"""
Configuration Validator for Email Phishing Analysis Agent

This script validates your API key configuration without requiring interactive input.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    """Load configuration from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv()
        print("✅ Loaded configuration from .env file")
    else:
        print("⚠️  No .env file found, using environment variables")
    
    # Prefer centralized settings where possible
    try:
        from src.core.config import get_settings
        s = get_settings()
        elastic_url = s.elastic_url or os.getenv('ELASTIC_URL', '')
        elastic_api_key = s.elastic_api_key or os.getenv('ELASTIC_API_KEY')
        aws_region = s.bedrock_region or os.getenv('BEDROCK_REGION', 'us-east-1')
    except Exception:
        elastic_url = os.getenv('ELASTIC_URL', '')
        elastic_api_key = os.getenv('ELASTIC_API_KEY')
        aws_region = os.getenv('BEDROCK_REGION', 'us-east-1')

    return {
        'aws_access_key': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'aws_region': aws_region,
        'elastic_url': elastic_url,
        'elastic_api_key': elastic_api_key
    }

def validate_aws_config(config):
    """Validate AWS configuration"""
    print("\n🔍 Validating AWS Configuration...")
    
    if not config['aws_access_key']:
        print("❌ AWS_ACCESS_KEY_ID not set")
        return False
    
    if not config['aws_secret_key']:
        print("❌ AWS_SECRET_ACCESS_KEY not set")
        return False
    
    print(f"✅ AWS Access Key ID: {config['aws_access_key'][:8]}...")
    print(f"✅ AWS Secret Key: {'*' * 8}...")
    print(f"✅ AWS Region: {config['aws_region']}")
    
    # Test AWS Bedrock access
    try:
        import boto3
        bedrock = boto3.client(
            'bedrock',
            region_name=config['aws_region'],
            aws_access_key_id=config['aws_access_key'],
            aws_secret_access_key=config['aws_secret_key']
        )
        
        # Try to list models
        response = bedrock.list_foundation_models()
        model_count = len(response.get('modelSummaries', []))
        print(f"✅ AWS Bedrock access verified ({model_count} models available)")
        return True
        
    except Exception as e:
        print(f"❌ AWS Bedrock access failed: {e}")
        return False

def validate_elastic_config(config):
    """Validate Elastic configuration"""
    print("\n🔍 Validating Elastic Configuration...")
    
    print(f"✅ Elastic URL: {config['elastic_url']}")
    
    if config['elastic_api_key']:
        print(f"✅ Elastic API Key: {config['elastic_api_key'][:8]}...")
    else:
        print("⚠️  Elastic API Key not set (optional)")
    
    # Test Elastic connection
    try:
        # Use MCPClient to verify tools list as a connectivity check
        from src.core.mcp_client import MCPClient
        client = MCPClient(elastic_url=config['elastic_url'], api_key=config['elastic_api_key'])
        tools = client.list_tools()
        print("✅ Elastic MCP Server connection verified")
        print(f"   Tools available: {len(tools)}")
        return True
    except Exception as e:
        print(f"❌ Elastic MCP Server connection failed: {e}")
        return False

def test_agent_initialization(config):
    """Test agent initialization"""
    print("\n🔍 Testing Agent Initialization...")
    
    try:
        from email_phishing_analyzer import EmailPhishingAnalyzer
        
        analyzer = EmailPhishingAnalyzer(
            elastic_url=config['elastic_url'],
            elastic_api_key=config['elastic_api_key'],
            bedrock_region=config['aws_region']
        )
        
        print("✅ Email Phishing Analyzer initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🔧 Email Phishing Analysis Agent - Configuration Validator")
    print("=" * 70)
    
    # Load configuration
    config = load_config()
    
    # Validate AWS
    aws_valid = validate_aws_config(config)
    
    # Validate Elastic
    elastic_valid = validate_elastic_config(config)
    
    # Test agent initialization
    agent_valid = test_agent_initialization(config)
    
    # Summary
    print("\n📊 Validation Summary")
    print("=" * 30)
    print(f"AWS Configuration: {'✅ Valid' if aws_valid else '❌ Invalid'}")
    print(f"Elastic Configuration: {'✅ Valid' if elastic_valid else '❌ Invalid'}")
    print(f"Agent Initialization: {'✅ Valid' if agent_valid else '❌ Invalid'}")
    
    if aws_valid and elastic_valid and agent_valid:
        print("\n🎉 All validations passed! Your agent is ready to use.")
        print("\nNext steps:")
        print("1. Run: python quick_start.py")
        print("2. Start API: python mcp_server.py")
        print("3. Test CLI: python cli.py --help")
        return True
    else:
        print("\n❌ Some validations failed. Please check the errors above.")
        print("\nSetup guide: cat setup_guide.md")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
