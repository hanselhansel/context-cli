# Context CLI Scoring Methodology

Context CLI scores URLs on a 0-100 scale across four pillars. Each pillar measures a distinct aspect of LLM readiness -- how well a page is structured for token-efficient extraction by AI crawlers and RAG pipelines.

## Score Overview

| Pillar | Max Points | Weight | What it measures |
|---|---|---|---|
| Content Density | 40 | Highest | Quality and structure of extractable text |
| Robots.txt AI Bot Access | 25 | High | Whether AI crawlers are permitted |
| Schema.org JSON-LD | 25 | High | Structured data markup for entity understanding |
| llms.txt Presence | 10 | Low | Emerging standard for LLM-specific instructions |

**Overall Score** = Content + Robots + Schema + llms.txt (max 100)

## Pillar 1: Content Density (max 40 points)

Content density is weighted highest because it's what LLMs actually extract and cite when answering questions. Context CLI converts the page to markdown using a headless browser (crawl4ai), then scores based on word count and structural elements.

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

### Content Sub-Signals (Informational)

In addition to scoring, Context CLI analyzes content quality signals reported in verbose output:

| Signal | What it checks | Research basis |
|---|---|---|
| **Readability** | Flesch-Kincaid grade level (8th-10th grade optimal) | AI citations correlate with readable content |
| **Heading structure** | H1-H6 hierarchy, one topic per heading | 40% more citations with proper headings |
| **Answer-first pattern** | Core answer in first sentence of each section | 44.2% of citations come from first 30% of text |
| **Chunk sizing** | Self-contained 50-150 word chunks | 2.3x more citations for properly chunked content |
| **Statistics density** | Numbers, percentages, data points | +20-30% visibility from statistical content |
| **Citation readiness** | Quotes, references, source mentions | +30-40% visibility from cited sources |
| **FAQ patterns** | Question-answer structures | FAQPage schema drives 60% more AI Overview inclusion |

## Pillar 2: Robots.txt AI Bot Access (max 25 points)

Robots.txt is the gatekeeper -- if an AI bot is blocked, it cannot crawl the site at all. The score is proportional to the number of AI bots allowed.

### Formula

```
robots_score = 25 * (allowed_bots / total_bots)
```

### AI Bots Checked (13 total)

| Bot | Operator |
|---|---|
| GPTBot | OpenAI |
| ChatGPT-User | OpenAI |
| OAI-SearchBot | OpenAI |
| Google-Extended | Google |
| ClaudeBot | Anthropic |
| PerplexityBot | Perplexity |
| Amazonbot | Amazon |
| DeepSeek-AI | DeepSeek |
| Grok | xAI |
| Meta-ExternalAgent | Meta |
| cohere-ai | Cohere |
| AI2Bot | Allen Institute for AI |
| ByteSpider | ByteDance/TikTok |

### Examples

- All 13 bots allowed: `25 * 13/13 = 25.0`
- 10 of 13 allowed: `25 * 10/13 = 19.2`
- All blocked: `0`
- No robots.txt found: `0` (treated as inaccessible)

### Informational Signals (not scored)

- **RSL (Really Simple Licensing)**: Detects `/license.xml` for AI crawl licensing terms
- **IETF Content-Usage header**: Checks for emerging `Content-Usage` HTTP header from IETF aipref Working Group
- **Crawl-delay directives**: Reports any crawl-delay settings in robots.txt
- **Sitemap presence**: Whether robots.txt references a sitemap

## Pillar 3: Schema.org JSON-LD (max 25 points)

Structured data provides "cheat sheets" that help AI understand page entities (products, articles, organizations, FAQs). Context CLI extracts all `<script type="application/ld+json">` blocks from the HTML.

### Formula (with type weighting)

```
schema_score = min(25, 8 + 5 * high_value_types + 3 * standard_types)
```

- **Base 8 points** for having any JSON-LD at all
- **+5 points** per high-value `@type` (see table below)
- **+3 points** per standard `@type`
- **Capped at 25**

### High-Value Schema Types (+5 each)

| Type | Why it's high-value |
|---|---|
| `FAQPage` | 60% more AI Overview inclusion |
| `HowTo` | Step-by-step content highly extractable by AI |
| `Article` | Core content type for AI citation |
| `Product` | Key for shopping AI (ChatGPT Shopping, Amazon Rufus) |
| `Recipe` | Structured recipes frequently cited by AI |

All other types (Organization, WebSite, BreadcrumbList, etc.) are worth +3 points each.

### Examples

| JSON-LD Blocks | Types Found | Score |
|---|---|---|
| 0 | 0 | 0 |
| 1 | 1 (Organization) | 11 (8 + 3) |
| 2 | 2 (Organization, FAQPage) | 16 (8 + 5 + 3) |
| 3 | 3 (Article, FAQPage, HowTo) | 23 (8 + 5 + 5 + 5) |
| 4+ | 4+ | 25 (capped) |

## Pillar 4: llms.txt Presence (max 10 points)

[llms.txt](https://llmstxt.org/) is an emerging standard for providing LLM-specific instructions about a site. Context CLI checks three locations:

1. `/llms.txt`
2. `/.well-known/llms.txt`
3. `/llms-full.txt` (companion file with complete docs)

### Scoring

- **10 points** if `llms.txt` or `llms-full.txt` found at any location (non-empty HTTP 200)
- **0 points** if not found

This pillar is weighted lowest because no major AI search engine heavily weights llms.txt yet, but it signals forward-thinking AI readiness.

## Informational Signals (not scored)

Context CLI detects additional quality signals reported in verbose mode but not included in the 0-100 score:

### E-E-A-T Signals

| Signal | What it checks |
|---|---|
| Authorship | Author name, bio, structured author data |
| Publication dates | Published/modified dates on content |
| About/Contact links | Links to about page, contact page |
| External citations | Links to authoritative external sources |
| Trust signals | Privacy policy, terms of service, credentials |

### RSL (Really Simple Licensing)

Detects `/license.xml` for AI crawl licensing and royalty terms per the RSL 1.0 standard (Dec 2025).

### IETF Content-Usage Header

Checks for the `Content-Usage` HTTP header from the IETF aipref Working Group.

## Multi-Page Site Lints

When linting multiple pages across a site, Context CLI uses **depth-weighted score aggregation**. Not all pages are created equal -- the homepage and top-level sections are more representative of a site's LLM readiness than deep nested pages.

### Depth Weights

| URL Depth | Weight | Examples |
|---|---|---|
| 0-1 segments | 3 | `/`, `/about`, `/blog` |
| 2 segments | 2 | `/blog/my-post`, `/products/widget` |
| 3+ segments | 1 | `/blog/2024/01/my-post` |

### How Aggregation Works

**Site-wide pillars** (Robots.txt and llms.txt) are computed once for the entire domain -- they don't vary by page.

**Per-page pillars** (Content Density and Schema.org) are scored individually for each page, then combined using a weighted average:

```
weighted_avg = sum(score_i * weight_i) / sum(weight_i)
```

### Page Discovery

Context CLI discovers pages using a two-tier strategy:

1. **Sitemap-first**: Fetches `/sitemap.xml` (and sitemap indexes), collecting up to 500 URLs
2. **Spider fallback**: If no sitemap is found, uses internal links extracted from the seed page crawl

Discovered URLs are:
- Filtered through robots.txt (GPTBot user-agent)
- Deduplicated and normalized
- Sampled diversely across path segments (round-robin across `/blog/*`, `/products/*`, etc.)
- Capped at `--max-pages` (default 10)

The seed URL is always included in the lint.
