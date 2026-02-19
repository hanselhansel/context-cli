"""Webhook notification system for audit results."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from context_cli.core.models import AuditReport, SiteAuditReport, WebhookPayload

logger = logging.getLogger(__name__)


def build_webhook_payload(
    report: AuditReport | SiteAuditReport,
) -> WebhookPayload:
    """Extract scores from an audit report into a WebhookPayload."""
    return WebhookPayload(
        url=report.url,
        overall_score=report.overall_score,
        robots_score=report.robots.score,
        llms_txt_score=report.llms_txt.score,
        schema_score=report.schema_org.score,
        content_score=report.content.score,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


async def send_webhook(webhook_url: str, payload: WebhookPayload) -> bool:
    """POST webhook payload as JSON. Returns True on 2xx, False otherwise."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload.model_dump(),
                timeout=10.0,
            )
        return 200 <= response.status_code < 300
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as exc:
        logger.warning("Webhook delivery failed: %s", exc)
        return False
