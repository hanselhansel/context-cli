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

- **Robots.txt AI bot access** — checks 13 AI crawlers (GPTBot, ClaudeBot, DeepSeek-AI, Grok, and more)
- **llms.txt & llms-full.txt** — detects both standard and extended LLM instruction files
- **Schema.org JSON-LD** — extracts and evaluates structured data with high-value type weighting (Product, Article, FAQ, HowTo)
- **Content density** — measures useful content vs. boilerplate with readability scoring, heading structure analysis, and answer-first detection
- **Batch mode** — audit multiple URLs from a file with `--file` and configurable `--concurrency`
- **Custom bot list** — override default bots with `--bots` for targeted checks
- **Verbose output** — detailed per-pillar breakdown with scoring explanations and recommendations
- **Rich CLI output** — formatted tables and scores via Rich
- **JSON / CSV / Markdown output** — machine-readable results for pipelines
- **MCP server** — expose the audit as a tool for AI agents via FastMCP
- **AEO Compiler** — LLM-powered `llms.txt` and `schema.jsonld` generation, with batch mode for multiple URLs
- **CI/CD integration** — `--fail-under` threshold, `--fail-on-blocked-bots`, per-pillar thresholds, baseline regression detection, GitHub Step Summary
- **GitHub Action** — composite action for CI pipelines with baseline support
- **Citation Radar** — query AI models to see what they cite and recommend, with brand tracking and domain classification

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

### Timeout

Set the HTTP timeout (default: 15 seconds):

```bash
aeo-cli audit example.com --timeout 30
```

### Custom Bot List

Override the default 13 bots with a custom list:

```bash
aeo-cli audit example.com --bots "GPTBot,ClaudeBot,PerplexityBot"
```

### Batch Mode

Audit multiple URLs from a file (one URL per line, `.txt` or `.csv`):

```bash
aeo-cli audit --file urls.txt
aeo-cli audit --file urls.txt --concurrency 5
aeo-cli audit --file urls.txt --format csv
```

### CI Mode

Fail the build if the AEO score is below a threshold:

```bash
aeo-cli audit example.com --fail-under 60
```

Fail if any AI bot is blocked:

```bash
aeo-cli audit example.com --fail-on-blocked-bots
```

#### Per-Pillar Thresholds

Gate CI on individual pillar scores:

```bash
aeo-cli audit example.com --robots-min 20 --content-min 30 --overall-min 60
```

Available: `--robots-min`, `--schema-min`, `--content-min`, `--llms-min`, `--overall-min`.

#### Baseline Regression Detection

Save a baseline and detect score regressions in future audits:

```bash
# Save current scores as baseline
aeo-cli audit example.com --single --save-baseline .aeo-baseline.json

# Compare against baseline (exit 1 if any pillar drops > 5 points)
aeo-cli audit example.com --single --baseline .aeo-baseline.json

# Custom regression threshold
aeo-cli audit example.com --single --baseline .aeo-baseline.json --regression-threshold 10
```

Exit codes: 0 = pass, 1 = score below threshold or regression detected, 2 = bots blocked.

When running in GitHub Actions, a markdown summary is automatically written to `$GITHUB_STEP_SUMMARY`.

### Quiet Mode

Suppress output, exit code 0 if score >= 50, 1 otherwise:

```bash
aeo-cli audit example.com --quiet
```

Use `--fail-under` with `--quiet` to override the default threshold:

```bash
aeo-cli audit example.com --quiet --fail-under 70
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

## AEO Compiler (Generate)

Generate `llms.txt` and `schema.jsonld` files from any URL using LLM analysis:

```bash
pip install aeo-cli[generate]
aeo-cli generate example.com
```

This crawls the URL, sends the content to an LLM, and writes optimized files to `./aeo-output/`.

### Batch Generate

Generate assets for multiple URLs from a file:

```bash
aeo-cli generate-batch urls.txt
aeo-cli generate-batch urls.txt --concurrency 5 --profile ecommerce
aeo-cli generate-batch urls.txt --json
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
aeo-cli generate example.com --model gpt-4o
```

### Industry Profiles

Tailor the output with `--profile`:

```bash
aeo-cli generate example.com --profile saas
aeo-cli generate example.com --profile ecommerce
```

Available: `generic`, `cpg`, `saas`, `ecommerce`, `blog`.

## Citation Radar

Query AI models to see what they cite and recommend for any search prompt:

```bash
pip install aeo-cli[generate]
aeo-cli radar "best project management tools" --brand Asana --brand Monday --model gpt-4o-mini
```

Options:
- `--brand/-b`: Brand name to track (repeatable)
- `--model/-m`: LLM model to query (repeatable, default: gpt-4o-mini)
- `--runs/-r`: Runs per model for statistical significance
- `--json`: Output as JSON

## GitHub Action

Use AEO-CLI in your CI pipeline:

```yaml
- name: Run AEO Audit
  uses: hanselhansel/aeo-cli@main
  with:
    url: 'https://your-site.com'
    fail-under: '60'
```

With baseline regression detection:

```yaml
- name: Run AEO Audit
  uses: hanselhansel/aeo-cli@main
  with:
    url: 'https://your-site.com'
    baseline-file: '.aeo-baseline.json'
    save-baseline: '.aeo-baseline.json'
    regression-threshold: '5'
```

The action sets up Python, installs aeo-cli, and runs the audit. Outputs `score` and `report-json` for downstream steps. See [docs/ci-integration.md](docs/ci-integration.md) for full documentation.

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
- **Schema.org (25 pts)** provides structured "cheat sheets" that help AI understand entities. High-value types (Product, Article, FAQ, HowTo, Recipe) receive bonus weighting. Valuable but not required for citation.
- **llms.txt (10 pts)** is an emerging standard. Both `/llms.txt` and `/llms-full.txt` are checked. No major AI search engine heavily weights it yet, but it signals forward-thinking AI readiness.

## AI Bots Checked

AEO-CLI checks access rules for 13 AI crawlers:

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
