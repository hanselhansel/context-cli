"""Webhook payload models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookPayload(BaseModel):
    """Payload sent to webhook URLs after an audit completes."""

    url: str = Field(description="Audited URL")
    overall_score: float = Field(description="Overall Readiness Score")
    robots_score: float = Field(description="Robots pillar score")
    llms_txt_score: float = Field(description="llms.txt pillar score")
    schema_score: float = Field(description="Schema.org pillar score")
    content_score: float = Field(description="Content pillar score")
    timestamp: str = Field(description="ISO 8601 timestamp")
    regression: bool = Field(default=False, description="Whether regression was detected")
