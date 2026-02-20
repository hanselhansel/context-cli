"""Run batch audit against 50 tech docs sites and save JSON results.

Usage:
    python benchmarks/run_benchmark.py

Requires context-linter to be installed: pip install -e ".[dev]"
Results are saved to benchmarks/data.json for report generation.
"""

import asyncio
import sys
import time
from pathlib import Path

from context_cli.core.batch import parse_url_file, run_batch_audit


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
    elapsed = time.time() - start

    out_path = Path(__file__).parent / "data.json"
    out_path.write_text(report.model_dump_json(indent=2))

    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Succeeded: {len(report.reports)}")
    print(f"  Failed:    {len(report.errors)}")
    print(f"  Output:    {out_path}")

    if report.errors:
        print("\nFailed URLs:")
        for url, err in report.errors.items():
            print(f"  {url}: {err}")


if __name__ == "__main__":
    asyncio.run(main())
