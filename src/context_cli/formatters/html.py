"""HTML report formatter for Context Lint reports — Lighthouse-style self-contained HTML."""

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
    return f"""<div class="gauge-container" style="--target-offset: {offset};">
<svg width="140" height="140" viewBox="0 0 140 140">
  <circle cx="70" cy="70" r="{r}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8"/>
  <circle class="score-circle" cx="70" cy="70" r="{r}" fill="none" stroke="{color}" stroke-width="8"
    stroke-dasharray="{circumference}" stroke-dashoffset="{circumference}"
    stroke-linecap="round" transform="rotate(-90 70 70)"/>
  <text x="70" y="70" text-anchor="middle" dominant-baseline="central"
    font-size="36" font-weight="700" fill="{color}">{score}</text>
</svg>
</div>"""


def _pillar_bar(label: str, score: float, max_score: float) -> str:
    """Generate an HTML bar for a pillar score."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    color = _score_color(score / max_score * 100 if max_score > 0 else 0)
    return f"""<div class="pillar-row">
  <div class="pillar-label">{html_lib.escape(label)}</div>
  <div class="pillar-bar-bg">
    <div class="pillar-bar-fill" style="width:0%;background:{color}"
         data-target-width="{pct:.1f}%"></div>
  </div>
  <div class="pillar-score">{score}/{max_score}</div>
</div>"""


def _pillar_detail(label: str, detail: str) -> str:
    """Generate an HTML detail section for a pillar."""
    return f"""<div class="detail-section">
  <h3>{html_lib.escape(label)}</h3>
  <p>{html_lib.escape(detail)}</p>
</div>"""


def _diagnostics_section(report: AuditReport | SiteAuditReport) -> str:
    """Generate an HTML diagnostics table section."""
    if not hasattr(report, "lint_result") or report.lint_result is None:
        return ""
    lr = report.lint_result
    if not lr.diagnostics:
        return ""
    severity_colors = {"error": "#ff4e42", "warn": "#ffa400", "info": "#0cce6b"}
    rows_html = ""
    for d in lr.diagnostics:
        color = severity_colors.get(d.severity, "#333")
        rows_html += (
            f'<tr><td>{html_lib.escape(d.code)}</td>'
            f'<td style="color:{color};font-weight:600">{html_lib.escape(d.severity)}</td>'
            f'<td title="{html_lib.escape(d.message)}">{html_lib.escape(d.message)}</td></tr>\n'
        )
    return f"""<div class="details">
  <h3>Diagnostics</h3>
  <table class="pages-table">
    <thead><tr><th>Code</th><th>Severity</th><th>Message</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def _token_waste_section(report: AuditReport | SiteAuditReport) -> str:
    """Generate an HTML token waste section."""
    if not hasattr(report, "lint_result") or report.lint_result is None:
        return ""
    lr = report.lint_result
    waste_color = _score_color(max(0, 100 - lr.context_waste_pct))
    checks_html = ""
    for check in lr.checks:
        status_color = "#0cce6b" if check.passed else "#ff4e42"
        status_text = "PASS" if check.passed else "FAIL"
        name_esc = html_lib.escape(check.name)
        detail_esc = html_lib.escape(check.detail)
        checks_html += (
            f'<tr><td title="{name_esc}">{name_esc}</td>'
            f'<td style="color:{status_color};font-weight:600">'
            f'{status_text}</td>'
            f'<td title="{detail_esc}">{detail_esc}</td>'
            f'</tr>\n'
        )
    pct = f"{lr.context_waste_pct:.0f}%"
    diagnostics = _diagnostics_section(report)
    return f"""<div class="panel details">
  <h2>Token Waste</h2>
  <div style="text-align:center;margin:16px 0">
    <span style="font-size:36px;font-weight:700;color:{waste_color}">{pct}</span>
    <span style="font-size:16px;color:#94a3b8;margin-left:8px;">Context Waste</span>
  </div>
  <p style="text-align:center;font-size:14px;color:#cbd5e1;margin-bottom:24px;">
    {lr.raw_tokens:,} raw tokens &rarr; {lr.clean_tokens:,} clean tokens
  </p>
  <table class="pages-table">
    <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
    <tbody>{checks_html}</tbody>
  </table>
</div>
{diagnostics}"""


def _errors_section(errors: list[str]) -> str:
    """Generate an HTML errors section."""
    if not errors:
        return ""
    items = "".join(f"<li>{html_lib.escape(e)}</li>" for e in errors)
    return f"""<div class="errors-section">
  <h3>Errors</h3>
  <ul>{items}</ul>
</div>"""


_ICON_LINK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"'
    ' viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    ' style="opacity:0.7">'
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07'
    'l-1.72 1.71"></path>'
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07'
    'l1.71-1.71"></path></svg>'
)

_ICON_GRID = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"'
    ' viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    ' style="opacity:0.8;color:#38bdf8;">'
    '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
    '<line x1="3" y1="9" x2="21" y2="9"></line>'
    '<line x1="9" y1="21" x2="9" y2="9"></line></svg>'
)

_ICON_INFO = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"'
    ' viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
    ' style="opacity:0.8;color:#a855f7;">'
    '<circle cx="12" cy="12" r="10"></circle>'
    '<line x1="12" y1="16" x2="12" y2="12"></line>'
    '<line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
)


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Outfit', sans-serif;
    background: #0f172a;
    background-image:
        radial-gradient(circle at top right, rgba(56,189,248,0.1), transparent 40%),
        radial-gradient(circle at bottom left, rgba(168,85,247,0.1), transparent 40%);
    color: #f8fafc;
    line-height: 1.6;
    min-height: 100vh;
}

.container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 32px 24px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}

/* Glassmorphism Panel Base */
.panel {
    background: rgba(30, 41, 59, 0.5);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.3s cubic-bezier(0.4,0,0.2,1),
        box-shadow 0.3s cubic-bezier(0.4,0,0.2,1);
}

.panel:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px -4px rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

.header {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 32px;
}

.header-info {
    flex: 1;
}

.header h1 {
    font-size: 28px;
    font-weight: 700;
    color: #f8fafc;
    margin-bottom: 8px;
    background: linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.header .url {
    font-size: 15px;
    color: #94a3b8;
    word-break: break-all;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}

.gauge-container {
    filter: drop-shadow(0 0 16px rgba(12, 206, 107, 0.2));
}

.pillars {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.panel h2 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 8px;
}

.pillar-row {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    background: rgba(15, 23, 42, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.03);
    transition: background 0.2s;
}

.pillar-row:hover {
    background: rgba(15, 23, 42, 0.6);
}

.pillar-label {
    width: 180px;
    font-size: 14px;
    font-weight: 500;
    color: #cbd5e1;
}

.pillar-bar-bg {
    flex: 1;
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    margin: 0 16px;
    overflow: hidden;
}

.pillar-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 0 10px currentColor; /* Glow effect */
}

.pillar-score {
    width: 60px;
    text-align: right;
    font-size: 15px;
    font-weight: 600;
    color: #f8fafc;
}

.details {
    grid-column: 1 / -1;
}

.detail-section {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.detail-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.detail-section h3 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 8px;
    color: #e2e8f0;
}

.detail-section p {
    font-size: 14px;
    color: #94a3b8;
    line-height: 1.5;
}

.errors-section {
    grid-column: 1 / -1;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
}

.errors-section h3 {
    font-size: 16px;
    font-weight: 600;
    color: #fca5a5;
    margin-bottom: 12px;
}

.errors-section ul {
    padding-left: 24px;
}

.errors-section li {
    font-size: 14px;
    color: #fecaca;
    margin-bottom: 6px;
}

.pages-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin-top: 16px;
    table-layout: fixed;
}

.pages-table th, .pages-table td {
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
}

/* Adjust column widths */
.pages-table th:nth-child(1) { width: 55%; }
.pages-table th:nth-child(2) { width: 15%; }
.pages-table th:nth-child(3) { width: 15%; }
.pages-table th:nth-child(4) { width: 15%; }

.pages-table th {
    font-weight: 600;
    color: #94a3b8;
    background: rgba(0, 0, 0, 0.2);
    text-transform: uppercase;
    font-size: 12px;
    letter-spacing: 0.05em;
}

.pages-table th:first-child { border-top-left-radius: 8px; border-bottom-left-radius: 8px;}
.pages-table th:last-child { border-top-right-radius: 8px; border-bottom-right-radius: 8px; }

.pages-table td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #cbd5e1;
}

.pages-table tbody tr {
    transition: background 0.2s;
}
.pages-table tbody tr:hover {
    background: rgba(255, 255, 255, 0.03);
}

.pages-table td:first-child {
    color: #f8fafc;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.site-info {
    grid-column: 1 / -1;
    display: flex;
    gap: 24px;
    font-size: 14px;
    color: #94a3b8;
    background: rgba(0, 0, 0, 0.2);
    padding: 16px 24px;
    border-radius: 12px;
}

.site-info span {
    font-weight: 600;
    color: #cbd5e1;
}

.footer {
    grid-column: 1 / -1;
    text-align: center;
    padding: 24px;
    font-size: 13px;
    color: #64748b;
    margin-top: 16px;
}

/* Animations */
@keyframes dash {
  from { stroke-dashoffset: 351.858; } /* 2 * PI * 56 */
  to { stroke-dashoffset: var(--target-offset); }
}

.score-circle {
    animation: dash 1.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Responsive */
@media (max-width: 768px) {
    .container {
        grid-template-columns: 1fr;
        padding: 16px;
    }
    .header {
        flex-direction: column;
        text-align: center;
        gap: 24px;
    }
    .pillar-label {
        width: 140px;
    }
    .site-info {
        flex-direction: column;
        gap: 12px;
    }
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
    token_waste = _token_waste_section(report)
    errors = _errors_section(report.errors)
    url_escaped = html_lib.escape(report.url)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Context Lint: {url_escaped}</title>
<style>{_CSS}</style>
<script>
  // Trigger animations after load
  document.addEventListener("DOMContentLoaded", () => {{
      setTimeout(() => {{
          document.querySelectorAll('.pillar-bar-fill').forEach(el => {{
              const targetWidth = el.getAttribute('data-target-width');
              el.style.width = targetWidth;
          }});
      }}, 100);

      // Stagger panel entrance
      const panels = document.querySelectorAll('.panel');
      panels.forEach((panel, i) => {{
          panel.style.opacity = '0';
          panel.style.transform = 'translateY(20px)';
          panel.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
          setTimeout(() => {{
              panel.style.opacity = '1';
              panel.style.transform = 'translateY(0)';
          }}, 100 + (i * 100));
      }});
  }});
</script>
</head>
<body>
<div class="container">
  <div class="panel header">
    <div class="header-info">
      <h1>Context Lint Report</h1>
      <div class="url">
        {_ICON_LINK}
        {url_escaped}
      </div>
    </div>
    {gauge}
  </div>
  <div class="panel pillars">
    <h2>{_ICON_GRID} Pillar Scores</h2>
    {pillars}
  </div>
  <div class="panel details">
    <h2>{_ICON_INFO} Details</h2>
    {details}
  </div>
  {token_waste}
  {errors}
  <div class="footer">Generated by Context CLI Linter</div>
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
                f'<tr><td title="{html_lib.escape(page.url)}">{html_lib.escape(page.url)}</td>'
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

    token_waste = _token_waste_section(report)
    errors = _errors_section(report.errors)
    url_escaped = html_lib.escape(report.url)
    domain_escaped = html_lib.escape(report.domain)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Context Lint Report: {domain_escaped}</title>
<style>{_CSS}</style>
<script>
  // Trigger animations after load
  document.addEventListener("DOMContentLoaded", () => {{
      setTimeout(() => {{
          document.querySelectorAll('.pillar-bar-fill').forEach(el => {{
              const targetWidth = el.getAttribute('data-target-width');
              el.style.width = targetWidth;
          }});
      }}, 100);

      // Stagger panel entrance
      const panels = document.querySelectorAll('.panel, .site-info');
      panels.forEach((panel, i) => {{
          panel.style.opacity = '0';
          panel.style.transform = 'translateY(20px)';
          panel.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
          setTimeout(() => {{
              panel.style.opacity = '1';
              panel.style.transform = 'translateY(0)';
          }}, 100 + (i * 100));
      }});
  }});
</script>
</head>
<body>
<div class="container">
  <div class="panel header">
    <div class="header-info">
      <h1>Context Lint Report</h1>
      <div class="url">
        {_ICON_LINK}
        {url_escaped}
      </div>
    </div>
    {gauge}
  </div>
  <div class="site-info">
    <div><span>Domain:</span> {domain_escaped}</div>
    <div><span>Discovery:</span> {html_lib.escape(report.discovery.method)}</div>
    <div><span>Pages audited:</span> {report.pages_audited}</div>
  </div>
  <div class="panel pillars">
    <h2>{_ICON_GRID} Pillar Scores</h2>
    {pillars}
  </div>
  <div class="panel details">
    <h2>{_ICON_INFO} Details</h2>
    {details}
  </div>
  {token_waste}
  {pages_html}
  {errors}
  <div class="footer">Generated by Context CLI Linter</div>
</div>
</body>
</html>"""
