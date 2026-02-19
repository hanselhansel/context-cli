"""Pillar 1: Robots.txt AI bot access checking."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from context_cli.core.models import BotAccessResult, RobotsReport

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
    url: str, client: httpx.AsyncClient, *, bots: list[str] | None = None
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

        bots_to_check = bots or AI_BOTS
        bot_results = []
        for bot_name in bots_to_check:
            allowed = rp.can_fetch(bot_name, "/")
            bot_results.append(BotAccessResult(
                bot=bot_name,
                allowed=allowed,
                detail="Allowed" if allowed else "Blocked by robots.txt",
            ))

        allowed_count = sum(1 for b in bot_results if b.allowed)
        return (
            RobotsReport(
                found=True,
                bots=bot_results,
                detail=f"{allowed_count}/{len(bots_to_check)} AI bots allowed",
            ),
            raw_text,
        )

    except httpx.HTTPError as e:
        return RobotsReport(found=False, detail=f"Failed to fetch robots.txt: {e}"), None
