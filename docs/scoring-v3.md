# V3 Scoring Methodology

Context CLI v3.0 introduces a fifth scoring pillar -- **Agent Readiness** -- that measures how well a site supports direct interaction with autonomous AI agents. V3 scoring is opt-in via `--scoring v3`; the existing V2 model remains the default.

## V2 vs V3 Comparison

| Pillar | V2 (default) | V3 (`--scoring v3`) | Change |
|---|---|---|---|
| Content Density | 40 | 35 | -5 |
| Robots.txt AI Bot Access | 25 | 20 | -5 |
| Schema.org JSON-LD | 25 | 20 | -5 |
| **Agent Readiness** | -- | **20** | **new** |
| llms.txt Presence | 10 | 5 | -5 |
| **Total** | **100** | **100** | -- |

Both models produce a 0-100 score. The total always sums to 100.

## Why V3?

The V2 scoring model was designed for a world where AI systems primarily consume web content through crawl-and-index pipelines: fetch HTML, extract text, build a search index. In that model, the key questions are "can the bot crawl?" (robots.txt), "is the content well-structured?" (content density + schema), and "are there LLM-specific instructions?" (llms.txt).

V3 reflects the emergence of **agentic AI** -- autonomous agents that interact with web services directly, negotiate content formats, discover API endpoints, and even handle payments. These agents need more than crawlable HTML. They need:

- Machine-readable interaction instructions (AGENTS.md)
- Content negotiation for token-efficient formats (Accept: text/markdown)
- Discoverable tool endpoints (MCP)
- Clean semantic structure for reliable extraction (semantic HTML)
- Payment signaling for premium content access (x402)
- Natural language query interfaces (NLWeb)

The 20-point Agent Readiness pillar captures these signals. The existing pillars are rebalanced slightly to make room, but their relative ordering is preserved: content remains the most important, followed by robots and schema at equal weight, then agent readiness, then llms.txt.

## Backward Compatibility

V2 remains the default scoring model. Existing CI pipelines, baselines, and historical scores are unaffected unless you explicitly opt in to V3:

```bash
# V2 (default, unchanged)
context-cli lint example.com

# V3 (opt-in)
context-cli lint example.com --scoring v3
```

Baseline files created with V2 are not directly comparable to V3 scores. If you switch scoring models, regenerate your baseline:

```bash
context-cli lint example.com --scoring v3 --save-baseline .context-baseline-v3.json
```

## Agent Readiness Pillar (20 points)

The Agent Readiness pillar is composed of six sub-checks. Each sub-check is scored independently, and the pillar score is the sum of all sub-check scores.

### Sub-check 1: AGENTS.md (5 points)

**What it checks:** Whether the site publishes an `AGENTS.md` file at a well-known location.

[AGENTS.md](https://docs.google.com/document/d/1ON2MRbDC2RVJpKMIoluHFz-bGDAELz3RjMLErxEDqn4) is an emerging convention for telling AI agents how to interact with a site -- what tools are available, what actions are permitted, rate limits, authentication methods, and acceptable use policies. It is the agent equivalent of `robots.txt`.

**Scoring:**

| Condition | Points |
|---|---|
| `AGENTS.md` found at `/AGENTS.md` or `/.well-known/AGENTS.md` (HTTP 200, non-empty) | 5 |
| Not found | 0 |

### Sub-check 2: Accept: text/markdown (5 points)

**What it checks:** Whether the server responds with markdown content when an AI agent sends `Accept: text/markdown` in its request headers.

Content negotiation via `Accept: text/markdown` allows agents to request a token-efficient representation of a page without parsing and cleaning raw HTML. This is the mechanism used by Cloudflare's Markdown for Agents feature and the Context CLI serve/middleware stack.

**Scoring:**

| Condition | Points |
|---|---|
| Server returns `Content-Type: text/markdown` when requested | 5 |
| Not supported | 0 |

### Sub-check 3: MCP Endpoint (4 points)

**What it checks:** Whether the site advertises a discoverable [Model Context Protocol](https://modelcontextprotocol.io/) endpoint.

MCP endpoints allow AI agents to call site-specific tools programmatically -- search, booking, data queries, etc. Context CLI checks for MCP endpoint advertisements in:

- `<link rel="mcp" href="...">` in HTML `<head>`
- `.well-known/mcp.json` endpoint
- AGENTS.md references to MCP endpoints

**Scoring:**

| Condition | Points |
|---|---|
| MCP endpoint discovered via any method | 4 |
| Not found | 0 |

### Sub-check 4: Semantic HTML (3 points)

**What it checks:** Quality of semantic HTML structure beyond basic content density.

While the Content Density pillar measures text volume and formatting, the Semantic HTML sub-check evaluates structural semantics that help agents reliably identify page regions: `<main>`, `<article>`, `<nav>`, `<aside>`, `<header>`, `<footer>`, `<section>`, ARIA landmarks, and role attributes.

**Scoring:**

| Condition | Points |
|---|---|
| 5+ distinct semantic/landmark elements found | 3 |
| 3-4 distinct semantic/landmark elements | 2 |
| 1-2 distinct semantic/landmark elements | 1 |
| No semantic elements | 0 |

### Sub-check 5: x402 Payment Signaling (2 points)

**What it checks:** Whether the site supports the x402 protocol for payment-gated agent access.

x402 is an emerging standard for HTTP-based micropayments. When a resource requires payment, the server responds with HTTP 402 and includes `x402-*` headers specifying payment methods, amounts, and supported currencies. This enables AI agents to autonomously pay for premium content access.

**Scoring:**

| Condition | Points |
|---|---|
| HTTP 402 response with valid `x402-*` headers, or `x402` metadata in AGENTS.md | 2 |
| Not detected | 0 |

### Sub-check 6: NLWeb Support (1 point)

**What it checks:** Whether the site supports the [NLWeb](https://github.com/nicholasgasior/nlweb) protocol for natural language web queries.

NLWeb allows AI agents to query a site using natural language and receive structured responses, enabling conversational interaction with web services without screen-scraping.

**Scoring:**

| Condition | Points |
|---|---|
| NLWeb endpoint discovered (via `/.well-known/nlweb.json` or HTML meta tags) | 1 |
| Not found | 0 |

## Rebalanced Pillars

The four existing pillars use the same internal scoring logic as V2, but their maximum points are scaled:

### Content Density (35 points in V3, was 40 in V2)

The internal scoring formula is unchanged (word count tiers + structure bonuses). The raw score is scaled from 0-40 to 0-35:

```
v3_content = v2_content * (35 / 40)
```

### Robots.txt AI Bot Access (20 points in V3, was 25 in V2)

```
v3_robots = 20 * (allowed_bots / total_bots)
```

### Schema.org JSON-LD (20 points in V3, was 25 in V2)

The type-weighting formula is scaled:

```
v3_schema = min(20, scaled_base + type_bonuses)
```

### llms.txt Presence (5 points in V3, was 10 in V2)

- **5 points** if `llms.txt` or `llms-full.txt` found
- **0 points** if not found

## Examples

| Site Profile | Content | Robots | Schema | Agent | llms.txt | V3 Total |
|---|---|---|---|---|---|---|
| Modern API docs site with AGENTS.md, markdown support, MCP | 30 | 20 | 15 | 19 | 5 | 89 |
| Well-optimized blog (no agent features) | 35 | 20 | 20 | 3 | 0 | 78 |
| Basic corporate site | 20 | 15 | 10 | 0 | 0 | 45 |
| SPA with blocked bots, no schema | 10 | 0 | 0 | 0 | 0 | 10 |

## CLI Usage

```bash
# V3 single page
context-cli lint example.com --single --scoring v3

# V3 verbose (shows agent readiness sub-check breakdown)
context-cli lint example.com --single --scoring v3 --verbose

# V3 with CI thresholds
context-cli lint example.com --scoring v3 --fail-under 70

# V3 baseline
context-cli lint example.com --scoring v3 --save-baseline .context-baseline-v3.json
```

## MCP Tool

The `agent_readiness_audit` MCP tool runs only the Agent Readiness sub-checks against a URL:

```
Call the agent_readiness_audit tool with url="https://example.com"
```

This returns a structured report with each sub-check's result, points earned, and detail.
