"""Verbose output renderer for AEO audit reports.

Provides detailed scoring breakdowns, per-pillar panels with formulas,
and actionable recommendations. Used by main.py when --verbose is passed.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from aeo_cli.core.models import (
    AuditReport,
    SiteAuditReport,
)
from aeo_cli.core.scoring import (
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


# ── Recommendations Engine ──────────────────────────────────────────────────


def generate_recommendations(report: AuditReport | SiteAuditReport) -> list[str]:
    """Generate actionable recommendations based on the audit report."""
    recs: list[str] = []

    # Robots recommendations
    if report.robots.found and report.robots.bots:
        blocked = [b.bot for b in report.robots.bots if not b.allowed]
        if blocked:
            bots_str = ", ".join(blocked)
            recs.append(f"Unblock {bots_str} in robots.txt")
    elif not report.robots.found:
        recs.append("Create a robots.txt file to explicitly allow AI bots")

    # llms.txt recommendations
    if not report.llms_txt.found:
        recs.append(f"Create /llms.txt to describe your site for AI agents (+{LLMS_TXT_MAX} pts)")

    # Schema recommendations
    if report.schema_org.blocks_found == 0:
        recs.append("Add JSON-LD structured data (Schema.org) to your pages")
    elif report.schema_org.score < SCHEMA_MAX:
        remaining = SCHEMA_MAX - report.schema_org.score
        if remaining > 0:
            more = -(-remaining // SCHEMA_HIGH_VALUE_BONUS)  # ceil division
            recs.append(
                f"Add {more} more high-value Schema.org type(s) to reach max score"
                f" (e.g., FAQPage, HowTo, Article, Product, Recipe)"
            )

    # Content recommendations
    if report.content.word_count == 0:
        recs.append("Add meaningful text content to your pages")
    else:
        # Find the next tier up (closest one above current word count)
        # Tiers are sorted descending, so iterate reversed to find lowest first
        current_tier = 0
        for mw, ts in CONTENT_WORD_TIERS:
            if report.content.word_count >= mw:
                current_tier = ts
                break
        next_tier = None
        for min_words, tier_score in reversed(CONTENT_WORD_TIERS):
            if report.content.word_count < min_words:
                next_tier = (min_words, tier_score)
                break
        if next_tier:
            min_words, tier_score = next_tier
            words_needed = min_words - report.content.word_count
            gain = tier_score - current_tier
            if gain > 0:
                recs.append(
                    f"Add {words_needed} more words to reach"
                    f" the {min_words}+ tier (+{gain} pts)"
                )
        # Structure bonuses
        if not report.content.has_headings:
            recs.append(
                f"Add headings (h1-h6) to structure your content (+{CONTENT_HEADING_BONUS} pts)"
            )
        if not report.content.has_lists:
            recs.append(f"Add bullet/numbered lists for scannability (+{CONTENT_LIST_BONUS} pts)")

    return recs


def render_recommendations(report: AuditReport | SiteAuditReport) -> Panel | None:
    """Render recommendations panel. Returns None if no recommendations."""
    recs = generate_recommendations(report)
    if not recs:
        return None

    lines = ["[bold]How to improve your AEO score:[/bold]", ""]
    for i, rec in enumerate(recs, 1):
        lines.append(f"  {i}. {rec}")

    return Panel(
        "\n".join(lines),
        title="Recommendations",
        border_style="cyan",
    )


# ── Compositors ─────────────────────────────────────────────────────────────


def render_verbose_single(report: AuditReport, console: Console) -> None:
    """Render all verbose panels for a single-page audit report."""
    console.print()
    console.print(
        "[bold]Scoring Methodology:[/bold] Content (40pts) + Robots (25pts) "
        "+ Schema (25pts) + llms.txt (10pts) = 100pts max"
    )

    console.print(render_robots_verbose(report))
    console.print(render_llms_verbose(report))
    console.print(render_schema_verbose(report))
    console.print(render_content_verbose(report))

    rec_panel = render_recommendations(report)
    if rec_panel:
        console.print(rec_panel)


def render_verbose_site(report: SiteAuditReport, console: Console) -> None:
    """Render all verbose panels for a multi-page site audit report."""
    console.print()
    console.print(
        "[bold]Scoring Methodology:[/bold] Content (40pts) + Robots (25pts) "
        "+ Schema (25pts) + llms.txt (10pts) = 100pts max"
    )

    # Site-wide panels (robots + llms.txt are the same across the site)
    console.print(render_robots_verbose(report))
    console.print(render_llms_verbose(report))

    # Aggregated schema + content panels
    console.print(render_schema_verbose(report))
    console.print(render_content_verbose(report))

    # Per-page breakdown panels
    if report.pages:
        console.print()
        console.print("[bold]Per-Page Detail:[/bold]")
        for page in report.pages:
            page_lines: list[str] = []
            # Schema for this page
            if page.schema_org.schemas:
                for s in page.schema_org.schemas:
                    props = ", ".join(s.properties[:5])
                    if len(s.properties) > 5:
                        props += f"... (+{len(s.properties) - 5} more)"
                    page_lines.append(f"  Schema: @type={s.schema_type} [{props}]")
            else:
                page_lines.append("  Schema: [dim]No JSON-LD found[/dim]")

            # Content for this page
            page_lines.append(
                f"  Content: {page.content.word_count} words,"
                f" score {page.content.score}/{CONTENT_MAX}"
            )

            if page.errors:
                for err in page.errors:
                    page_lines.append(f"  [red]Error: {err}[/red]")

            page_color = _border_color(
                page.schema_org.score + page.content.score,
                SCHEMA_MAX + CONTENT_MAX,
            )
            console.print(Panel(
                "\n".join(page_lines),
                title=page.url,
                border_style=page_color,
            ))

    # Aggregation explanation
    _render_aggregation_explanation(report, console)

    # Recommendations
    rec_panel = render_recommendations(report)
    if rec_panel:
        console.print(rec_panel)


def _render_aggregation_explanation(
    report: SiteAuditReport, console: Console,
) -> None:
    """Render panel explaining how per-page scores are aggregated."""
    if not report.pages:
        return

    lines = [
        "[bold]Score Aggregation Method[/bold]",
        "",
        "  Per-page scores (Schema + Content) are weighted by URL depth:",
        "    Depth 0-1 (homepage, top sections): weight 3",
        "    Depth 2: weight 2",
        "    Depth 3+: weight 1",
        "",
        "  Robots.txt and llms.txt scores are site-wide (not averaged).",
    ]

    # Show the actual weights used
    from urllib.parse import urlparse

    weight_lines: list[str] = []
    for page in report.pages:
        path = urlparse(page.url).path.strip("/")
        depth = len(path.split("/")) if path else 0
        if depth <= 1:
            w = 3
        elif depth == 2:
            w = 2
        else:
            w = 1
        weight_lines.append(f"    {page.url}: depth {depth} → weight {w}")

    if weight_lines:
        lines.append("")
        lines.extend(weight_lines)

    console.print(Panel(
        "\n".join(lines),
        title="Aggregation Detail",
        border_style="blue",
    ))
