"""Bedrock (Claude) LLM client wrapper with retry/backoff.

Encapsulates common invocation patterns for Claude models via
AWS Bedrock runtime. Provides a simple `invoke_text` helper
that returns the first text block for convenience.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover - optional import in some environments
    boto3 = None  # type: ignore

from .config import get_settings
from src.adapters.llm_client import LLMClient as LLMClientProtocol


class LLMInvokeError(RuntimeError):
    pass


class BedrockLLMClient(LLMClientProtocol):
    def __init__(self, *, region_name: Optional[str] = None):
        cfg = get_settings()
        region = region_name or cfg.bedrock_region
        if boto3 is None:
            raise LLMInvokeError("boto3 is not available to create Bedrock client")
        self._client = boto3.client('bedrock-runtime', region_name=region)

    def invoke(
        self,
        *,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        retries: int = 3,
        base_delay_s: int = 2,
    ) -> Dict[str, Any]:
        """Invoke a Claude model; retry on throttling with exponential backoff."""
        last_error: Optional[Exception] = None
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }

        for attempt in range(retries):
            try:
                resp = self._client.invoke_model(modelId=model_id, body=json.dumps(payload))
                return json.loads(resp['body'].read())
            except Exception as e:  # noqa: PERF203
                last_error = e
                if "ThrottlingException" in str(e) and attempt < retries - 1:
                    delay = base_delay_s * (2 ** attempt)
                    time.sleep(delay)
                    continue
                break
        raise LLMInvokeError(f"Bedrock invocation failed: {last_error}")

    def invoke_text(
        self,
        *,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 2000,
        retries: int = 3,
        base_delay_s: int = 2,
    ) -> str:
        data = self.invoke(
            model_id=model_id,
            messages=messages,
            max_tokens=max_tokens,
            retries=retries,
            base_delay_s=base_delay_s,
        )
        try:
            return data['content'][0]['text']
        except Exception as e:  # noqa: PERF203
            raise LLMInvokeError(f"Unexpected Bedrock response format: {e}") from e
