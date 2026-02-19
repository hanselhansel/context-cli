"""Query dispatcher — sends prompts to LLM models."""

from __future__ import annotations

from typing import Any


async def dispatch_queries(config: Any) -> list[Any]:
    """Dispatch prompts to LLM models.

    Raises NotImplementedError until fully implemented by another agent.
    """
    raise NotImplementedError("Stub — dispatcher not yet implemented")
