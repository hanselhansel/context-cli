# MCP Integration Guide

Context CLI includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server, allowing AI agents to run LLM readiness lints programmatically.

## What is MCP?

MCP is an open protocol that lets AI assistants (like Claude, ChatGPT, etc.) call external tools in a standardized way. By exposing Context CLI as an MCP server, any MCP-compatible AI agent can lint URLs for LLM readiness without the user needing to run CLI commands manually.

## Starting the MCP Server

```bash
context-cli mcp
```

This starts the server using **stdio transport** -- it communicates via standard input/output, which is how most MCP clients (Claude Desktop, Claude Code, etc.) expect to connect.

## Claude Desktop Configuration

To make Context CLI available as a tool in Claude Desktop, add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

After saving, restart Claude Desktop. You'll see "context-cli" listed under available tools.

## Claude Code Configuration

To use Context CLI as an MCP tool in Claude Code:

```bash
claude mcp add context-cli -- context-cli mcp
```

## Available Tools

### `audit`

Lint a URL for LLM readiness and token efficiency.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | The URL to lint |
| `single_page` | `boolean` | `false` | Lint only the given URL (skip multi-page discovery) |
| `max_pages` | `integer` | `10` | Maximum number of pages to lint in multi-page mode |

**Returns:** `AuditReport` (single page) or `SiteAuditReport` (multi-page) as dict.

### `generate`

Generate llms.txt and schema.jsonld for a URL using LLM analysis.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | URL to generate assets for |
| `profile` | `string` | `"generic"` | Industry profile (generic, cpg, saas, ecommerce, blog) |
| `model` | `string` | `null` | LLM model to use (auto-detected from env if not set) |
| `output_dir` | `string` | `"./context-output"` | Directory to write generated files |

**Returns:** `GenerateResult` as dict.

### `compare`

Compare lint results between two URLs.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url1` | `string` | (required) | First URL to lint |
| `url2` | `string` | (required) | Second URL to lint |

**Returns:** `CompareReport` as dict, including per-pillar deltas and a winner summary.

### `history`

Retrieve lint history for a URL from local SQLite storage.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | URL to look up history for |
| `limit` | `integer` | `10` | Maximum number of history entries to return |

**Returns:** List of historical lint reports as dicts.

### `recommend`

Lint a URL and generate actionable recommendations to improve its score.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | URL to lint and generate recommendations for |

**Returns:** List of `Recommendation` objects as dicts, sorted by estimated impact. Each recommendation includes: pillar, action, estimated_impact, priority, and detail.

## Example: Single Page Lint

**Request** (from an AI agent):
```
Call the audit tool with url="https://example.com" and single_page=true
```

**Response** (abbreviated):
```json
{
  "url": "https://example.com",
  "overall_score": 52.5,
  "robots": {
    "found": true,
    "bots": [
      {"bot": "GPTBot", "allowed": true, "detail": "Allowed"},
      {"bot": "ClaudeBot", "allowed": true, "detail": "Allowed"}
    ],
    "score": 25.0,
    "detail": "13/13 AI bots allowed"
  },
  "llms_txt": {
    "found": false,
    "url": null,
    "score": 0,
    "detail": "llms.txt not found"
  },
  "schema_org": {
    "blocks_found": 1,
    "schemas": [
      {"schema_type": "Organization", "properties": ["name", "url", "logo"]}
    ],
    "score": 11,
    "detail": "1 JSON-LD block(s) found"
  },
  "content": {
    "word_count": 325,
    "char_count": 2150,
    "has_headings": true,
    "has_lists": false,
    "has_code_blocks": false,
    "score": 22,
    "detail": "325 words, has headings"
  },
  "errors": []
}
```

## Example: Get Recommendations

**Request:**
```
Call the recommend tool with url="https://example.com"
```

**Response** (abbreviated):
```json
[
  {
    "pillar": "llms_txt",
    "action": "Create an llms.txt file",
    "estimated_impact": 10.0,
    "priority": "high",
    "detail": "No llms.txt file was found. Create /llms.txt with..."
  },
  {
    "pillar": "schema_org",
    "action": "Add high-value schema types",
    "estimated_impact": 5.0,
    "priority": "high",
    "detail": "Add FAQPage, Article, or HowTo schema..."
  }
]
```

## Use Cases

- **Content teams**: Ask Claude to "lint our blog for LLM readiness" -- it calls the tool automatically
- **SEO monitoring**: Build an AI agent that periodically lints your site and flags regressions
- **Competitive analysis**: Use `compare` to pit two URLs against each other
- **Score improvement**: Use `recommend` to get actionable suggestions sorted by impact
- **CI/CD integration**: Use the MCP tool in automated pipelines to gate deployments on score thresholds
- **Trend tracking**: Use `history` to track score changes over time

## Technical Details

- The MCP server is built with [FastMCP](https://github.com/jlowin/fastmcp)
- Transport: stdio (standard for desktop AI clients)
- All Pydantic `Field(description=...)` annotations propagate to the MCP tool schema, giving AI agents rich parameter descriptions
- The server exposes 5 tools: `audit`, `generate`, `compare`, `history`, `recommend`
