# Context Compiler (Generate Command)

The generate command uses LLM analysis to produce optimized files that improve your site's LLM readiness. It crawls a URL, sends the content to an LLM, and writes structured output files.

## Overview

The Context Compiler pipeline:

1. **Crawl** -- fetches and renders the target URL
2. **Extract** -- pulls content, structure, and metadata
3. **Analyze** -- sends extracted data to an LLM with specialized prompts
4. **Generate** -- writes output files to `./context-output/` (or custom directory)

## Output Files

### llms.txt

A machine-readable file that tells LLMs how to interact with your site. Placed at `/llms.txt` on your domain, it provides:

- Site description and purpose
- Content structure guidance
- Preferred citation format
- Key pages and their topics

```bash
context-cli generate example.com
```

### schema.jsonld

Optimized Schema.org JSON-LD structured data based on your page content. The compiler analyzes your content and generates appropriate schema types (Article, Product, FAQ, HowTo, etc.) with complete properties.

```bash
context-cli generate example.com
```

### AGENTS.md

An [AGENTS.md](https://docs.google.com/document/d/1ON2MRbDC2RVJpKMIoluHFz-bGDAELz3RjMLErxEDqn4) file that tells AI agents how to interact with your site, including available endpoints, authentication requirements, rate limits, and data formats.

```bash
context-cli generate example.com --agents-md
```

## Batch Mode

Generate assets for multiple URLs from a file:

```bash
context-cli generate-batch urls.txt
context-cli generate-batch urls.txt --concurrency 5 --profile ecommerce
context-cli generate-batch urls.txt --json
```

Each URL's output goes to a subdirectory under the output directory.

## Industry Profiles

Tailor the generated output with `--profile`:

```bash
context-cli generate example.com --profile saas
```

Available profiles:

| Profile | Optimized for |
|---|---|
| `generic` | General-purpose sites (default) |
| `cpg` | Consumer packaged goods |
| `saas` | Software-as-a-Service products |
| `ecommerce` | E-commerce and product pages |
| `blog` | Blog and content sites |

Profiles adjust the LLM prompts to emphasize relevant schema types, content structures, and agent interaction patterns for each industry.

## BYOK (Bring Your Own Key)

The generate command auto-detects your LLM provider from environment variables:

| Priority | Env Variable | Default Model |
|---|---|---|
| 1 | `OPENAI_API_KEY` | gpt-4o-mini |
| 2 | `ANTHROPIC_API_KEY` | claude-3-haiku-20240307 |
| 3 | Ollama running locally | ollama/llama3.2 |

Override with `--model`:

```bash
context-cli generate example.com --model gpt-4o
```

No API key is needed if you have Ollama running locally -- the compiler will use it as a fallback.

## Web Server Config Generation

Generate web server configuration snippets for routing `Accept: text/markdown` requests:

```bash
context-cli generate-config nginx
context-cli generate-config apache
context-cli generate-config caddy
```

See [serve-modes.md](serve-modes.md) for details on content negotiation and deployment.

## x402 Payment Config

Generate x402 payment signaling configuration for monetizing AI agent access:

```bash
context-cli generate-x402
```

This generates configuration for HTTP 402 responses and x402 headers that signal payment-gated access to AI agents.
