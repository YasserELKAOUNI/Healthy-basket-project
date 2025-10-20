"""Centralized configuration for MCP and LLM usage.

This module consolidates environment-driven settings such as MCP endpoint,
API keys, index names, Bedrock model IDs, timeouts, and character limits.

Other modules should import Settings via `get_settings()` and avoid
reading environment variables directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load env once at import (idempotent if already loaded elsewhere)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # MCP / Elastic
    elastic_url: str
    elastic_api_key: str

    # Default indices (domain-specific)
    products_index: str = "products"

    # Bedrock / LLM
    bedrock_region: str = "us-east-1"
    # Default preferred and fallback model ids (can be overridden by env)
    claude_primary_model_id: str = os.getenv(
        "CLAUDE_PRIMARY_MODEL_ID",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    )
    claude_fallback_model_id: str = os.getenv(
        "CLAUDE_FALLBACK_MODEL_ID",
        "anthropic.claude-3-5-sonnet-20240620-v1:0",
    )

    # Networking
    http_timeout_seconds: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))

    # Output / Limits
    character_limit: int = int(os.getenv("CHARACTER_LIMIT", "25000"))


_cached_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return cached settings (loaded from environment) to be used across modules."""
    global _cached_settings
    if _cached_settings is not None:
        return _cached_settings

    elastic_url = os.getenv("ELASTIC_URL", "")
    elastic_api_key = os.getenv("ELASTIC_API_KEY", "")
    bedrock_region = os.getenv("BEDROCK_REGION", "us-east-1")

    # Allow index override
    products_index = os.getenv("PRODUCTS_INDEX", "products")

    _cached_settings = Settings(
        elastic_url=elastic_url,
        elastic_api_key=elastic_api_key,
        bedrock_region=bedrock_region,
        products_index=products_index,
    )
    return _cached_settings

