"""Tests for Accept: text/markdown probe check."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from context_cli.core.checks.markdown_accept import check_markdown_accept


@pytest.mark.asyncio
async def test_supports_text_markdown():
    """Server responds with Content-Type: text/markdown."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/markdown; charset=utf-8"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_markdown_accept("https://example.com", mock_client)

    assert report.supported is True
    assert report.content_type == "text/markdown; charset=utf-8"
    assert report.score == 5.0


@pytest.mark.asyncio
async def test_supports_text_x_markdown():
    """Server responds with Content-Type: text/x-markdown."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/x-markdown"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_markdown_accept("https://example.com", mock_client)

    assert report.supported is True
    assert report.content_type == "text/x-markdown"
    assert report.score == 5.0


@pytest.mark.asyncio
async def test_no_markdown_support():
    """Server responds with text/html (no markdown support)."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_markdown_accept("https://example.com", mock_client)

    assert report.supported is False
    assert report.score == 0
    assert "does not support" in report.detail.lower()


@pytest.mark.asyncio
async def test_network_error():
    """httpx.ConnectError returns safe default."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    report = await check_markdown_accept("https://example.com", mock_client)

    assert report.supported is False
    assert report.score == 0
    assert "failed" in report.detail.lower()


@pytest.mark.asyncio
async def test_redirect_followed():
    """Client follows redirects and checks final Content-Type."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/markdown"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_markdown_accept("https://example.com/old-page", mock_client)

    assert report.supported is True
    # Verify follow_redirects=True was passed
    call_kwargs = mock_client.get.call_args
    assert call_kwargs.kwargs.get("follow_redirects") is True
