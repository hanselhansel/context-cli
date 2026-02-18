# AEO-CLI — Claude Code Project Context

## Overview
AEO-CLI is an open-source Agentic Engine Optimization CLI tool. It audits URLs for AI crawler readiness — checking robots.txt bot access, llms.txt presence, JSON-LD structured data, and content density — returning a 0-100 AEO score as structured JSON. It also runs as a FastMCP server for AI agent integration.

## Tech Stack
- **Language**: Python 3.10+
- **CLI**: Typer + Rich
- **HTTP**: httpx (async)
- **HTML parsing**: BeautifulSoup4
- **Crawling**: crawl4ai (headless browser)
- **Data models**: Pydantic v2
- **MCP server**: FastMCP
- **Testing**: pytest + pytest-asyncio
- **Linting**: Ruff

## Architecture
```
CLI (main.py)  ←→  MCP Server (server.py)
      └────────┬───────────┘
         audit_url() in auditor.py
        ╱       │       ╲
  crawler.py  auditor.py  models.py
```
- `models.py` defines ALL data contracts (Pydantic)
- `auditor.py` is the core entry point: `audit_url(url) → AuditReport`
- `main.py` and `server.py` are thin wrappers around `audit_url()`

## Project Structure
```
src/aeo_cli/
├── __init__.py          # Package version
├── main.py              # Typer CLI (entry point: aeo-cli)
├── server.py            # FastMCP server
└── core/
    ├── models.py        # Pydantic models
    ├── auditor.py       # Audit orchestration + scoring
    └── crawler.py       # crawl4ai wrapper
tests/
├── test_models.py
├── test_auditor.py
└── test_cli.py
```

## Commands
```bash
pip install -e ".[dev]"      # Install with dev deps
crawl4ai-setup               # Install browser for crawl4ai
pytest                       # Run tests
ruff check src/ tests/       # Lint
aeo-cli audit <url>          # Run audit (Rich output)
aeo-cli audit <url> --json   # Run audit (JSON output)
aeo-cli mcp                  # Start MCP stdio server
```

## Conventions
- Async-first: core logic is async, CLI bridges with `asyncio.run()`
- All errors captured in `AuditReport.errors`, never crash the audit
- Pydantic `Field(description=...)` on all model fields (propagates to MCP schemas)
- src-layout packaging
- Ruff for linting (line-length=100)

## Scoring Pillars (0-100 total, revised 2026-02-18)
| Pillar | Max Points | Source |
|--------|-----------|--------|
| Content density | 40 | Markdown conversion (highest: what LLMs actually cite) |
| Robots.txt AI bot access | 25 | robots.txt parsing (gatekeeper) |
| Schema.org JSON-LD | 25 | HTML extraction (structured entity signals) |
| llms.txt presence | 10 | HTTP probe (emerging standard, low impact today) |

## AI Bots Checked
GPTBot, ChatGPT-User, Google-Extended, ClaudeBot, PerplexityBot, Amazonbot, OAI-SearchBot
