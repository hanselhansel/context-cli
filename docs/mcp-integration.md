# MCP Integration Guide

AEO-CLI includes a built-in [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server, allowing AI agents to run AEO audits programmatically.

## What is MCP?

MCP is an open protocol that lets AI assistants (like Claude, ChatGPT, etc.) call external tools in a standardized way. By exposing AEO-CLI as an MCP server, any MCP-compatible AI agent can audit URLs for AI crawler readiness without the user needing to run CLI commands manually.

## Starting the MCP Server

```bash
aeo-cli mcp
```

This starts the server using **stdio transport** — it communicates via standard input/output, which is how most MCP clients (Claude Desktop, Claude Code, etc.) expect to connect.

## Claude Desktop Configuration

To make AEO-CLI available as a tool in Claude Desktop, add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

After saving, restart Claude Desktop. You'll see "aeo-cli" listed under available tools.

## Claude Code Configuration

To use AEO-CLI as an MCP tool in Claude Code:

```bash
claude mcp add aeo-cli -- aeo-cli mcp
```

## Available Tool

### `audit`

Audit a URL for AI engine optimization readiness.

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | The URL to audit |
| `single_page` | `boolean` | `false` | If `true`, audit only the given URL. If `false`, discover and audit multiple pages across the site. |
| `max_pages` | `integer` | `10` | Maximum number of pages to audit in multi-page mode |

**Returns:** A dictionary matching the `AuditReport` (single page) or `SiteAuditReport` (multi-page) schema.

### Example: Single Page Audit

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
    "detail": "7/7 AI bots allowed"
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
    "score": 13,
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

### Example: Multi-Page Site Audit

**Request:**
```
Call the audit tool with url="https://example.com" and max_pages=5
```

**Response** (abbreviated):
```json
{
  "url": "https://example.com",
  "domain": "example.com",
  "overall_score": 61.3,
  "robots": { "score": 25.0, "detail": "7/7 AI bots allowed" },
  "llms_txt": { "score": 0, "detail": "llms.txt not found" },
  "schema_org": { "score": 15.5, "detail": "4 JSON-LD block(s) across 5 pages (weighted avg score 15.5)" },
  "content": { "score": 20.8, "detail": "avg 520 words across 5 pages (weighted avg score 20.8)" },
  "discovery": {
    "method": "sitemap",
    "urls_found": 47,
    "urls_sampled": ["https://example.com", "https://example.com/about", "..."],
    "detail": "method=sitemap, found=47, sampled=5"
  },
  "pages": [
    { "url": "https://example.com", "schema_org": { "score": 13 }, "content": { "score": 22 } },
    { "url": "https://example.com/about", "schema_org": { "score": 18 }, "content": { "score": 15 } }
  ],
  "pages_audited": 5,
  "pages_failed": 0,
  "errors": []
}
```

## Use Cases

- **Content teams**: Ask Claude to "audit our blog for AEO readiness" — it calls the tool automatically
- **SEO monitoring**: Build an AI agent that periodically audits your site and flags regressions
- **Competitive analysis**: Have an AI compare AEO scores across competitor sites
- **CI/CD integration**: Use the MCP tool in automated pipelines to gate deployments on AEO thresholds

## Technical Details

- The MCP server is built with [FastMCP](https://github.com/jlowin/fastmcp)
- Transport: stdio (standard for desktop AI clients)
- All Pydantic `Field(description=...)` annotations propagate to the MCP tool schema, giving AI agents rich parameter descriptions
- The server is a thin wrapper around the same `audit_url()` and `audit_site()` functions used by the CLI
