"""Tests for semantic HTML quality check."""

from __future__ import annotations

from context_cli.core.checks.semantic_html import check_semantic_html


def test_fully_semantic_html():
    """HTML with all semantic elements and ARIA landmarks scores 3/3."""
    html = """
    <html>
    <body>
        <header role="banner">Site Header</header>
        <nav role="navigation">Menu</nav>
        <main role="main">
            <article>Content</article>
        </main>
        <footer role="contentinfo">Footer</footer>
    </body>
    </html>
    """
    report = check_semantic_html(html)

    assert report.has_main is True
    assert report.has_article is True
    assert report.has_header is True
    assert report.has_footer is True
    assert report.has_nav is True
    assert report.aria_landmarks >= 2
    assert report.score == 3.0


def test_minimal_html_no_semantic():
    """Plain HTML with no semantic elements scores 0."""
    html = "<html><body><div>Hello</div></body></html>"
    report = check_semantic_html(html)

    assert report.has_main is False
    assert report.has_article is False
    assert report.has_header is False
    assert report.has_nav is False
    assert report.aria_landmarks == 0
    assert report.score == 0.0
    assert "No semantic HTML elements found" in report.detail


def test_partial_main_no_aria():
    """HTML with <main> but no ARIA landmarks scores 1."""
    html = "<html><body><main><p>Content</p></main></body></html>"
    report = check_semantic_html(html)

    assert report.has_main is True
    assert report.aria_landmarks == 0
    assert report.score == 1.0


def test_aria_only_no_semantic_tags():
    """HTML with ARIA landmarks but no semantic tags scores 1."""
    html = """
    <html><body>
        <div role="banner">Header</div>
        <div role="navigation">Nav</div>
        <div role="main">Content</div>
    </body></html>
    """
    report = check_semantic_html(html)

    assert report.has_main is False
    assert report.has_nav is False
    assert report.aria_landmarks == 3
    assert report.score == 1.0


def test_empty_html():
    """Empty string returns safe default."""
    report = check_semantic_html("")

    assert report.has_main is False
    assert report.score == 0.0
    assert report.detail == "No HTML to analyze"


def test_header_and_nav_without_main():
    """Header + nav without main/article scores 1 (from header+nav point)."""
    html = """
    <html><body>
        <header>Site</header>
        <nav>Menu</nav>
        <div>Content</div>
    </body></html>
    """
    report = check_semantic_html(html)

    assert report.has_header is True
    assert report.has_nav is True
    assert report.has_main is False
    assert report.score == 1.0
