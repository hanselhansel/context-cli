"""Tests for IETF Content-Usage HTTP header detection."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from aeo_cli.core.checks.content_usage import check_content_usage
from aeo_cli.core.models import ContentUsageReport


def _mock_client(
    headers: dict[str, str] | None = None,
    status_code: int = 200,
    error: Exception | None = None,
) -> AsyncMock:
    """Create a mock httpx.AsyncClient with configurable HEAD response."""
    mock = AsyncMock(spec=httpx.AsyncClient)
    if error:
        mock.head = AsyncMock(side_effect=error)
    else:
        resp = AsyncMock()
        resp.status_code = status_code
        resp.headers = httpx.Headers(headers or {})
        mock.head = AsyncMock(return_value=resp)
    return mock


class TestCheckContentUsage:
    """Tests for check_content_usage() function."""

    @pytest.mark.asyncio
    async def test_no_header(self) -> None:
        report = await check_content_usage("https://example.com", _mock_client())
        assert isinstance(report, ContentUsageReport)
        assert not report.header_found
        assert report.header_value is None
        assert report.allows_training is None
        assert report.allows_search is None

    @pytest.mark.asyncio
    async def test_header_allows_all(self) -> None:
        client = _mock_client({"Content-Usage": "training=yes, search=yes"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.header_value == "training=yes, search=yes"
        assert report.allows_training is True
        assert report.allows_search is True

    @pytest.mark.asyncio
    async def test_header_blocks_training(self) -> None:
        client = _mock_client({"Content-Usage": "training=no, search=yes"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.allows_training is False
        assert report.allows_search is True

    @pytest.mark.asyncio
    async def test_header_blocks_search(self) -> None:
        client = _mock_client({"Content-Usage": "training=yes, search=no"})
        report = await check_content_usage("https://example.com", client)
        assert report.allows_training is True
        assert report.allows_search is False

    @pytest.mark.asyncio
    async def test_header_blocks_all(self) -> None:
        client = _mock_client({"Content-Usage": "training=no, search=no"})
        report = await check_content_usage("https://example.com", client)
        assert report.allows_training is False
        assert report.allows_search is False

    @pytest.mark.asyncio
    async def test_partial_training_only(self) -> None:
        client = _mock_client({"Content-Usage": "training=no"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.allows_training is False
        assert report.allows_search is None

    @pytest.mark.asyncio
    async def test_partial_search_only(self) -> None:
        client = _mock_client({"Content-Usage": "search=yes"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.allows_training is None
        assert report.allows_search is True

    @pytest.mark.asyncio
    async def test_http_error(self) -> None:
        client = _mock_client(error=httpx.ConnectError("Connection refused"))
        report = await check_content_usage("https://example.com", client)
        assert not report.header_found
        assert "error" in report.detail.lower() or "failed" in report.detail.lower()

    @pytest.mark.asyncio
    async def test_non_200_status(self) -> None:
        client = _mock_client(status_code=404)
        report = await check_content_usage("https://example.com", client)
        assert not report.header_found

    @pytest.mark.asyncio
    async def test_url_passthrough(self) -> None:
        client = _mock_client({"Content-Usage": "training=yes"})
        await check_content_usage("https://example.com/page", client)
        client.head.assert_called_once_with("https://example.com/page", follow_redirects=True)

    @pytest.mark.asyncio
    async def test_detail_with_header(self) -> None:
        client = _mock_client({"Content-Usage": "training=yes, search=no"})
        report = await check_content_usage("https://example.com", client)
        assert "Content-Usage" in report.detail

    @pytest.mark.asyncio
    async def test_detail_without_header(self) -> None:
        report = await check_content_usage("https://example.com", _mock_client())
        assert "not found" in report.detail.lower() or "not present" in report.detail.lower()

    @pytest.mark.asyncio
    async def test_empty_header_value(self) -> None:
        client = _mock_client({"Content-Usage": ""})
        report = await check_content_usage("https://example.com", client)
        assert not report.header_found

    @pytest.mark.asyncio
    async def test_case_insensitive_values(self) -> None:
        client = _mock_client({"Content-Usage": "Training=YES, Search=NO"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.allows_training is True
        assert report.allows_search is False

    @pytest.mark.asyncio
    async def test_unknown_bool_value(self) -> None:
        """Unknown values (not yes/no) should result in None."""
        client = _mock_client({"Content-Usage": "training=maybe, search=restricted"})
        report = await check_content_usage("https://example.com", client)
        assert report.header_found
        assert report.allows_training is None
        assert report.allows_search is None
