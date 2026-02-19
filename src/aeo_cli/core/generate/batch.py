"""Batch generation orchestrator for multiple URLs."""

from __future__ import annotations

from aeo_cli.core.models import BatchGenerateConfig, BatchGenerateResult


async def generate_batch(config: BatchGenerateConfig) -> BatchGenerateResult:
    """Batch generate llms.txt + schema.jsonld for multiple URLs."""
    raise NotImplementedError("Stub — real implementation in batch-core agent")
