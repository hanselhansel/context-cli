"""Tests for HTTP retry wrapper with exponential backoff."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from aeo_cli.core.models import RetryConfig
from aeo_cli.core.retry import request_with_retry


@pytest.mark.asyncio
async def test_no_retry_on_success():
    """A 200 response should return immediately without retries."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_response)

    config = RetryConfig(max_retries=3, backoff_base=0.01)
    result = await request_with_retry(
        mock_client, "GET", "https://example.com", retry_config=config
    )

    assert result.status_code == 200
    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_retry_on_429():
    """A 429 should trigger retries, then succeed on the next attempt."""
    response_429 = AsyncMock(spec=httpx.Response)
    response_429.status_code = 429

    response_200 = AsyncMock(spec=httpx.Response)
    response_200.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=[response_429, response_200])

    config = RetryConfig(max_retries=3, backoff_base=0.01)
    with patch("aeo_cli.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await request_with_retry(
            mock_client, "GET", "https://example.com", retry_config=config
        )

    assert result.status_code == 200
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted_returns_last_response():
    """If all retries are exhausted on retryable status, return the last response."""
    response_503 = AsyncMock(spec=httpx.Response)
    response_503.status_code = 503

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=response_503)

    config = RetryConfig(max_retries=2, backoff_base=0.01)
    with patch("aeo_cli.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await request_with_retry(
            mock_client, "GET", "https://example.com", retry_config=config
        )

    assert result.status_code == 503
    assert mock_client.request.call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_retry_on_network_error():
    """Network errors should trigger retries."""
    response_200 = AsyncMock(spec=httpx.Response)
    response_200.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(
        side_effect=[httpx.ConnectError("Connection refused"), response_200]
    )

    config = RetryConfig(max_retries=3, backoff_base=0.01)
    with patch("aeo_cli.core.retry.asyncio.sleep", new_callable=AsyncMock):
        result = await request_with_retry(
            mock_client, "GET", "https://example.com", retry_config=config
        )

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_no_retry_on_404():
    """A 404 should not trigger retries (not in retry_on_status)."""
    response_404 = AsyncMock(spec=httpx.Response)
    response_404.status_code = 404

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=response_404)

    config = RetryConfig(max_retries=3, backoff_base=0.01)
    result = await request_with_retry(
        mock_client, "GET", "https://example.com", retry_config=config
    )

    assert result.status_code == 404
    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_default_config():
    """Using default config (None) should work without errors."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_response)

    result = await request_with_retry(mock_client, "GET", "https://example.com")

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_retry_exhausted_raises_last_exception():
    """All attempts raise ConnectError, max_retries=1 → re-raises last exception."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    config = RetryConfig(max_retries=1, backoff_base=0.01)
    with patch("aeo_cli.core.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await request_with_retry(
                mock_client, "GET", "https://example.com", retry_config=config
            )
