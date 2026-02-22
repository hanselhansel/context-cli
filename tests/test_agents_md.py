"""Tests for AGENTS.md detection check."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from context_cli.core.checks.agents_md import check_agents_md


@pytest.mark.asyncio
async def test_found_at_agents_md():
    """AGENTS.md found at /agents.md (first probe path)."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/markdown; charset=utf-8"}
    mock_response.text = "# AGENTS\n"

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_agents_md("https://example.com/page", mock_client)

    assert report.found is True
    assert report.url == "https://example.com/agents.md"
    assert report.score == 5.0
    assert "found" in report.detail.lower()


@pytest.mark.asyncio
async def test_found_at_well_known():
    """AGENTS.md found at /.well-known/agents.md after earlier paths return 404."""
    call_count = 0

    async def side_effect(url: str, **kwargs: object) -> AsyncMock:
        nonlocal call_count
        call_count += 1
        resp = AsyncMock()
        if "/.well-known/agents.md" in url:
            resp.status_code = 200
            resp.headers = {"content-type": "text/plain"}
            resp.text = "# AGENTS\n"
        else:
            resp.status_code = 404
            resp.headers = {}
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=side_effect)

    report = await check_agents_md("https://example.com", mock_client)

    assert report.found is True
    assert report.url == "https://example.com/.well-known/agents.md"
    assert report.score == 5.0


@pytest.mark.asyncio
async def test_not_found_all_404():
    """All probe paths return 404."""
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.headers = {}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_agents_md("https://example.com", mock_client)

    assert report.found is False
    assert report.score == 0
    assert "no agents.md found" in report.detail.lower()


@pytest.mark.asyncio
async def test_network_error():
    """httpx.ConnectError on all probes returns safe default."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    report = await check_agents_md("https://example.com", mock_client)

    assert report.found is False
    assert report.score == 0


@pytest.mark.asyncio
async def test_non_text_response_skipped():
    """A 200 response with non-text content-type is skipped."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/octet-stream"}

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_agents_md("https://example.com", mock_client)

    assert report.found is False
    assert report.score == 0
