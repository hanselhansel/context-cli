"""Brand analyzer for citation radar."""

from __future__ import annotations

from aeo_cli.core.models import ModelRadarResult, RadarConfig, RadarReport


def build_radar_report(
    config: RadarConfig, results: list[ModelRadarResult]
) -> RadarReport:
    """Build an aggregated radar report from per-model results."""
    raise NotImplementedError("Stub — implemented by radar-analyzer agent")
