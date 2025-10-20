from __future__ import annotations

from typing import Protocol, Dict, Any, List


class LLMClient(Protocol):
    """Abstract interface for LLM invocations."""

    def invoke(
        self,
        *,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        retries: int = 3,
        base_delay_s: int = 2,
    ) -> Dict[str, Any]:
        ...

    def invoke_text(
        self,
        *,
        model_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 2000,
        retries: int = 3,
        base_delay_s: int = 2,
    ) -> str:
        ...

