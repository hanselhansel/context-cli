"""Check for NLWeb support (well-known endpoint and schema extensions)."""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx

from context_cli.core.models import NlwebReport

NLWEB_TYPES: set[str] = {"NLWebEndpoint", "NLWebService"}
NLWEB_ACTIONS: set[str] = {"NLSearchAction", "NLQueryAction"}

DEFAULT_TIMEOUT: int = 15


def _check_schema_extensions(html: str) -> bool:
    """Check HTML for NLWeb Schema.org extensions in JSON-LD blocks."""
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html):
        try:
            data = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            # Check @type for NLWeb types
            item_type = item.get("@type", "")
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(t in NLWEB_TYPES for t in types):
                return True
            # Check potentialAction for NLWeb actions
            actions = item.get("potentialAction", [])
            if isinstance(actions, dict):
                actions = [actions]
            if isinstance(actions, list):
                for action in actions:
                    if isinstance(action, dict):
                        action_type = action.get("@type", "")
                        action_types = (
                            action_type if isinstance(action_type, list) else [action_type]
                        )
                        if any(t in NLWEB_ACTIONS for t in action_types):
                            return True
    return False


async def check_nlweb(
    url: str, client: httpx.AsyncClient, html: str = ""
) -> NlwebReport:
    """Check if a site supports NLWeb protocol.

    Probes /.well-known/nlweb and checks HTML for NLWeb Schema.org extensions.
    """
    well_known_found = False
    schema_found = False

    try:
        parsed = urlparse(url)
        well_known_url = f"{parsed.scheme}://{parsed.netloc}/.well-known/nlweb"
        resp = await client.get(well_known_url, follow_redirects=True)
        well_known_found = resp.status_code == 200
    except httpx.HTTPError:
        pass

    if html:
        schema_found = _check_schema_extensions(html)

    score = 0.0
    if well_known_found:
        score += 0.5
    if schema_found:
        score += 0.5

    found = well_known_found or schema_found

    if not found:
        return NlwebReport(
            found=False,
            score=0,
            detail="No NLWeb support detected",
        )

    parts: list[str] = []
    if well_known_found:
        parts.append("/.well-known/nlweb found")
    if schema_found:
        parts.append("NLWeb schema extensions found")

    return NlwebReport(
        found=True,
        well_known_found=well_known_found,
        schema_extensions=schema_found,
        score=score,
        detail=f"NLWeb: {'; '.join(parts)}",
    )
