"""Tests for webhook notification system."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from context_cli.core.models import (
    AuditReport,
    ContentReport,
    DiscoveryResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
    SiteAuditReport,
    WebhookPayload,
)
from context_cli.core.webhook import build_webhook_payload, send_webhook
from context_cli.main import app

runner = CliRunner()


def _mock_report() -> AuditReport:
    """Build a known AuditReport for webhook tests."""
    return AuditReport(
        url="https://example.com",
        overall_score=72.5,
        robots=RobotsReport(found=True, score=25.0, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=20.0, detail="2 blocks"),
        content=ContentReport(word_count=800, score=17.5, detail="800 words"),
    )


# -- WebhookPayload model tests -----------------------------------------------


def test_webhook_payload_serialization():
    """WebhookPayload should serialize to JSON with all expected fields."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=72.5,
        robots_score=25.0,
        llms_txt_score=10.0,
        schema_score=20.0,
        content_score=17.5,
        timestamp="2026-01-01T00:00:00Z",
    )
    data = payload.model_dump()
    assert data["url"] == "https://example.com"
    assert data["overall_score"] == 72.5
    assert data["robots_score"] == 25.0
    assert data["llms_txt_score"] == 10.0
    assert data["schema_score"] == 20.0
    assert data["content_score"] == 17.5
    assert data["timestamp"] == "2026-01-01T00:00:00Z"
    assert data["regression"] is False


def test_webhook_payload_regression_flag():
    """WebhookPayload should accept a regression flag."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=50.0,
        robots_score=10.0,
        llms_txt_score=0.0,
        schema_score=15.0,
        content_score=25.0,
        timestamp="2026-01-01T00:00:00Z",
        regression=True,
    )
    assert payload.regression is True


# -- build_webhook_payload tests -----------------------------------------------


def test_build_webhook_payload_extracts_scores():
    """build_webhook_payload should extract all pillar scores from AuditReport."""
    report = _mock_report()
    payload = build_webhook_payload(report)

    assert payload.url == "https://example.com"
    assert payload.overall_score == 72.5
    assert payload.robots_score == 25.0
    assert payload.llms_txt_score == 10.0
    assert payload.schema_score == 20.0
    assert payload.content_score == 17.5
    assert payload.regression is False
    assert payload.timestamp  # non-empty timestamp


def test_build_webhook_payload_timestamp_format():
    """Timestamp should be ISO 8601 format."""
    report = _mock_report()
    payload = build_webhook_payload(report)
    # Should be parseable as ISO 8601 (contains T and Z or +00:00)
    assert "T" in payload.timestamp


# -- send_webhook tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_send_webhook_success():
    """send_webhook should return True on 200 response."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=72.5,
        robots_score=25.0,
        llms_txt_score=10.0,
        schema_score=20.0,
        content_score=17.5,
        timestamp="2026-01-01T00:00:00Z",
    )
    mock_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com"))
    with patch("context_cli.core.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_webhook("https://hooks.example.com", payload)

    assert result is True
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_webhook_failure_returns_false():
    """send_webhook should return False on non-2xx response."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=50.0,
        robots_score=10.0,
        llms_txt_score=0.0,
        schema_score=15.0,
        content_score=25.0,
        timestamp="2026-01-01T00:00:00Z",
    )
    mock_response = httpx.Response(500, request=httpx.Request("POST", "https://hooks.example.com"))
    with patch("context_cli.core.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_webhook("https://hooks.example.com", payload)

    assert result is False


@pytest.mark.asyncio
async def test_send_webhook_timeout_returns_false():
    """send_webhook should return False on timeout."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=50.0,
        robots_score=10.0,
        llms_txt_score=0.0,
        schema_score=15.0,
        content_score=25.0,
        timestamp="2026-01-01T00:00:00Z",
    )
    with patch("context_cli.core.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_webhook("https://hooks.example.com", payload)

    assert result is False


@pytest.mark.asyncio
async def test_send_webhook_connection_error_returns_false():
    """send_webhook should return False on connection error."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=50.0,
        robots_score=10.0,
        llms_txt_score=0.0,
        schema_score=15.0,
        content_score=25.0,
        timestamp="2026-01-01T00:00:00Z",
    )
    with patch("context_cli.core.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_webhook("https://hooks.example.com", payload)

    assert result is False


@pytest.mark.asyncio
async def test_send_webhook_posts_json_payload():
    """send_webhook should POST the payload as JSON."""
    payload = WebhookPayload(
        url="https://example.com",
        overall_score=72.5,
        robots_score=25.0,
        llms_txt_score=10.0,
        schema_score=20.0,
        content_score=17.5,
        timestamp="2026-01-01T00:00:00Z",
    )
    mock_response = httpx.Response(200, request=httpx.Request("POST", "https://hooks.example.com"))
    with patch("context_cli.core.webhook.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await send_webhook("https://hooks.example.com", payload)

    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == "https://hooks.example.com"
    assert "json" in call_kwargs[1]
    json_data = call_kwargs[1]["json"]
    assert json_data["url"] == "https://example.com"
    assert json_data["overall_score"] == 72.5


# -- CLI --webhook flag integration tests --------------------------------------


def _mock_site_report() -> SiteAuditReport:
    """Build a known SiteAuditReport for CLI webhook tests."""
    return SiteAuditReport(
        url="https://example.com",
        domain="example.com",
        overall_score=68.0,
        robots=RobotsReport(found=True, score=25.0, detail="7/7 allowed"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="Found"),
        schema_org=SchemaReport(blocks_found=2, score=13.0, detail="2 blocks"),
        content=ContentReport(word_count=700, score=20.0, detail="700 words"),
        discovery=DiscoveryResult(method="sitemap", urls_found=50, detail="50 found"),
        pages_audited=2,
    )


def test_cli_webhook_flag_single():
    """--webhook flag should trigger send_webhook after single-page audit."""

    async def _fake_audit(url, **kwargs):
        return _mock_report()

    async def _fake_send(url, payload):
        return True

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit),
        patch("context_cli.core.webhook.send_webhook", side_effect=_fake_send) as mock_send,
        patch(
            "context_cli.core.webhook.build_webhook_payload",
            return_value=WebhookPayload(
                url="https://example.com",
                overall_score=72.5,
                robots_score=25.0,
                llms_txt_score=10.0,
                schema_score=20.0,
                content_score=17.5,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ) as mock_build,
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single",
                  "--webhook", "https://hooks.example.com"]
        )

    assert result.exit_code == 0
    mock_build.assert_called_once()
    mock_send.assert_called_once()


def test_cli_webhook_flag_site():
    """--webhook flag should trigger send_webhook after site audit."""

    async def _fake_audit(*a, **kw):
        return _mock_site_report()

    async def _fake_send(url, payload):
        return True

    with (
        patch("context_cli.cli.audit.audit_site", side_effect=_fake_audit),
        patch("context_cli.core.webhook.send_webhook", side_effect=_fake_send) as mock_send,
        patch(
            "context_cli.core.webhook.build_webhook_payload",
            return_value=WebhookPayload(
                url="https://example.com",
                overall_score=68.0,
                robots_score=25.0,
                llms_txt_score=10.0,
                schema_score=13.0,
                content_score=20.0,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ),
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com",
                  "--webhook", "https://hooks.example.com"]
        )

    assert result.exit_code == 0
    mock_send.assert_called_once()


def test_cli_webhook_failure_does_not_crash():
    """--webhook failure should warn but not fail the audit."""

    async def _fake_audit(url, **kwargs):
        return _mock_report()

    async def _fake_send(url, payload):
        return False

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit),
        patch("context_cli.core.webhook.send_webhook", side_effect=_fake_send),
        patch(
            "context_cli.core.webhook.build_webhook_payload",
            return_value=WebhookPayload(
                url="https://example.com",
                overall_score=72.5,
                robots_score=25.0,
                llms_txt_score=10.0,
                schema_score=20.0,
                content_score=17.5,
                timestamp="2026-01-01T00:00:00Z",
            ),
        ),
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single",
                  "--webhook", "https://hooks.example.com"]
        )

    assert result.exit_code == 0
    assert "webhook" in result.output.lower()


def test_cli_webhook_exception_does_not_crash():
    """--webhook exception should warn but not fail the audit."""

    async def _fake_audit(url, **kwargs):
        return _mock_report()

    with (
        patch("context_cli.cli.audit.audit_url", side_effect=_fake_audit),
        patch(
            "context_cli.core.webhook.build_webhook_payload",
            side_effect=RuntimeError("unexpected error"),
        ),
    ):
        result = runner.invoke(
            app, ["lint", "https://example.com", "--single",
                  "--webhook", "https://hooks.example.com"]
        )

    assert result.exit_code == 0
    assert "webhook" in result.output.lower() or "error" in result.output.lower()
