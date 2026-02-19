"""Leaderboard formatters — markdown and JSON output for batch URL comparison."""

from __future__ import annotations

import json

from context_cli.core.models import AuditReport


def _waste_pct(report: AuditReport) -> float:
    """Extract context waste percentage from a report."""
    if report.lint_result:
        return report.lint_result.context_waste_pct
    return report.content.context_waste_pct


def _rag_ready(waste: float, threshold: float) -> str:
    """Return RAG Ready status based on waste threshold."""
    return "Yes" if waste < threshold else "No"


def _sort_reports(reports: list[AuditReport]) -> list[AuditReport]:
    """Sort reports by waste percentage ascending (lowest waste first)."""
    return sorted(reports, key=_waste_pct)


def format_leaderboard_md(
    reports: list[AuditReport],
    waste_threshold: float = 70.0,
) -> str:
    """Format a leaderboard as a Markdown table sorted by token efficiency."""
    sorted_reports = _sort_reports(reports)
    lines: list[str] = []
    lines.append("# Context Leaderboard")
    lines.append("")
    lines.append("| Rank | URL | Score | Waste % | RAG Ready |")
    lines.append("|------|-----|-------|---------|-----------|")

    for i, report in enumerate(sorted_reports, start=1):
        waste = _waste_pct(report)
        ready = _rag_ready(waste, waste_threshold)
        lines.append(
            f"| {i} | {report.url} | {report.overall_score:.1f} "
            f"| {waste:.1f}% | {ready} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_leaderboard_json(
    reports: list[AuditReport],
    waste_threshold: float = 70.0,
) -> str:
    """Format a leaderboard as JSON sorted by token efficiency."""
    sorted_reports = _sort_reports(reports)
    entries = []
    for i, report in enumerate(sorted_reports, start=1):
        waste = _waste_pct(report)
        entries.append({
            "rank": i,
            "url": report.url,
            "score": report.overall_score,
            "waste_pct": round(waste, 1),
            "rag_ready": waste < waste_threshold,
        })

    return json.dumps({"leaderboard": entries}, indent=2)
