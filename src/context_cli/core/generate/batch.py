"""Batch generation orchestrator — generate llms.txt + schema.jsonld for multiple URLs."""

from __future__ import annotations

import asyncio
import os
import re
from urllib.parse import urlparse

from context_cli.core.models import (
    BatchGenerateConfig,
    BatchGenerateResult,
    BatchPageResult,
    GenerateConfig,
)

from .compiler import generate_assets
from .llm import detect_model


def _sanitize_url_to_dirname(url: str) -> str:
    """Convert a URL into a safe directory name.

    Strips scheme, replaces non-alphanumeric chars (except dots/hyphens) with underscores,
    and collapses consecutive underscores.
    """
    parsed = urlparse(url)
    # Combine host (with port) and path, stripping trailing slashes
    raw = parsed.netloc + parsed.path.rstrip("/")
    # Add query params if present
    if parsed.query:
        raw += "_" + parsed.query
    # Replace non-safe characters with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9.\-]", "_", raw)
    # Collapse consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    # Strip leading/trailing underscores
    return sanitized.strip("_")


async def generate_batch(config: BatchGenerateConfig) -> BatchGenerateResult:
    """Batch generate llms.txt + schema.jsonld for multiple URLs.

    Uses asyncio.Semaphore for concurrency control.
    Each URL's output goes to output_dir/{sanitized_url}/.
    Failures are captured per-URL; one failure does not kill the batch.
    """
    model = config.model or detect_model()
    semaphore = asyncio.Semaphore(config.concurrency)

    async def _process_url(url: str) -> BatchPageResult:
        subdir = _sanitize_url_to_dirname(url)
        url_output_dir = os.path.join(config.output_dir, subdir)
        per_url_config = GenerateConfig(
            url=url,
            profile=config.profile,
            model=model,
            output_dir=url_output_dir,
        )
        async with semaphore:
            try:
                result = await generate_assets(per_url_config)
                return BatchPageResult(
                    url=url,
                    success=True,
                    llms_txt_path=result.llms_txt_path,
                    schema_jsonld_path=result.schema_jsonld_path,
                )
            except Exception as exc:
                return BatchPageResult(
                    url=url,
                    success=False,
                    error=str(exc),
                )

    tasks = [_process_url(url) for url in config.urls]
    results = await asyncio.gather(*tasks)

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    return BatchGenerateResult(
        total=len(config.urls),
        succeeded=succeeded,
        failed=failed,
        results=list(results),
        model_used=model,
        profile=config.profile,
        output_dir=config.output_dir,
    )
