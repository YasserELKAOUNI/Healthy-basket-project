from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
from email_phishing_analyzer import EmailPhishingAnalyzer, PhishingAnalysisResult
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Email Phishing Analysis Agent",
    description="AI-powered email phishing detection using Bedrock Claude 4.5 and Elastic MCP Server",
    version="1.0.0"
)

# Initialize the analyzer with validation
ELASTIC_URL = os.getenv('ELASTIC_URL', 'https://searchsearch-a9ed61.kb.europe-west1.gcp.elastic.cloud')
ELASTIC_API_KEY = os.getenv('ELASTIC_API_KEY')
BEDROCK_REGION = os.getenv('BEDROCK_REGION', 'us-east-1')

# Validate required environment variables
missing_vars = []
if not os.getenv('AWS_ACCESS_KEY_ID'):
    missing_vars.append('AWS_ACCESS_KEY_ID')
if not os.getenv('AWS_SECRET_ACCESS_KEY'):
    missing_vars.append('AWS_SECRET_ACCESS_KEY')

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.error("Run 'python setup_api_keys.py' to configure API keys")
    analyzer = None
else:
    try:
        analyzer = EmailPhishingAnalyzer(ELASTIC_URL, ELASTIC_API_KEY, BEDROCK_REGION)
        logger.info("Email Phishing Analyzer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize analyzer: {e}")
        analyzer = None

# Pydantic models for API
class EmailData(BaseModel):
    sender: str
    sender_name: Optional[str] = None
    subject: str
    body: Dict[str, Any]
    recipient: str
    timestamp: Optional[str] = None
    attachments: Optional[List[str]] = None

class AnalysisRequest(BaseModel):
    email: EmailData
    include_similar_search: bool = True
    auto_index: bool = True

class AnalysisResponse(BaseModel):
    analysis_result: Dict[str, Any]
    similar_emails: Optional[List[Dict[str, Any]]] = None
    indexed: bool = False
    analysis_timestamp: str

class SearchRequest(BaseModel):
    query: str
    size: int = 10
    index: str = "emails"

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_hits: int
    query: str

class HealthResponse(BaseModel):
    status: str
    elastic_connected: bool
    bedrock_configured: bool
    timestamp: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test Elastic connection
        elastic_connected = True
        try:
            analyzer.elastic_client.search("test", size=1)
        except:
            elastic_connected = False
        
        # Test Bedrock configuration
        bedrock_configured = True
        try:
            # Check if AWS credentials are configured
            import boto3
            boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
        except:
            bedrock_configured = False
        
        return HealthResponse(
            status="healthy" if elastic_connected and bedrock_configured else "degraded",
            elastic_connected=elastic_connected,
            bedrock_configured=bedrock_configured,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_email(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze an email for phishing indicators"""
    if analyzer is None:
        raise HTTPException(
            status_code=503, 
            detail="Analyzer not initialized. Please check API key configuration."
        )
    
    try:
        # Convert Pydantic model to dict
        email_data = request.email.dict()
        
        # Perform analysis
        logger.info(f"Analyzing email from {email_data.get('sender')}")
        analysis_result = analyzer.analyze_email(email_data)
        
        # Convert result to dict for JSON serialization
        result_dict = {
            "is_phishing": analysis_result.is_phishing,
            "confidence_score": analysis_result.confidence_score,
            "risk_factors": analysis_result.risk_factors,
            "suspicious_urls": analysis_result.suspicious_urls,
            "suspicious_domains": analysis_result.suspicious_domains,
            "suspicious_keywords": analysis_result.suspicious_keywords,
            "sender_analysis": analysis_result.sender_analysis,
            "content_analysis": analysis_result.content_analysis,
            "recommendations": analysis_result.recommendations
        }
        
        # Search for similar emails if requested
        similar_emails = None
        if request.include_similar_search:
            similar_emails = analyzer.search_similar_emails(email_data)
        
        # Index email if requested
        indexed = False
        if request.auto_index:
            indexed = analyzer.index_email_for_analysis(email_data, analysis_result)
        
        return AnalysisResponse(
            analysis_result=result_dict,
            similar_emails=similar_emails,
            indexed=indexed,
            analysis_timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Email analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/search", response_model=SearchResponse)
async def search_emails(request: SearchRequest):
    """Search emails in the database"""
    if analyzer is None:
        raise HTTPException(
            status_code=503, 
            detail="Analyzer not initialized. Please check API key configuration."
        )
    
    try:
        results = analyzer.elastic_client.search_emails(request.query, request.size)
        
        hits = results.get('hits', {}).get('hits', [])
        total_hits = results.get('hits', {}).get('total', {}).get('value', 0)
        
        return SearchResponse(
            results=hits,
            total_hits=total_hits,
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Email search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/index")
async def index_email(email_data: EmailData):
    """Index an email in the database"""
    try:
        # Convert to dict and add timestamp if not provided
        data = email_data.dict()
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now().isoformat()
        
        success = analyzer.elastic_client.index_email(data)
        
        if success:
            return {"message": "Email indexed successfully", "timestamp": data['timestamp']}
        else:
            raise HTTPException(status_code=500, detail="Failed to index email")
            
    except Exception as e:
        logger.error(f"Email indexing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get analysis statistics"""
    try:
        # This would typically query Elasticsearch for statistics
        # For now, return basic info
        return {
            "message": "Statistics endpoint - implement based on your Elasticsearch queries",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Email Phishing Analysis Agent API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze",
            "search": "/search",
            "index": "/index",
            "stats": "/stats",
            "docs": "/docs"
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "mcp_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
