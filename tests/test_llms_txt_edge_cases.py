"""Edge-case tests for llms.txt presence check."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from aeo_cli.core.auditor import check_llms_txt


@pytest.mark.asyncio
async def test_llms_txt_found_at_root():
    """llms.txt at /llms.txt should be detected."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "# LLMs.txt\nThis site is AI-friendly."

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.url == "https://example.com/llms.txt"


@pytest.mark.asyncio
async def test_llms_txt_empty_file():
    """An empty llms.txt (whitespace only) should not count as found."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "   \n  \n  "

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is False


@pytest.mark.asyncio
async def test_llms_txt_not_found():
    """404 on both paths should report not found."""
    mock_response = AsyncMock()
    mock_response.status_code = 404

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is False
    assert report.url is None


@pytest.mark.asyncio
async def test_llms_txt_http_error():
    """Network error should be handled gracefully."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is False


@pytest.mark.asyncio
async def test_llms_txt_well_known_path():
    """llms.txt at /.well-known/llms.txt should be detected when /llms.txt returns 404."""
    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = AsyncMock()
        if "/llms.txt" in url and "well-known" not in url:
            resp.status_code = 404
            resp.text = ""
        else:
            resp.status_code = 200
            resp.text = "# LLMs instructions"
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert "well-known" in report.url
