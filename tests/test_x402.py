"""Tests for x402 payment signaling check."""

from __future__ import annotations

import httpx
import pytest

from context_cli.core.checks.x402 import check_x402


def _make_client(handler):
    """Create an httpx.AsyncClient with a mock transport."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_x402_full_score():
    """Test 402 status + payment headers → score=2."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, headers={"X-Payment": "required"})

    async with _make_client(handler) as client:
        report = await check_x402("https://example.com/api", client)

    assert report.found is True
    assert report.has_402_status is True
    assert report.has_payment_header is True
    assert report.score == 2
    assert "HTTP 402 status" in report.detail
    assert "x-payment" in report.detail


@pytest.mark.asyncio
async def test_x402_status_only():
    """Test 402 status code only → score=1."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402)

    async with _make_client(handler) as client:
        report = await check_x402("https://example.com/api", client)

    assert report.found is True
    assert report.has_402_status is True
    assert report.has_payment_header is False
    assert report.score == 1
    assert "HTTP 402 status" in report.detail


@pytest.mark.asyncio
async def test_x402_headers_only():
    """Test payment headers on non-402 response → score=1."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Payment-Address": "0xabc", "X-402-Receipt": "token123"}
        )

    async with _make_client(handler) as client:
        report = await check_x402("https://example.com/api", client)

    assert report.found is True
    assert report.has_402_status is False
    assert report.has_payment_header is True
    assert report.score == 1
    assert "headers:" in report.detail


@pytest.mark.asyncio
async def test_x402_not_found():
    """Test no x402 support → score=0."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _make_client(handler) as client:
        report = await check_x402("https://example.com", client)

    assert report.found is False
    assert report.has_402_status is False
    assert report.has_payment_header is False
    assert report.score == 0
    assert "No x402 payment signaling detected" in report.detail


@pytest.mark.asyncio
async def test_x402_network_error():
    """Test network error returns safe default."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async with _make_client(handler) as client:
        report = await check_x402("https://example.com", client)

    assert report.found is False
    assert report.score == 0
    assert "Failed to check x402" in report.detail
