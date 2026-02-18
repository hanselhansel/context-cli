# AEO-CLI

[![Tests](https://github.com/hanselhansel/aeo-cli/actions/workflows/test.yml/badge.svg)](https://github.com/hanselhansel/aeo-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/aeo-cli.svg)](https://pypi.org/project/aeo-cli/)

**Audit any URL for AI crawler readiness. Get a 0-100 AEO score.**

## What is AEO?

Agentic Engine Optimization (AEO) is the practice of making your website discoverable and accessible to AI agents and LLM-powered search engines. As AI crawlers like GPTBot, ClaudeBot, and PerplexityBot become major traffic sources, AEO ensures your content is structured, permitted, and optimized for these systems.

AEO-CLI checks how well a URL is prepared for AI consumption and returns a structured score.

## Features

- **Robots.txt AI bot access** — checks whether major AI crawlers are allowed or blocked
- **llms.txt presence** — detects the emerging standard for LLM-specific site instructions
- **Schema.org JSON-LD** — extracts and evaluates structured data markup
- **Content density** — measures useful content vs. boilerplate via markdown conversion
- **Rich CLI output** — formatted tables and scores via Rich
- **JSON output** — machine-readable results for pipelines
- **MCP server** — expose the audit as a tool for AI agents via FastMCP

## Installation

```bash
pip install aeo-cli
```

AEO-CLI uses a headless browser for content extraction. After installing, run:

```bash
crawl4ai-setup
```

### Development install

```bash
git clone https://github.com/your-org/aeo-cli.git
cd aeo-cli
pip install -e ".[dev]"
crawl4ai-setup
```

## Quick Start

```bash
aeo-cli audit example.com
```

This runs a full audit and prints a Rich-formatted report with your AEO score.

## CLI Usage

### Single Page Audit

Audit only the specified URL (skip multi-page discovery):

```bash
aeo-cli audit example.com --single
```

### Multi-Page Site Audit (default)

Discover pages via sitemap/spider and audit up to 10 pages:

```bash
aeo-cli audit example.com
```

### Limit Pages

```bash
aeo-cli audit example.com --max-pages 5
```

### JSON Output

Get structured JSON for CI pipelines, dashboards, or scripting:

```bash
aeo-cli audit example.com --json
```

### CSV / Markdown Output

```bash
aeo-cli audit example.com --format csv
aeo-cli audit example.com --format markdown
```

### Verbose Mode

Show detailed per-pillar breakdown with scoring explanations:

```bash
aeo-cli audit example.com --single --verbose
```

### Quiet Mode (CI)

Suppress output, exit code 0 if score >= 50, 1 otherwise:

```bash
aeo-cli audit example.com --quiet
```

### Start MCP server

```bash
aeo-cli mcp
```

Launches a FastMCP stdio server exposing the audit as a tool for AI agents.

## MCP Integration

To use AEO-CLI as a tool in Claude Desktop, add this to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "aeo-cli": {
      "command": "aeo-cli",
      "args": ["mcp"]
    }
  }
}
```

Once configured, Claude can call the `audit_url` tool directly to check any URL's AEO readiness.

## Score Breakdown

AEO-CLI returns a score from 0 to 100, composed of four pillars:

| Pillar | Max Points | What it measures |
|---|---|---|
| Content density | 40 | Quality and depth of extractable text content |
| Robots.txt AI bot access | 25 | Whether AI crawlers are allowed in robots.txt |
| Schema.org JSON-LD | 25 | Structured data markup (Product, Article, FAQ, etc.) |
| llms.txt presence | 10 | Whether a /llms.txt file exists for LLM guidance |

### Scoring rationale (2026-02-18)

The weights reflect how AI search engines (ChatGPT, Perplexity, Claude) actually consume web content:

- **Content density (40 pts)** is weighted highest because it's what LLMs extract and cite when answering questions. Rich, well-structured content with headings and lists gives AI better material to work with.
- **Robots.txt (25 pts)** is the gatekeeper — if a bot is blocked, it literally cannot crawl. It's critical but largely binary (either you're blocking or you're not).
- **Schema.org (25 pts)** provides structured "cheat sheets" that help AI understand entities (products, articles, organizations). Valuable but not required for citation.
- **llms.txt (10 pts)** is an emerging standard. No major AI search engine heavily weights it yet, but it signals forward-thinking AI readiness.

## AI Bots Checked

AEO-CLI checks access rules for these AI crawlers:

- GPTBot
- ChatGPT-User
- Google-Extended
- ClaudeBot
- PerplexityBot
- Amazonbot
- OAI-SearchBot

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## License

MIT
