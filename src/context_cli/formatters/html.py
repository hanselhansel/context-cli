"""HTML report formatter for AEO audit reports — Lighthouse-style self-contained HTML."""

from __future__ import annotations

import html as html_lib

from context_cli.core.models import AuditReport, SiteAuditReport


def _score_color(score: float) -> str:
    """Return hex color for a score value (green/yellow/red)."""
    if score >= 80:
        return "#0cce6b"
    if score >= 50:
        return "#ffa400"
    return "#ff4e42"


def _gauge_svg(score: float) -> str:
    """Generate an SVG circular gauge for the overall score."""
    color = _score_color(score)
    # Circle parameters
    r = 56
    circumference = 2 * 3.14159 * r
    offset = circumference * (1 - score / 100)
    return f"""<svg width="140" height="140" viewBox="0 0 140 140">
  <circle cx="70" cy="70" r="{r}" fill="none" stroke="#e0e0e0" stroke-width="8"/>
  <circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="8"
    stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
    stroke-linecap="round" transform="rotate(-90 70 70)"/>
  <text x="70" y="70" text-anchor="middle" dominant-baseline="central"
    font-size="32" font-weight="bold" fill="{color}">{score}</text>
</svg>"""


def _pillar_bar(label: str, score: float, max_score: float) -> str:
    """Generate an HTML bar for a pillar score."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    color = _score_color(score / max_score * 100 if max_score > 0 else 0)
    return f"""<div class="pillar-row">
  <div class="pillar-label">{html_lib.escape(label)}</div>
  <div class="pillar-bar-bg">
    <div class="pillar-bar-fill" style="width:{pct:.1f}%;background:{color}"></div>
  </div>
  <div class="pillar-score">{score}/{max_score}</div>
</div>"""


def _pillar_detail(label: str, detail: str) -> str:
    """Generate an HTML detail section for a pillar."""
    return f"""<div class="detail-section">
  <h3>{html_lib.escape(label)}</h3>
  <p>{html_lib.escape(detail)}</p>
</div>"""


def _errors_section(errors: list[str]) -> str:
    """Generate an HTML errors section."""
    if not errors:
        return ""
    items = "".join(f"<li>{html_lib.escape(e)}</li>" for e in errors)
    return f"""<div class="errors-section">
  <h3>Errors</h3>
  <ul>{items}</ul>
</div>"""


_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5; color: #333; line-height: 1.6; }
.container { max-width: 800px; margin: 0 auto; padding: 24px; }
.header { text-align: center; padding: 32px 0; background: #fff; border-radius: 8px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.header h1 { font-size: 20px; color: #555; margin-bottom: 16px; }
.header .url { font-size: 14px; color: #888; word-break: break-all; }
.pillars { background: #fff; border-radius: 8px; padding: 24px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.pillars h2 { font-size: 16px; margin-bottom: 16px; color: #555; }
.pillar-row { display: flex; align-items: center; margin-bottom: 12px; }
.pillar-label { width: 180px; font-size: 14px; font-weight: 500; }
.pillar-bar-bg { flex: 1; height: 12px; background: #e0e0e0; border-radius: 6px;
  margin: 0 12px; overflow: hidden; }
.pillar-bar-fill { height: 100%; border-radius: 6px; transition: width 0.3s; }
.pillar-score { width: 70px; text-align: right; font-size: 14px; font-weight: 600; }
.details { background: #fff; border-radius: 8px; padding: 24px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.details h2 { font-size: 16px; margin-bottom: 16px; color: #555; }
.detail-section { margin-bottom: 16px; padding-bottom: 16px;
  border-bottom: 1px solid #eee; }
.detail-section:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.detail-section h3 { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.detail-section p { font-size: 13px; color: #666; }
.errors-section { background: #fff3f3; border-radius: 8px; padding: 24px;
  margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.errors-section h3 { font-size: 14px; font-weight: 600; color: #cc0000; margin-bottom: 8px; }
.errors-section ul { padding-left: 20px; }
.errors-section li { font-size: 13px; color: #666; margin-bottom: 4px; }
.pages-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
.pages-table th, .pages-table td { padding: 8px 12px; text-align: left;
  border-bottom: 1px solid #eee; font-size: 13px; }
.pages-table th { font-weight: 600; color: #555; }
.pages-table td:first-child { word-break: break-all; }
.site-info { font-size: 13px; color: #666; margin-bottom: 16px; }
.site-info span { font-weight: 600; }
.footer { text-align: center; padding: 16px; font-size: 12px; color: #999; }
@media (max-width: 600px) {
  .container { padding: 12px; }
  .pillar-label { width: 120px; font-size: 12px; }
  .pillar-score { width: 60px; font-size: 12px; }
  .header h1 { font-size: 16px; }
}
"""


def format_single_report_html(report: AuditReport) -> str:
    """Format a single-page AuditReport as self-contained HTML."""
    gauge = _gauge_svg(report.overall_score)
    pillars = "\n".join([
        _pillar_bar("Robots.txt AI Access", report.robots.score, 25),
        _pillar_bar("llms.txt Presence", report.llms_txt.score, 10),
        _pillar_bar("Schema.org JSON-LD", report.schema_org.score, 25),
        _pillar_bar("Content Density", report.content.score, 40),
    ])
    details = "\n".join([
        _pillar_detail("Robots.txt AI Access", report.robots.detail),
        _pillar_detail("llms.txt Presence", report.llms_txt.detail),
        _pillar_detail("Schema.org JSON-LD", report.schema_org.detail),
        _pillar_detail("Content Density", report.content.detail),
    ])
    errors = _errors_section(report.errors)
    url_escaped = html_lib.escape(report.url)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AEO Audit: {url_escaped}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>AEO Audit Report</h1>
    {gauge}
    <div class="url">{url_escaped}</div>
  </div>
  <div class="pillars">
    <h2>Pillar Scores</h2>
    {pillars}
  </div>
  <div class="details">
    <h2>Details</h2>
    {details}
  </div>
  {errors}
  <div class="footer">Generated by aeo-cli</div>
</div>
</body>
</html>"""


def format_site_report_html(report: SiteAuditReport) -> str:
    """Format a site-level SiteAuditReport as self-contained HTML."""
    gauge = _gauge_svg(report.overall_score)
    pillars = "\n".join([
        _pillar_bar("Robots.txt AI Access", report.robots.score, 25),
        _pillar_bar("llms.txt Presence", report.llms_txt.score, 10),
        _pillar_bar("Schema.org JSON-LD", report.schema_org.score, 25),
        _pillar_bar("Content Density", report.content.score, 40),
    ])
    details = "\n".join([
        _pillar_detail("Robots.txt AI Access", report.robots.detail),
        _pillar_detail("llms.txt Presence", report.llms_txt.detail),
        _pillar_detail("Schema.org JSON-LD", report.schema_org.detail),
        _pillar_detail("Content Density", report.content.detail),
    ])

    # Pages table
    pages_html = ""
    if report.pages:
        rows = ""
        for page in report.pages:
            total = page.schema_org.score + page.content.score
            rows += (
                f"<tr><td>{html_lib.escape(page.url)}</td>"
                f"<td>{page.schema_org.score}</td>"
                f"<td>{page.content.score}</td>"
                f"<td>{total}</td></tr>\n"
            )
        pages_html = f"""<div class="details">
    <h2>Per-Page Breakdown</h2>
    <table class="pages-table">
      <thead><tr><th>URL</th><th>Schema</th><th>Content</th><th>Total</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>"""

    errors = _errors_section(report.errors)
    url_escaped = html_lib.escape(report.url)
    domain_escaped = html_lib.escape(report.domain)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AEO Site Audit: {domain_escaped}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>AEO Site Audit Report</h1>
    {gauge}
    <div class="url">{url_escaped}</div>
  </div>
  <div class="site-info">
    <span>Domain:</span> {domain_escaped} &middot;
    <span>Discovery:</span> {html_lib.escape(report.discovery.method)} &middot;
    <span>Pages audited:</span> {report.pages_audited}
  </div>
  <div class="pillars">
    <h2>Pillar Scores</h2>
    {pillars}
  </div>
  <div class="details">
    <h2>Details</h2>
    {details}
  </div>
  {pages_html}
  {errors}
  <div class="footer">Generated by aeo-cli</div>
</div>
</body>
</html>"""
