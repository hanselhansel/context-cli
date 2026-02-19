"""Judge — evaluates LLM responses for brand mentions and recommendations."""

from __future__ import annotations

from typing import Any

from aeo_cli.core.models import JudgeResult


async def judge_all(
    results: list[Any], brand: str, competitors: list[str]
) -> list[JudgeResult]:
    """Judge all LLM responses for brand mentions and recommendations.

    Raises NotImplementedError until fully implemented by another agent.
    """
    raise NotImplementedError("Stub — judge not yet implemented")
