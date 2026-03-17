# API Reference

This document covers the public API surface of Context CLI: the Python API for programmatic use, the MCP tools for AI agent integration, and the CLI commands.

## Python API

### `audit_url(url, **kwargs) -> AuditReport`

Lint a single URL and return an audit report.

```python
from context_cli.core.auditor import audit_url

report = await audit_url("https://example.com")
print(report.score)          # 0-100 overall score
print(report.robots)         # robots.txt check result
print(report.schema)         # Schema.org check result
print(report.content)        # content density result
print(report.llms_txt)       # llms.txt check result
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str` | (required) | URL to audit |
| `timeout` | `int` | `15` | HTTP timeout in seconds |
| `bots` | `list[str]` | `None` | Custom bot list (default: 13 bots) |
| `scoring` | `str` | `"v2"` | Scoring model (`"v2"` or `"v3"`) |
| `single` | `bool` | `False` | Skip multi-page discovery |
| `max_pages` | `int` | `10` | Max pages to lint in multi-page mode |

### `audit_site(url, **kwargs) -> list[AuditReport]`

Lint multiple pages discovered from a URL.

```python
from context_cli.core.auditor import audit_site

reports = await audit_site("https://example.com", max_pages=5)
for report in reports:
    print(f"{report.url}: {report.score}")
```

### `AuditReport`

The data model returned by audit functions.

```python
@dataclass
class AuditReport:
    url: str                    # audited URL
    score: float                # overall 0-100 score
    robots: RobotsResult        # robots.txt check
    schema: SchemaResult        # Schema.org check
    content: ContentResult      # content density check
    llms_txt: LlmsTxtResult     # llms.txt check
    agent_readiness: AgentReadinessResult  # V3 only
    pillar_scores: dict         # per-pillar scores
    recommendations: list[str]  # improvement suggestions
```

## MCP Tools

The MCP server exposes these tools via FastMCP. Start with `context-cli mcp`.

### `audit`

Run a full LLM readiness audit on a URL.

**Input:** `{ "url": "https://example.com" }`

**Output:** Full audit report with score, pillar breakdown, and recommendations.

### `agent_readiness_audit`

Run agent readiness checks against a URL (V3 scoring).

**Input:** `{ "url": "https://example.com" }`

**Output:** Agent readiness sub-check results (AGENTS.md, Accept: text/markdown, MCP endpoint, semantic HTML, x402, NLWeb).

### `convert_to_markdown`

Convert a URL's HTML to clean, token-efficient markdown.

**Input:** `{ "url": "https://example.com" }`

**Output:** Converted markdown content with optional token reduction statistics.

### `generate_agents_md`

Generate an AGENTS.md file for a URL based on its content and structure.

**Input:** `{ "url": "https://example.com" }`

**Output:** Generated AGENTS.md content.

### `generate`

Generate llms.txt and schema.jsonld files from a URL using LLM analysis.

**Input:** `{ "url": "https://example.com" }`

**Output:** Generated file contents.

### `compare`

Compare audit results between two URLs or two points in time.

**Input:** `{ "url1": "https://a.com", "url2": "https://b.com" }`

**Output:** Side-by-side comparison of scores and pillar breakdowns.

### `history`

Retrieve audit history for a URL.

**Input:** `{ "url": "https://example.com" }`

**Output:** Historical audit results with score trends.

### `recommend`

Get actionable recommendations for improving a URL's LLM readiness.

**Input:** `{ "url": "https://example.com" }`

**Output:** Prioritized list of improvements with expected score impact.

## CLI Commands

### Core Commands

| Command | Description |
|---|---|
| `context-cli lint <url>` | Lint a URL for LLM readiness |
| `context-cli markdown <url>` | Convert a URL to markdown |
| `context-cli serve` | Start the reverse proxy server |
| `context-cli mcp` | Start the MCP server |

### Generate Commands

| Command | Description |
|---|---|
| `context-cli generate <url>` | Generate llms.txt and schema.jsonld |
| `context-cli generate-batch <file>` | Batch generate for multiple URLs |
| `context-cli generate-config <server>` | Generate web server config |
| `context-cli generate-x402` | Generate x402 payment config |

### Analysis Commands

| Command | Description |
|---|---|
| `context-cli radar <prompt>` | Query AI models for citations |
| `context-cli benchmark <file>` | Run share-of-recommendation benchmark |
| `context-cli compare <url1> <url2>` | Compare two URLs |
| `context-cli history <url>` | View audit history |

### Common Flags

| Flag | Applies to | Description |
|---|---|---|
| `--single` | `lint` | Skip multi-page discovery |
| `--json` | all | Output as JSON |
| `--format` | `lint` | Output format (`csv`, `markdown`) |
| `--verbose` | `lint` | Detailed per-pillar breakdown |
| `--quiet` | `lint` | Suppress output, exit code only |
| `--timeout` | `lint`, `markdown` | HTTP timeout in seconds |
| `--fail-under` | `lint` | Minimum score threshold for CI |
| `--fail-on-blocked-bots` | `lint` | Fail if AI bots are blocked |
| `--scoring` | `lint` | Scoring model (`v2`, `v3`) |
| `--file` | `lint` | Batch lint from file |
| `--concurrency` | `lint`, `generate-batch` | Parallel workers |
