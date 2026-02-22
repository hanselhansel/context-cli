"""Tests for MCP endpoint detection check."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from context_cli.core.checks.mcp_endpoint import check_mcp_endpoint


def _make_response(status_code: int = 200, json_data: object = None, json_error: bool = False):
    """Create a MagicMock httpx.Response (sync methods like .json())."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_error:
        resp.json.side_effect = json.JSONDecodeError("err", "", 0)
    elif json_data is not None:
        resp.json.return_value = json_data
    return resp


@pytest.mark.asyncio
async def test_mcp_endpoint_found_with_tools():
    """MCP endpoint returns valid JSON with tools array."""
    payload = {"tools": [{"name": "search"}, {"name": "fetch"}]}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_make_response(json_data=payload))

    report = await check_mcp_endpoint("https://example.com/page", mock_client)

    assert report.found is True
    assert report.url == "https://example.com/.well-known/mcp.json"
    assert report.tools_count == 2
    assert report.score == 4.0
    assert "2 tool(s)" in report.detail


@pytest.mark.asyncio
async def test_mcp_endpoint_found_empty_tools():
    """MCP endpoint returns valid JSON with empty tools array."""
    payload = {"tools": []}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_make_response(json_data=payload))

    report = await check_mcp_endpoint("https://example.com", mock_client)

    assert report.found is True
    assert report.tools_count == 0
    assert report.score == 4.0
    assert "0 tool(s)" in report.detail


@pytest.mark.asyncio
async def test_mcp_endpoint_found_no_tools_key():
    """MCP endpoint returns valid JSON but without a 'tools' key."""
    payload = {"name": "My MCP", "version": "1.0"}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_make_response(json_data=payload))

    report = await check_mcp_endpoint("https://example.com", mock_client)

    assert report.found is True
    assert report.tools_count is None
    assert report.score == 4.0
    assert report.detail == "MCP endpoint found"


@pytest.mark.asyncio
async def test_mcp_endpoint_invalid_json():
    """MCP endpoint returns 200 but body is not valid JSON."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_make_response(json_error=True))

    report = await check_mcp_endpoint("https://example.com", mock_client)

    assert report.found is True
    assert report.score == 1.0
    assert "invalid JSON" in report.detail


@pytest.mark.asyncio
async def test_mcp_endpoint_not_found_404():
    """MCP endpoint returns HTTP 404."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=_make_response(status_code=404))

    report = await check_mcp_endpoint("https://example.com", mock_client)

    assert report.found is False
    assert report.score == 0
    assert "404" in report.detail


@pytest.mark.asyncio
async def test_mcp_endpoint_network_error():
    """Network error when probing MCP endpoint."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    report = await check_mcp_endpoint("https://example.com", mock_client)

    assert report.found is False
    assert report.score == 0
    assert "Failed to probe" in report.detail
