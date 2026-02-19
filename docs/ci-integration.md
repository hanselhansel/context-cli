# CI Integration Guide

Context CLI integrates into CI/CD pipelines to catch LLM-readiness regressions before they reach production. Use it to enforce minimum scores, detect blocked AI bots, limit token waste, and generate lint reports as part of your build process.

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
        id: lint
        uses: hanselhansel/context-cli@main
        with:
          url: 'https://your-site.com'
          fail-under: '60'
          max-context-waste: '80'

      - name: Check results
        run: |
          echo "Score: ${{ steps.lint.outputs.score }}"
          echo "Token Waste: ${{ steps.lint.outputs.token-waste }}%"
```

## CLI Flags for CI

| Flag | Description | Example |
|------|-------------|---------|
| `--fail-under N` | Exit 1 if overall score < N | `--fail-under 60` |
| `--fail-on-blocked-bots` | Exit 2 if any AI bot is blocked | `--fail-on-blocked-bots` |
| `--max-context-waste N` | Fail if context waste percentage exceeds N (0-100) | `--max-context-waste 80` |
| `--require-llms-txt` | Fail if llms.txt is not present on the site | `--require-llms-txt` |
| `--require-bot-access` | Fail if any AI bots are blocked by robots.txt | `--require-bot-access` |
| `--robots-min N` | Fail if robots.txt pillar score < N (0-25) | `--robots-min 15` |
| `--schema-min N` | Fail if Schema.org pillar score < N (0-25) | `--schema-min 10` |
| `--content-min N` | Fail if content density pillar score < N (0-40) | `--content-min 20` |
| `--llms-min N` | Fail if llms.txt pillar score < N (0-10) | `--llms-min 5` |
| `--overall-min N` | Fail if overall score < N (0-100, alternative to --fail-under) | `--overall-min 60` |
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
| 2 | AI bot blocked (when `--fail-on-blocked-bots` or `--require-bot-access` is set) |
| 3 | Token waste exceeds `--max-context-waste` threshold |
| 4 | llms.txt missing (when `--require-llms-txt` is set) |

## Token Waste Thresholds

Token waste measures how much of a page's raw HTML is noise (boilerplate, tracking scripts, hidden elements) versus useful content that LLMs can consume. A high waste percentage means LLMs burn tokens on irrelevant markup.

### CLI Usage

```bash
# Fail if more than 80% of tokens are waste
context-cli lint https://your-site.com --max-context-waste 80

# Combine with score threshold
context-cli lint https://your-site.com --fail-under 60 --max-context-waste 80

# Require llms.txt presence (ensures LLM-specific content guidance exists)
context-cli lint https://your-site.com --require-llms-txt

# Require all AI bots have access via robots.txt
context-cli lint https://your-site.com --require-bot-access
```

### GitHub Action Usage

```yaml
- name: Run Context Lint
  uses: hanselhansel/context-cli@main
  with:
    url: 'https://your-site.com'
    fail-under: '60'
    max-context-waste: '80'
    require-llms-txt: 'true'
    require-bot-access: 'true'
```

### Interpreting Token Waste

| Waste % | Rating | Action |
|---------|--------|--------|
| 0-30% | Excellent | Content is clean and LLM-friendly |
| 30-50% | Good | Minor optimization opportunities |
| 50-70% | Fair | Consider reducing boilerplate/scripts |
| 70-100% | Poor | Significant noise; LLMs waste most tokens on irrelevant content |

### Accessing Token Waste in Workflows

The `token-waste` output provides the waste percentage for use in subsequent steps:

```yaml
- name: Run Context Lint
  id: lint
  uses: hanselhansel/context-cli@main
  with:
    url: 'https://your-site.com'
    max-context-waste: '80'

- name: Report token waste
  run: |
    echo "Token Waste: ${{ steps.lint.outputs.token-waste }}%"
    if [ "${{ steps.lint.outputs.token-waste }}" != "N/A" ]; then
      echo "::notice::Context waste is ${{ steps.lint.outputs.token-waste }}%"
    fi
```

## Per-Pillar Thresholds

Enforce minimum scores on individual pillars to catch regressions in specific areas:

```bash
# Enforce per-pillar minimums
context-cli lint https://your-site.com \
  --robots-min 15 \
  --schema-min 10 \
  --content-min 20 \
  --llms-min 5 \
  --overall-min 60
```

### GitHub Action Per-Pillar Inputs

```yaml
- name: Run Context Lint
  uses: hanselhansel/context-cli@main
  with:
    url: 'https://your-site.com'
    robots-min: '15'
    schema-min: '10'
    content-min: '20'
    llms-min: '5'
    overall-min: '60'
    max-context-waste: '80'
```

### Pillar Score Ranges

| Pillar | Flag | Max Score | Description |
|--------|------|-----------|-------------|
| Robots.txt | `--robots-min` | 25 | AI bot access via robots.txt |
| Schema.org | `--schema-min` | 25 | Structured data (JSON-LD) quality |
| Content | `--content-min` | 40 | Content density and readability |
| llms.txt | `--llms-min` | 10 | Presence and quality of llms.txt |
| Overall | `--overall-min` | 100 | Sum of all pillars |

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
- `token_waste_pct` (context waste percentage)
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

Baseline files can also track token waste over time. When using `--save-baseline`, the baseline JSON includes `context_waste_pct` so regressions in token efficiency are detected alongside score regressions.

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
| `baseline-file` | No | -- | Path to baseline JSON file for regression detection |
| `save-baseline` | No | -- | Path to save current scores as baseline JSON |
| `regression-threshold` | No | `5` | Minimum score drop to flag as regression |
| `robots-min` | No | -- | Minimum robots.txt pillar score (0-25) |
| `schema-min` | No | -- | Minimum Schema.org pillar score (0-25) |
| `content-min` | No | -- | Minimum content density pillar score (0-40) |
| `llms-min` | No | -- | Minimum llms.txt pillar score (0-10) |
| `overall-min` | No | -- | Minimum overall score (0-100) |
| `webhook-url` | No | -- | Webhook URL to POST results to |
| `max-context-waste` | No | -- | Maximum acceptable context waste % (0-100). Fail if exceeded. |
| `require-llms-txt` | No | `false` | Fail if llms.txt is not present on the site |
| `require-bot-access` | No | `false` | Fail if any AI bots are blocked by robots.txt |
| `python-version` | No | `3.12` | Python version to use |

### Outputs

| Output | Description |
|--------|-------------|
| `score` | Overall LLM readiness score (0-100) |
| `report-json` | Full lint report as JSON |
| `token-waste` | Context waste percentage from Token Waste analysis |

### Using Outputs

Access the score, token waste, and report in subsequent steps:

```yaml
steps:
  - name: Run Context Lint
    id: lint
    uses: hanselhansel/context-cli@main
    with:
      url: 'https://your-site.com'
      max-context-waste: '80'

  - name: Check score
    run: |
      echo "Score: ${{ steps.lint.outputs.score }}"
      echo "Token Waste: ${{ steps.lint.outputs.token-waste }}%"
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
- Token waste analysis with diagnostic codes
- Mobile-friendly responsive layout

## Examples

See the example workflows in [`.github/examples/`](../.github/examples/):

- **[context-lint.yml](../.github/examples/context-lint.yml)** -- Basic workflow with score threshold and token waste enforcement
- **[context-lint-preview.yml](../.github/examples/context-lint-preview.yml)** -- Lint Vercel/Netlify preview deploys with bot access requirements
- **[context-lint-inline.yml](../.github/examples/context-lint-inline.yml)** -- Inline steps with all Token Waste flags

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

### Token waste shows N/A

If the `token-waste` output shows `N/A`, it means:

- The crawl4ai browser failed to install (content analysis unavailable)
- The page could not be fetched or parsed
- The lint ran in a mode that skips content analysis

Check the `report-json` output for error details.
