"""Run batch audit against 50 tech docs sites and save JSON results.

Usage:
    python benchmarks/run_benchmark.py

Requires context-linter to be installed: pip install -e ".[dev]"
Results are saved to benchmarks/data.json for report generation.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

from context_cli.core.batch import parse_url_file, run_batch_audit
from context_cli.core.markdown_engine.converter import convert_url_to_markdown


async def collect_markdown_stats(
    urls: list[str],
    progress_callback: callable | None = None,
) -> dict[str, dict]:
    """Run markdown conversion for each URL and collect token reduction stats.

    Returns a dict mapping URL -> stats dict with keys:
        raw_html_chars, clean_md_chars, raw_tokens, clean_tokens, reduction_pct
    """
    results: dict[str, dict] = {}
    total = len(urls)
    for i, url in enumerate(urls, 1):
        if progress_callback:
            progress_callback(f"[{i}/{total}] Converting {url} to markdown...")
        try:
            _md, stats = await convert_url_to_markdown(url, timeout=30)
            results[url] = stats
        except Exception as exc:
            if progress_callback:
                progress_callback(f"  Skipping {url}: {exc}")
    return results


async def main() -> None:
    url_file = Path(__file__).parent / "urls.txt"
    if not url_file.exists():
        print("Error: urls.txt not found")
        sys.exit(1)

    urls = parse_url_file(str(url_file))
    print(f"Loaded {len(urls)} URLs from {url_file.name}")
    print("Starting benchmark audit (multi-page deep crawl, concurrency=3)...")
    print("  Each site: up to 10 sub-pages discovered via sitemap/spider\n")

    start = time.time()
    report = await run_batch_audit(
        urls,
        single=False,
        max_pages=10,
        concurrency=3,
        timeout=30,
        progress_callback=lambda msg: print(f"  {msg}"),
    )
    audit_elapsed = time.time() - start
    print(f"\nAudit complete in {audit_elapsed:.1f}s")

    # Collect markdown conversion stats for successful report URLs
    successful_urls = [r.url for r in report.reports]
    print(f"\nCollecting markdown conversion stats for {len(successful_urls)} sites...")
    md_start = time.time()
    markdown_stats = await collect_markdown_stats(
        successful_urls,
        progress_callback=lambda msg: print(f"  {msg}"),
    )
    md_elapsed = time.time() - md_start
    print(f"Markdown conversion complete in {md_elapsed:.1f}s")
    print(f"  Converted: {len(markdown_stats)}/{len(successful_urls)}")

    # Build combined output: audit data + markdown stats
    audit_data = json.loads(report.model_dump_json())
    audit_data["markdown_stats"] = markdown_stats

    out_path = Path(__file__).parent / "data.json"
    out_path.write_text(json.dumps(audit_data, indent=2))

    total_elapsed = time.time() - start
    print(f"\nDone in {total_elapsed:.1f}s")
    print(f"  Succeeded: {len(report.reports)}")
    print(f"  Failed:    {len(report.errors)}")
    print(f"  Markdown:  {len(markdown_stats)} converted")
    print(f"  Output:    {out_path}")

    if report.errors:
        print("\nFailed URLs:")
        for url, err in report.errors.items():
            print(f"  {url}: {err}")


if __name__ == "__main__":
    asyncio.run(main())
