"""Edge-case tests for robots.txt parsing and AI bot access checks."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from context_cli.core.checks.robots import check_robots


@pytest.mark.asyncio
async def test_empty_robots_txt():
    """An empty robots.txt should allow all bots (no rules = open access)."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = ""

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, raw_text = await check_robots("https://example.com", mock_client)

    assert report.found is True
    assert all(b.allowed for b in report.bots)
    assert raw_text == ""


@pytest.mark.asyncio
async def test_wildcard_disallow_all():
    """Disallow: / for all user-agents should block every AI bot."""
    robots_txt = "User-agent: *\nDisallow: /\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, _ = await check_robots("https://example.com", mock_client)

    assert report.found is True
    assert all(not b.allowed for b in report.bots)


@pytest.mark.asyncio
async def test_specific_bot_blocked():
    """Only GPTBot blocked, others should be allowed."""
    robots_txt = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, _ = await check_robots("https://example.com", mock_client)

    gptbot = next(b for b in report.bots if b.bot == "GPTBot")
    claudebot = next(b for b in report.bots if b.bot == "ClaudeBot")
    assert gptbot.allowed is False
    assert claudebot.allowed is True


@pytest.mark.asyncio
async def test_malformed_robots_txt():
    """Malformed content should still parse without crashing."""
    robots_txt = "this is not valid robots.txt\nrandom garbage\n@#$%\n"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = robots_txt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, raw_text = await check_robots("https://example.com", mock_client)

    assert report.found is True
    assert len(report.bots) == 13
    assert raw_text == robots_txt


@pytest.mark.asyncio
async def test_robots_txt_server_error():
    """A 500 response should report robots.txt as not found."""
    mock_response = AsyncMock()
    mock_response.status_code = 500

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=mock_response)

    report, raw_text = await check_robots("https://example.com", mock_client)

    assert report.found is False
    assert raw_text is None
    assert "500" in report.detail
