"""Pillar 1: Robots.txt AI bot access checking."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from aeo_cli.core.models import BotAccessResult, RobotsReport

AI_BOTS: list[str] = [
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "ClaudeBot",
    "PerplexityBot",
    "Amazonbot",
    "OAI-SearchBot",
    "DeepSeek-AI",
    "Grok",
    "Meta-ExternalAgent",
    "cohere-ai",
    "AI2Bot",
    "ByteSpider",
]

DEFAULT_TIMEOUT: int = 15


async def check_robots(
    url: str, client: httpx.AsyncClient
) -> tuple[RobotsReport, str | None]:
    """Fetch robots.txt and check AI bot access.

    Returns:
        (report, raw_robots_text) — raw text is provided so discovery can filter URLs.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        resp = await client.get(robots_url, follow_redirects=True)
        if resp.status_code != 200:
            return (
                RobotsReport(
                    found=False, detail=f"robots.txt returned HTTP {resp.status_code}"
                ),
                None,
            )

        raw_text = resp.text
        rp = RobotFileParser()
        rp.parse(raw_text.splitlines())

        bots = []
        for bot in AI_BOTS:
            allowed = rp.can_fetch(bot, "/")
            bots.append(BotAccessResult(
                bot=bot,
                allowed=allowed,
                detail="Allowed" if allowed else "Blocked by robots.txt",
            ))

        allowed_count = sum(1 for b in bots if b.allowed)
        return (
            RobotsReport(
                found=True,
                bots=bots,
                detail=f"{allowed_count}/{len(AI_BOTS)} AI bots allowed",
            ),
            raw_text,
        )

    except httpx.HTTPError as e:
        return RobotsReport(found=False, detail=f"Failed to fetch robots.txt: {e}"), None
