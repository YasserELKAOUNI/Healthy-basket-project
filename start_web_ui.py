#!/usr/bin/env python3
"""
Startup script for Smart MCP Email Phishing Analysis Web UI
"""

import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import jinja2
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def check_config():
    """Check if configuration is set up"""
    from dotenv import load_dotenv
    load_dotenv()
    
    elastic_url = os.getenv('ELASTIC_URL')
    elastic_api_key = os.getenv('ELASTIC_API_KEY')
    
    if not elastic_url or not elastic_api_key:
        print("❌ Missing configuration")
        print("Please set ELASTIC_URL and ELASTIC_API_KEY in your .env file")
        return False
    
    print("✅ Configuration is set up")
    return True

def start_server():
    """Start the web server"""
    print("🚀 Starting Smart MCP Groceries Health Basket Analysis Web UI...")
    print("📱 Open your browser and go to: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        subprocess.run([sys.executable, "web_ui.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    print("🛒 Smart MCP Groceries Health Basket Analysis Web UI")
    print("=" * 60)
    
    if not check_requirements():
        return
    
    if not check_config():
        return
    
    start_server()

if __name__ == "__main__":
    main()
