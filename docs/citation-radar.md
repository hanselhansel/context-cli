# Citation Radar

Citation Radar queries AI models to discover what they cite and recommend for any search prompt. It helps you understand your brand's visibility in AI-generated responses.

## What It Does

Citation Radar sends a prompt to one or more LLM models, collects the responses, and analyzes them to extract:

- **Cited domains** -- which websites the model references or links to
- **Recommended brands** -- which brands or products the model mentions favorably
- **Domain classification** -- categorizes cited domains (e.g., official site, review site, news, social)
- **Brand tracking** -- tracks specific brands you care about across responses

## Usage

```bash
pip install context-linter[generate]
context-cli radar "best project management tools" --brand Asana --brand Monday --model gpt-4o-mini
```

### Options

| Flag | Description |
|---|---|
| `--brand` / `-b` | Brand name to track (repeatable) |
| `--model` / `-m` | LLM model to query (repeatable, default: `gpt-4o-mini`) |
| `--runs` / `-r` | Number of runs per model for statistical significance |
| `--json` | Output results as JSON |

## Supported Models

Citation Radar uses the same LLM provider infrastructure as the generate command. It auto-detects your provider from environment variables:

| Priority | Env Variable | Default Model |
|---|---|---|
| 1 | `OPENAI_API_KEY` | gpt-4o-mini |
| 2 | `ANTHROPIC_API_KEY` | claude-3-haiku-20240307 |
| 3 | Ollama running locally | ollama/llama3.2 |

Override with `--model`:

```bash
context-cli radar "best CRM software" --model gpt-4o --model claude-3-haiku-20240307
```

## Output

The default output is a Rich-formatted table showing:

- Each cited domain with frequency count
- Domain classification (official, review, news, etc.)
- Brand mention counts for tracked brands
- Citation share percentage per brand

### JSON Output

```bash
context-cli radar "best analytics tools" --brand Mixpanel --brand Amplitude --json
```

Returns structured JSON with full citation data, domain classifications, and brand tracking results.

## Use Cases

- **SEO/AEO monitoring** -- understand which domains AI models cite for your target keywords
- **Competitive analysis** -- compare your brand's AI visibility against competitors
- **Content strategy** -- identify which types of content (reviews, docs, blogs) get cited most
- **AI readiness validation** -- verify that improving your Context CLI score translates to better AI citations
