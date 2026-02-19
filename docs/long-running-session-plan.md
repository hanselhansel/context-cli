# AEO-CLI Long-Running Session Plan

> A comprehensive, multi-day Claude Code development plan for evolving aeo-cli into the
> definitive open-source AEO toolkit — grounded in market research, validated by continuous
> testing, and protected against hallucination drift.

**Generated**: 2026-02-19
**Branch**: `claude/aeo-research-planning-9sZcI`

---

## Table of Contents

1. [Market Intelligence Summary](#1-market-intelligence-summary)
2. [Research & Trends Shaping AEO](#2-research--trends-shaping-aeo)
3. [Current State of aeo-cli](#3-current-state-of-aeo-cli)
4. [Strategic Roadmap (Feature Phases)](#4-strategic-roadmap-feature-phases)
5. [Long-Running Session Architecture](#5-long-running-session-architecture)
6. [Anti-Hallucination Framework](#6-anti-hallucination-framework)
7. [Hooks Configuration](#7-hooks-configuration)
8. [Workflow Cadence & Checkpoints](#8-workflow-cadence--checkpoints)
9. [Appendix: Competitive Landscape Detail](#9-appendix-competitive-landscape-detail)

---

## 1. Market Intelligence Summary

### The AEO Market in 2026

The AEO/GEO space has exploded into a **$200M+ funded category with 24+ platforms**. Terminology remains fragmented (AEO, GEO, LLMO, AI SEO, AIO, AIEO), but the core mission is universal: optimize content so AI search engines cite your brand.

**Key market signals:**
- **World Economic Forum** featured AEO at its Annual Meeting 2026
- **97% of CMOs** reported positive AEO impact in 2025; **94% plan to increase investment** in 2026
- AI traffic to retail sites increased **1,100% YoY** (Adobe, Sept 2025)
- Gartner predicts **25% drop in traditional search volume by 2026**
- Agentic AI market projected to reach **$45B by 2030** (from $8.5B in 2026)

### Venture-Backed Leaders

| Company | Funding | Differentiator |
|---------|---------|---------------|
| **Profound** | $58.5M (Sequoia) | Market leader. 400M+ real user prompts, 10+ AI engine tracking |
| **Adobe LLM Optimizer** | Adobe Cloud | Edge-layer AI content delivery, MCP/A2A support |
| **Scrunch AI** | $26M | Agent Experience Platform — parallel AI-ready site version |
| **Bluefish AI** | $24M (NEA/Salesforce) | Verified data feeds to LLM providers |
| **Peec AI** | $29M | Berlin-based, 1,500+ marketing teams, from $105/mo |
| **Evertune** | $19M+ (Felicis) | 1M+ prompts/brand/month monitoring |

### Where aeo-cli is Unique

**No other tool in the market offers this combination:**
1. **CLI-first** — the only command-line AEO audit tool
2. **Developer-focused** — market is dominated by marketer-facing SaaS
3. **Open-source** — only GetCito and LLM Brand Tracker are OSS (neither has same scope)
4. **MCP server** — only Adobe and Schema App mention MCP among commercial tools
5. **Four-pillar scoring** — structured, reproducible, CI-integrable
6. **No signup required** — zero-friction developer experience

### Closest Competitors by Functionality

| Tool | Type | Score? | robots.txt? | llms.txt? | Schema? | CLI? | OSS? |
|------|------|--------|------------|-----------|---------|------|------|
| **aeo-cli** | CLI + MCP | 0-100 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Delante AI Audit | Web | 0-100 | ✅ | ✅ | ✅ | ❌ | ❌ |
| FastAEOCheck | Web | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| LLMAudit.ai | Web | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Drupal AEO | CMS plugin | 0-100 | ✅ | ❌ | ✅ | ❌ | ✅ |
| AEO Chrome Ext | Browser | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## 2. Research & Trends Shaping AEO

### 2.1 Generative Engine Optimization (GEO) — Academic Research

The landmark paper **"GEO: Generative Engine Optimization"** (Georgia Tech, Princeton, IIT Delhi, Allen Institute) introduced systematic study of how to optimize content for AI-generated responses.

**Key findings relevant to aeo-cli:**
- **Cite Sources** boost: +30-40% visibility in generative engines
- **Statistics inclusion**: +20-30% improvement
- **Quotations from authoritative sources**: +15-25%
- **Fluency optimization**: +5-10%
- **Technical terms and jargon**: +10-15% for specialized queries
- Content structure matters more than keyword density for AI engines

**Implication for aeo-cli**: Consider adding "citation readiness" and "statistical density" as sub-signals within the Content Density pillar.

### 2.2 The llms.txt Standard — Reality Check

- **Proposed**: September 2024 by Jeremy Howard (Answer.AI / fast.ai)
- **Adoption claims vary wildly**: NerdyData says 951 domains; BuiltWith says 844K+; Majestic Million found only 105 (May 2025)
- **Major adopters**: Anthropic, Stripe, Cloudflare, Zapier, Vercel, Coinbase, Svelte
- **Companion**: `llms-full.txt` — complete docs in single Markdown file

**CRITICAL FINDING — No confirmed AI usage:**
- Google's John Mueller (mid-2025): "No AI system currently uses llms.txt"
- Semrush server log analysis: **Zero visits** from GPTBot, PerplexityBot, or ClaudeBot to llms.txt files (Aug-Oct 2025)
- ALLMO.ai analysis of 94K+ cited URLs: **No measurable citation uplift** from llms.txt
- 8 out of 9 sites saw **no traffic change** after implementation
- Only 1 out of 50 most-cited domains in AI search has `/llms.txt` (Target.com)
- Not a single top-1,000 website has implemented it

**Where it does have value**: Developer documentation, agent workflows (Google A2A references it), API-heavy SaaS products.

**Implication for aeo-cli**: The 10-point weight is **appropriately calibrated** (not too high). Consider also checking for `llms-full.txt`. Do NOT increase the weight — the data does not support it.

### 2.3 How LLMs Actually Cite Sources — Research Data

**SourceCheckup (Nature Communications, April 2025):**
- **50-90% of LLM responses** are not fully supported by the sources they cite
- Even GPT-4o with Web Search: ~30% of statements are unsupported
- Evaluated 7 LLMs on 800 questions, 58,000 statement-source pairs

**2025 AI Visibility Report (680M+ citations analyzed):**
- **Brand search volume** (not backlinks) is the strongest citation predictor (0.334 correlation)
- Sources with **self-contained chunks of 50-150 words** receive **2.3x more citations**
- **65% of AI bot traffic** targets content published within the past year
- **44.2% of all LLM citations** come from the first 30% of text (intro matters most)
- Only **12% of URLs cited** by ChatGPT/Perplexity/Copilot rank in Google's top 10
- **80% of cited URLs don't rank in Google's top 100** — AI citation ≠ SEO ranking

**Content architecture for citation:**
- **Self-contained chunks of 134-167 words** are optimal for Google AI Overviews extraction
- Proper hierarchical headings (H2/H3/H4) → **40% more citations**
- Evidence-backed content with statistics → **28% higher AI inclusion**
- **Answer-first structure**: Core answer must appear in first sentence of each section
- Recommended reading level: **8th-10th grade**
- One topic per heading (multi-topic sections get treated as single chunk by LLMs)

**Implication for aeo-cli**: Content Density pillar should evolve to check chunk sizing, answer-first patterns, readability grade, and heading structure — not just word count.

### 2.4 AI Crawler Ecosystem — What's Changing

- **21% of top 1,000 websites** now have robots.txt rules for GPTBot
- **560,000+ sites** have rules for ChatGPT, Claude, and other AI bots
- Non-human traffic reached **~40% of visits** to the average website in 2025
- **Cloudflare** now blocks AI crawlers by default (since Jul 2025) with AI Crawl Control
- **HTTP 402 (Payment Required)** emerging as monetization mechanism for AI crawl access

**The compliance problem (Duke University, May 2025):**
- Many AI bots **never check robots.txt at all**
- Compliance **drops as rules become stricter**
- Courts ruled robots.txt is NOT enforceable under DMCA (Ziff Davis v. OpenAI, 2025)

**Really Simple Licensing (RSL) — New Standard (Dec 2025):**
- Launched by RSS co-creator Eckart Walther and former Ask.com CEO Doug Leeds
- Augments robots.txt with `/license.xml` for licensing and royalty terms
- Supports: free, attribution, subscription, **pay-per-crawl**, **pay-per-inference**
- RSL 1.0 is now an **official industry standard** (Dec 2025)
- Supporters: Reddit, Medium, Yahoo, Quora, Stack Overflow, Cloudflare, Akamai, Fastly, AP

**IETF AI Preferences Working Group (aipref) — In Progress:**
- Launched January 2025, creating standardized AI content preference rules
- Key deliverables: AI Usage Preferences Vocabulary, `Content-Usage` HTTP header, robots.txt extensions
- Co-chaired by Mark Nottingham, with Google's Gary Illyes participating

**New AI bots to consider adding to aeo-cli:**
- DeepSeek-AI
- Grok/xAI crawler
- Meta AI crawler
- Cohere crawler
- AI2Bot (Allen Institute)
- ByteSpider (ByteDance/TikTok)

### 2.5 Schema.org & Structured Data for AI

- GPT-4 accuracy jumps from **16% to 54%** correct responses when content relies on structured data (Data World)
- Structured data increases AI citations by **44%** (2025)
- Pages with proper schema are **3x more likely** to earn AI citations
- Schema drives **20-40% higher CTR** through rich snippets
- Brands with comprehensive schema see **57% more AI Overview triggers** on long-tail queries
- **Schema App** launched MCP Server to expose structured data directly to AI assistants
- **Wells Fargo** case study: resolved Google AI Overview hallucinations using proper schema
- **WordLift** offers "Agentic AI Audit" evaluating AI-readiness of structured data
- Schema.org types most impactful for AI: `FAQPage`, `HowTo`, `Article`, `Product`, `Organization`
- Google's John Mueller confirmed schema types "come and go" but JSON-LD remains preferred format

**Implication for aeo-cli**: Schema pillar at 25 points is well-validated. Consider weighting specific schema types differently (FAQ/HowTo worth more than generic Organization).

### 2.6 Content Optimization for AI Engines

Research on how Google AI Overviews, Perplexity, and ChatGPT select content:
- **Direct answers** to questions are prioritized
- **Lists and tables** are extracted more frequently
- **FAQ markup** significantly increases AI Overview inclusion
- **E-E-A-T signals** (authorship, expertise indicators) influence AI citation
- **Freshness** matters — recently updated content preferred
- **Readability** (Flesch-Kincaid) correlates with AI citation likelihood

### 2.7 MCP (Model Context Protocol) & AI Agent Access

- MCP is becoming the standard protocol for AI tool integration
- **Adobe LLM Optimizer** supports both MCP and A2A (Agent-to-Agent) protocols
- **Schema App's MCP Server** exposes knowledge graphs to AI assistants
- **LangChain mcpdoc** serves llms.txt to IDEs via MCP

**Implication for aeo-cli**: Our MCP server is ahead of the curve. Consider expanding MCP tools beyond `audit()` and `generate()`.

### 2.8 Emerging Protocols & Standards

| Protocol/Standard | Origin | Status | What It Does |
|-------------------|--------|--------|--------------|
| **MCP** | Anthropic → Linux Foundation | Production | Connect agents to data/tools (JSON-RPC) |
| **A2A** | Google → Linux Foundation | v0.3 (150+ orgs) | Agent-to-agent collaboration (HTTP/SSE) |
| **WebMCP** | Google+Microsoft / W3C | Early preview (Feb 2026) | Agent-to-browser interaction (postMessage) |
| **RSL** | RSL Collective | Standard (Dec 2025) | Content licensing for AI (pay-per-crawl) |
| **IETF AI Preferences** | IETF aipref WG | Draft | Content-Usage HTTP headers, robots.txt extensions |
| **TDMRep** | W3C | Community Group | Text/data mining rights (EU DSM Directive) |
| **agents.txt** | Community | Emerging | AI agent identity + interaction rules for e-commerce |

### 2.9 Emerging Concepts

| Concept | Description | Relevance |
|---------|-------------|-----------|
| **Agent Experience (AX)** | Designing for AI agent UX, not just human UX | New pillar candidate |
| **AI-Ready Content Delivery** | Serving different content to AI vs humans (Adobe, Scrunch) | Future feature |
| **Agentic Commerce** | AI shopping agents — Gartner: 90% B2B buying AI-mediated by 2028 | Growing fast |
| **Content Fingerprinting** | Tracking AI citation attribution | Monitoring feature |
| **Really Simple Licensing** | Publisher monetization of AI crawl access | New check candidate |
| **Chunk Relevance** | Self-contained 50-150 word chunks get 2.3x more citations | Content scoring |

### 2.10 Research Validation of aeo-cli Scoring Pillars

| aeo-cli Pillar | Weight | Research Validation | Evolution Path |
|---------------|--------|---------------------|----------------|
| Content Density | 40 pts | **Strongly validated** — chunk clarity, LLM readability, content depth are #1 factor | Add chunk sizing, answer-first detection, readability grade, heading structure |
| Robots.txt AI Bot Access | 25 pts | **Validated as gatekeeper** — but compliance is unreliable | Add RSL check, IETF Content-Usage header detection |
| Schema.org JSON-LD | 25 pts | **Strongly validated** — 3x citation likelihood, 44% citation increase | Add entity density, type weighting (FAQ/HowTo > generic) |
| llms.txt Presence | 10 pts | **Low impact confirmed** — zero measurable citation uplift | Weight appropriately low; add `llms-full.txt` check |

---

## 3. Current State of aeo-cli

### Metrics

| Metric | Value |
|--------|-------|
| Version | 0.2.1 |
| Python LOC (src) | ~1,800 |
| Python LOC (tests) | ~5,300 |
| Test cases | 308 |
| Code coverage | 100% |
| CLI commands | 3 (audit, generate, mcp) |
| MCP tools | 2 (audit, generate) |
| Output formats | 5 (Rich, JSON, CSV, Markdown, GitHub Summary) |
| AI bots checked | 7 |

### Architecture Strengths
- Clean async-first design
- Pydantic v2 models with MCP schema propagation
- 100% test coverage with edge case tests
- CI/CD with GitHub Actions (3-version matrix)
- GitHub Action for CI integration

### Identified Gaps & Opportunities

**High-Value:**
1. Batch mode (`--file urls.csv`)
2. Results persistence (SQLite history)
3. Custom scoring profiles (YAML config)
4. Additional AI bots (DeepSeek, Grok, ByteSpider, etc.)
5. `llms-full.txt` checking
6. Schema type weighting (FAQ/HowTo worth more)
7. Readability scoring (Flesch-Kincaid as content sub-signal)
8. Citation readiness analysis (statistics, quotes, direct answers)

**Medium-Value:**
9. Comparative analysis (`aeo-cli compare url1 url2`)
10. Score history & regression tracking
11. Webhook notifications (Slack, Discord)
12. PDF/HTML report export
13. Performance metrics (page load time)
14. Custom bot profiles via CLI flag

**Infrastructure:**
15. Structured logging (JSON logs)
16. Configurable timeouts
17. Cross-run caching (persistent robots.txt cache)
18. Plugin architecture for custom pillars

---

## 4. Strategic Roadmap (Feature Phases)

### Phase 1: Strengthen the Core (Days 1-3)

**Goal**: Make the existing 4 pillars best-in-class based on research findings.

| # | Task | Research Basis | Priority | Complexity |
|---|------|----------------|----------|------------|
| 1 | Add new AI bots (DeepSeek, Grok, ByteSpider, Meta AI, AI2Bot, Cohere) | 560K+ sites now manage AI bots; market expects comprehensive coverage | High | Low |
| 2 | Check `llms-full.txt` alongside `llms.txt` | Part of the llms.txt spec; Anthropic + Vercel use it | High | Low |
| 3 | Schema type weighting (FAQ/HowTo/Article > generic Organization) | FAQ schema → 60% more AI Overview inclusion; 3x citation likelihood | High | Medium |
| 4 | Content chunk analysis (50-150 word self-contained chunks) | 2.3x more citations for properly chunked content | High | Medium |
| 5 | Readability scoring (Flesch-Kincaid grade level) | 8th-10th grade optimal for AI citation; Delante already checks this | High | Medium |
| 6 | Heading structure analysis (one topic per heading, proper H2/H3/H4 hierarchy) | 40% more citations with proper hierarchical organization | High | Medium |
| 7 | Answer-first pattern detection | 44.2% of citations come from first 30% of text | Medium | Medium |
| 8 | Batch mode: `--file urls.csv` or `--file urls.txt` | No competitor offers batch CLI auditing | High | Medium |
| 9 | Configurable crawl4ai timeout via `--timeout` flag | Quality-of-life improvement | Medium | Low |
| 10 | Custom bot list via `--bots` flag or config file | Enterprise need | Medium | Low |

### Phase 2: Intelligence Layer (Days 3-5)

**Goal**: Move beyond basic auditing to actionable intelligence.

| # | Task | Research Basis | Priority | Complexity |
|---|------|----------------|----------|------------|
| 11 | Citation readiness score (statistics density, quote density, FAQ patterns) | GEO paper: +30-40% visibility from citations, +20-30% from statistics | High | Medium |
| 12 | Comparative analysis: `aeo-cli compare url1 url2` | Unique feature — no competitor offers CLI comparison | High | Medium |
| 13 | Score history with SQLite persistence | Monthly citation monitoring recommended; enables regression detection | High | Medium |
| 14 | Recommendation engine ("Add FAQ schema to boost +8 points") | Scrunch, Goodie, and Profound all offer recommendations | High | High |
| 15 | RSL (Really Simple Licensing) detection (`/license.xml`) | Official standard since Dec 2025; Reddit, Medium, Cloudflare support it | Medium | Low |
| 16 | IETF Content-Usage header detection | Coming standard from IETF aipref WG | Medium | Low |
| 17 | Regression detection (score dropped since last audit) | Quarterly audit cadence now recommended | Medium | Medium |
| 18 | E-E-A-T signal detection (authorship, expertise markers) | 96% of AI Overview citations come from E-E-A-T content | Medium | Medium |

### Phase 3: Ecosystem Expansion (Days 5-7)

**Goal**: Make aeo-cli the hub of AEO workflows.

| # | Task | Research Basis | Priority | Complexity |
|---|------|----------------|----------|------------|
| 19 | Configuration file support (`.aeorc.yml`) | Custom scoring profiles needed for enterprise | High | Medium |
| 20 | MCP tool expansion (compare, history, recommend) | Adobe + Schema App both expanding MCP; stay ahead | High | Medium |
| 21 | Plugin architecture for custom pillars | Enables community-driven pillar development | High | High |
| 22 | Webhook notifications (Slack, Discord, custom URL) | Monitoring cadence requires automated alerting | Medium | Medium |
| 23 | HTML report export (Lighthouse-style) | Profound/Goodie provide visual reports; CLI needs parity | Medium | High |
| 24 | `aeo-cli watch` — continuous monitoring mode | 65% of AI bot traffic targets recent content; freshness matters | Medium | Medium |

### Phase 4: Polish & Ship (Days 7-8)

**Goal**: Production-ready release.

| Task | Priority | Est. Complexity |
|------|----------|----------------|
| Documentation updates (scoring.md, new features) | High | Low |
| CHANGELOG entries | High | Low |
| Version bump to 0.3.0 | High | Low |
| Performance benchmarking | Medium | Medium |
| Docker image | Low | Low |

---

## 5. Long-Running Session Architecture

### Session Structure (Not One Giant Session)

**DO NOT** run a single session for days. Instead, use a **daily session cadence**:

```
Day 1 Session: Plan + Phase 1a
    ↓ commit, push, /clear or new session
Day 2 Session: Phase 1b + Phase 2a
    ↓ commit, push, /clear or new session
Day 3 Session: Phase 2b + Phase 3a
    ↓ commit, push, /clear or new session
...
```

### Why Daily Resets?

1. **Context window degradation**: After ~200K tokens of conversation, auto-compaction starts losing nuance
2. **Hallucination drift**: Without grounding reset, Claude may start referencing code that was refactored 3 hours ago
3. **CLAUDE.md re-injection**: Fresh sessions re-read CLAUDE.md, restoring full project context
4. **Git as checkpoint**: Each day's work is committed, providing rollback points

### Session Lifecycle

```
┌─────────────────────────────────────────────┐
│  SESSION START                              │
│  • CLAUDE.md loaded (project rules)         │
│  • .claude/rules/*.md loaded (topic rules)  │
│  • Auto-memory loaded (past learnings)      │
│  • SessionStart hook runs setup scripts     │
│  • Todo list from previous day reviewed     │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  DEVELOPMENT LOOP (repeat per feature)      │
│  1. Read relevant source files              │
│  2. Implement changes                       │
│  3. PostToolUse hook → auto-lint (ruff)     │
│  4. Write/update tests                      │
│  5. Run pytest (manually or via hook)       │
│  6. Fix failures                            │
│  7. Commit when green                       │
│  8. Check /context — compact if >70%        │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│  SESSION END                                │
│  • Stop hook → verify tests pass            │
│  • Stop hook → verify git status clean      │
│  • Push to branch                           │
│  • Write progress summary to todo/notes     │
└─────────────────────────────────────────────┘
```

### Context Management Strategy

| Trigger | Action |
|---------|--------|
| Context >60% full | Use subagents for exploration tasks |
| Context >70% full | `/compact focus on [current feature]` |
| Switching features | `/clear` if features are unrelated |
| After large refactor | New session with `claude --continue` |
| Every 2 hours | Check `/context` proactively |

---

## 6. Anti-Hallucination Framework

### Layer 1: Static Grounding (Always Present)

**CLAUDE.md** — Already in place. Enhance with:

```markdown
# Compact Instructions
When context compacts, ALWAYS preserve:
- Current scoring pillar weights (40/25/25/10)
- The 4 pillars: Content Density, Robots.txt, Schema.org, llms.txt
- Test command: pytest tests/ -v
- Lint command: ruff check src/ tests/
- Type check: mypy src/
- AI bots list in auditor.py
```

**.claude/rules/** — Create topic-specific rule files:

```
.claude/rules/
├── testing.md        # "Always mock HTTP calls, use pytest-asyncio"
├── scoring.md        # "Pillar weights are 40/25/25/10, never change without explicit request"
├── async-patterns.md # "All core logic is async, CLI bridges with asyncio.run()"
└── models.md         # "All Pydantic fields must have Field(description=...)"
```

### Layer 2: Dynamic Grounding (Hooks)

Hooks enforce behavior **deterministically** — Claude doesn't need to "remember" to run tests.

| Hook Event | Purpose | When |
|------------|---------|------|
| `PostToolUse` (Edit/Write) | Auto-lint with ruff | Every file change |
| `Stop` | Verify tests pass | Before Claude stops |
| `Stop` | Verify git status | Before Claude stops |
| `PreCompact` | Re-inject critical context | Before auto-compaction |

### Layer 3: Verification Gates

**Every feature must pass before moving on:**

```bash
# Gate 1: Lint
ruff check src/ tests/

# Gate 2: Type check
mypy src/

# Gate 3: Tests pass
pytest tests/ -v

# Gate 4: Coverage maintained
pytest --cov=src/aeo_cli --cov-fail-under=95 tests/

# Gate 5: Git clean
git status  # No uncommitted changes
```

### Layer 4: Human Checkpoints

| When | What |
|------|------|
| End of each phase | Review committed code, approve direction |
| Before scoring changes | Verify new weights/signals make sense |
| Before new pillar | Approve pillar design and weight allocation |
| Before version bump | Full manual review of CHANGELOG |

### Layer 5: Test-Driven Development

**Every new feature follows TDD:**
1. Write failing test first
2. Implement minimum code to pass
3. Refactor while green
4. Verify existing tests still pass

This prevents hallucinated implementations — the test is the source of truth.

---

## 7. Hooks Configuration

### Recommended `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(pytest*)",
      "Bash(ruff check*)",
      "Bash(ruff format*)",
      "Bash(mypy src/*)",
      "Bash(make ci*)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git push*)",
      "Bash(pip install*)",
      "Bash(python -m*)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "ruff check --fix $(echo $TOOL_INPUT | python3 -c \"import sys,json; print(json.load(sys.stdin).get('file_path',''))\" 2>/dev/null) 2>/dev/null || true"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /home/user/aeo-cli && python -m pytest tests/ -q --tb=short 2>&1 | tail -5"
          }
        ]
      },
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /home/user/aeo-cli && git status --short"
          }
        ]
      }
    ]
  }
}
```

### Hook Explanation

| Hook | Trigger | What It Does | Why |
|------|---------|-------------|-----|
| PostToolUse (Edit/Write) | Every file edit | Auto-fix lint issues | Prevents lint debt accumulation |
| Stop (pytest) | Before Claude stops responding | Runs test suite | Catches broken code before it's "done" |
| Stop (git status) | Before Claude stops responding | Shows uncommitted files | Prevents forgotten changes |

### Optional Advanced Hooks

**PreCompact hook** (re-inject context before auto-compaction):
```json
{
  "PreCompact": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "cat /home/user/aeo-cli/CLAUDE.md | head -50"
        }
      ]
    }
  ]
}
```

**SessionStart hook** (verify environment on session start):
```json
{
  "SessionStart": [
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "cd /home/user/aeo-cli && python -c 'import aeo_cli; print(f\"aeo-cli v{aeo_cli.__version__}\")' && git branch --show-current"
        }
      ]
    }
  ]
}
```

---

## 8. Workflow Cadence & Checkpoints

### Daily Workflow

```
╔══════════════════════════════════════════════════════════╗
║  MORNING: Start Session                                 ║
║  1. Review previous day's commits (git log --oneline)   ║
║  2. Run full CI: make ci                                ║
║  3. Update todo list with today's targets               ║
║  4. Pick first feature from phase roadmap               ║
╠══════════════════════════════════════════════════════════╣
║  MIDDAY: Development                                    ║
║  5. TDD cycle for each feature (test → implement → ✅)  ║
║  6. Commit after each green feature                     ║
║  7. Check /context after every 3-4 features             ║
║  8. /compact if needed, or /clear between features      ║
╠══════════════════════════════════════════════════════════╣
║  EVENING: Wrap Up                                       ║
║  9. Run full CI: make ci                                ║
║  10. Push all commits                                   ║
║  11. Update CHANGELOG.md                                ║
║  12. Write tomorrow's todo list                         ║
╚══════════════════════════════════════════════════════════╝
```

### Per-Feature Workflow

```
1. READ   — Read the target source file(s)
2. TEST   — Write failing test for the new behavior
3. CODE   — Implement minimum to pass test
4. LINT   — (auto via PostToolUse hook)
5. VERIFY — Run pytest for the feature's test file
6. TYPE   — Run mypy src/
7. COMMIT — git commit with descriptive message
8. NEXT   — Move to next feature or take checkpoint
```

### Checkpoint Schedule

| Checkpoint | Frequency | Gate |
|-----------|-----------|------|
| **Micro** | After each feature | pytest + ruff pass |
| **Minor** | After each sub-phase | Full `make ci` pass |
| **Major** | After each phase | Human review + full CI + git push |
| **Release** | After Phase 4 | Version bump + CHANGELOG + tag |

### Context Health Checks

| Check | Command | Frequency |
|-------|---------|-----------|
| Context usage | `/context` | Every 2 hours |
| Token cost | `/cost` | End of day |
| MCP status | `/mcp` | Start of session |
| Git state | `git status` | Before/after features |

---

## 9. Appendix: Competitive Landscape Detail

### Tier 1: Market Leaders (Full-Stack AEO Platforms)

**Profound** ($58.5M, Sequoia-backed)
- Tracks brand visibility across 10+ AI engines
- 400M+ real user prompts via "Conversation Explorer"
- G2 Winter 2026 AEO Leader
- Enterprise: Ramp, US Bank, Indeed, MongoDB, DocuSign
- From $499/mo

**Adobe LLM Optimizer** (Adobe Experience Cloud)
- "Optimize at Edge" — serves AI-friendly content at CDN layer
- Chrome extension for free page-level AI readability diagnostics
- Supports MCP and A2A protocols
- Native Adobe Experience Manager integration

**Scrunch AI** ($26M)
- Agent Experience Platform (AXP) — parallel AI-ready site version
- Only Scrunch and Adobe offer AI-optimized content delivery
- SOC 2 compliant, from $250/mo

### AI Crawler Management Tools

**Cloudflare AI Crawl Control**
- Enterprise-grade AI crawler management
- One-click AI bot blocking
- Pay-per-crawl monetization (HTTP 402)
- AI Labyrinth anti-scraping honeypot
- Default AI crawler blocking since Jul 2025

**Dark Visitors / Known Agents**
- AI bot directory and analytics
- Automatic robots.txt generation via API
- WordPress plugin, real-time bot tracking

### llms.txt Ecosystem

- **Official spec**: github.com/AnswerDotAI/llms-txt (Jeremy Howard)
- **Generator**: llms-txt.io, Firecrawl llmstxt-generator
- **Directory**: llms-txt-hub (GitHub)
- **Platforms**: Mintlify, Fern (auto-generate llms.txt)
- **Framework plugins**: VitePress, Docusaurus, Drupal

### Open-Source AEO Tools

| Project | Description |
|---------|-------------|
| **GetCito** | "World's First Open Source AIO/AEO/GEO Tool" — multi-engine monitoring |
| **LLM Brand Tracker** | Track brand in LLM responses (ChatGPT) |
| **ai.robots.txt** | Community-curated AI agent block lists |
| **n8n AI SEO Workflow** | Open automation for AI readability checks |
| **AEO WordPress Plugin** | 10 checks: schema, FAQ, robots.txt, Open Graph |
| **Drupal AEO Module** | 0-100 scoring with auto-fix capabilities |

### Thought Leaders

| Person | Known For |
|--------|-----------|
| **Jason Barnard** (Kalicube) | Coined "Answer Engine Optimization" (2017-2018), 13 patents |
| **Jeremy Howard** (Answer.AI) | Created llms.txt standard (Sept 2024) |
| **Evan Bailyn** | Founded the GEO field |
| **Mike King** (iPullRank) | "Relevance Engineering" approach |
| **Lily Ray** | Real-time AI Overviews analysis, LLM manipulation experiments |
| **Kevin Indig** (Growth Memo) | First usability study of Google AI Overviews |

---

## Summary

This plan provides:

1. **Market context** — aeo-cli occupies a genuinely unique niche (CLI + MCP + OSS + 4-pillar scoring)
2. **Research-backed feature roadmap** — aligned with GEO academic research and industry trends
3. **4-phase development plan** — Core → Intelligence → Ecosystem → Ship
4. **Anti-hallucination framework** — 5 layers from static CLAUDE.md to human checkpoints
5. **Hooks configuration** — deterministic quality enforcement (auto-lint, test gates, git checks)
6. **Workflow cadence** — daily sessions with micro/minor/major checkpoints
7. **Context management** — proactive compaction, subagent delegation, session boundaries

The key insight: **don't run one giant session**. Run daily sessions with committed checkpoints, hooks for automated quality enforcement, and human review at phase boundaries. CLAUDE.md + rules + hooks provide the grounding; TDD provides the verification; git provides the rollback safety net.
