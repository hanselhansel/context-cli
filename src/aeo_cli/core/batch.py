"""Batch audit: parse URL files and run concurrent audits."""

from __future__ import annotations

import asyncio
import csv
import io
from collections.abc import Callable

from aeo_cli.core.auditor import audit_site, audit_url
from aeo_cli.core.models import AuditReport, BatchAuditReport, SiteAuditReport


def parse_url_file(path: str) -> list[str]:
    """Read URLs from a .txt or .csv file.

    - Skips empty lines and lines starting with #
    - For .csv files, uses the first column as URL (skips header if present)
    - Auto-prepends https:// to URLs without a scheme
    """
    with open(path) as f:
        raw = f.read()

    if path.endswith(".csv"):
        return _parse_csv(raw)
    return _parse_txt(raw)


def _parse_txt(raw: str) -> list[str]:
    """Parse a plain text file with one URL per line."""
    urls: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(_ensure_scheme(stripped))
    return urls


def _parse_csv(raw: str) -> list[str]:
    """Parse a CSV file, using the first column as URL."""
    urls: list[str] = []
    reader = csv.reader(io.StringIO(raw))
    for row in reader:
        if not row:
            continue
        cell = row[0].strip()
        if not cell or cell.startswith("#"):
            continue
        # Skip header row (heuristic: if first cell doesn't look like a URL)
        if cell.lower() in ("url", "urls", "uri", "link", "website"):
            continue
        urls.append(_ensure_scheme(cell))
    return urls


def _ensure_scheme(url: str) -> str:
    """Prepend https:// if the URL has no scheme."""
    if not url.startswith("http"):
        return f"https://{url}"
    return url


async def run_batch_audit(
    urls: list[str],
    *,
    single: bool = False,
    max_pages: int = 10,
    timeout: int = 15,
    concurrency: int = 3,
    progress_callback: Callable[[str], None] | None = None,
    bots: list[str] | None = None,
) -> BatchAuditReport:
    """Run audits for multiple URLs with concurrency limiting.

    Args:
        urls: List of URLs to audit.
        single: If True, run single-page audits; otherwise multi-page site audits.
        max_pages: Max pages per site audit.
        timeout: HTTP timeout in seconds.
        concurrency: Max concurrent audits.
        progress_callback: Called with status messages for each URL.
    """
    semaphore = asyncio.Semaphore(concurrency)
    reports: list[AuditReport | SiteAuditReport] = []
    errors: dict[str, str] = {}

    async def _audit_one(url: str) -> None:
        async with semaphore:
            if progress_callback:
                progress_callback(f"Auditing {url}...")
            try:
                report: AuditReport | SiteAuditReport
                if single:
                    report = await audit_url(url, timeout=timeout, bots=bots)
                else:
                    report = await audit_site(
                        url, max_pages=max_pages, timeout=timeout, bots=bots
                    )
                reports.append(report)
            except Exception as e:
                errors[url] = str(e)

    tasks = [asyncio.create_task(_audit_one(u)) for u in urls]
    await asyncio.gather(*tasks)

    return BatchAuditReport(urls=urls, reports=reports, errors=errors)
