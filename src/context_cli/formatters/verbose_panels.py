"""Per-pillar verbose panels for Context Lint reports.

Each function renders a Rich Panel with detailed scoring breakdown,
formulas, and per-item details for one audit pillar.
Informational signal panels (RSL, Content-Usage, E-E-A-T) use blue borders.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from context_cli.core.models import (
    AuditReport,
    SiteAuditReport,
)
from context_cli.core.scoring import (
    CONTENT_CODE_BONUS,
    CONTENT_HEADING_BONUS,
    CONTENT_LIST_BONUS,
    CONTENT_MAX,
    CONTENT_WORD_TIERS,
    HIGH_VALUE_TYPES,
    LLMS_TXT_MAX,
    ROBOTS_MAX,
    SCHEMA_BASE_SCORE,
    SCHEMA_HIGH_VALUE_BONUS,
    SCHEMA_MAX,
    SCHEMA_STANDARD_BONUS,
)

# ── Pillar max scores ────────────────────────────────────────────────────────

PILLAR_MAX: dict[str, int] = {
    "robots": ROBOTS_MAX,
    "llms_txt": LLMS_TXT_MAX,
    "schema_org": SCHEMA_MAX,
    "content": CONTENT_MAX,
}


# ── Color helpers ────────────────────────────────────────────────────────────


def score_color(score: float, pillar: str) -> Text:
    """Return a Rich Text with the score colored by threshold (green/yellow/red)."""
    max_pts = PILLAR_MAX[pillar]
    ratio = score / max_pts if max_pts else 0
    if ratio >= 0.7:
        color = "green"
    elif ratio >= 0.4:
        color = "yellow"
    else:
        color = "red"
    return Text(f"{score}", style=color)


def overall_color(score: float) -> str:
    """Return a Rich color string for an overall 0-100 score."""
    if score >= 70:
        return "green"
    elif score >= 40:
        return "yellow"
    return "red"


def _border_color(score: float, max_pts: float) -> str:
    """Return a border color based on score ratio."""
    ratio = score / max_pts if max_pts else 0
    if ratio >= 0.7:
        return "green"
    elif ratio >= 0.4:
        return "yellow"
    return "red"


# ── Robots Verbose Panel ────────────────────────────────────────────────────


def render_robots_verbose(report: AuditReport | SiteAuditReport) -> Panel:
    """Render detailed robots.txt panel with per-bot details and scoring formula."""
    robots = report.robots
    lines: list[str] = []

    color = _border_color(robots.score, ROBOTS_MAX)
    score_text = f"[{color}]{robots.score}[/{color}]/{ROBOTS_MAX}"
    lines.append(f"[bold]Robots.txt AI Bot Access[/bold] — Score: {score_text}")

    if robots.found and robots.bots:
        allowed_count = sum(1 for b in robots.bots if b.allowed)
        total = len(robots.bots)
        lines.append("")
        lines.append(
            f"  [dim]Formula:[/dim] {allowed_count}/{total} × {ROBOTS_MAX} = {robots.score}"
        )
        lines.append("")
        for bot in robots.bots:
            status = "[green]Allowed[/green]" if bot.allowed else "[red]Blocked[/red]"
            detail = f" — {bot.detail}" if bot.detail else ""
            lines.append(f"  {bot.bot}: {status}{detail}")
    else:
        lines.append("")
        lines.append("  [yellow]robots.txt not found or inaccessible[/yellow]")
        lines.append("  [dim]All bots assumed allowed (score 0 — cannot verify access)[/dim]")

    return Panel(
        "\n".join(lines),
        title="Robots.txt Detail",
        border_style=color,
    )


# ── llms.txt Verbose Panel ──────────────────────────────────────────────────


def render_llms_verbose(report: AuditReport | SiteAuditReport) -> Panel:
    """Render detailed llms.txt panel with binary scoring explanation."""
    llms = report.llms_txt
    color = _border_color(llms.score, LLMS_TXT_MAX)
    score_text = f"[{color}]{llms.score}[/{color}]/{LLMS_TXT_MAX}"
    lines: list[str] = [f"[bold]llms.txt Presence[/bold] — Score: {score_text}"]

    lines.append("")
    lines.append(
        f"  [dim]Scoring:[/dim] Binary — {LLMS_TXT_MAX} if found, 0 if not"
    )

    if llms.found:
        lines.append(f"  [green]Found at:[/green] {llms.url}")
        if llms.detail:
            lines.append(f"  Detail: {llms.detail}")
    else:
        lines.append("  [red]Not found[/red]")
        lines.append("  Paths checked: /llms.txt, /.well-known/llms.txt")

    return Panel(
        "\n".join(lines),
        title="llms.txt Detail",
        border_style=color,
    )


# ── Schema Verbose Panel ────────────────────────────────────────────────────


def render_schema_verbose(report: AuditReport | SiteAuditReport) -> Panel:
    """Render detailed Schema.org panel with formula and property names."""
    schema = report.schema_org
    color = _border_color(schema.score, SCHEMA_MAX)
    score_text = f"[{color}]{schema.score}[/{color}]/{SCHEMA_MAX}"
    lines: list[str] = [f"[bold]Schema.org JSON-LD[/bold] — Score: {score_text}"]

    if schema.blocks_found > 0:
        unique_types = {s.schema_type for s in schema.schemas}
        n_high = sum(1 for t in unique_types if t in HIGH_VALUE_TYPES)
        n_std = len(unique_types) - n_high
        raw = (
            SCHEMA_BASE_SCORE
            + SCHEMA_HIGH_VALUE_BONUS * n_high
            + SCHEMA_STANDARD_BONUS * n_std
        )
        capped = min(SCHEMA_MAX, raw)
        lines.append("")
        lines.append(
            f"  [dim]Formula:[/dim] base {SCHEMA_BASE_SCORE}"
            f" + {SCHEMA_HIGH_VALUE_BONUS} × {n_high} high-value"
            f" + {SCHEMA_STANDARD_BONUS} × {n_std} standard"
            f" = {raw}"
            + (f" → capped at {SCHEMA_MAX}" if raw > SCHEMA_MAX else "")
            + f" = {capped}"
        )
        lines.append(f"  Blocks found: {schema.blocks_found}")
        lines.append("")
        for s in schema.schemas:
            props = ", ".join(s.properties) if s.properties else "(no properties)"
            lines.append(f"  @type: [bold]{s.schema_type}[/bold]")
            lines.append(f"    Properties: {props}")
    else:
        lines.append("")
        lines.append("  [yellow]No JSON-LD structured data found[/yellow]")

    return Panel(
        "\n".join(lines),
        title="Schema.org Detail",
        border_style=color,
    )


# ── Content Verbose Panel ───────────────────────────────────────────────────


def render_content_verbose(report: AuditReport | SiteAuditReport) -> Panel:
    """Render detailed content panel with word tier breakdown and bonus formula."""
    content = report.content
    color = _border_color(content.score, CONTENT_MAX)
    score_text = f"[{color}]{content.score}[/{color}]/{CONTENT_MAX}"
    lines: list[str] = [f"[bold]Content Density[/bold] — Score: {score_text}"]

    lines.append("")
    lines.append(f"  Word count: [bold]{content.word_count}[/bold]")
    lines.append(f"  Char count: {content.char_count}")

    # Word tier breakdown — highlight the active tier
    lines.append("")
    lines.append("  [dim]Word count tiers:[/dim]")
    active_tier_score = 0
    for min_words, tier_score in CONTENT_WORD_TIERS:
        if content.word_count >= min_words and active_tier_score == 0:
            lines.append(f"    [green]→ {min_words}+ words = {tier_score} pts (active)[/green]")
            active_tier_score = tier_score
        else:
            lines.append(f"    [dim]  {min_words}+ words = {tier_score} pts[/dim]")
    if active_tier_score == 0:
        lines.append("    [red]  < {0} words = 0 pts (below minimum)[/red]".format(
            CONTENT_WORD_TIERS[-1][0]
        ))

    # Bonus breakdown
    heading_pts = CONTENT_HEADING_BONUS if content.has_headings else 0
    list_pts = CONTENT_LIST_BONUS if content.has_lists else 0
    code_pts = CONTENT_CODE_BONUS if content.has_code_blocks else 0
    raw_total = active_tier_score + heading_pts + list_pts + code_pts
    capped = min(CONTENT_MAX, raw_total)

    lines.append("")
    lines.append(
        f"  [dim]Formula:[/dim] {active_tier_score} base"
        f" + {heading_pts} headings"
        f" + {list_pts} lists"
        f" + {code_pts} code"
        f" = {raw_total}"
        + (f" → capped at {CONTENT_MAX}" if raw_total > CONTENT_MAX else "")
        + f" = {capped}/{CONTENT_MAX}"
    )

    lines.append("")
    h_status = "[green]Yes[/green]" if content.has_headings else "[red]No[/red]"
    l_status = "[green]Yes[/green]" if content.has_lists else "[red]No[/red]"
    c_status = "[green]Yes[/green]" if content.has_code_blocks else "[red]No[/red]"
    lines.append(
        f"  Headings: {h_status} (+{CONTENT_HEADING_BONUS})"
        f"  Lists: {l_status} (+{CONTENT_LIST_BONUS})"
        f"  Code blocks: {c_status} (+{CONTENT_CODE_BONUS})"
    )

    return Panel(
        "\n".join(lines),
        title="Content Detail",
        border_style=color,
    )


# ── Token Analysis Panel ───────────────────────────────────────────────────


def render_token_analysis_verbose(
    report: AuditReport | SiteAuditReport,
) -> Panel | None:
    """Render token analysis panel with waste metrics, lint checks, and diagnostics."""
    if report.lint_result is None:
        return None

    lr = report.lint_result
    waste_color = (
        "green" if lr.context_waste_pct < 30
        else ("yellow" if lr.context_waste_pct < 70 else "red")
    )

    lines: list[str] = [
        "[bold]Token Analysis[/bold] [dim](context efficiency metrics)[/dim]",
        "",
        f"  Raw HTML tokens:     {lr.raw_tokens:>10,}",
        f"  Clean MD tokens:     {lr.clean_tokens:>10,}",
        f"  Context Waste:       [{waste_color}]{lr.context_waste_pct:>9.1f}%[/{waste_color}]",
    ]
    if lr.raw_tokens > 0:
        wasted = lr.raw_tokens - lr.clean_tokens
        lines[-1] += f"  ({wasted:,} wasted tokens)"

    if lr.checks:
        lines.append("")
        lines.append("  [bold]Lint Checks:[/bold]")
        for check in lr.checks:
            if check.severity == "warn":
                status = "[yellow]WARN[/yellow]"
            elif check.passed:
                status = "[green]PASS[/green]"
            else:
                status = "[red]FAIL[/red]"
            lines.append(f"    {status} {check.name}: {check.detail}")

    if lr.diagnostics:
        lines.append("")
        lines.append("  [bold]Diagnostics:[/bold]")
        for d in lr.diagnostics:
            d_color = (
                "red" if d.severity == "error"
                else ("yellow" if d.severity == "warn" else "cyan")
            )
            lines.append(f"    [{d_color}]{d.code}[/{d_color}]  {d.message}")

    return Panel(
        "\n".join(lines),
        title="Token Analysis",
        border_style=waste_color,
    )


# ── Informational Signal Panels (not scored) ──────────────────────────────


def render_rsl_verbose(report: AuditReport | SiteAuditReport) -> Panel | None:
    """Render RSL (Robots Specification Language) informational panel."""
    if report.rsl is None:
        return None

    rsl = report.rsl
    lines: list[str] = ["[bold]RSL Analysis[/bold] [dim](informational — not scored)[/dim]"]

    if not (rsl.has_crawl_delay or rsl.has_sitemap_directive or rsl.has_ai_specific_rules):
        lines.append("")
        lines.append(f"  {rsl.detail}")
        return Panel("\n".join(lines), title="RSL Detail", border_style="blue")

    lines.append("")
    if rsl.has_crawl_delay:
        lines.append(f"  Crawl-delay: [bold]{rsl.crawl_delay_value}s[/bold]")

    if rsl.has_sitemap_directive:
        lines.append(f"  Sitemap directives: {len(rsl.sitemap_urls)}")
        for url in rsl.sitemap_urls:
            lines.append(f"    {url}")

    if rsl.has_ai_specific_rules:
        agents = ", ".join(rsl.ai_specific_agents)
        lines.append(f"  AI-specific User-agent blocks: {agents}")

    return Panel("\n".join(lines), title="RSL Detail", border_style="blue")


def render_content_usage_verbose(
    report: AuditReport | SiteAuditReport,
) -> Panel | None:
    """Render IETF Content-Usage header informational panel."""
    if report.content_usage is None:
        return None

    cu = report.content_usage
    lines: list[str] = [
        "[bold]Content-Usage Header[/bold] [dim](informational — not scored)[/dim]"
    ]

    if not cu.header_found:
        lines.append("")
        lines.append("  [dim]Content-Usage header not found[/dim]")
        return Panel("\n".join(lines), title="Content-Usage Detail", border_style="blue")

    lines.append("")
    lines.append(f"  Header value: [bold]{cu.header_value}[/bold]")
    lines.append("")

    train_icon = "[green]Yes[/green]" if cu.allows_training else "[red]No[/red]"
    search_icon = "[green]Yes[/green]" if cu.allows_search else "[red]No[/red]"
    lines.append(f"  Training allowed: {train_icon}")
    lines.append(f"  Search allowed: {search_icon}")

    return Panel("\n".join(lines), title="Content-Usage Detail", border_style="blue")


def render_eeat_verbose(report: AuditReport | SiteAuditReport) -> Panel | None:
    """Render E-E-A-T (Experience, Expertise, Authority, Trust) informational panel."""
    if report.eeat is None:
        return None

    eeat = report.eeat
    lines: list[str] = [
        "[bold]E-E-A-T Signals[/bold] [dim](informational — not scored)[/dim]"
    ]

    has_any = (
        eeat.has_author or eeat.has_date or eeat.has_about_page
        or eeat.has_contact_info or eeat.has_citations or eeat.trust_signals
    )
    if not has_any:
        lines.append("")
        lines.append(f"  {eeat.detail}")
        return Panel("\n".join(lines), title="E-E-A-T Detail", border_style="blue")

    lines.append("")
    if eeat.has_author:
        name = eeat.author_name or "(detected)"
        lines.append(f"  Author: [bold]{name}[/bold]")
    else:
        lines.append("  Author: [dim]not found[/dim]")

    date_icon = "[green]Yes[/green]" if eeat.has_date else "[red]No[/red]"
    lines.append(f"  Publication date: {date_icon}")

    about_icon = "[green]Yes[/green]" if eeat.has_about_page else "[red]No[/red]"
    lines.append(f"  About page link: {about_icon}")

    contact_icon = "[green]Yes[/green]" if eeat.has_contact_info else "[red]No[/red]"
    lines.append(f"  Contact info: {contact_icon}")

    if eeat.has_citations:
        lines.append(f"  External citations: [bold]{eeat.citation_count}[/bold]")
    else:
        lines.append("  External citations: [dim]none[/dim]")

    if eeat.trust_signals:
        signals = ", ".join(eeat.trust_signals)
        lines.append(f"  Trust signals: {signals}")

    return Panel("\n".join(lines), title="E-E-A-T Detail", border_style="blue")
