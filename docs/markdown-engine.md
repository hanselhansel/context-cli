# Markdown-for-Agents Engine

Context CLI includes a Markdown-for-Agents engine that converts web pages into clean, token-efficient markdown optimized for LLM consumption. It is an open-source alternative to Cloudflare's [Markdown for Agents](https://developers.cloudflare.com/speed/optimization/content/markdown-for-agents/) feature (available only on Pro+ plans).

## Overview

When an AI agent fetches a web page, the raw HTML contains enormous amounts of noise -- navigation bars, JavaScript bundles, CSS, tracking scripts, cookie banners, ads, and boilerplate. An LLM processing this HTML wastes tokens on content that adds no value to its task.

The markdown engine strips this noise and produces clean markdown that preserves only the meaningful content. Typical token reduction is **70% or more** -- a page with 10,000 raw HTML tokens might convert to 2,500 clean markdown tokens.

## Pipeline

The engine uses a three-stage pipeline:

```
Raw HTML ──> [Sanitize] ──> [Extract] ──> [Convert] ──> Clean Markdown
```

### Stage 1: Sanitize

The sanitizer removes elements that never contain useful content:

- `<script>` and `<noscript>` elements
- `<style>` elements and inline styles
- `<iframe>` elements (ads, embeds)
- HTML comments
- SVG and canvas elements
- Hidden elements (`display:none`, `aria-hidden="true"`)
- Cookie consent banners and overlays
- Navigation and footer boilerplate (heuristic detection)

The sanitizer operates on the raw HTML string before DOM parsing, using both regex patterns for simple cases and DOM traversal for structural detection.

### Stage 2: Extract

The extractor identifies the primary content region of the page:

- Looks for semantic landmarks: `<main>`, `<article>`, `[role="main"]`
- Falls back to the largest content block by text density
- Strips sidebar (`<aside>`), navigation (`<nav>`), and footer (`<footer>`) elements
- Preserves `<table>`, `<figure>`, `<blockquote>`, and other content-bearing elements within the main region

The goal is to isolate the content a human reader would consider "the page" -- not the chrome around it.

### Stage 3: Convert

The converter transforms the extracted HTML into clean markdown:

- Headings (`<h1>`-`<h6>`) become `#`-`######`
- Paragraphs become text blocks with blank line separation
- Lists (`<ul>`, `<ol>`) become markdown lists with proper nesting
- Links become `[text](url)` with relative URLs resolved to absolute
- Images become `![alt](src)` with alt text preserved
- Tables become pipe-delimited markdown tables
- Code blocks (`<pre><code>`) become fenced code blocks with language detection
- Inline formatting (`<strong>`, `<em>`, `<code>`) maps to markdown equivalents
- Redundant whitespace is collapsed

## Configuration

The engine is configurable via `MarkdownEngineConfig`:

| Option | Type | Default | Description |
|---|---|---|---|
| `include_links` | `bool` | `true` | Include hyperlinks in output |
| `include_images` | `bool` | `true` | Include image references in output |
| `include_tables` | `bool` | `true` | Include table rendering |
| `max_heading_depth` | `int` | `6` | Maximum heading level to preserve (1-6) |
| `collapse_whitespace` | `bool` | `true` | Collapse multiple blank lines into one |
| `absolute_urls` | `bool` | `true` | Resolve relative URLs to absolute |
| `strip_nav` | `bool` | `true` | Remove navigation elements |
| `strip_footer` | `bool` | `true` | Remove footer elements |

## Usage

### As a CLI command

Convert a single URL to markdown and print to stdout:

```bash
context-cli markdown https://example.com
```

Show token reduction statistics alongside the output:

```bash
context-cli markdown https://example.com --stats
```

The `--stats` flag appends a summary showing raw HTML token count, clean markdown token count, and the percentage reduction.

Generate a static markdown site with one `.md` file per discovered page:

```bash
context-cli markdown https://example.com --static -o ./output/
```

This discovers pages using the same sitemap/spider strategy as `lint`, converts each page, and writes the markdown files to the output directory, preserving the URL path structure.

### As a library

Use the engine directly in Python code:

```python
from context_cli.core.markdown import MarkdownEngine, MarkdownEngineConfig

engine = MarkdownEngine(config=MarkdownEngineConfig(
    include_images=False,
    strip_nav=True,
))

html = "<html><body><main><h1>Hello</h1><p>World</p></main></body></html>"
markdown = engine.convert(html, base_url="https://example.com")
print(markdown)
# # Hello
#
# World
```

For async usage with URL fetching:

```python
from context_cli.core.markdown import convert_url

result = await convert_url("https://example.com")
print(result.markdown)
print(f"Token reduction: {result.reduction_pct:.1f}%")
```

### As a reverse proxy (serve mode)

Run a reverse proxy that transparently serves markdown to AI agents:

```bash
context-cli serve --upstream https://example.com --port 8080
```

The proxy inspects the `Accept` header on each incoming request:

- If `Accept: text/markdown` is present, the proxy fetches the upstream HTML, converts it through the engine, and returns `Content-Type: text/markdown`.
- Otherwise, the request is proxied to the upstream unchanged.

This allows a single origin server to serve both human-readable HTML and agent-optimized markdown from the same URLs.

### As ASGI middleware

Add markdown serving to FastAPI, Starlette, or any ASGI application:

```python
from fastapi import FastAPI
from context_cli.middleware import MarkdownASGIMiddleware

app = FastAPI()

@app.get("/article/{slug}")
async def article(slug: str):
    return HTMLResponse(render_article(slug))

# Wrap the app -- agents requesting text/markdown get converted output
app = MarkdownASGIMiddleware(app)
```

### As WSGI middleware

Add markdown serving to Django, Flask, or any WSGI application:

```python
from flask import Flask
from context_cli.middleware import MarkdownWSGIMiddleware

app = Flask(__name__)

@app.route("/article/<slug>")
def article(slug):
    return render_article(slug)

app.wsgi_app = MarkdownWSGIMiddleware(app.wsgi_app)
```

## Content Negotiation

All serve modes (reverse proxy, ASGI, WSGI) use the same content negotiation logic:

1. Check the `Accept` request header for `text/markdown`.
2. If present, intercept the response body (which is assumed to be HTML).
3. Run the HTML through the markdown engine pipeline.
4. Return the result with `Content-Type: text/markdown; charset=utf-8`.
5. If `Accept: text/markdown` is not present, pass the request through without modification.

This follows the same convention as Cloudflare's Markdown for Agents, ensuring compatibility with any AI agent that implements the `Accept: text/markdown` pattern.

## Comparison with Cloudflare's Markdown for Agents

| Feature | Context CLI | Cloudflare |
|---|---|---|
| Availability | Open source, self-hosted | Pro+ plan (paid) |
| Deployment | CLI, proxy, middleware, library | Cloudflare edge network |
| Content negotiation | `Accept: text/markdown` | `Accept: text/markdown` |
| Conversion quality | Three-stage pipeline | Cloudflare's internal engine |
| Static site generation | Yes (`--static` flag) | No |
| Token stats | Yes (`--stats` flag) | No |
| MCP tool | Yes (`convert_to_markdown`) | No |
| Customization | `MarkdownEngineConfig` | Dashboard toggle |
| Latency | Depends on deployment | Edge-optimized |

Context CLI is designed for teams that want full control over their markdown conversion pipeline, need to self-host, or want to use the engine as a library within their own applications. Cloudflare's offering is a zero-config edge solution for sites already on their network.

## Token Reduction Expectations

The engine targets **70% or greater** token reduction on typical web pages. Actual results depend on the page content:

| Page Type | Typical Raw Tokens | Typical Clean Tokens | Reduction |
|---|---|---|---|
| Blog post | 8,000-15,000 | 1,500-4,000 | 70-85% |
| Documentation page | 10,000-25,000 | 2,000-6,000 | 75-85% |
| E-commerce product | 15,000-40,000 | 2,000-5,000 | 80-90% |
| Landing page | 5,000-12,000 | 500-2,000 | 75-90% |
| SPA (JavaScript-heavy) | 3,000-8,000 | 200-1,000 | 70-95% |

Pages with minimal boilerplate (e.g., plain documentation sites) will see lower reduction percentages because there is less noise to strip. Pages with heavy JavaScript frameworks, ad networks, and tracking scripts will see the highest reductions.

## MCP Tool

The `convert_to_markdown` MCP tool exposes the markdown engine to AI agents:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `string` | (required) | URL to convert |
| `include_links` | `boolean` | `true` | Include hyperlinks in output |
| `include_images` | `boolean` | `true` | Include image references |
| `stats` | `boolean` | `false` | Include token reduction statistics |

**Returns:** A `MarkdownResult` dict containing `markdown` (the converted text), and optionally `raw_tokens`, `clean_tokens`, and `reduction_pct` when `stats=true`.
