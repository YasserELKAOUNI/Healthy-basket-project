from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Pagination(BaseModel):
    limit: int
    offset: int
    has_more: Optional[bool] = None
    next_offset: Optional[int] = None


class AnalyzeResponse(BaseModel):
    query: str
    intent: Dict[str, Any]
    mcp_result: Dict[str, Any]
    pagination: Pagination
    schema_version: str
    truncated: Optional[bool] = None
    truncation_message: Optional[str] = None
    llm_analysis: Optional[str] = None


class ToolHints(BaseModel):
    readOnly: bool = Field(default=False)
    destructive: bool = Field(default=False)
    idempotent: bool = Field(default=False)
    openWorld: bool = Field(default=False)


class ToolInfo(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="inputSchema")
    annotations: Optional[Dict[str, Any]] = None
    hints: Optional[ToolHints] = None


class ToolListResponse(BaseModel):
    tools: List[ToolInfo]


class HealthResponse(BaseModel):
    status: str
    config_loaded: bool
    timestamp: str

