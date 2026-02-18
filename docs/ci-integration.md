# CI Integration Guide

AEO-CLI integrates into CI/CD pipelines to catch AI-readiness regressions before they reach production. Use it to enforce minimum AEO scores, detect blocked AI bots, and generate audit reports as part of your build process.

## Quick Start

Add this to `.github/workflows/aeo-audit.yml`:

```yaml
name: AEO Audit
on:
  push:
    branches: [main]
  pull_request:

jobs:
  aeo-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run AEO Audit
        uses: hanselhansel/aeo-cli@main
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
| `--format markdown` | Markdown output (ideal for step summaries) | `--format markdown` |
| `--single` | Single-page audit (skip multi-page discovery) | `--single` |
| `--max-pages N` | Limit pages in multi-page mode (default: 10) | `--max-pages 5` |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Audit passed (score meets threshold) |
| 1 | Score below `--fail-under` threshold (or below 50 in `--quiet` mode) |
| 2 | AI bot blocked (when `--fail-on-blocked-bots` is set) |

## GitHub Action

The `hanselhansel/aeo-cli` composite action wraps the CLI with convenient inputs and outputs.

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | — | URL to audit |
| `fail-under` | No | — | Fail if score is below this threshold (0-100) |
| `fail-on-blocked-bots` | No | `false` | Fail (exit 2) if any AI bot is blocked |
| `single-page` | No | `false` | Audit only the given URL (skip discovery) |
| `max-pages` | No | `10` | Maximum pages to audit in multi-page mode |
| `python-version` | No | `3.12` | Python version to use |

### Outputs

| Output | Description |
|--------|-------------|
| `score` | Overall AEO score (0-100) |
| `report-json` | Full audit report as JSON |

### Using Outputs

Access the score and report in subsequent steps:

```yaml
steps:
  - name: Run AEO Audit
    id: aeo
    uses: hanselhansel/aeo-cli@main
    with:
      url: 'https://your-site.com'

  - name: Check score
    run: |
      echo "AEO Score: ${{ steps.aeo.outputs.score }}"
      if [ "${{ steps.aeo.outputs.score }}" -lt 50 ]; then
        echo "::warning::AEO score is below 50"
      fi
```

## GitHub Step Summary

When `--fail-under` or `--fail-on-blocked-bots` flags are used in CI, the audit output is displayed directly in the GitHub Actions step log. For richer summaries, pipe markdown output to `$GITHUB_STEP_SUMMARY`:

```yaml
- name: Run AEO Audit
  run: |
    aeo-cli audit https://your-site.com --format markdown >> $GITHUB_STEP_SUMMARY
```

This renders the full audit report as a formatted table in the GitHub Actions summary tab.

## Examples

See the example workflows in [`.github/examples/`](../.github/examples/):

- **[aeo-audit.yml](../.github/examples/aeo-audit.yml)** — Basic workflow with score threshold
- **[aeo-audit-preview.yml](../.github/examples/aeo-audit-preview.yml)** — Audit Vercel/Netlify preview deploys
- **[aeo-audit-inline.yml](../.github/examples/aeo-audit-inline.yml)** — Inline steps without the composite action

## Troubleshooting

### crawl4ai browser setup fails

The `crawl4ai-setup` command installs a headless Chromium browser for content analysis. If it fails:

- The action emits a `::warning::` and continues — content density scoring may be limited
- Ensure `ubuntu-latest` is used (browser dependencies are pre-installed)
- If you only need robots.txt/llms.txt/schema checks, content analysis is optional

### Audit times out

Multi-page audits crawl up to `--max-pages` URLs. To speed things up:

- Use `--single` for single-page audits (fastest)
- Lower `--max-pages` (e.g., `--max-pages 3`)
- Set a workflow timeout: `timeout-minutes: 10`

### Rate limiting

Some sites rate-limit automated requests. If you see connection errors:

- Add a delay between CI runs (avoid running on every commit)
- Use `--single` to reduce request volume
- Consider auditing only on `main` branch pushes, not every PR

### Score is 0

A score of 0 usually means the URL was unreachable or returned an error. Check:

- The URL is publicly accessible (not behind auth or VPN)
- The URL includes the protocol (`https://`)
- DNS resolves correctly from the CI runner
