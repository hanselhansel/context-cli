"""Generate a stunning HTML benchmark report from context-linter audit data.

Reads benchmarks/data.json (output of run_benchmark.py) and produces:
  - benchmarks/report.html  — interactive dark-themed report with Chart.js
  - benchmarks/x_thread.md  — ready-to-post X thread with key findings

Usage:
    python benchmarks/generate_report.py
"""

from __future__ import annotations

import html as html_lib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# ── Company & Category Mapping ───────────────────────────────────────────────

COMPANIES: dict[str, tuple[str, str]] = {
    # AI Companies (15)
    "docs.anthropic.com": ("Anthropic", "AI Companies"),
    "platform.openai.com": ("OpenAI", "AI Companies"),
    "ai.google.dev": ("Google AI", "AI Companies"),
    "docs.cohere.com": ("Cohere", "AI Companies"),
    "docs.mistral.ai": ("Mistral", "AI Companies"),
    "huggingface.co": ("Hugging Face", "AI Companies"),
    "api-docs.deepseek.com": ("DeepSeek", "AI Companies"),
    "docs.x.ai": ("xAI", "AI Companies"),
    "console.groq.com": ("Groq", "AI Companies"),
    "replicate.com": ("Replicate", "AI Companies"),
    "docs.together.ai": ("Together AI", "AI Companies"),
    "docs.perplexity.ai": ("Perplexity", "AI Companies"),
    "docs.fireworks.ai": ("Fireworks AI", "AI Companies"),
    "llama.meta.com": ("Meta Llama", "AI Companies"),
    "platform.stability.ai": ("Stability AI", "AI Companies"),
    # Cloud Providers (8)
    "docs.aws.amazon.com": ("AWS", "Cloud Providers"),
    "cloud.google.com": ("Google Cloud", "Cloud Providers"),
    "learn.microsoft.com": ("Azure", "Cloud Providers"),
    "developers.cloudflare.com": ("Cloudflare", "Cloud Providers"),
    "docs.digitalocean.com": ("DigitalOcean", "Cloud Providers"),
    "fly.io": ("Fly.io", "Cloud Providers"),
    "docs.railway.com": ("Railway", "Cloud Providers"),
    "docs.render.com": ("Render", "Cloud Providers"),
    # Dev Tools & APIs (15)
    "docs.stripe.com": ("Stripe", "Dev Tools"),
    "www.twilio.com": ("Twilio", "Dev Tools"),
    "docs.github.com": ("GitHub", "Dev Tools"),
    "docs.gitlab.com": ("GitLab", "Dev Tools"),
    "vercel.com": ("Vercel", "Dev Tools"),
    "docs.netlify.com": ("Netlify", "Dev Tools"),
    "supabase.com": ("Supabase", "Dev Tools"),
    "www.prisma.io": ("Prisma", "Dev Tools"),
    "www.algolia.com": ("Algolia", "Dev Tools"),
    "auth0.com": ("Auth0", "Dev Tools"),
    "docs.datadoghq.com": ("Datadog", "Dev Tools"),
    "docs.sentry.io": ("Sentry", "Dev Tools"),
    "learning.postman.com": ("Postman", "Dev Tools"),
    "docs.docker.com": ("Docker", "Dev Tools"),
    "planetscale.com": ("PlanetScale", "Dev Tools"),
    # Frameworks & Languages (12)
    "react.dev": ("React", "Frameworks"),
    "nextjs.org": ("Next.js", "Frameworks"),
    "vuejs.org": ("Vue", "Frameworks"),
    "svelte.dev": ("Svelte", "Frameworks"),
    "docs.djangoproject.com": ("Django", "Frameworks"),
    "fastapi.tiangolo.com": ("FastAPI", "Frameworks"),
    "doc.rust-lang.org": ("Rust", "Frameworks"),
    "go.dev": ("Go", "Frameworks"),
    "docs.python.org": ("Python", "Frameworks"),
    "nodejs.org": ("Node.js", "Frameworks"),
    "tailwindcss.com": ("Tailwind CSS", "Frameworks"),
    "developer.mozilla.org": ("MDN", "Frameworks"),
}

CATEGORY_COLORS = {
    "AI Companies": ("#818cf8", "rgba(129,140,248,0.15)"),
    "Cloud Providers": ("#22c55e", "rgba(34,197,94,0.15)"),
    "Dev Tools": ("#eab308", "rgba(234,179,8,0.15)"),
    "Frameworks": ("#f472b6", "rgba(244,114,182,0.15)"),
}

CATEGORY_ORDER = ["AI Companies", "Cloud Providers", "Dev Tools", "Frameworks"]

BOT_SHORT_NAMES = {
    "GPTBot": "GPT",
    "ChatGPT-User": "Chat",
    "Google-Extended": "Goog",
    "ClaudeBot": "Clde",
    "PerplexityBot": "Pplx",
    "Amazonbot": "Amzn",
    "OAI-SearchBot": "OAI",
    "DeepSeek-AI": "DSek",
    "Grok": "Grok",
    "Meta-ExternalAgent": "Meta",
    "cohere-ai": "Cohr",
    "AI2Bot": "AI2",
    "ByteSpider": "Byte",
}

BOT_NAMES = list(BOT_SHORT_NAMES.keys())


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg-0:#09090b;--bg-1:#0f0f14;--bg-2:#18181f;--bg-3:#27272a;
  --border:rgba(255,255,255,0.06);--border-2:rgba(255,255,255,0.1);
  --text-0:#fafafa;--text-1:#a1a1aa;--text-2:#71717a;
  --accent:#818cf8;--accent-2:#a78bfa;
  --green:#22c55e;--yellow:#eab308;--red:#ef4444;
  --radius:12px;
}
html{scroll-behavior:smooth}
body{
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  background:var(--bg-0);color:var(--text-0);
  line-height:1.6;-webkit-font-smoothing:antialiased;
}
.container{max-width:1200px;margin:0 auto;padding:0 24px}

/* ─ Hero ─ */
.hero{
  padding:80px 0 48px;text-align:center;
  background:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(99,102,241,0.12),transparent);
}
.hero-badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;
  background:rgba(129,140,248,0.1);color:var(--accent);
  border:1px solid rgba(129,140,248,0.2);margin-bottom:24px;
  text-transform:uppercase;letter-spacing:0.08em;
}
.hero h1{
  font-size:clamp(2rem,5vw,3.5rem);font-weight:800;
  line-height:1.1;margin-bottom:16px;
  background:linear-gradient(135deg,#818cf8 0%,#c084fc 40%,#f472b6 70%,#818cf8 100%);
  background-size:300% 300%;
  animation:gradient-shift 8s ease infinite;
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
@keyframes gradient-shift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
.hero p{font-size:1.15rem;color:var(--text-1);max-width:640px;margin:0 auto}

/* ─ Stats Bar ─ */
.stats-bar{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:1px;background:var(--border);border-radius:var(--radius);
  overflow:hidden;margin:48px auto;max-width:900px;
  border:1px solid var(--border);
}
.stat{
  background:var(--bg-2);padding:28px 20px;text-align:center;
  transition:background .2s;
}
.stat:hover{background:var(--bg-3)}
.stat-value{font-size:2rem;font-weight:800;line-height:1}
.stat-label{font-size:12px;color:var(--text-2);margin-top:8px;
  text-transform:uppercase;letter-spacing:0.06em;font-weight:500}

/* ─ Section ─ */
.section{margin:64px 0}
.section-header{margin-bottom:32px}
.section-header h2{font-size:1.75rem;font-weight:700;margin-bottom:8px}
.section-header p{color:var(--text-1);font-size:0.95rem}

/* ─ Table ─ */
.table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:var(--radius)}
table{width:100%;border-collapse:collapse;font-size:14px}
thead{position:sticky;top:0;z-index:2}
th{
  background:var(--bg-2);padding:14px 16px;text-align:left;
  font-weight:600;font-size:12px;text-transform:uppercase;
  letter-spacing:0.05em;color:var(--text-2);
  border-bottom:1px solid var(--border-2);white-space:nowrap;
}
td{padding:12px 16px;border-bottom:1px solid var(--border);white-space:nowrap}
tbody tr{transition:background .15s}
tbody tr:hover{background:rgba(255,255,255,0.02)}
.rank{font-weight:700;color:var(--text-2);width:48px}
.company-cell{display:flex;align-items:center;gap:10px;min-width:180px}
.company-cell img{width:20px;height:20px;border-radius:4px;flex-shrink:0}
.company-cell span{font-weight:600}
.score-pill{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:48px;padding:4px 14px;border-radius:20px;
  font-weight:700;font-size:13px;
}
.badge{
  padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.06em;white-space:nowrap;
}
.pillar-val{font-variant-numeric:tabular-nums}
.waste-val{color:var(--text-1);font-variant-numeric:tabular-nums}
.top5 td{background:rgba(34,197,94,0.04)}
.bottom5 td{background:rgba(239,68,68,0.04)}
th.sortable{cursor:pointer;user-select:none}
th.sortable:hover{color:var(--text-0)}
th.sortable::after{content:' \\2195';opacity:.3}

/* ─ Charts ─ */
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.chart-grid .full{grid-column:1/-1}
.chart-card{
  background:var(--bg-2);border:1px solid var(--border);
  border-radius:var(--radius);padding:28px;
}
.chart-card h3{font-size:1.1rem;font-weight:700;margin-bottom:4px}
.chart-card .chart-sub{font-size:13px;color:var(--text-2);margin-bottom:20px}
.chart-wrapper{position:relative}

/* ─ Heatmap ─ */
.heatmap-scroll{overflow-x:auto}
.heatmap{border-collapse:collapse;font-size:12px;width:100%}
.heatmap th{
  padding:6px 4px;font-weight:600;color:var(--text-2);
  writing-mode:vertical-lr;text-orientation:mixed;
  transform:rotate(180deg);height:80px;text-align:left;
}
.heatmap th.company-th{
  writing-mode:horizontal-tb;transform:none;
  text-align:right;padding-right:12px;height:auto;min-width:140px;
  font-weight:500;color:var(--text-1);
}
.heatmap td{padding:3px;text-align:center}
.hm-cell{
  width:28px;height:28px;border-radius:4px;margin:0 auto;
  display:flex;align-items:center;justify-content:center;
  font-size:10px;font-weight:700;
}
.hm-yes{background:rgba(34,197,94,0.25);color:var(--green)}
.hm-no{background:rgba(239,68,68,0.2);color:var(--red)}

/* ─ Insights ─ */
.insights-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}
.insight{
  padding:24px;background:var(--bg-2);border-radius:var(--radius);
  border-left:4px solid var(--accent);
  border-top:1px solid var(--border);border-right:1px solid var(--border);
  border-bottom:1px solid var(--border);
}
.insight.irony{border-left-color:var(--red)}
.insight.positive{border-left-color:var(--green)}
.insight.warning{border-left-color:var(--yellow)}
.insight-tag{
  font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.08em;margin-bottom:8px;
}
.insight-text{font-size:15px;font-weight:500;line-height:1.5}
.insight-detail{font-size:13px;color:var(--text-2);margin-top:8px}

/* ─ Category Sections ─ */
.cat-section{margin-top:48px}
.cat-header{display:flex;align-items:center;gap:12px;margin-bottom:20px}
.cat-dot{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.cat-header h3{font-size:1.25rem;font-weight:700}
.cat-table{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px}
.cat-table th{text-align:left;padding:10px 12px;font-size:11px;
  text-transform:uppercase;letter-spacing:.05em;color:var(--text-2);
  border-bottom:1px solid var(--border-2);background:var(--bg-2)}
.cat-table td{padding:10px 12px;border-bottom:1px solid var(--border)}
.best-badge{
  display:inline-flex;align-items:center;gap:4px;
  padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;
  background:rgba(34,197,94,0.12);color:var(--green);
  text-transform:uppercase;letter-spacing:0.06em;
}

/* ─ Methodology / Footer ─ */
.methodology{padding:64px 0;border-top:1px solid var(--border);margin-top:80px}
.method-grid{display:grid;grid-template-columns:1fr 1fr;gap:48px;margin-bottom:48px}
.method-pillar{display:flex;align-items:baseline;gap:12px;margin-bottom:12px}
.method-weight{
  font-size:1.5rem;font-weight:800;color:var(--accent);min-width:48px;
  text-align:right;
}
.method-name{font-weight:600}
.method-desc{font-size:13px;color:var(--text-2)}
.cta-box{
  background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.08));
  border:1px solid rgba(99,102,241,0.15);border-radius:var(--radius);
  padding:40px;text-align:center;
}
.cta-box h3{font-size:1.5rem;font-weight:700;margin-bottom:12px}
.cta-box p{color:var(--text-1);margin-bottom:20px}
.cta-code{
  display:inline-block;background:var(--bg-0);border:1px solid var(--border-2);
  border-radius:8px;padding:12px 24px;font-family:'SF Mono',Monaco,monospace;
  font-size:14px;color:var(--accent);letter-spacing:0.02em;
}
.footer-links{
  display:flex;justify-content:center;gap:32px;margin-top:32px;
  font-size:13px;
}
.footer-links a{color:var(--text-2);text-decoration:none;transition:color .2s}
.footer-links a:hover{color:var(--accent)}
.timestamp{text-align:center;font-size:12px;color:var(--text-2);margin-top:40px}

/* ─ Responsive ─ */
@media(max-width:768px){
  .chart-grid{grid-template-columns:1fr}
  .method-grid{grid-template-columns:1fr}
  .hero{padding:48px 0 32px}
  .hero h1{font-size:1.75rem}
  .stats-bar{grid-template-columns:repeat(2,1fr)}
  .insights-grid{grid-template-columns:1fr}
}
"""

# ── Helper Functions ─────────────────────────────────────────────────────────


def score_color(score: float) -> str:
    """Return hex color for a score value (green/yellow/red)."""
    if score >= 80:
        return "#22c55e"
    if score >= 50:
        return "#eab308"
    return "#ef4444"


def score_color_bg(score: float) -> str:
    """Return a low-opacity background for a score value."""
    if score >= 80:
        return "rgba(34,197,94,0.12)"
    if score >= 50:
        return "rgba(234,179,8,0.12)"
    return "rgba(239,68,68,0.12)"


def get_company_info(url: str) -> tuple[str, str]:
    """Return (company_name, category) from URL."""
    domain = urlparse(url).netloc.lower()
    if domain in COMPANIES:
        return COMPANIES[domain]
    for key, val in COMPANIES.items():
        if key in domain or domain.endswith(key):
            return val
    return (domain, "Other")


def get_domain(url: str) -> str:
    """Extract domain from URL for favicon lookup."""
    return urlparse(url).netloc


def esc(text: str) -> str:
    """HTML-escape a string."""
    return html_lib.escape(str(text))


# ── Data Processing ──────────────────────────────────────────────────────────


def load_data(path: Path) -> dict:
    """Load raw benchmark JSON data."""
    with open(path) as f:
        return json.load(f)


def process_reports(data: dict) -> list[dict]:
    """Extract flat dicts from audit reports for analysis.

    Handles both AuditReport (single-page) and SiteAuditReport (multi-page).
    Extracts V3 agent_readiness data and markdown_stats when present.
    """
    # Load top-level markdown_stats (keyed by URL)
    md_stats_map = data.get("markdown_stats", {})

    results = []
    for report in data.get("reports", []):
        url = report["url"]
        name, category = get_company_info(url)
        robots = report.get("robots", {})
        llms = report.get("llms_txt", {})
        schema = report.get("schema_org", {})
        content = report.get("content", {})
        bot_results = {}
        for b in robots.get("bots", []):
            bot_results[b["bot"]] = b["allowed"]

        # Multi-page site audit fields (SiteAuditReport)
        pages_audited = report.get("pages_audited", 1)
        pages_failed = report.get("pages_failed", 0)
        discovery = report.get("discovery", {})
        discovery_method = discovery.get("method", "single")

        # V3: Agent readiness data
        ar = report.get("agent_readiness") or {}
        agent_readiness_score = ar.get("score", 0)
        agents_md = ar.get("agents_md", {})
        md_accept = ar.get("markdown_accept", {})
        mcp_ep = ar.get("mcp_endpoint", {})
        semantic = ar.get("semantic_html", {})
        x402 = ar.get("x402", {})
        nlweb = ar.get("nlweb", {})

        # Markdown conversion stats (from top-level markdown_stats)
        md_stats = md_stats_map.get(url, {})

        results.append({
            "url": url,
            "name": name,
            "category": category,
            "domain": report.get("domain", get_domain(url)),
            "overall_score": report.get("overall_score", 0),
            "robots_score": robots.get("score", 0),
            "llms_score": llms.get("score", 0),
            "schema_score": schema.get("score", 0),
            "content_score": content.get("score", 0),
            "llms_found": llms.get("found", False),
            "llms_full_found": llms.get("llms_full_found", False),
            "schema_blocks": schema.get("blocks_found", 0),
            "word_count": content.get("word_count", 0),
            "raw_tokens": content.get("estimated_raw_tokens", 0),
            "clean_tokens": content.get("estimated_clean_tokens", 0),
            "waste_pct": content.get("context_waste_pct", 0),
            "bots": bot_results,
            "pages_audited": pages_audited,
            "pages_failed": pages_failed,
            "discovery_method": discovery_method,
            # V3: Agent readiness
            "agent_readiness_score": agent_readiness_score,
            "has_agents_md": agents_md.get("found", False),
            "has_markdown_accept": md_accept.get("supported", False),
            "has_mcp_endpoint": mcp_ep.get("found", False),
            "has_semantic_html": semantic.get("score", 0) > 0,
            "has_x402": x402.get("found", False),
            "has_nlweb": nlweb.get("found", False),
            # Markdown conversion stats
            "md_raw_html_chars": md_stats.get("raw_html_chars", 0),
            "md_clean_md_chars": md_stats.get("clean_md_chars", 0),
            "md_raw_tokens": md_stats.get("raw_tokens", 0),
            "md_clean_tokens": md_stats.get("clean_tokens", 0),
            "md_reduction_pct": md_stats.get("reduction_pct", 0),
        })
    results.sort(key=lambda r: r["overall_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_category_stats(reports: list[dict]) -> dict[str, dict]:
    """Compute average pillar scores per category."""
    buckets: dict[str, list[dict]] = {}
    for r in reports:
        buckets.setdefault(r["category"], []).append(r)
    stats = {}
    for cat in CATEGORY_ORDER:
        items = buckets.get(cat, [])
        if not items:
            continue
        n = len(items)
        stats[cat] = {
            "count": n,
            "avg_overall": round(sum(r["overall_score"] for r in items) / n, 1),
            "avg_robots": round(sum(r["robots_score"] for r in items) / n, 1),
            "avg_llms": round(sum(r["llms_score"] for r in items) / n, 1),
            "avg_schema": round(sum(r["schema_score"] for r in items) / n, 1),
            "avg_content": round(sum(r["content_score"] for r in items) / n, 1),
            "avg_words": round(sum(r["word_count"] for r in items) / n),
            "llms_adoption": sum(1 for r in items if r["llms_found"]),
            "best": max(items, key=lambda r: r["overall_score"]),
        }
    return stats


def compute_insights(reports: list[dict], cat_stats: dict[str, dict]) -> list[dict]:
    """Generate data-driven insights from the benchmark results."""
    insights = []
    n = len(reports)
    if n == 0:
        return insights

    avg_score = sum(r["overall_score"] for r in reports) / n
    best = reports[0]
    worst = reports[-1]
    avg_waste = sum(r["waste_pct"] for r in reports) / n
    llms_count = sum(1 for r in reports if r["llms_found"])
    llms_full_count = sum(1 for r in reports if r["llms_full_found"])
    schema_sites = sum(1 for r in reports if r["schema_blocks"] > 0)

    # Headline
    insights.append({
        "tag": "Headline",
        "text": f"The average LLM readiness score across all {n} tech docs sites is "
                f"just {avg_score:.0f}/100.",
        "detail": f"Best: {best['name']} ({best['overall_score']:.0f}) | "
                  f"Worst: {worst['name']} ({worst['overall_score']:.0f})",
        "style": "",
    })

    # Content volume
    word_counts = sorted([r["word_count"] for r in reports], reverse=True)
    total_words = sum(word_counts)
    max_words_site = max(reports, key=lambda r: r["word_count"])
    min_words_site = min(reports, key=lambda r: r["word_count"])
    insights.append({
        "tag": "Content Volume",
        "text": f"Total content across all {n} sites: {total_words:,} words. "
                f"The most content-rich site ({max_words_site['name']}) has "
                f"{max_words_site['word_count']:,} words \u2014 "
                f"{max_words_site['word_count'] // max(min_words_site['word_count'], 1)}x "
                f"more than the least ({min_words_site['name']}, "
                f"{min_words_site['word_count']:,} words).",
        "detail": "More content generally means more surface area for AI systems "
                  "to learn from, but quality and structure matter more than volume.",
        "style": "",
    })

    # AI companies blocking AI bots (the irony)
    ai_reports = [r for r in reports if r["category"] == "AI Companies"]
    if ai_reports:
        ai_blockers = []
        for r in ai_reports:
            blocked = [b for b, allowed in r["bots"].items() if not allowed]
            if blocked:
                ai_blockers.append(r["name"])
        if ai_blockers:
            pct = len(ai_blockers) / len(ai_reports) * 100
            insights.append({
                "tag": "The Irony Index",
                "text": f"{pct:.0f}% of AI companies that BUILD AI tools block "
                        f"AI crawlers from their own documentation.",
                "detail": f"Offenders: {', '.join(ai_blockers)}",
                "style": "irony",
            })

    # llms.txt adoption
    insights.append({
        "tag": "llms.txt Adoption",
        "text": f"Only {llms_count} of {n} sites have llms.txt \u2014 the simplest "
                f"optimization with the biggest signal to AI systems.",
        "detail": f"{llms_full_count} also provide llms-full.txt for comprehensive context.",
        "style": "warning" if llms_count < n // 2 else "positive",
    })

    # Category comparison
    cat_ranking = sorted(cat_stats.items(), key=lambda x: x[1]["avg_overall"], reverse=True)
    if len(cat_ranking) >= 2:
        top_cat, top_stat = cat_ranking[0]
        bot_cat, bot_stat = cat_ranking[-1]
        insights.append({
            "tag": "Category Gap",
            "text": f"{top_cat} lead with an average score of {top_stat['avg_overall']:.0f}, "
                    f"while {bot_cat} trail at {bot_stat['avg_overall']:.0f}.",
            "detail": "Category averages reveal systemic differences in how "
                      "industries prioritize AI readiness.",
            "style": "",
        })

    # Content density across categories
    content_ranking = sorted(cat_stats.items(), key=lambda x: x[1]["avg_content"], reverse=True)
    if len(content_ranking) >= 2:
        tc, ts = content_ranking[0]
        bc, bs = content_ranking[-1]
        if ts["avg_content"] > 0 and bs["avg_content"] > 0:
            ratio = ts["avg_content"] / bs["avg_content"]
            insights.append({
                "tag": "Content Density",
                "text": f"{tc} docs score {ratio:.1f}x higher on content density "
                        f"than {bc} docs.",
                "detail": f"{tc}: {ts['avg_content']:.0f}/40 avg | "
                          f"{bc}: {bs['avg_content']:.0f}/40 avg",
                "style": "positive" if ratio > 1.5 else "",
            })

    # Schema.org impact
    with_schema = [r for r in reports if r["schema_blocks"] > 0]
    without_schema = [r for r in reports if r["schema_blocks"] == 0]
    if with_schema and without_schema:
        avg_with = sum(r["overall_score"] for r in with_schema) / len(with_schema)
        avg_without = sum(r["overall_score"] for r in without_schema) / len(without_schema)
        delta = avg_with - avg_without
        insights.append({
            "tag": "Schema.org Impact",
            "text": f"Sites with JSON-LD structured data score {delta:+.0f} points "
                    f"higher on average ({avg_with:.0f} vs {avg_without:.0f}).",
            "detail": f"{len(with_schema)} of {n} sites have at least one JSON-LD block.",
            "style": "positive" if delta > 5 else "",
        })

    # llms.txt correlation
    with_llms = [r for r in reports if r["llms_found"]]
    without_llms = [r for r in reports if not r["llms_found"]]
    if with_llms and without_llms:
        avg_with = sum(r["overall_score"] for r in with_llms) / len(with_llms)
        avg_without = sum(r["overall_score"] for r in without_llms) / len(without_llms)
        delta = avg_with - avg_without
        insights.append({
            "tag": "llms.txt Correlation",
            "text": f"Sites with llms.txt score {delta:+.0f} points higher on average "
                    f"({avg_with:.0f} vs {avg_without:.0f}).",
            "detail": "Correlation doesn\u2019t imply causation, but sites that care about "
                      "AI readiness tend to care about all pillars.",
            "style": "positive" if delta > 0 else "",
        })

    # Agent Readiness insight
    agents_md_count = sum(1 for r in reports if r.get("has_agents_md", False))
    md_accept_count = sum(1 for r in reports if r.get("has_markdown_accept", False))
    mcp_count = sum(1 for r in reports if r.get("has_mcp_endpoint", False))
    avg_agent_score = sum(r.get("agent_readiness_score", 0) for r in reports) / n
    insights.append({
        "tag": "Agent Readiness",
        "text": f"Average agent readiness score: {avg_agent_score:.1f}/20. "
                f"Only {agents_md_count}/{n} have AGENTS.md, "
                f"{md_accept_count}/{n} support Accept: text/markdown, "
                f"and {mcp_count}/{n} expose MCP endpoints.",
        "detail": "Agent readiness is the newest pillar — most sites have not "
                  "yet adopted these standards for AI agent interoperability.",
        "style": "warning" if avg_agent_score < 10 else "positive",
    })

    # Token Reduction insight
    md_sites = [r for r in reports if r.get("md_reduction_pct", 0) > 0]
    if md_sites:
        avg_reduction = sum(r["md_reduction_pct"] for r in md_sites) / len(md_sites)
        best_md = max(md_sites, key=lambda r: r["md_reduction_pct"])
        insights.append({
            "tag": "Token Reduction",
            "text": f"Converting HTML to clean markdown reduces tokens by "
                    f"{avg_reduction:.0f}% on average across {len(md_sites)} sites.",
            "detail": f"Best reduction: {best_md['name']} at "
                      f"{best_md['md_reduction_pct']:.0f}%. "
                      f"Serving markdown instead of HTML can dramatically cut "
                      f"context window waste for LLM consumers.",
            "style": "positive",
        })

    # Best content but blocking bots
    for r in reports[:10]:
        blocked = [b for b, allowed in r["bots"].items() if not allowed]
        if r["content_score"] >= 30 and len(blocked) >= 5:
            insights.append({
                "tag": "Hidden Gem",
                "text": f"{r['name']} has excellent content ({r['content_score']:.0f}/40) "
                        f"but blocks {len(blocked)}/13 AI bots, making it effectively "
                        f"invisible to AI systems.",
                "detail": f"Blocked: {', '.join(blocked[:5])}{'...' if len(blocked) > 5 else ''}",
                "style": "irony",
            })
            break  # Only one

    return insights


# ── HTML Builders ────────────────────────────────────────────────────────────


def build_hero() -> str:
    return """<header class="hero">
<div class="container">
  <div class="hero-badge">Benchmark Report</div>
  <h1>The LLM Readiness of<br>Tech Documentation</h1>
  <p>We deep-crawled 50 of the biggest tech docs sites &mdash; up to 10 pages each
  &mdash; to find out which companies are actually ready for the AI era.
  The results are&hellip; revealing.</p>
</div>
</header>"""


def build_stats_bar(reports: list[dict], cat_stats: dict) -> str:
    n = len(reports)
    if n == 0:
        return ""
    avg = sum(r["overall_score"] for r in reports) / n
    best = reports[0]
    llms_count = sum(1 for r in reports if r["llms_found"])
    total_pages = sum(r["pages_audited"] for r in reports)
    schema_count = sum(1 for r in reports if r["schema_blocks"] > 0)

    # V3: Agent readiness average
    avg_agent = sum(r["agent_readiness_score"] for r in reports) / n
    agent_color = score_color(avg_agent / 20 * 100)  # normalize to 0-100 scale

    # Markdown token reduction average (only for sites with data)
    md_sites = [r for r in reports if r["md_reduction_pct"] > 0]
    avg_reduction = (
        sum(r["md_reduction_pct"] for r in md_sites) / len(md_sites)
        if md_sites else 0
    )

    return f"""<div class="container">
<div class="stats-bar">
  <div class="stat">
    <div class="stat-value" style="color:{score_color(avg)}">{avg:.0f}</div>
    <div class="stat-label">Avg Score</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:var(--green)">{esc(best['name'])}</div>
    <div class="stat-label">Top Scorer ({best['overall_score']:.0f})</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:var(--accent)">{total_pages}</div>
    <div class="stat-label">Pages Audited</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:var(--accent)">{llms_count}/{n}</div>
    <div class="stat-label">Have llms.txt</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:var(--yellow)">{schema_count}/{n}</div>
    <div class="stat-label">Have Schema.org</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:{agent_color}">{avg_agent:.1f}/20</div>
    <div class="stat-label">Avg Agent Readiness</div>
  </div>
  <div class="stat">
    <div class="stat-value" style="color:var(--accent)">{avg_reduction:.0f}%</div>
    <div class="stat-label">Avg Token Reduction</div>
  </div>
</div>
</div>"""


def build_rankings_table(reports: list[dict]) -> str:
    rows = []
    for r in reports:
        color = score_color(r["overall_score"])
        bg = score_color_bg(r["overall_score"])
        cat_color, cat_bg = CATEGORY_COLORS.get(r["category"], ("#888", "rgba(136,136,136,0.15)"))
        row_class = ""
        if r["rank"] <= 5:
            row_class = " class=\"top5\""
        elif r["rank"] > len(reports) - 5:
            row_class = " class=\"bottom5\""
        favicon = f"https://www.google.com/s2/favicons?sz=32&domain={esc(r['domain'])}"
        pages = r.get("pages_audited", 1)
        rows.append(
            f'<tr{row_class}>'
            f'<td class="rank">#{r["rank"]}</td>'
            f'<td><div class="company-cell">'
            f'<img src="{favicon}" alt="" loading="lazy" '
            f'onerror="this.style.display=\'none\'">'
            f'<span>{esc(r["name"])}</span></div></td>'
            f'<td><span class="badge" style="background:{cat_bg};color:{cat_color}">'
            f'{esc(r["category"])}</span></td>'
            f'<td><span class="score-pill" style="background:{bg};color:{color}">'
            f'{r["overall_score"]:.0f}</span></td>'
            f'<td class="pillar-val">{r["robots_score"]:.0f}/25</td>'
            f'<td class="pillar-val">{r["llms_score"]:.0f}/10</td>'
            f'<td class="pillar-val">{r["schema_score"]:.0f}/25</td>'
            f'<td class="pillar-val">{r["content_score"]:.0f}/40</td>'
            f'<td class="pillar-val" style="color:var(--text-1)">'
            f'{r["word_count"]:,}</td>'
            f'<td class="pillar-val" style="color:var(--text-2)">{pages}</td>'
            f'</tr>'
        )

    return f"""<section class="section" id="rankings">
<div class="container">
  <div class="section-header">
    <h2>Overall Rankings</h2>
    <p>All {len(reports)} sites ranked by LLM readiness score (multi-page deep audit). Click column headers to sort.</p>
  </div>
  <div class="table-wrap">
    <table id="rankingsTable">
      <thead><tr>
        <th class="sortable">Rank</th>
        <th>Company</th>
        <th>Category</th>
        <th class="sortable">Score</th>
        <th class="sortable">Robots</th>
        <th class="sortable">llms.txt</th>
        <th class="sortable">Schema</th>
        <th class="sortable">Content</th>
        <th class="sortable">Words</th>
        <th class="sortable">Pages</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</div>
</section>"""


def build_chart_section() -> str:
    """Build chart container HTML — charts are populated by JS."""
    return """<section class="section" id="charts">
<div class="container">
  <div class="section-header">
    <h2>Visual Analysis</h2>
    <p>Interactive charts revealing patterns across all 50 sites.</p>
  </div>
  <div class="chart-grid">

    <div class="chart-card full">
      <h3>Score Distribution</h3>
      <p class="chart-sub">All sites ranked by overall LLM readiness score</p>
      <div class="chart-wrapper">
        <canvas id="scoreDistChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <h3>Category Averages</h3>
      <p class="chart-sub">Average pillar scores by industry category</p>
      <div class="chart-wrapper">
        <canvas id="categoryChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <h3>Content Volume</h3>
      <p class="chart-sub">Total word count per site (aggregated across crawled pages)</p>
      <div class="chart-wrapper">
        <canvas id="wordsChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <h3>llms.txt Adoption</h3>
      <p class="chart-sub">How many sites provide machine-readable context?</p>
      <div class="chart-wrapper">
        <canvas id="llmsChart"></canvas>
      </div>
    </div>

    <div class="chart-card">
      <h3>Pillar Radar: Top 5 vs Bottom 5</h3>
      <p class="chart-sub">Normalized pillar scores comparing the best and worst performers</p>
      <div class="chart-wrapper">
        <canvas id="radarChart"></canvas>
      </div>
    </div>

    <div class="chart-card full">
      <h3>Markdown Token Reduction</h3>
      <p class="chart-sub">Token savings from HTML-to-markdown conversion per site</p>
      <div class="chart-wrapper">
        <canvas id="tokenReductionChart"></canvas>
      </div>
    </div>

  </div>
</div>
</section>"""


def build_bot_heatmap(reports: list[dict]) -> str:
    """Build the bot access heatmap as an HTML table."""
    # Column headers (bot short names)
    headers = "".join(f"<th>{esc(BOT_SHORT_NAMES.get(b, b[:4]))}</th>" for b in BOT_NAMES)

    # Rows (one per company, sorted by score)
    rows = []
    for r in reports:
        cells = []
        for bot in BOT_NAMES:
            allowed = r["bots"].get(bot)
            if allowed is True:
                cells.append('<td><div class="hm-cell hm-yes">\u2713</div></td>')
            elif allowed is False:
                cells.append('<td><div class="hm-cell hm-no">\u2717</div></td>')
            else:
                cells.append('<td><div class="hm-cell" style="color:var(--text-2)">\u2014</div></td>')
        rows.append(
            f'<tr><th class="company-th">{esc(r["name"])}</th>{"".join(cells)}</tr>'
        )

    # Summary row: count allowed per bot
    summary_cells = []
    for bot in BOT_NAMES:
        allowed_count = sum(1 for r in reports if r["bots"].get(bot) is True)
        total = sum(1 for r in reports if bot in r["bots"])
        pct = allowed_count / total * 100 if total else 0
        color = score_color(pct)
        summary_cells.append(
            f'<td><div class="hm-cell" style="color:{color};font-weight:800">'
            f'{allowed_count}</div></td>'
        )

    return f"""<section class="section" id="heatmap">
<div class="container">
  <div class="section-header">
    <h2>AI Bot Access Heatmap</h2>
    <p>Which companies allow which AI crawlers? Green = allowed, Red = blocked.</p>
  </div>
  <div class="chart-card">
    <div class="heatmap-scroll">
      <table class="heatmap">
        <thead><tr><th class="company-th"></th>{headers}</tr></thead>
        <tbody>
          {''.join(rows)}
          <tr style="border-top:2px solid var(--border-2)">
            <th class="company-th" style="font-weight:700;color:var(--text-0)">
              Allowed</th>{' '.join(summary_cells)}
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
</section>"""


AGENT_CHECKS = [
    ("has_agents_md", "AGENTS.md"),
    ("has_markdown_accept", "Accept:md"),
    ("has_mcp_endpoint", "MCP"),
    ("has_semantic_html", "Semantic"),
    ("has_x402", "x402"),
    ("has_nlweb", "NLWeb"),
]

AGENT_SHORT_NAMES = {
    "AGENTS.md": "AGT",
    "Accept:md": "MD",
    "MCP": "MCP",
    "Semantic": "Sem",
    "x402": "402",
    "NLWeb": "NLW",
}


def build_agent_heatmap(reports: list[dict]) -> str:
    """Build the agent readiness heatmap as an HTML table."""
    headers = "".join(
        f"<th>{esc(AGENT_SHORT_NAMES.get(label, label))}</th>"
        for _, label in AGENT_CHECKS
    )

    rows = []
    for r in reports:
        cells = []
        for key, _label in AGENT_CHECKS:
            val = r.get(key, False)
            if val:
                cells.append(
                    '<td><div class="hm-cell hm-yes">\u2713</div></td>'
                )
            else:
                cells.append(
                    '<td><div class="hm-cell hm-no">\u2717</div></td>'
                )
        rows.append(
            f'<tr><th class="company-th">{esc(r["name"])}</th>'
            f'{"".join(cells)}</tr>'
        )

    # Summary row: count per check
    summary_cells = []
    for key, _label in AGENT_CHECKS:
        count = sum(1 for r in reports if r.get(key, False))
        pct = count / len(reports) * 100 if reports else 0
        color = score_color(pct)
        summary_cells.append(
            f'<td><div class="hm-cell" style="color:{color};font-weight:800">'
            f'{count}</div></td>'
        )

    return f"""<section class="section" id="agent-heatmap">
<div class="container">
  <div class="section-header">
    <h2>Agent Readiness Heatmap</h2>
    <p>Which sites support the 6 agent readiness checks? Green = present, Red = absent.</p>
  </div>
  <div class="chart-card">
    <div class="heatmap-scroll">
      <table class="heatmap">
        <thead><tr><th class="company-th"></th>{headers}</tr></thead>
        <tbody>
          {''.join(rows)}
          <tr style="border-top:2px solid var(--border-2)">
            <th class="company-th" style="font-weight:700;color:var(--text-0)">
              Present</th>{' '.join(summary_cells)}
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
</section>"""


def build_insights_section(insights: list[dict]) -> str:
    cards = []
    for ins in insights:
        style_class = f' {ins["style"]}' if ins["style"] else ""
        tag_color = {
            "irony": "var(--red)", "positive": "var(--green)",
            "warning": "var(--yellow)",
        }.get(ins["style"], "var(--accent)")
        cards.append(
            f'<div class="insight{style_class}">'
            f'<div class="insight-tag" style="color:{tag_color}">{esc(ins["tag"])}</div>'
            f'<div class="insight-text">{esc(ins["text"])}</div>'
            f'<div class="insight-detail">{esc(ins["detail"])}</div>'
            f'</div>'
        )

    return f"""<section class="section" id="insights">
<div class="container">
  <div class="section-header">
    <h2>Key Insights</h2>
    <p>Data-driven findings from the benchmark \u2014 some obvious, some surprising.</p>
  </div>
  <div class="insights-grid">{''.join(cards)}</div>
</div>
</section>"""


def build_category_sections(reports: list[dict], cat_stats: dict) -> str:
    sections = []
    for cat in CATEGORY_ORDER:
        stat = cat_stats.get(cat)
        if not stat:
            continue
        cat_reports = sorted(
            [r for r in reports if r["category"] == cat],
            key=lambda r: r["overall_score"],
            reverse=True,
        )
        cat_color = CATEGORY_COLORS.get(cat, ("#888", ""))[0]
        rows = []
        for i, r in enumerate(cat_reports):
            color = score_color(r["overall_score"])
            bg = score_color_bg(r["overall_score"])
            best_mark = ""
            if i == 0:
                best_mark = ' <span class="best-badge">Best in class</span>'
            rows.append(
                f'<tr><td>#{i + 1}</td>'
                f'<td style="font-weight:600">{esc(r["name"])}{best_mark}</td>'
                f'<td><span class="score-pill" style="background:{bg};color:{color}">'
                f'{r["overall_score"]:.0f}</span></td>'
                f'<td class="pillar-val">{r["robots_score"]:.0f}</td>'
                f'<td class="pillar-val">{r["llms_score"]:.0f}</td>'
                f'<td class="pillar-val">{r["schema_score"]:.0f}</td>'
                f'<td class="pillar-val">{r["content_score"]:.0f}</td>'
                f'<td class="pillar-val" style="color:var(--text-1)">'
                f'{r["word_count"]:,}</td></tr>'
            )
        sections.append(
            f'<div class="cat-section">'
            f'<div class="cat-header">'
            f'<div class="cat-dot" style="background:{cat_color}"></div>'
            f'<h3>{esc(cat)}</h3>'
            f'<span style="color:var(--text-2);font-size:14px">'
            f'Avg: {stat["avg_overall"]:.0f}/100 '
            f'| llms.txt: {stat["llms_adoption"]}/{stat["count"]}'
            f'</span></div>'
            f'<table class="cat-table"><thead><tr>'
            f'<th>#</th><th>Company</th><th>Score</th>'
            f'<th>Robots</th><th>llms.txt</th><th>Schema</th>'
            f'<th>Content</th><th>Words</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    return f"""<section class="section" id="categories">
<div class="container">
  <div class="section-header">
    <h2>Category Deep Dives</h2>
    <p>How does each industry segment stack up?</p>
  </div>
  {''.join(sections)}
</div>
</section>"""


def build_methodology() -> str:
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    return f"""<footer class="methodology">
<div class="container">
  <div class="section-header">
    <h2>Methodology</h2>
    <p>How we measure LLM readiness (V3 scoring)</p>
  </div>
  <div class="method-grid">
    <div>
      <div class="method-pillar">
        <div class="method-weight">40</div>
        <div><div class="method-name">Content Density</div>
        <div class="method-desc">Word count, headings, lists, code blocks,
        readability, chunk structure, answer-first ratio</div></div>
      </div>
      <div class="method-pillar">
        <div class="method-weight">25</div>
        <div><div class="method-name">Robots.txt AI Bot Access</div>
        <div class="method-desc">Access rules for 13 AI crawlers including
        GPTBot, ClaudeBot, PerplexityBot, and more</div></div>
      </div>
      <div class="method-pillar">
        <div class="method-weight">20</div>
        <div><div class="method-name">Agent Readiness</div>
        <div class="method-desc">AGENTS.md, Accept: text/markdown,
        MCP endpoints, semantic HTML, x402, NLWeb &mdash;
        new V3 pillar measuring how well a site supports AI agents</div></div>
      </div>
    </div>
    <div>
      <div class="method-pillar">
        <div class="method-weight">25</div>
        <div><div class="method-name">Schema.org JSON-LD</div>
        <div class="method-desc">Structured data blocks that help AI systems
        understand page context and relationships</div></div>
      </div>
      <div class="method-pillar">
        <div class="method-weight">10</div>
        <div><div class="method-name">llms.txt Presence</div>
        <div class="method-desc">Machine-readable context file that tells AI
        systems what your site is about</div></div>
      </div>
      <div class="method-pillar">
        <div class="method-weight" style="font-size:1rem;color:var(--text-1)">\u2728</div>
        <div><div class="method-name">Markdown Conversion</div>
        <div class="method-desc">HTML-to-markdown token reduction &mdash;
        how much context waste can be eliminated by serving clean markdown
        instead of raw HTML</div></div>
      </div>
    </div>
  </div>
  <div class="cta-box">
    <h3>Run Your Own Audit</h3>
    <p>context-linter is free, open-source, and takes 30 seconds to set up.</p>
    <code class="cta-code">pip install context-linter &amp;&amp; context-cli lint yoursite.com</code>
    <br><br>
    <code class="cta-code">context-cli markdown yoursite.com</code>
    <div class="footer-links">
      <a href="https://pypi.org/project/context-linter/" target="_blank">PyPI</a>
      <a href="https://github.com/nicholasgriffintn/context-cli" target="_blank">GitHub</a>
    </div>
  </div>
  <div class="timestamp">Generated on {now} using context-linter v3.0</div>
</div>
</footer>"""


# ── Chart.js Code Generation ────────────────────────────────────────────────


def build_chart_js(reports: list[dict], cat_stats: dict) -> str:
    """Generate the JavaScript code that creates all Chart.js charts."""
    # Prepare data for charts
    labels = [r["name"] for r in reports]
    scores = [r["overall_score"] for r in reports]
    colors = [score_color(s) for s in scores]

    # Category averages data
    cat_labels = [c for c in CATEGORY_ORDER if c in cat_stats]
    cat_data = {
        "robots": [round(cat_stats[c]["avg_robots"] / 25 * 100) for c in cat_labels],
        "llms": [round(cat_stats[c]["avg_llms"] / 10 * 100) for c in cat_labels],
        "schema": [round(cat_stats[c]["avg_schema"] / 25 * 100) for c in cat_labels],
        "content": [round(cat_stats[c]["avg_content"] / 40 * 100) for c in cat_labels],
    }

    # Word count data (replaces token waste scatter for multi-page audits)
    word_data = [
        {"name": r["name"], "words": r["word_count"], "cat": r["category"]}
        for r in reports
    ]

    # llms.txt adoption
    llms_full = sum(1 for r in reports if r["llms_full_found"])
    llms_only = sum(1 for r in reports if r["llms_found"] and not r["llms_full_found"])
    llms_none = len(reports) - llms_full - llms_only

    # Radar: top 5 vs bottom 5 (normalized to 0-100)
    top5 = reports[:5]
    bot5 = reports[-5:] if len(reports) >= 5 else reports
    top5_avg = [
        round(sum(r["robots_score"] for r in top5) / len(top5) / 25 * 100),
        round(sum(r["llms_score"] for r in top5) / len(top5) / 10 * 100),
        round(sum(r["schema_score"] for r in top5) / len(top5) / 25 * 100),
        round(sum(r["content_score"] for r in top5) / len(top5) / 40 * 100),
    ]
    bot5_avg = [
        round(sum(r["robots_score"] for r in bot5) / len(bot5) / 25 * 100),
        round(sum(r["llms_score"] for r in bot5) / len(bot5) / 10 * 100),
        round(sum(r["schema_score"] for r in bot5) / len(bot5) / 25 * 100),
        round(sum(r["content_score"] for r in bot5) / len(bot5) / 40 * 100),
    ]

    # Token reduction data (sorted by reduction %, descending)
    token_reduction_data = sorted(
        [
            {
                "name": r["name"],
                "reduction": r.get("md_reduction_pct", 0),
                "cat": r["category"],
            }
            for r in reports
            if r.get("md_reduction_pct", 0) > 0
        ],
        key=lambda d: d["reduction"],
        reverse=True,
    )

    chart_data = json.dumps({
        "labels": labels,
        "scores": scores,
        "colors": colors,
        "catLabels": cat_labels,
        "catData": cat_data,
        "wordData": word_data,
        "llmsAdoption": {"full": llms_full, "only": llms_only, "none": llms_none},
        "radarTop": top5_avg,
        "radarBot": bot5_avg,
        "topNames": [r["name"] for r in top5],
        "botNames": [r["name"] for r in bot5],
        "catColors": {c: CATEGORY_COLORS[c][0] for c in CATEGORY_ORDER},
        "tokenReduction": token_reduction_data,
    })

    return f"""<script>
const D = {chart_data};

Chart.defaults.color = '#a1a1aa';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

// ─ Score Distribution ─
const scoreCtx = document.getElementById('scoreDistChart');
scoreCtx.height = D.labels.length * 28;
new Chart(scoreCtx, {{
  type: 'bar',
  data: {{
    labels: D.labels,
    datasets: [{{
      data: D.scores,
      backgroundColor: D.colors.map(c => c + '40'),
      borderColor: D.colors,
      borderWidth: 1,
      borderRadius: 4,
      barThickness: 20,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ctx.parsed.x.toFixed(0) + '/100'
        }}
      }}
    }},
    scales: {{
      x: {{ min: 0, max: 100, grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
      y: {{ grid: {{ display: false }},
           ticks: {{ font: {{ size: 12 }} }} }}
    }}
  }}
}});

// ─ Category Averages ─
new Chart(document.getElementById('categoryChart'), {{
  type: 'bar',
  data: {{
    labels: D.catLabels,
    datasets: [
      {{ label: 'Robots', data: D.catData.robots, backgroundColor: '#818cf8', borderRadius: 4 }},
      {{ label: 'llms.txt', data: D.catData.llms, backgroundColor: '#a78bfa', borderRadius: 4 }},
      {{ label: 'Schema', data: D.catData.schema, backgroundColor: '#c084fc', borderRadius: 4 }},
      {{ label: 'Content', data: D.catData.content, backgroundColor: '#f472b6', borderRadius: 4 }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y + '%' }} }}
    }},
    scales: {{
      y: {{ min: 0, max: 100, title: {{ display: true, text: '% of max pillar score' }},
           grid: {{ color: 'rgba(255,255,255,0.04)' }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ─ Content Volume (Word Count) ─
const catColorMap = D.catColors;
const wordsSorted = D.wordData.slice().sort((a, b) => b.words - a.words);
const wordsLabels = wordsSorted.map(d => d.name);
const wordsValues = wordsSorted.map(d => d.words);
const wordsColors = wordsSorted.map(d => (catColorMap[d.cat] || '#888') + '80');
const wordsBorders = wordsSorted.map(d => catColorMap[d.cat] || '#888');
const wordsCtx = document.getElementById('wordsChart');
wordsCtx.height = Math.max(400, wordsSorted.length * 22);
new Chart(wordsCtx, {{
  type: 'bar',
  data: {{
    labels: wordsLabels,
    datasets: [{{
      data: wordsValues,
      backgroundColor: wordsColors,
      borderColor: wordsBorders,
      borderWidth: 1,
      borderRadius: 4,
      barThickness: 16,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ctx.parsed.x.toLocaleString() + ' words'
        }}
      }}
    }},
    scales: {{
      x: {{ grid: {{ color: 'rgba(255,255,255,0.04)' }},
           title: {{ display: true, text: 'Word Count (across all crawled pages)' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11 }} }} }}
    }}
  }}
}});

// ─ llms.txt Adoption Donut ─
new Chart(document.getElementById('llmsChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['llms.txt + llms-full.txt', 'llms.txt only', 'Neither'],
    datasets: [{{
      data: [D.llmsAdoption.full, D.llmsAdoption.only, D.llmsAdoption.none],
      backgroundColor: ['#22c55e40', '#eab30840', '#ef444440'],
      borderColor: ['#22c55e', '#eab308', '#ef4444'],
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true,
    cutout: '65%',
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }}
    }}
  }}
}});

// ─ Radar: Top 5 vs Bottom 5 ─
new Chart(document.getElementById('radarChart'), {{
  type: 'radar',
  data: {{
    labels: ['Robots (25)', 'llms.txt (10)', 'Schema (25)', 'Content (40)'],
    datasets: [
      {{
        label: 'Top 5 avg (' + D.topNames.join(', ') + ')',
        data: D.radarTop,
        backgroundColor: 'rgba(34,197,94,0.1)',
        borderColor: '#22c55e',
        borderWidth: 2,
        pointBackgroundColor: '#22c55e',
      }},
      {{
        label: 'Bottom 5 avg (' + D.botNames.join(', ') + ')',
        data: D.radarBot,
        backgroundColor: 'rgba(239,68,68,0.1)',
        borderColor: '#ef4444',
        borderWidth: 2,
        pointBackgroundColor: '#ef4444',
      }}
    ]
  }},
  options: {{
    responsive: true,
    scales: {{
      r: {{
        min: 0, max: 100,
        grid: {{ color: 'rgba(255,255,255,0.06)' }},
        angleLines: {{ color: 'rgba(255,255,255,0.06)' }},
        pointLabels: {{ font: {{ size: 12 }} }},
        ticks: {{ display: false }}
      }}
    }},
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16, font: {{ size: 11 }} }} }}
    }}
  }}
}});

// ─ Markdown Token Reduction ─
if (D.tokenReduction && D.tokenReduction.length > 0) {{
  const trLabels = D.tokenReduction.map(d => d.name);
  const trValues = D.tokenReduction.map(d => d.reduction);
  const trColors = D.tokenReduction.map(d => {{
    const pct = d.reduction;
    if (pct >= 80) return '#22c55e';
    if (pct >= 50) return '#eab308';
    return '#ef4444';
  }});
  const trCtx = document.getElementById('tokenReductionChart');
  trCtx.height = Math.max(400, D.tokenReduction.length * 24);
  new Chart(trCtx, {{
    type: 'bar',
    data: {{
      labels: trLabels,
      datasets: [{{
        data: trValues,
        backgroundColor: trColors.map(c => c + '40'),
        borderColor: trColors,
        borderWidth: 1,
        borderRadius: 4,
        barThickness: 18,
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: ctx => ctx.parsed.x.toFixed(1) + '% token reduction'
          }}
        }}
      }},
      scales: {{
        x: {{ min: 0, max: 100,
             grid: {{ color: 'rgba(255,255,255,0.04)' }},
             title: {{ display: true, text: 'Token Reduction (%)' }} }},
        y: {{ grid: {{ display: false }},
             ticks: {{ font: {{ size: 11 }} }} }}
      }}
    }}
  }});
}}

// ─ Table Sorting ─
document.querySelectorAll('#rankingsTable th.sortable').forEach((th, i) => {{
  let asc = false;
  th.addEventListener('click', () => {{
    asc = !asc;
    const tbody = document.querySelector('#rankingsTable tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const colIndex = th.cellIndex;
    rows.sort((a, b) => {{
      let va = a.cells[colIndex].textContent.replace(/[#%\\/]/g, '').trim();
      let vb = b.cells[colIndex].textContent.replace(/[#%\\/]/g, '').trim();
      const na = parseFloat(va), nb = parseFloat(vb);
      if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
      return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});
</script>"""


# ── Main Assembly ────────────────────────────────────────────────────────────


def generate_html(reports: list[dict], cat_stats: dict, insights: list[dict]) -> str:
    """Assemble the complete HTML report."""
    hero = build_hero()
    stats = build_stats_bar(reports, cat_stats)
    rankings = build_rankings_table(reports)
    charts = build_chart_section()
    heatmap = build_bot_heatmap(reports)
    agent_heatmap = build_agent_heatmap(reports)
    insights_html = build_insights_section(insights)
    categories = build_category_sections(reports, cat_stats)
    methodology = build_methodology()
    chart_js = build_chart_js(reports, cat_stats)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>LLM Readiness Benchmark \u2014 50 Tech Docs Sites | context-linter</title>
<meta name="description" content="We audited 50 major tech docs sites for AI readiness. Interactive charts, rankings, and insights.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{CSS}</style>
</head>
<body>
{hero}
{stats}
{rankings}
{charts}
{heatmap}
{agent_heatmap}
{insights_html}
{categories}
{methodology}
{chart_js}
</body>
</html>"""


# ── X Thread Generator ───────────────────────────────────────────────────────


def generate_x_thread(reports: list[dict], insights: list[dict], cat_stats: dict) -> str:
    """Generate an X thread markdown file with key findings."""
    n = len(reports)
    if n == 0:
        return "# No data to generate thread from.\n"

    avg = sum(r["overall_score"] for r in reports) / n
    best = reports[0]
    worst = reports[-1]
    llms_count = sum(1 for r in reports if r["llms_found"])
    total_pages = sum(r["pages_audited"] for r in reports)

    ai_reports = [r for r in reports if r["category"] == "AI Companies"]
    ai_blockers = [r for r in ai_reports
                   if any(not a for a in r["bots"].values())]

    cat_ranking = sorted(cat_stats.items(), key=lambda x: x[1]["avg_overall"], reverse=True)

    tweets = []

    # Tweet 1: Hook
    tweets.append(
        f"We audited {n} of the biggest tech docs sites for LLM readiness.\n\n"
        f"The average score? {avg:.0f}/100.\n\n"
        f"Most tech companies are NOT ready for the AI era.\n\n"
        f"Here's the full breakdown \U0001f9f5\n\n"
        f"#AI #LLM #DevTools"
    )

    # Tweet 2: Winner
    tweets.append(
        f"\U0001f3c6 The #1 most LLM-ready docs site: {best['name']} "
        f"({best['overall_score']:.0f}/100)\n\n"
        f"At the bottom: {worst['name']} ({worst['overall_score']:.0f}/100)\n\n"
        f"[Screenshot: Score Distribution chart]"
    )

    # Tweet 3: Deep crawl depth
    tweets.append(
        f"We didn't just check homepages.\n\n"
        f"We deep-crawled {total_pages} pages across {n} sites "
        f"(up to 10 sub-pages each) to get REAL data, "
        f"not surface-level snapshots.\n\n"
        f"[Screenshot: Rankings table with Pages column]"
    )

    # Tweet 4: The irony
    if ai_blockers:
        tweets.append(
            f"\U0001f926 {len(ai_blockers)} of {len(ai_reports)} AI companies "
            f"block AI crawlers from their OWN documentation.\n\n"
            f"Companies that build AI tools... blocking AI.\n\n"
            f"[Screenshot: Bot Access Heatmap, AI Companies section]"
        )

    # Tweet 5: llms.txt
    tweets.append(
        f"\U0001f4c4 Only {llms_count}/{n} sites have llms.txt.\n\n"
        f"It's the simplest optimization: a single file that tells AI systems "
        f"what your site is about.\n\n"
        f"[Screenshot: llms.txt Adoption donut chart]"
    )

    # Tweet 6: Category comparison
    if cat_ranking:
        tweets.append(
            "\U0001f4ca Category rankings:\n\n"
            + "\n".join(f"{i+1}. {c} \u2014 avg {s['avg_overall']:.0f}/100"
                        for i, (c, s) in enumerate(cat_ranking))
            + "\n\n[Screenshot: Category Averages chart]"
        )

    # Tweet 7: Best in each category
    best_per_cat = []
    for cat in CATEGORY_ORDER:
        s = cat_stats.get(cat)
        if s:
            best_per_cat.append(f"\u2022 {cat}: {s['best']['name']} "
                                f"({s['best']['overall_score']:.0f})")
    if best_per_cat:
        tweets.append(
            "\U0001f3c5 Best in class:\n\n" + "\n".join(best_per_cat)
            + "\n\n[Screenshot: Category Deep Dives]"
        )

    # Tweet 8: Insights
    for ins in insights:
        if ins["tag"] in ("Schema.org Impact", "llms.txt Correlation"):
            tweets.append(f"\U0001f50d {ins['text']}\n\n{ins['detail']}")
            break

    # Tweet 9: CTA
    tweets.append(
        f"\U0001f680 Want to check your own site's LLM readiness?\n\n"
        f"pip install context-linter\n"
        f"context-cli lint yoursite.com\n\n"
        f"Full interactive report with all {n} sites: [link to report]\n\n"
        f"#AI #LLM #SEO #DevTools"
    )

    # Format as markdown
    lines = ["# X Thread: Tech Docs LLM Readiness Benchmark\n"]
    lines.append(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n")
    lines.append("---\n")
    for i, tweet in enumerate(tweets, 1):
        lines.append(f"## Tweet {i}/{len(tweets)}\n")
        lines.append(tweet + "\n")
        lines.append(f"\n*Characters: {len(tweet)}*\n")
        lines.append("---\n")

    return "\n".join(lines)


# ── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    data_path = Path(__file__).parent / "data.json"
    if not data_path.exists():
        print("Error: data.json not found. Run run_benchmark.py first.")
        sys.exit(1)

    print("Loading benchmark data...")
    data = load_data(data_path)
    reports = process_reports(data)
    print(f"  Processed {len(reports)} reports")

    cat_stats = compute_category_stats(reports)
    insights = compute_insights(reports, cat_stats)
    print(f"  Generated {len(insights)} insights")

    html = generate_html(reports, cat_stats, insights)
    out_path = Path(__file__).parent / "report.html"
    out_path.write_text(html)
    print(f"  Report: {out_path} ({len(html):,} bytes)")

    thread = generate_x_thread(reports, insights, cat_stats)
    thread_path = Path(__file__).parent / "x_thread.md"
    thread_path.write_text(thread)
    print(f"  X thread: {thread_path}")

    print("\nDone! Open report.html in a browser to view.")


if __name__ == "__main__":
    main()
