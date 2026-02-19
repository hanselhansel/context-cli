"""Edge-case tests for llms.txt presence check."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from context_cli.core.checks.llms_txt import check_llms_txt


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


# ── llms-full.txt Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llms_full_txt_found_at_root():
    """llms-full.txt at /llms-full.txt should be detected."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        if "llms-full.txt" in url and "well-known" not in url:
            resp.status_code = 200
            resp.text = "# Full LLMs content"
        elif "/llms.txt" in url and "full" not in url:
            resp.status_code = 200
            resp.text = "# LLMs.txt"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is True
    assert report.llms_full_url == "https://example.com/llms-full.txt"


@pytest.mark.asyncio
async def test_llms_full_txt_found_at_well_known():
    """llms-full.txt at /.well-known/llms-full.txt should be detected."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        if "well-known/llms-full.txt" in url:
            resp.status_code = 200
            resp.text = "# Full LLMs content"
        elif "/llms.txt" in url and "full" not in url:
            resp.status_code = 200
            resp.text = "# LLMs.txt"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is True
    assert report.llms_full_url == "https://example.com/.well-known/llms-full.txt"


@pytest.mark.asyncio
async def test_only_llms_full_txt_found():
    """Only llms-full.txt present (no llms.txt) should still score."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        if "llms-full.txt" in url and "well-known" not in url:
            resp.status_code = 200
            resp.text = "# Full LLMs content"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is False  # llms.txt not found
    assert report.llms_full_found is True
    assert report.llms_full_url == "https://example.com/llms-full.txt"
    assert "llms-full.txt" in report.detail


@pytest.mark.asyncio
async def test_both_llms_and_llms_full_found():
    """Both llms.txt and llms-full.txt present should be reported."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        resp.status_code = 200
        resp.text = "# Content"
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is True
    assert "llms.txt" in report.detail
    assert "llms-full.txt" in report.detail


@pytest.mark.asyncio
async def test_llms_full_txt_not_found():
    """When only llms.txt exists, llms_full_found should be False."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        if "/llms.txt" in url and "full" not in url and "well-known" not in url:
            resp.status_code = 200
            resp.text = "# LLMs.txt"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is False
    assert report.llms_full_url is None


@pytest.mark.asyncio
async def test_llms_full_txt_empty_not_counted():
    """An empty llms-full.txt should not count as found."""
    async def mock_get(url, **kwargs):
        resp = AsyncMock()
        if "llms-full.txt" in url:
            resp.status_code = 200
            resp.text = "   \n  "
        elif "/llms.txt" in url:
            resp.status_code = 200
            resp.text = "# LLMs.txt"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is False


@pytest.mark.asyncio
async def test_llms_full_txt_http_error():
    """HTTP error on llms-full.txt should not crash; llms.txt still found."""
    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "llms-full.txt" in url:
            raise httpx.ConnectError("Connection refused")
        resp = AsyncMock()
        if "/llms.txt" in url and "full" not in url and "well-known" not in url:
            resp.status_code = 200
            resp.text = "# LLMs.txt"
        else:
            resp.status_code = 404
            resp.text = ""
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_get)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is True
    assert report.llms_full_found is False


@pytest.mark.asyncio
async def test_neither_llms_found():
    """Neither llms.txt nor llms-full.txt found should report not found."""
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.text = ""

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report = await check_llms_txt("https://example.com", mock_client)

    assert report.found is False
    assert report.llms_full_found is False
    assert report.url is None
    assert report.llms_full_url is None
