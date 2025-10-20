#!/usr/bin/env python3
"""
Web UI for Smart MCP-based Email Phishing Analysis
"""

from fastapi import FastAPI, Request, Form, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

# Import our smart grocery MCP CLI functions
from src.groceries.service import execute as groceries_execute
from src.groceries.formatting import (
    format_search_results,
    format_product_result,
)
from src.core.mcp_client import MCPClient
from src.core.config import get_settings
from src.api.models import AnalyzeResponse, ToolListResponse, HealthResponse, ToolHints, ToolInfo

app = FastAPI(title="Smart MCP Groceries Health Basket Analysis UI", version="1.0.0")
router_v1 = APIRouter(prefix="/api/v1")

# Templates directory
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/analyze")
async def analyze_query(
    query: str = Form(...),
    use_llm: bool = Form(True)
):
    """Analyze query using smart MCP CLI"""
    
    try:
        # Execute the smart query (includes intent analysis and MCP tool execution)
        smart_result = groceries_execute(query, use_llm=use_llm)
        
        # Prepare response
        response_data = {
            "query": query,
            "intent": smart_result['intent'],
            "mcp_result": smart_result['mcp_result'],
            "timestamp": datetime.now().isoformat()
        }
        
        if not use_llm:
            # Format raw results
            if smart_result['intent']['action'] in ['search_products', 'nutrition_search', 'promotions_search', 'analyze_basket']:
                response_data["formatted_results"] = format_search_results(smart_result['mcp_result'])
            elif smart_result['intent']['action'] == 'get_product':
                response_data["formatted_results"] = format_product_result(smart_result['mcp_result'])
            else:
                response_data["formatted_results"] = json.dumps(smart_result['mcp_result'], indent=2)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/tools")
async def get_available_tools():
    """Get available MCP tools"""
    try:
        client = MCPClient()
        client.initialize(client_name="healthy-basket-ui", client_version="1.0.0")
        tools = client.list_tools()
        enriched: List[Dict[str, Any]] = []
        for t in tools:
            ann = t.get("annotations") or {}
            hints = {
                "readOnly": bool(ann.get("readOnlyHint", False)),
                "destructive": bool(ann.get("destructiveHint", False)),
                "idempotent": bool(ann.get("idempotentHint", False)),
                "openWorld": bool(ann.get("openWorldHint", False)),
            }
            item = dict(t)
            item["hints"] = hints
            enriched.append(item)
        return JSONResponse(content={"tools": enriched})
            
    except Exception as e:
        return JSONResponse(content={"tools": [], "error": str(e)})

@app.get("/api/status")
async def get_status():
    """Get system status"""
    s = get_settings()
    return JSONResponse(content={
        "status": "online",
        "config_loaded": bool(s.elastic_url and s.elastic_api_key),
        "timestamp": datetime.now().isoformat()
    })


# v1 API: typed routes
@router_v1.post("/analyze", response_model=AnalyzeResponse)
async def analyze_v1(query: str, use_llm: bool = True):
    result = groceries_execute(query, use_llm=use_llm)
    return AnalyzeResponse(**result)


@router_v1.get("/tools", response_model=ToolListResponse)
async def tools_v1():
    client = MCPClient()
    client.initialize(client_name="healthy-basket-ui", client_version="1.0.0")
    tools = client.list_tools()
    enriched = []
    for t in tools:
        ann = t.get("annotations") or {}
        hints = ToolHints(
            readOnly=bool(ann.get("readOnlyHint", False)),
            destructive=bool(ann.get("destructiveHint", False)),
            idempotent=bool(ann.get("idempotentHint", False)),
            openWorld=bool(ann.get("openWorldHint", False)),
        )
        item = ToolInfo(
            name=t.get("name"),
            description=t.get("description"),
            input_schema=t.get("input_schema") or t.get("inputSchema"),
            annotations=ann,
            hints=hints,
        )
        enriched.append(item)
    return ToolListResponse(tools=enriched)


@router_v1.get("/health", response_model=HealthResponse)
async def health_v1():
    s = get_settings()
    return HealthResponse(status="online", config_loaded=bool(s.elastic_url and s.elastic_api_key), timestamp=datetime.now().isoformat())


app.include_router(router_v1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
