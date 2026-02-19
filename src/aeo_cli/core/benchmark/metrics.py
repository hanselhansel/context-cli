"""Metrics — computes benchmark report from judged results."""

from __future__ import annotations

from typing import Any

from aeo_cli.core.models import BenchmarkReport


def compute_report(config: Any, results: Any) -> BenchmarkReport:
    """Compute a benchmark report from config and judged results.

    Raises NotImplementedError until fully implemented by another agent.
    """
    raise NotImplementedError("Stub — metrics not yet implemented")
