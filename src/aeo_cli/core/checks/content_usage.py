"""IETF Content-Usage HTTP header detection (aipref Working Group draft)."""

from __future__ import annotations

import re

import httpx

from aeo_cli.core.models import ContentUsageReport

# Pattern to extract key=value pairs from the header
_KV_RE = re.compile(r"(\w+)\s*=\s*(\w+)")


def _parse_bool(value: str) -> bool | None:
    """Parse a yes/no value to bool, case-insensitive."""
    lower = value.strip().lower()
    if lower == "yes":
        return True
    if lower == "no":
        return False
    return None


async def check_content_usage(
    url: str, client: httpx.AsyncClient
) -> ContentUsageReport:
    """Check for the IETF Content-Usage HTTP header via HEAD request."""
    try:
        resp = await client.head(url, follow_redirects=True)
    except httpx.HTTPError as e:
        return ContentUsageReport(
            detail=f"Content-Usage check failed: {e}",
        )

    if resp.status_code != 200:
        return ContentUsageReport(
            detail="Content-Usage header not found (non-200 response)",
        )

    raw = resp.headers.get("content-usage", "").strip()
    if not raw:
        return ContentUsageReport(
            detail="Content-Usage header not found",
        )

    # Parse key=value pairs
    pairs = {m.group(1).lower(): m.group(2) for m in _KV_RE.finditer(raw)}

    allows_training = _parse_bool(pairs["training"]) if "training" in pairs else None
    allows_search = _parse_bool(pairs["search"]) if "search" in pairs else None

    # Build detail
    parts: list[str] = [f"Content-Usage: {raw}"]
    if allows_training is not None:
        parts.append(f"training={'allowed' if allows_training else 'blocked'}")
    if allows_search is not None:
        parts.append(f"search={'allowed' if allows_search else 'blocked'}")

    return ContentUsageReport(
        header_found=True,
        header_value=raw,
        allows_training=allows_training,
        allows_search=allows_search,
        detail="; ".join(parts),
    )
