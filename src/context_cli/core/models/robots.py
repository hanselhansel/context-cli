"""Robots.txt AI bot access models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BotAccessResult(BaseModel):
    """Result of checking a single AI bot's access in robots.txt."""

    bot: str = Field(description="Name of the AI bot (e.g., GPTBot, ClaudeBot)")
    allowed: bool = Field(description="Whether the bot is allowed by robots.txt")
    detail: str = Field(default="", description="Additional detail (e.g., Disallow rule found)")


class RobotsReport(BaseModel):
    """Aggregated robots.txt analysis for AI bots. Max 25 points."""

    found: bool = Field(description="Whether robots.txt was accessible")
    bots: list[BotAccessResult] = Field(
        default_factory=list, description="Per-bot access results"
    )
    score: float = Field(default=0, description="Robots pillar score (0-25)")
    detail: str = Field(default="", description="Summary of robots.txt findings")
