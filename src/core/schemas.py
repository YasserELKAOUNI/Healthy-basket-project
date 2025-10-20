from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Reference(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(default=None, description="Document identifier")
    index: Optional[str] = Field(default=None, description="Index name")


class HitContent(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Content is dynamic; accept any fields and pass through


class HitData(BaseModel):
    model_config = ConfigDict(extra="allow")

    reference: Optional[Reference] = None
    content: Optional[Dict[str, Any]] = None


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: Optional[HitData] = None


class SearchPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    results: List[SearchHit] = Field(default_factory=list)


def try_validate_search_payload(payload: Dict[str, Any]) -> Optional[SearchPayload]:
    """Validate a parsed MCP payload for search results.

    Returns a SearchPayload or None if validation fails.
    """
    try:
        return SearchPayload.model_validate(payload)
    except Exception:
        return None

