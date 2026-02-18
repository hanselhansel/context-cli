# AEO-CLI — Claude Code Project Context

## Overview
AEO-CLI is an open-source Agentic Engine Optimization CLI tool. It audits URLs for AI crawler readiness — checking robots.txt bot access, llms.txt presence, JSON-LD structured data, and content density — returning a 0-100 AEO score as structured JSON. It also runs as a FastMCP server for AI agent integration.

## Tech Stack
- **Language**: Python 3.10+
- **CLI**: Typer + Rich
- **HTTP**: httpx (async) with retry logic
- **HTML parsing**: BeautifulSoup4
- **Crawling**: crawl4ai (headless browser)
- **Data models**: Pydantic v2
- **MCP server**: FastMCP
- **Testing**: pytest + pytest-asyncio + pytest-cov
- **Linting**: Ruff
- **Type checking**: mypy (with Pydantic plugin)
- **CI**: GitHub Actions (test + lint + mypy, Python 3.10/3.11/3.12 matrix)

## Architecture
```
CLI (main.py)  ←→  MCP Server (server.py)
      └────────┬───────────┘
         audit_url() in auditor.py
        ╱       │       ╲
  crawler.py  auditor.py  models.py
                │
  formatters/   core/
  ├── csv.py    ├── cache.py     # Robots.txt caching
  └── markdown  ├── retry.py     # HTTP retry with backoff
                └── discovery.py
```
- `models.py` defines ALL data contracts (Pydantic) + OutputFormat enum + RetryConfig
- `auditor.py` is the core entry point: `audit_url(url) → AuditReport`
- `main.py` and `server.py` are thin wrappers around `audit_url()`
- `formatters/` provides CSV and Markdown output alternatives

## Project Structure
```
src/aeo_cli/
├── __init__.py          # Package version
├── py.typed             # PEP 561 typed marker
├── main.py              # Typer CLI (entry point: aeo-cli)
├── server.py            # FastMCP server
├── formatters/
│   ├── csv.py           # CSV output formatter
│   └── markdown.py      # Markdown output formatter
└── core/
    ├── models.py        # Pydantic models + enums
    ├── auditor.py       # Audit orchestration + scoring
    ├── crawler.py       # crawl4ai wrapper
    ├── cache.py         # Robots.txt caching
    ├── retry.py         # HTTP retry with backoff
    └── discovery.py     # Sitemap/spider page discovery
tests/
├── test_models.py       ├── test_robots_edge_cases.py
├── test_auditor.py      ├── test_llms_txt_edge_cases.py
├── test_cli.py          ├── test_schema_edge_cases.py
├── test_discovery.py    ├── test_content_boundaries.py
├── test_site_audit.py   ├── test_scoring_integration.py
├── test_mcp_server.py   ├── test_crawler_errors.py
├── test_formatters.py   ├── test_sitemap_parsing.py
├── test_retry.py        ├── test_spider.py
├── test_cache.py        ├── test_page_weight_edges.py
├── test_verbose_output.py └── test_cli_errors.py
docs/
├── scoring.md           # Scoring methodology
└── mcp-integration.md   # MCP server usage guide
```

## Commands
```bash
pip install -e ".[dev]"              # Install with dev deps
crawl4ai-setup                       # Install browser for crawl4ai
pytest                               # Run tests (with coverage)
ruff check src/ tests/               # Lint
mypy src/                            # Type check
make ci                              # Run lint + typecheck + tests
aeo-cli audit <url>                  # Multi-page site audit (Rich output)
aeo-cli audit <url> --single         # Single-page audit
aeo-cli audit <url> --json           # JSON output
aeo-cli audit <url> --format csv     # CSV output
aeo-cli audit <url> --format markdown # Markdown output
aeo-cli audit <url> --verbose        # Detailed pillar breakdown
aeo-cli audit <url> --quiet          # Silent mode (exit code only)
aeo-cli mcp                          # Start MCP stdio server
```

## Conventions
- Async-first: core logic is async, CLI bridges with `asyncio.run()`
- All errors captured in `AuditReport.errors`, never crash the audit
- Pydantic `Field(description=...)` on all model fields (propagates to MCP schemas)
- src-layout packaging
- Ruff for linting (line-length=100)
- mypy for type checking (check_untyped_defs=true)
- pytest-cov for coverage reporting

## Scoring Pillars (0-100 total, revised 2026-02-18)
| Pillar | Max Points | Source |
|--------|-----------|--------|
| Content density | 40 | Markdown conversion (highest: what LLMs actually cite) |
| Robots.txt AI bot access | 25 | robots.txt parsing (gatekeeper) |
| Schema.org JSON-LD | 25 | HTML extraction (structured entity signals) |
| llms.txt presence | 10 | HTTP probe (emerging standard, low impact today) |

## AI Bots Checked
GPTBot, ChatGPT-User, Google-Extended, ClaudeBot, PerplexityBot, Amazonbot, OAI-SearchBot
