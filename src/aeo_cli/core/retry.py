"""HTTP retry wrapper with exponential backoff for transient failures."""

from __future__ import annotations

import asyncio
import logging

import httpx

from aeo_cli.core.models import RetryConfig

logger = logging.getLogger(__name__)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    retry_config: RetryConfig | None = None,
    **kwargs,
) -> httpx.Response:
    """Make an HTTP request with retry logic for transient failures.

    Args:
        client: httpx async client to use.
        method: HTTP method (GET, POST, etc.).
        url: Target URL.
        retry_config: Retry settings. Uses defaults if None.
        **kwargs: Passed through to client.request().

    Returns:
        The final httpx.Response.

    Raises:
        httpx.HTTPError: If all retries are exhausted.
    """
    config = retry_config or RetryConfig()
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)

            if response.status_code not in config.retry_on_status:
                return response

            if attempt < config.max_retries:
                delay = min(
                    config.backoff_base * (2 ** attempt),
                    config.backoff_max,
                )
                logger.debug(
                    "Retry %d/%d for %s (HTTP %d), waiting %.1fs",
                    attempt + 1, config.max_retries, url, response.status_code, delay,
                )
                await asyncio.sleep(delay)
            else:
                return response

        except httpx.HTTPError as exc:
            last_exception = exc
            if attempt < config.max_retries:
                delay = min(
                    config.backoff_base * (2 ** attempt),
                    config.backoff_max,
                )
                logger.debug(
                    "Retry %d/%d for %s (%s), waiting %.1fs",
                    attempt + 1, config.max_retries, url, exc, delay,
                )
                await asyncio.sleep(delay)

    if last_exception:
        raise last_exception
    raise httpx.HTTPError(  # pragma: no cover
        f"All {config.max_retries} retries exhausted for {url}"
    )
