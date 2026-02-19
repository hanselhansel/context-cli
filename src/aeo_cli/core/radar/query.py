"""Query dispatcher for citation radar."""

from __future__ import annotations

from aeo_cli.core.models import ModelRadarResult, RadarConfig


async def query_models(config: RadarConfig) -> list[ModelRadarResult]:
    """Query configured LLM models with the radar prompt."""
    raise NotImplementedError("Stub — implemented by radar-core agent")
