# CI Integration Guide

Context CLI integrates into CI/CD pipelines to catch LLM-readiness regressions before they reach production. Use it to enforce minimum scores, detect blocked AI bots, and generate lint reports as part of your build process.

## Quick Start

Add this to `.github/workflows/context-lint.yml`:

```yaml
name: Context Lint
on:
  push:
    branches: [main]
  pull_request:

jobs:
  context-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Context Lint
        uses: hanselhansel/context-cli@main
        with:
          url: 'https://your-site.com'
          fail-under: '60'
```

## CLI Flags for CI

| Flag | Description | Example |
|------|-------------|---------|
| `--fail-under N` | Exit 1 if overall score < N | `--fail-under 60` |
| `--fail-on-blocked-bots` | Exit 2 if any AI bot is blocked | `--fail-on-blocked-bots` |
| `--quiet` | Suppress output; exit 0 if score >= 50, else 1 | `--quiet` |
| `--json` | Machine-readable JSON output | `--json` |
| `--format FORMAT` | Output format: json, csv, markdown, or html | `--format markdown` |
| `--single` | Single-page lint (skip multi-page discovery) | `--single` |
| `--max-pages N` | Limit pages in multi-page mode (default: 10) | `--max-pages 5` |
| `--timeout N` | HTTP timeout in seconds (default: 15) | `--timeout 30` |
| `--bots LIST` | Custom AI bot list (comma-separated) | `--bots GPTBot,ClaudeBot` |
| `--save` | Save lint results to local history | `--save` |
| `--regression-threshold N` | Score drop threshold for regression (default: 5) | `--regression-threshold 10` |
| `--webhook URL` | POST results to webhook after lint | `--webhook https://hooks.slack.com/...` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Lint passed (score meets threshold) |
| 1 | Score below `--fail-under` threshold (or below 50 in `--quiet` mode) |
| 2 | AI bot blocked (when `--fail-on-blocked-bots` is set) |

## Configuration File

Create `.contextrc.yml` in your project root or home directory to set defaults:

```yaml
timeout: 30
max_pages: 5
save: true
verbose: false
bots:
  - GPTBot
  - ClaudeBot
  - PerplexityBot
format: json
regression_threshold: 10
```

CLI flags override config file values when explicitly set.

## Webhook Notifications

Send lint results to Slack, Discord, or any webhook URL:

```bash
context-cli lint https://your-site.com --webhook https://hooks.slack.com/services/...
```

The webhook receives a JSON payload with:
- `url`, `overall_score`, pillar scores
- `timestamp` (ISO 8601)
- `regression` flag (true if score dropped)

## Score History & Regression Detection

Track scores over time with `--save` and detect regressions:

```bash
# Save each lint to local history
context-cli lint https://your-site.com --save

# View history
context-cli history https://your-site.com

# Detect regression with custom threshold
context-cli lint https://your-site.com --save --regression-threshold 10
```

## Continuous Monitoring

Use the `watch` command for ongoing monitoring:

```bash
# Lint every hour, save results, alert via webhook
context-cli watch https://your-site.com \
  --interval 3600 \
  --save \
  --webhook https://hooks.slack.com/services/... \
  --fail-under 50
```

## GitHub Action

The `hanselhansel/context-cli` composite action wraps the CLI with convenient inputs and outputs.

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | -- | URL to lint |
| `fail-under` | No | -- | Fail if score is below this threshold (0-100) |
| `fail-on-blocked-bots` | No | `false` | Fail (exit 2) if any AI bot is blocked |
| `single-page` | No | `false` | Lint only the given URL (skip discovery) |
| `max-pages` | No | `10` | Maximum pages to lint in multi-page mode |
| `python-version` | No | `3.12` | Python version to use |

### Outputs

| Output | Description |
|--------|-------------|
| `score` | Overall LLM readiness score (0-100) |
| `report-json` | Full lint report as JSON |

### Using Outputs

Access the score and report in subsequent steps:

```yaml
steps:
  - name: Run Context Lint
    id: lint
    uses: hanselhansel/context-cli@main
    with:
      url: 'https://your-site.com'

  - name: Check score
    run: |
      echo "Score: ${{ steps.lint.outputs.score }}"
      if [ "${{ steps.lint.outputs.score }}" -lt 50 ]; then
        echo "::warning::LLM readiness score is below 50"
      fi
```

## GitHub Step Summary

When running in GitHub Actions, Context CLI automatically writes a summary to `$GITHUB_STEP_SUMMARY` if the environment variable is set. You can also generate markdown output:

```yaml
- name: Run Context Lint
  run: |
    context-cli lint https://your-site.com --format markdown >> $GITHUB_STEP_SUMMARY
```

## HTML Reports

Generate Lighthouse-style HTML reports:

```bash
context-cli lint https://your-site.com --format html
# Creates: context-report-your-site.com.html
```

The HTML report is self-contained (inline CSS, no external dependencies) and includes:
- Circular score gauge with color coding
- Per-pillar breakdown with detail sections
- Mobile-friendly responsive layout

## Examples

See the example workflows in [`.github/examples/`](../.github/examples/):

- **[context-lint.yml](../.github/examples/context-lint.yml)** -- Basic workflow with score threshold
- **[context-lint-preview.yml](../.github/examples/context-lint-preview.yml)** -- Lint Vercel/Netlify preview deploys
- **[context-lint-inline.yml](../.github/examples/context-lint-inline.yml)** -- Inline steps without the composite action

## Troubleshooting

### crawl4ai browser setup fails

The `crawl4ai-setup` command installs a headless Chromium browser for content analysis. If it fails:

- The action emits a `::warning::` and continues -- content density scoring may be limited
- Ensure `ubuntu-latest` is used (browser dependencies are pre-installed)
- If you only need robots.txt/llms.txt/schema checks, content analysis is optional

### Lint times out

Multi-page lints crawl up to `--max-pages` URLs. To speed things up:

- Use `--single` for single-page lints (fastest)
- Lower `--max-pages` (e.g., `--max-pages 3`)
- Increase `--timeout` for slow sites
- Set a workflow timeout: `timeout-minutes: 10`

### Rate limiting

Some sites rate-limit automated requests. If you see connection errors:

- Add a delay between CI runs (avoid running on every commit)
- Use `--single` to reduce request volume
- Consider linting only on `main` branch pushes, not every PR

### Score is 0

A score of 0 usually means the URL was unreachable or returned an error. Check:

- The URL is publicly accessible (not behind auth or VPN)
- The URL includes the protocol (`https://`)
- DNS resolves correctly from the CI runner
