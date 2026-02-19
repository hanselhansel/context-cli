"""Pillar 3: Schema.org JSON-LD extraction and analysis."""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from context_cli.core.models import SchemaOrgResult, SchemaReport


def check_schema_org(html: str) -> SchemaReport:  # noqa: C901
    """Extract and analyze JSON-LD structured data from HTML."""
    if not html:
        return SchemaReport(detail="No HTML to analyze")

    soup = BeautifulSoup(html, "html.parser")
    ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    schemas: list[SchemaOrgResult] = []
    for script in ld_scripts:
        try:
            data = json.loads(script.string or "")
            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "Unknown")
                    if isinstance(schema_type, list):
                        schema_type = ", ".join(schema_type)
                    props = [k for k in item.keys() if not k.startswith("@")]
                    schemas.append(SchemaOrgResult(
                        schema_type=schema_type,
                        properties=props,
                    ))
        except (json.JSONDecodeError, TypeError):
            continue

    blocks_found = len(schemas)
    detail = f"{blocks_found} JSON-LD block(s) found" if blocks_found else "No JSON-LD found"

    return SchemaReport(blocks_found=blocks_found, schemas=schemas, detail=detail)
