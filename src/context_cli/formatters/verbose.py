"""Verbose output compositor for Context Lint reports.

Orchestrates per-pillar panels, recommendations, and aggregation
explanations into the full --verbose CLI output.
"""

from __future__ import annotations

from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel

from context_cli.core.models import (
    AuditReport,
    SiteAuditReport,
)
from context_cli.core.scoring import CONTENT_MAX, SCHEMA_MAX
from context_cli.formatters.recommendations import (
    generate_recommendations,
    render_recommendations,
)
from context_cli.formatters.verbose_panels import (
    PILLAR_MAX,
    _border_color,
    overall_color,
    render_content_usage_verbose,
    render_content_verbose,
    render_eeat_verbose,
    render_llms_verbose,
    render_robots_verbose,
    render_rsl_verbose,
    render_schema_verbose,
    score_color,
)

# Re-export public API so existing consumers can import from this module
__all__ = [
    "PILLAR_MAX",
    "generate_recommendations",
    "overall_color",
    "render_content_usage_verbose",
    "render_content_verbose",
    "render_eeat_verbose",
    "render_llms_verbose",
    "render_recommendations",
    "render_robots_verbose",
    "render_rsl_verbose",
    "render_schema_verbose",
    "render_verbose_single",
    "render_verbose_site",
    "score_color",
]


# ── Compositors ─────────────────────────────────────────────────────────────


def _render_informational_panels(
    report: AuditReport | SiteAuditReport, console: Console,
) -> None:
    """Render informational signal panels (RSL, Content-Usage, E-E-A-T) if present."""
    rsl_panel = render_rsl_verbose(report)
    if rsl_panel:
        console.print(rsl_panel)

    cu_panel = render_content_usage_verbose(report)
    if cu_panel:
        console.print(cu_panel)

    eeat_panel = render_eeat_verbose(report)
    if eeat_panel:
        console.print(eeat_panel)


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

    _render_informational_panels(report, console)

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

    # Informational signal panels
    _render_informational_panels(report, console)

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
