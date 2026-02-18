# AEO Scoring Methodology

AEO-CLI scores URLs on a 0-100 scale across four pillars. Each pillar measures a distinct aspect of AI crawler readiness.

## Score Overview

| Pillar | Max Points | Weight | What it measures |
|---|---|---|---|
| Content Density | 40 | Highest | Quality and structure of extractable text |
| Robots.txt AI Bot Access | 25 | High | Whether AI crawlers are permitted |
| Schema.org JSON-LD | 25 | High | Structured data markup for entity understanding |
| llms.txt Presence | 10 | Low | Emerging standard for LLM-specific instructions |

**Overall AEO Score** = Content + Robots + Schema + llms.txt (max 100)

## Pillar 1: Content Density (max 40 points)

Content density is weighted highest because it's what LLMs actually extract and cite when answering questions. AEO-CLI converts the page to markdown using a headless browser (crawl4ai), then scores based on word count and structural elements.

### Word Count Tiers

| Word Count | Base Points |
|---|---|
| 1,500+ | 25 |
| 800-1,499 | 20 |
| 400-799 | 15 |
| 150-399 | 8 |
| < 150 | 0 |

### Structure Bonuses

Structure bonuses reward content that is well-organized and easy for LLMs to extract:

| Feature | Bonus | Why it matters |
|---|---|---|
| Headings (`#`, `##`, etc.) | +7 | Headings help LLMs identify topic structure |
| Lists (bullet/numbered) | +5 | Lists are highly extractable by LLMs |
| Code blocks (`` ``` ``) | +3 | Valuable for technical content citations |

The total content score is capped at 40. For example, a page with 1,500+ words, headings, lists, and code blocks scores: min(40, 25 + 7 + 5 + 3) = **40**.

## Pillar 2: Robots.txt AI Bot Access (max 25 points)

Robots.txt is the gatekeeper — if an AI bot is blocked, it cannot crawl the site at all. The score is proportional to the number of AI bots allowed.

### Formula

```
robots_score = 25 * (allowed_bots / total_bots)
```

### AI Bots Checked (7 total)

| Bot | Operator |
|---|---|
| GPTBot | OpenAI |
| ChatGPT-User | OpenAI |
| OAI-SearchBot | OpenAI |
| Google-Extended | Google |
| ClaudeBot | Anthropic |
| PerplexityBot | Perplexity |
| Amazonbot | Amazon |

### Examples

- All 7 bots allowed: `25 * 7/7 = 25.0`
- 5 of 7 allowed: `25 * 5/7 = 17.9`
- All blocked: `0`
- No robots.txt found: `0` (treated as inaccessible)

## Pillar 3: Schema.org JSON-LD (max 25 points)

Structured data provides "cheat sheets" that help AI understand page entities (products, articles, organizations, FAQs). AEO-CLI extracts all `<script type="application/ld+json">` blocks from the HTML.

### Formula

```
schema_score = min(25, 8 + 5 * unique_types)
```

- **Base 8 points** for having any JSON-LD at all
- **+5 points** per unique `@type` found (e.g., Organization, Article, Product)
- **Capped at 25**

### Examples

| JSON-LD Blocks | Unique @types | Score |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 1 (Organization) | 13 |
| 2 | 2 (Organization, WebSite) | 18 |
| 3 | 3 (Organization, WebSite, Article) | 23 |
| 4+ | 4+ | 25 (capped) |

## Pillar 4: llms.txt Presence (max 10 points)

[llms.txt](https://llmstxt.org/) is an emerging standard for providing LLM-specific instructions about a site. AEO-CLI checks two locations:

1. `/llms.txt`
2. `/.well-known/llms.txt`

### Scoring

- **10 points** if found at either location (non-empty response with HTTP 200)
- **0 points** if not found

This pillar is weighted lowest because no major AI search engine heavily weights llms.txt yet, but it signals forward-thinking AI readiness.

## Multi-Page Site Audits

When auditing multiple pages across a site, AEO-CLI uses **depth-weighted score aggregation**. Not all pages are created equal — the homepage and top-level sections are more representative of a site's AEO readiness than deep nested pages.

### Depth Weights

| URL Depth | Weight | Examples |
|---|---|---|
| 0-1 segments | 3 | `/`, `/about`, `/blog` |
| 2 segments | 2 | `/blog/my-post`, `/products/widget` |
| 3+ segments | 1 | `/blog/2024/01/my-post` |

### How Aggregation Works

**Site-wide pillars** (Robots.txt and llms.txt) are computed once for the entire domain — they don't vary by page.

**Per-page pillars** (Content Density and Schema.org) are scored individually for each page, then combined using a weighted average:

```
weighted_avg = sum(score_i * weight_i) / sum(weight_i)
```

For example, with 3 pages:
- Homepage (`/`, depth 0, weight 3): content score 35
- Blog index (`/blog`, depth 1, weight 3): content score 28
- Blog post (`/blog/my-post`, depth 2, weight 2): content score 32

```
weighted_content = (35*3 + 28*3 + 32*2) / (3 + 3 + 2) = 253 / 8 = 31.6
```

### Page Discovery

AEO-CLI discovers pages using a two-tier strategy:

1. **Sitemap-first**: Fetches `/sitemap.xml` (and sitemap indexes), collecting up to 500 URLs
2. **Spider fallback**: If no sitemap is found, uses internal links extracted from the seed page crawl

Discovered URLs are:
- Filtered through robots.txt (GPTBot user-agent)
- Deduplicated and normalized
- Sampled diversely across path segments (round-robin across `/blog/*`, `/products/*`, etc.)
- Capped at `--max-pages` (default 10)

The seed URL is always included in the audit.
