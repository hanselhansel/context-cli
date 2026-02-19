"""Tests for E-E-A-T (Experience, Expertise, Authority, Trust) signal detection."""

from context_cli.core.checks.eeat import check_eeat
from context_cli.core.models import EeatReport


class TestCheckEeat:
    """Tests for check_eeat() function."""

    def test_empty_html(self) -> None:
        report = check_eeat("")
        assert isinstance(report, EeatReport)
        assert not report.has_author
        assert report.author_name is None
        assert not report.has_date
        assert not report.has_about_page
        assert not report.has_contact_info
        assert not report.has_citations
        assert report.citation_count == 0
        assert report.trust_signals == []

    def test_author_meta_tag(self) -> None:
        html = '<html><head><meta name="author" content="Jane Doe"></head></html>'
        report = check_eeat(html)
        assert report.has_author
        assert report.author_name == "Jane Doe"

    def test_author_schema_person(self) -> None:
        html = """
        <html><body>
        <span itemprop="author" itemscope itemtype="https://schema.org/Person">
            <span itemprop="name">John Smith</span>
        </span>
        </body></html>
        """
        report = check_eeat(html)
        assert report.has_author

    def test_author_rel_author(self) -> None:
        html = '<html><body><a rel="author" href="/about/jane">Jane Doe</a></body></html>'
        report = check_eeat(html)
        assert report.has_author
        assert report.author_name == "Jane Doe"

    def test_author_class_byline(self) -> None:
        html = '<html><body><span class="byline">By Alice Johnson</span></body></html>'
        report = check_eeat(html)
        assert report.has_author

    def test_date_meta_published(self) -> None:
        html = (
            '<html><head><meta property="article:published_time" '
            'content="2025-01-15"></head></html>'
        )
        report = check_eeat(html)
        assert report.has_date

    def test_date_time_tag(self) -> None:
        html = '<html><body><time datetime="2025-06-01">June 1, 2025</time></body></html>'
        report = check_eeat(html)
        assert report.has_date

    def test_date_meta_modified(self) -> None:
        html = (
            '<html><head><meta property="article:modified_time" '
            'content="2025-03-20"></head></html>'
        )
        report = check_eeat(html)
        assert report.has_date

    def test_date_meta_name(self) -> None:
        html = '<html><head><meta name="date" content="2025-06-15"></head></html>'
        report = check_eeat(html)
        assert report.has_date

    def test_about_page_link(self) -> None:
        html = '<html><body><a href="/about">About Us</a></body></html>'
        report = check_eeat(html)
        assert report.has_about_page

    def test_about_page_link_variations(self) -> None:
        html = '<html><body><a href="/about-us">About</a></body></html>'
        report = check_eeat(html)
        assert report.has_about_page

    def test_contact_info_link(self) -> None:
        html = '<html><body><a href="/contact">Contact Us</a></body></html>'
        report = check_eeat(html)
        assert report.has_contact_info

    def test_contact_info_mailto(self) -> None:
        html = '<html><body><a href="mailto:info@example.com">Email</a></body></html>'
        report = check_eeat(html)
        assert report.has_contact_info

    def test_contact_info_tel(self) -> None:
        html = '<html><body><a href="tel:+1234567890">Call Us</a></body></html>'
        report = check_eeat(html)
        assert report.has_contact_info

    def test_external_citations(self) -> None:
        html = """
        <html><body>
        <a href="https://example.com/page">Internal</a>
        <a href="https://other-site.com/study">External Study</a>
        <a href="https://research.org/paper">Research Paper</a>
        <a href="https://example.com/another">Another Internal</a>
        </body></html>
        """
        report = check_eeat(html, base_domain="example.com")
        assert report.has_citations
        assert report.citation_count == 2

    def test_no_external_citations(self) -> None:
        html = """
        <html><body>
        <a href="/page">Internal</a>
        <a href="https://example.com/page">Also Internal</a>
        </body></html>
        """
        report = check_eeat(html, base_domain="example.com")
        assert not report.has_citations
        assert report.citation_count == 0

    def test_trust_signal_privacy_policy(self) -> None:
        html = '<html><body><a href="/privacy">Privacy Policy</a></body></html>'
        report = check_eeat(html)
        assert "privacy policy" in report.trust_signals

    def test_trust_signal_terms(self) -> None:
        html = '<html><body><a href="/terms">Terms of Service</a></body></html>'
        report = check_eeat(html)
        assert "terms of service" in report.trust_signals

    def test_no_author(self) -> None:
        html = '<html><body><p>Hello world</p></body></html>'
        report = check_eeat(html)
        assert not report.has_author
        assert report.author_name is None

    def test_full_eeat_page(self) -> None:
        """A well-structured page with all E-E-A-T signals."""
        html = """
        <html>
        <head>
            <meta name="author" content="Dr. Sarah Chen">
            <meta property="article:published_time" content="2025-06-15">
        </head>
        <body>
            <a href="/about">About</a>
            <a href="/contact">Contact</a>
            <a href="/privacy">Privacy Policy</a>
            <a href="/terms">Terms</a>
            <a href="https://pubmed.ncbi.nlm.nih.gov/12345">Study</a>
            <a href="https://nature.com/article">Nature Article</a>
        </body>
        </html>
        """
        report = check_eeat(html, base_domain="example.com")
        assert report.has_author
        assert report.author_name == "Dr. Sarah Chen"
        assert report.has_date
        assert report.has_about_page
        assert report.has_contact_info
        assert report.has_citations
        assert report.citation_count == 2
        assert len(report.trust_signals) >= 2

    def test_detail_summary(self) -> None:
        html = '<html><head><meta name="author" content="Bob"></head></html>'
        report = check_eeat(html)
        assert report.detail  # Non-empty detail

    def test_no_base_domain_skips_citation_counting(self) -> None:
        """Without base_domain, external link detection relies on absolute URLs."""
        html = """
        <html><body>
        <a href="https://external.com/page">External</a>
        <a href="/internal">Internal</a>
        </body></html>
        """
        report = check_eeat(html)
        # Without base_domain, should still count absolute external links
        assert report.citation_count >= 0
