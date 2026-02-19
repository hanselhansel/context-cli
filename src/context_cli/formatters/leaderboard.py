"""Leaderboard formatter — sorted markdown/JSON tables for batch URL comparison."""

from __future__ import annotations

import json

from context_cli.core.models import AuditReport


def _is_rag_ready(report: AuditReport, waste_threshold: float) -> bool:
    """Determine if a URL is RAG-ready based on lint checks.

    RAG Ready = llms.txt present AND all AI bots allowed AND waste < threshold.
    """
    llms_present = report.llms_txt.found

    bots_ok = True
    if report.robots.found and report.robots.bots:
        bots_ok = all(b.allowed for b in report.robots.bots)

    waste_ok = True
    if report.lint_result:
        waste_ok = report.lint_result.context_waste_pct < waste_threshold

    return llms_present and bots_ok and waste_ok


def _sort_reports(reports: list[AuditReport]) -> list[AuditReport]:
    """Sort reports by context waste % ascending (cleanest first).

    Reports without lint_result go to the end with waste treated as 100%.
    """

    def sort_key(r: AuditReport) -> float:
        if r.lint_result:
            return r.lint_result.context_waste_pct
        return 100.0

    return sorted(reports, key=sort_key)


def format_leaderboard_md(
    reports: list[AuditReport],
    waste_threshold: float = 70.0,
) -> str:
    """Format reports as a sorted markdown leaderboard table.

    Columns: #, Target URL, Raw Tokens, MD Tokens, Context Waste %, llms.txt,
             Bots OK, RAG Ready?
    Sorted by: Context Waste % ascending (cleanest first).
    """
    sorted_reports = _sort_reports(reports)

    lines = [
        "# Context CLI Leaderboard",
        "",
        (
            f"> {len(reports)} URLs audited"
            f" | Sorted by Context Waste % (lowest first)"
            f" | RAG Ready threshold: {waste_threshold:.0f}%"
        ),
        "",
        (
            "| # | Target URL | Raw Tokens | MD Tokens"
            " | Context Waste % | llms.txt | Bots OK | RAG Ready? |"
        ),
        (
            "|--:|------------|----------:|----------:"
            "|----------------:|:--------:|:-------:|:----------:|"
        ),
    ]

    for i, report in enumerate(sorted_reports, 1):
        raw = report.lint_result.raw_tokens if report.lint_result else 0
        clean = report.lint_result.clean_tokens if report.lint_result else 0
        waste = report.lint_result.context_waste_pct if report.lint_result else 0.0

        llms = "Yes" if report.llms_txt.found else "No"

        bots_ok = "Yes"
        if report.robots.found and report.robots.bots:
            if any(not b.allowed for b in report.robots.bots):
                bots_ok = "No"

        rag = "Yes" if _is_rag_ready(report, waste_threshold) else "No"

        lines.append(
            f"| {i} | {report.url} | {raw:,} | {clean:,}"
            f" | {waste:.0f}% | {llms} | {bots_ok} | {rag} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_leaderboard_json(
    reports: list[AuditReport],
    waste_threshold: float = 70.0,
) -> str:
    """Format reports as a JSON leaderboard."""
    sorted_reports = _sort_reports(reports)

    entries = []
    for i, report in enumerate(sorted_reports, 1):
        raw = report.lint_result.raw_tokens if report.lint_result else 0
        clean = report.lint_result.clean_tokens if report.lint_result else 0
        waste = (
            report.lint_result.context_waste_pct if report.lint_result else 0.0
        )

        entries.append(
            {
                "rank": i,
                "url": report.url,
                "raw_tokens": raw,
                "clean_tokens": clean,
                "context_waste_pct": waste,
                "llms_txt": report.llms_txt.found,
                "bots_ok": (
                    all(b.allowed for b in report.robots.bots)
                    if report.robots.bots
                    else True
                ),
                "rag_ready": _is_rag_ready(report, waste_threshold),
            }
        )

    return json.dumps(
        {"leaderboard": entries, "waste_threshold": waste_threshold}, indent=2
    )
