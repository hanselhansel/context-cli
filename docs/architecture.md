# Architecture Overview

This document describes the high-level architecture of Context CLI.

## Entry Points

Context CLI has two primary entry points:

### CLI (`src/context_cli/main.py`)

The command-line interface is built with Click and exposes subcommands: `lint`, `markdown`, `serve`, `generate`, `generate-batch`, `generate-config`, `generate-x402`, `radar`, `benchmark`, `compare`, `history`, `mcp`, and `watch`. Each subcommand is defined in its own module under `src/context_cli/cli/`.

### MCP Server (`src/context_cli/server.py`)

The MCP (Model Context Protocol) server exposes the linter as a set of tools for AI agents via FastMCP. It runs as a stdio server and provides 8 tools including `audit`, `generate`, `compare`, `history`, `recommend`, `agent_readiness_audit`, `convert_to_markdown`, and `generate_agents_md`.

## Core Modules

### Auditor (`src/context_cli/core/auditor.py`)

The central orchestrator. Given a URL, the auditor crawls the page, runs all checks, computes the score, and returns an `AuditReport`. It coordinates the crawler, individual checks, and scoring logic.

### Crawler (`src/context_cli/core/crawler.py`)

Uses crawl4ai (backed by Playwright) to fetch and render web pages. Returns raw HTML and extracted content for downstream checks.

### Discovery (`src/context_cli/core/discovery.py`)

Multi-page discovery via sitemap parsing and link spidering. Used by the default multi-page lint mode.

### Checks (`src/context_cli/core/checks/`)

Individual check modules, each responsible for one aspect of LLM readiness:

- `robots.py` -- robots.txt AI bot access (13 bots)
- `schema.py` -- Schema.org JSON-LD extraction and evaluation
- `content.py` -- content density, readability, heading structure
- `llms_txt.py` -- llms.txt and llms-full.txt detection
- `agents_md.py` -- AGENTS.md file detection
- `markdown_accept.py` -- Accept: text/markdown support
- `mcp_endpoint.py` -- MCP endpoint discovery
- `semantic_html.py` -- semantic HTML quality
- `x402.py` -- x402 payment signaling
- `nlweb.py` -- NLWeb protocol support

### Scoring (`src/context_cli/core/scoring.py`)

Computes the 0-100 score from individual check results. Supports both V2 (four pillars) and V3 (five pillars with agent readiness) scoring models.

### Models (`src/context_cli/core/models/`)

Pydantic/dataclass models for audit reports, check results, and intermediate data. Key model: `AuditReport` in `models/audit.py`.

## Scoring Models

### V2 (default)

Four pillars: Content Density (40), Robots.txt (25), Schema.org (25), llms.txt (10).

### V3 (`--scoring v3`)

Five pillars: Content Density (35), Robots.txt (20), Schema.org (20), Agent Readiness (20), llms.txt (5). See [scoring-v3.md](scoring-v3.md) for the full methodology.

## Plugins (`src/context_cli/core/plugin.py`)

Extensible plugin system for adding custom checks. Plugins are discovered and loaded at runtime.

## Generate / Compiler (`src/context_cli/core/generate/`)

LLM-powered generation of `llms.txt`, `schema.jsonld`, and `AGENTS.md` files. Uses a compiler architecture:

- `compiler.py` -- orchestrates the generation pipeline
- `llm.py` -- LLM provider abstraction (OpenAI, Anthropic, Ollama)
- `prompts.py` -- prompt templates for each output type
- `profiles.py` -- industry-specific profiles (SaaS, ecommerce, blog, etc.)
- `batch.py` -- batch generation for multiple URLs

## Markdown Engine (`src/context_cli/core/markdown_engine/`)

Three-stage pipeline for converting HTML to clean, token-efficient markdown:

1. **Sanitizer** (`sanitizer.py`) -- strips scripts, styles, ads, navigation
2. **Extractor** (`extractor.py`) -- identifies main content area
3. **Converter** (`converter.py`) -- converts cleaned HTML to markdown

## Serve Modes (`src/context_cli/core/serve/`)

Three deployment options for serving markdown to AI agents:

- `proxy.py` -- standalone reverse proxy
- `middleware.py` -- ASGI and WSGI middleware
- `static_gen.py` -- static markdown site generator

## Formatters (`src/context_cli/formatters/`)

Output formatting modules: Rich terminal tables, JSON, CSV, Markdown, HTML, CI summary, and verbose panels.

## Data Flow

```
URL
 |
 v
Crawler (crawl4ai + Playwright)
 |
 v
Discovery (sitemap/spider) -----> [page URLs]
 |                                      |
 v                                      v
Checks (robots, schema, content, ...)   Checks (per page)
 |                                      |
 v                                      v
Scoring (V2 or V3)                 Scoring (per page)
 |                                      |
 v                                      v
AuditReport                        AuditReport[]
 |
 v
Formatter (Rich / JSON / CSV / Markdown)
 |
 v
Output (terminal / file / CI summary)
```
