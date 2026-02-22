# Context CLI

[![Tests](https://github.com/hanselhansel/context-cli/actions/workflows/test.yml/badge.svg)](https://github.com/hanselhansel/context-cli/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/context-cli.svg)](https://pypi.org/project/context-cli/)

**Lint any URL for LLM readiness. Get a 0-100 score for token efficiency, RAG readiness, agent compatibility, and LLM extraction quality.**

## What is Context CLI?

Context CLI is an LLM Readiness Linter that checks how well a URL is structured for AI consumption. As LLM-powered search engines, RAG pipelines, and AI agents become primary consumers of web content, your pages need to be optimized for token efficiency, structured data extraction, agent interoperability, and machine-readable formatting.

Context CLI analyzes your content across five pillars (V3 scoring) and returns a structured score from 0 to 100.

## Features

- **Robots.txt AI bot access** -- checks 13 AI crawlers (GPTBot, ClaudeBot, DeepSeek-AI, Grok, and more)
- **llms.txt & llms-full.txt** -- detects both standard and extended LLM instruction files
- **Schema.org JSON-LD** -- extracts and evaluates structured data with high-value type weighting (Product, Article, FAQ, HowTo)
- **Content density** -- measures useful content vs. boilerplate with readability scoring, heading structure analysis, and answer-first detection
- **Agent Readiness (V3)** -- 20-point pillar checking AGENTS.md, `Accept: text/markdown`, MCP endpoints, semantic HTML, x402 payment signaling, and NLWeb support
- **Markdown-for-Agents engine** -- convert any URL to clean, token-efficient markdown; open-source alternative to Cloudflare's Markdown for Agents
- **Serve modes** -- reverse proxy, ASGI middleware, and WSGI middleware that serve markdown to agents via `Accept: text/markdown`
- **Batch mode** -- lint multiple URLs from a file with `--file` and configurable `--concurrency`
- **Custom bot list** -- override default bots with `--bots` for targeted checks
- **Verbose output** -- detailed per-pillar breakdown with scoring explanations and recommendations
- **Rich CLI output** -- formatted tables and scores via Rich
- **JSON / CSV / Markdown output** -- machine-readable results for pipelines
- **MCP server** -- expose the linter as a tool for AI agents via FastMCP (8 tools including agent readiness, markdown conversion, and AGENTS.md generation)
- **Context Compiler** -- LLM-powered `llms.txt`, `schema.jsonld`, and `AGENTS.md` generation, with batch mode for multiple URLs
- **Web server config generation** -- generate nginx, Apache, and Caddy configs for `Accept: text/markdown` routing
- **x402 payment config generation** -- generate payment signaling configuration for monetizing agent access
- **CI/CD integration** -- `--fail-under` threshold, `--fail-on-blocked-bots`, per-pillar thresholds, baseline regression detection, GitHub Step Summary
- **GitHub Action** -- composite action for CI pipelines with baseline support
- **Citation Radar** -- query AI models to see what they cite and recommend, with brand tracking and domain classification
- **Share-of-Recommendation Benchmark** -- track how often AI models mention and recommend your brand vs competitors, with LLM-as-judge analysis

## Installation

```bash
pip install context-linter
```

Context CLI uses a headless browser for content extraction. After installing, run:

```bash
crawl4ai-setup
```

### Development install

```bash
git clone https://github.com/your-org/context-cli.git
cd context-cli
pip install -e ".[dev]"
crawl4ai-setup
```

## Quick Start

```bash
context-cli lint example.com
```

This runs a full lint and prints a Rich-formatted report with your LLM readiness score.

## CLI Usage

### Single Page Lint

Lint only the specified URL (skip multi-page discovery):

```bash
context-cli lint example.com --single
```

### Multi-Page Site Lint (default)

Discover pages via sitemap/spider and lint up to 10 pages:

```bash
context-cli lint example.com
```

### Limit Pages

```bash
context-cli lint example.com --max-pages 5
```

### JSON Output

Get structured JSON for CI pipelines, dashboards, or scripting:

```bash
context-cli lint example.com --json
```

### CSV / Markdown Output

```bash
context-cli lint example.com --format csv
context-cli lint example.com --format markdown
```

### Verbose Mode

Show detailed per-pillar breakdown with scoring explanations:

```bash
context-cli lint example.com --single --verbose
```

### Timeout

Set the HTTP timeout (default: 15 seconds):

```bash
context-cli lint example.com --timeout 30
```

### Custom Bot List

Override the default 13 bots with a custom list:

```bash
context-cli lint example.com --bots "GPTBot,ClaudeBot,PerplexityBot"
```

### Batch Mode

Lint multiple URLs from a file (one URL per line, `.txt` or `.csv`):

```bash
context-cli lint --file urls.txt
context-cli lint --file urls.txt --concurrency 5
context-cli lint --file urls.txt --format csv
```

### CI Mode

Fail the build if the score is below a threshold:

```bash
context-cli lint example.com --fail-under 60
```

Fail if any AI bot is blocked:

```bash
context-cli lint example.com --fail-on-blocked-bots
```

#### Per-Pillar Thresholds

Gate CI on individual pillar scores:

```bash
context-cli lint example.com --robots-min 20 --content-min 30 --overall-min 60
```

Available: `--robots-min`, `--schema-min`, `--content-min`, `--llms-min`, `--overall-min`.

#### Baseline Regression Detection

Save a baseline and detect score regressions in future lints:

```bash
# Save current scores as baseline
context-cli lint example.com --single --save-baseline .context-baseline.json

# Compare against baseline (exit 1 if any pillar drops > 5 points)
context-cli lint example.com --single --baseline .context-baseline.json

# Custom regression threshold
context-cli lint example.com --single --baseline .context-baseline.json --regression-threshold 10
```

Exit codes: 0 = pass, 1 = score below threshold or regression detected, 2 = bots blocked.

When running in GitHub Actions, a markdown summary is automatically written to `$GITHUB_STEP_SUMMARY`.

### Quiet Mode

Suppress output, exit code 0 if score >= 50, 1 otherwise:

```bash
context-cli lint example.com --quiet
```

Use `--fail-under` with `--quiet` to override the default threshold:

```bash
context-cli lint example.com --quiet --fail-under 70
```

### Markdown Conversion

Convert any URL to clean, token-efficient markdown optimized for LLM consumption:

```bash
context-cli markdown https://example.com
```

Show token reduction statistics (raw HTML tokens vs. clean markdown tokens):

```bash
context-cli markdown https://example.com --stats
```

Generate a static markdown site (one `.md` file per discovered page):

```bash
context-cli markdown https://example.com --static -o ./output/
```

The markdown engine uses a three-stage pipeline (Sanitize, Extract, Convert) to strip boilerplate, navigation, ads, and scripts, producing clean markdown that typically achieves 70%+ token reduction. See [docs/markdown-engine.md](docs/markdown-engine.md) for details.

### Reverse Proxy Server

Serve markdown to AI agents automatically via `Accept: text/markdown` content negotiation:

```bash
context-cli serve --upstream https://example.com --port 8080
```

When an AI agent sends a request with `Accept: text/markdown`, the proxy fetches the upstream HTML, converts it through the markdown engine, and returns clean markdown. Regular browser requests receive the original HTML unchanged.

### V3 Scoring

Use the V3 scoring model with the Agent Readiness pillar:

```bash
context-cli lint https://example.com --scoring v3
```

V3 adds a 20-point Agent Readiness pillar and rebalances the existing pillars. See [docs/scoring-v3.md](docs/scoring-v3.md) for the full methodology.

### Start MCP server

```bash
context-cli mcp
```

Launches a FastMCP stdio server exposing the linter as a tool for AI agents.

## MCP Integration

To use Context CLI as a tool in Claude Desktop, add this to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "context-cli": {
      "command": "context-cli",
      "args": ["mcp"]
    }
  }
}
```

Once configured, Claude can call the `audit_url` tool directly to check any URL's LLM readiness.

### New MCP Tools (v3.0)

In addition to the existing tools (`audit`, `generate`, `compare`, `history`, `recommend`), v3.0 adds:

- **`agent_readiness_audit`** -- run agent readiness checks (AGENTS.md, Accept: text/markdown, MCP endpoints, semantic HTML, x402, NLWeb) against a URL
- **`convert_to_markdown`** -- convert any URL's HTML to clean, token-efficient markdown
- **`generate_agents_md`** -- generate an AGENTS.md file for a given URL based on its content and structure

See [docs/mcp-integration.md](docs/mcp-integration.md) for full tool documentation.

## Context Compiler (Generate)

Generate `llms.txt` and `schema.jsonld` files from any URL using LLM analysis:

```bash
pip install context-linter[generate]
context-cli generate example.com
```

This crawls the URL, sends the content to an LLM, and writes optimized files to `./context-output/`.

### Batch Generate

Generate assets for multiple URLs from a file:

```bash
context-cli generate-batch urls.txt
context-cli generate-batch urls.txt --concurrency 5 --profile ecommerce
context-cli generate-batch urls.txt --json
```

Each URL's output goes to a subdirectory under `--output-dir`.

### BYOK (Bring Your Own Key)

The generate command auto-detects your LLM provider from environment variables:

| Priority | Env Variable | Model Used |
|----------|-------------|------------|
| 1 | `OPENAI_API_KEY` | gpt-4o-mini |
| 2 | `ANTHROPIC_API_KEY` | claude-3-haiku-20240307 |
| 3 | Ollama running locally | ollama/llama3.2 |

Override with `--model`:

```bash
context-cli generate example.com --model gpt-4o
```

### Industry Profiles

Tailor the output with `--profile`:

```bash
context-cli generate example.com --profile saas
context-cli generate example.com --profile ecommerce
```

Available: `generic`, `cpg`, `saas`, `ecommerce`, `blog`.

### AGENTS.md Generation

Generate an [AGENTS.md](https://docs.google.com/document/d/1ON2MRbDC2RVJpKMIoluHFz-bGDAELz3RjMLErxEDqn4) file that tells AI agents how to interact with your site:

```bash
context-cli generate example.com --agents-md
```

### Web Server Config Generation

Generate web server configuration snippets for routing `Accept: text/markdown` requests:

```bash
context-cli generate-config nginx
context-cli generate-config apache
context-cli generate-config caddy
```

Each generates a config snippet that detects `Accept: text/markdown` in incoming requests and routes them to the Context CLI markdown endpoint or a local markdown-serving backend.

### x402 Payment Config Generation

Generate x402 payment signaling configuration for monetizing AI agent access:

```bash
context-cli generate-x402
```

## Serve Modes

Context CLI provides three ways to serve markdown to AI agents that send `Accept: text/markdown` requests.

### Reverse Proxy

Run a standalone reverse proxy that sits in front of your existing site:

```bash
context-cli serve --upstream https://example.com --port 8080
```

Requests with `Accept: text/markdown` receive converted markdown. All other requests are proxied to the upstream unchanged.

### ASGI Middleware (FastAPI / Starlette)

Add markdown serving to any ASGI application:

```python
from context_cli.middleware import MarkdownASGIMiddleware

app = FastAPI()
app = MarkdownASGIMiddleware(app)
```

### WSGI Middleware (Django / Flask)

Add markdown serving to any WSGI application:

```python
from context_cli.middleware import MarkdownWSGIMiddleware

app = MarkdownWSGIMiddleware(app)
```

Both middleware variants intercept requests with `Accept: text/markdown`, convert the response HTML through the markdown engine, and return clean markdown with `Content-Type: text/markdown`.

## Citation Radar

Query AI models to see what they cite and recommend for any search prompt:

```bash
pip install context-linter[generate]
context-cli radar "best project management tools" --brand Asana --brand Monday --model gpt-4o-mini
```

Options:
- `--brand/-b`: Brand name to track (repeatable)
- `--model/-m`: LLM model to query (repeatable, default: gpt-4o-mini)
- `--runs/-r`: Runs per model for statistical significance
- `--json`: Output as JSON

## Share-of-Recommendation Benchmark

Track how AI models mention and recommend your brand across multiple prompts:

```bash
pip install context-linter[generate]
context-cli benchmark prompts.txt -b "YourBrand" -c "Competitor1" -c "Competitor2"
```

Options:
- `prompts.txt`: CSV (with `prompt,category,intent` columns) or plain text (one prompt per line)
- `--brand/-b`: Target brand to track (required)
- `--competitor/-c`: Competitor brand (repeatable)
- `--model/-m`: LLM model to query (repeatable, default: gpt-4o-mini)
- `--runs/-r`: Runs per model per prompt (default: 3)
- `--yes/-y`: Skip cost confirmation prompt
- `--json`: Output as JSON

## GitHub Action

Use Context CLI in your CI pipeline:

```yaml
- name: Run Context Lint
  uses: hanselhansel/context-cli@main
  with:
    url: 'https://your-site.com'
    fail-under: '60'
```

With baseline regression detection:

```yaml
- name: Run Context Lint
  uses: hanselhansel/context-cli@main
  with:
    url: 'https://your-site.com'
    baseline-file: '.context-baseline.json'
    save-baseline: '.context-baseline.json'
    regression-threshold: '5'
```

The action sets up Python, installs context-cli, and runs the lint. Outputs `score` and `report-json` for downstream steps. See [docs/ci-integration.md](docs/ci-integration.md) for full documentation.

## Score Breakdown

Context CLI supports two scoring models. V2 (default) uses four pillars; V3 adds a fifth pillar for agent readiness.

### V2 Scoring (default)

| Pillar | Max Points | What it measures |
|---|---|---|
| Content density | 40 | Quality and depth of extractable text content |
| Robots.txt AI bot access | 25 | Whether AI crawlers are allowed in robots.txt |
| Schema.org JSON-LD | 25 | Structured data markup (Product, Article, FAQ, etc.) |
| llms.txt presence | 10 | Whether a /llms.txt file exists for LLM guidance |

### V3 Scoring (`--scoring v3`)

| Pillar | Max Points | What it measures |
|---|---|---|
| Content density | 35 | Quality and depth of extractable text content |
| Robots.txt AI bot access | 20 | Whether AI crawlers are allowed in robots.txt |
| Schema.org JSON-LD | 20 | Structured data markup (Product, Article, FAQ, etc.) |
| Agent Readiness | 20 | Preparedness for autonomous AI agent interaction |
| llms.txt presence | 5 | Whether a /llms.txt file exists for LLM guidance |

The Agent Readiness pillar checks six sub-signals:

| Sub-check | Points | What it detects |
|---|---|---|
| AGENTS.md | 5 | Presence of an AGENTS.md file describing agent interaction |
| Accept: text/markdown | 5 | Server responds to `Accept: text/markdown` with markdown content |
| MCP endpoint | 4 | Presence of a discoverable MCP (Model Context Protocol) endpoint |
| Semantic HTML | 3 | Quality of semantic HTML structure (landmark elements, ARIA roles) |
| x402 payment signaling | 2 | HTTP 402 or x402 headers indicating payment-gated agent access |
| NLWeb support | 1 | Support for the NLWeb protocol for natural language web queries |

See [docs/scoring-v3.md](docs/scoring-v3.md) for the full V3 methodology.

### Scoring rationale

The V2 weights reflect how AI search engines (ChatGPT, Perplexity, Claude) actually consume web content:

- **Content density (40 pts)** is weighted highest because it's what LLMs extract and cite when answering questions. Rich, well-structured content with headings and lists gives AI better material to work with.
- **Robots.txt (25 pts)** is the gatekeeper -- if a bot is blocked, it literally cannot crawl. It's critical but largely binary (either you're blocking or you're not).
- **Schema.org (25 pts)** provides structured "cheat sheets" that help AI understand entities. High-value types (Product, Article, FAQ, HowTo, Recipe) receive bonus weighting. Valuable but not required for citation.
- **llms.txt (10 pts)** is an emerging standard. Both `/llms.txt` and `/llms-full.txt` are checked. No major AI search engine heavily weights it yet, but it signals forward-thinking AI readiness.

V3 rebalances these weights to accommodate the new Agent Readiness pillar, reflecting the growing importance of direct agent interaction alongside traditional crawl-and-index patterns.

## AI Bots Checked

Context CLI checks access rules for 13 AI crawlers:

- GPTBot
- ChatGPT-User
- Google-Extended
- ClaudeBot
- PerplexityBot
- Amazonbot
- OAI-SearchBot
- DeepSeek-AI
- Grok
- Meta-ExternalAgent
- cohere-ai
- AI2Bot
- ByteSpider

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
