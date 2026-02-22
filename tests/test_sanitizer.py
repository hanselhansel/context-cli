"""Tests for the HTML sanitizer module."""

from __future__ import annotations

from bs4 import BeautifulSoup

from context_cli.core.markdown_engine.config import MarkdownEngineConfig
from context_cli.core.markdown_engine.sanitizer import (
    _remove_by_patterns,
    sanitize_html,
)


class TestSanitizeEmptyInput:
    """Tests for empty/falsy HTML input."""

    def test_empty_string(self) -> None:
        assert sanitize_html("") == ""

    def test_none_like_empty(self) -> None:
        """Empty string is the only falsy input (type is str)."""
        assert sanitize_html("") == ""


class TestStripScripts:
    """Tests for script element removal."""

    def test_removes_inline_script(self) -> None:
        html = '<html><body><script>alert("hi")</script><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "<script" not in result
        assert "Content" in result

    def test_removes_external_script(self) -> None:
        html = '<html><body><script src="app.js"></script><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "<script" not in result
        assert "Content" in result

    def test_removes_multiple_scripts(self) -> None:
        html = (
            "<html><body>"
            "<script>var a=1;</script>"
            "<p>Content</p>"
            '<script src="b.js"></script>'
            "</body></html>"
        )
        result = sanitize_html(html)
        assert "<script" not in result
        assert "Content" in result

    def test_preserves_scripts_when_disabled(self) -> None:
        html = '<html><body><script>alert("hi")</script><p>Content</p></body></html>'
        config = MarkdownEngineConfig(strip_scripts=False)
        result = sanitize_html(html, config=config)
        assert "<script" in result


class TestStripStyles:
    """Tests for style element removal."""

    def test_removes_style_block(self) -> None:
        html = "<html><head><style>body{color:red}</style></head><body><p>Content</p></body></html>"
        result = sanitize_html(html)
        assert "<style" not in result
        assert "Content" in result

    def test_removes_multiple_styles(self) -> None:
        html = (
            "<html><head>"
            "<style>.a{}</style>"
            "<style>.b{}</style>"
            "</head><body><p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "<style" not in result

    def test_preserves_styles_when_disabled(self) -> None:
        html = "<html><head><style>body{}</style></head><body><p>Content</p></body></html>"
        config = MarkdownEngineConfig(strip_styles=False)
        result = sanitize_html(html, config=config)
        assert "<style" in result


class TestStripNav:
    """Tests for nav element removal."""

    def test_removes_nav(self) -> None:
        html = '<html><body><nav><a href="/">Home</a></nav><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "<nav" not in result
        assert "Content" in result

    def test_preserves_nav_when_disabled(self) -> None:
        html = '<html><body><nav><a href="/">Home</a></nav><p>Content</p></body></html>'
        config = MarkdownEngineConfig(strip_nav=False)
        result = sanitize_html(html, config=config)
        assert "<nav" in result


class TestStripHeader:
    """Tests for header element removal."""

    def test_removes_header(self) -> None:
        html = "<html><body><header><h1>Logo</h1></header><main><p>Content</p></main></body></html>"
        result = sanitize_html(html)
        assert "<header" not in result
        assert "Content" in result

    def test_preserves_header_when_disabled(self) -> None:
        html = "<html><body><header><h1>Logo</h1></header><p>Content</p></body></html>"
        config = MarkdownEngineConfig(strip_header=False)
        result = sanitize_html(html, config=config)
        assert "<header" in result


class TestStripFooter:
    """Tests for footer element removal."""

    def test_removes_footer(self) -> None:
        html = "<html><body><p>Content</p><footer>Copyright 2024</footer></body></html>"
        result = sanitize_html(html)
        assert "<footer" not in result
        assert "Content" in result

    def test_preserves_footer_when_disabled(self) -> None:
        html = "<html><body><p>Content</p><footer>Copyright 2024</footer></body></html>"
        config = MarkdownEngineConfig(strip_footer=False)
        result = sanitize_html(html, config=config)
        assert "<footer" in result


class TestCookieBannerRemoval:
    """Tests for cookie banner removal by class/id patterns."""

    def test_removes_by_class_cookie(self) -> None:
        html = '<html><body><div class="cookie-banner">Accept</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "cookie-banner" not in result
        assert "Accept" not in result
        assert "Content" in result

    def test_removes_by_id_consent(self) -> None:
        html = (
            '<html><body><div id="consent-modal">Accept cookies</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "consent-modal" not in result
        assert "Content" in result

    def test_removes_gdpr_banner(self) -> None:
        html = '<html><body><div class="gdpr-notice">GDPR info</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "gdpr" not in result.lower()
        assert "Content" in result

    def test_removes_privacy_banner(self) -> None:
        html = (
            '<html><body><div class="privacy-banner">Privacy</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "privacy-banner" not in result
        assert "Content" in result

    def test_removes_cc_banner(self) -> None:
        html = '<html><body><div id="cc-banner">Cookies</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "cc-banner" not in result

    def test_removes_cookie_notice(self) -> None:
        html = (
            '<html><body><div class="cookie-notice">Notice</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "cookie-notice" not in result

    def test_removes_cookieConsent_case_insensitive(self) -> None:
        html = (
            '<html><body><div class="CookieConsent">Consent</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Consent</div>" not in result
        assert "Content" in result

    def test_preserves_cookie_banners_when_disabled(self) -> None:
        html = '<html><body><div class="cookie-banner">Accept</div><p>Content</p></body></html>'
        config = MarkdownEngineConfig(strip_cookie_banners=False)
        result = sanitize_html(html, config=config)
        assert "cookie-banner" in result


class TestAdContainerRemoval:
    """Tests for ad container removal by id/class patterns."""

    def test_removes_by_class_ad_prefix(self) -> None:
        html = '<html><body><div class="ad-container">Buy now</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "ad-container" not in result
        assert "Content" in result

    def test_removes_by_id_ads_prefix(self) -> None:
        html = '<html><body><div id="ads-sidebar">Promo</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "ads-sidebar" not in result

    def test_removes_advert_class(self) -> None:
        html = '<html><body><div class="advert-box">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "advert" not in result

    def test_removes_banner_ad(self) -> None:
        html = '<html><body><div class="banner-ad">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "banner-ad" not in result

    def test_removes_google_ads(self) -> None:
        html = '<html><body><div id="google_ads_frame">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "google_ads" not in result

    def test_removes_sponsored(self) -> None:
        html = '<html><body><div class="sponsored-content">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "sponsored" not in result

    def test_removes_dfp_ad(self) -> None:
        html = '<html><body><div id="dfp-slot-1">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "dfp-" not in result

    def test_removes_gpt_ad(self) -> None:
        html = '<html><body><div id="gpt-ad-top">Ad</div><p>Content</p></body></html>'
        result = sanitize_html(html)
        assert "gpt-ad" not in result

    def test_preserves_ads_when_disabled(self) -> None:
        html = '<html><body><div class="ad-container">Buy now</div><p>Content</p></body></html>'
        config = MarkdownEngineConfig(strip_ads=False)
        result = sanitize_html(html, config=config)
        assert "ad-container" in result


class TestHiddenElementRemoval:
    """Tests for hidden element removal."""

    def test_removes_aria_hidden(self) -> None:
        html = (
            '<html><body><span aria-hidden="true">Hidden icon</span>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Hidden icon" not in result
        assert "Content" in result

    def test_removes_display_none(self) -> None:
        html = (
            '<html><body><div style="display:none">Hidden</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Hidden</div>" not in result
        assert "Content" in result

    def test_removes_display_none_with_spaces(self) -> None:
        html = (
            '<html><body><div style="display: none">Hidden</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Hidden</div>" not in result

    def test_removes_display_none_uppercase(self) -> None:
        html = (
            '<html><body><div style="Display:None">Hidden</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Hidden</div>" not in result

    def test_preserves_visible_elements(self) -> None:
        html = (
            '<html><body><div style="display:block">Visible</div>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "Visible" in result


class TestNoscriptAndIframeRemoval:
    """Tests for noscript and iframe removal."""

    def test_removes_noscript(self) -> None:
        html = (
            "<html><body><noscript>Enable JS</noscript>"
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "<noscript" not in result
        assert "Content" in result

    def test_removes_iframe(self) -> None:
        html = (
            '<html><body><iframe src="https://ads.example.com"></iframe>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "<iframe" not in result
        assert "Content" in result

    def test_removes_multiple_iframes(self) -> None:
        html = (
            "<html><body>"
            '<iframe src="a.html"></iframe>'
            '<iframe src="b.html"></iframe>'
            "<p>Content</p></body></html>"
        )
        result = sanitize_html(html)
        assert "<iframe" not in result


class TestCustomConfig:
    """Tests for custom configuration options."""

    def test_disable_all_stripping(self) -> None:
        html = (
            "<html><body>"
            "<script>var x=1;</script>"
            "<style>.a{}</style>"
            "<nav>Nav</nav>"
            "<header>Header</header>"
            "<footer>Footer</footer>"
            '<div class="cookie-banner">Cookie</div>'
            '<div class="ad-container">Ad</div>'
            "<p>Content</p>"
            "</body></html>"
        )
        config = MarkdownEngineConfig(
            strip_scripts=False,
            strip_styles=False,
            strip_nav=False,
            strip_footer=False,
            strip_header=False,
            strip_cookie_banners=False,
            strip_ads=False,
        )
        result = sanitize_html(html, config=config)
        # Structural elements preserved (cookie/ad still present)
        assert "<script" in result
        assert "<style" in result
        assert "<nav" in result
        assert "<header" in result
        assert "<footer" in result
        assert "cookie-banner" in result
        assert "ad-container" in result
        # Hidden elements and noscript/iframe still removed (always on)
        assert "Content" in result

    def test_custom_cookie_patterns(self) -> None:
        html = (
            '<html><body><div class="tracking-popup">Accept</div>'
            "<p>Content</p></body></html>"
        )
        config = MarkdownEngineConfig(
            cookie_banner_patterns=["tracking-popup"]
        )
        result = sanitize_html(html, config=config)
        assert "tracking-popup" not in result
        assert "Content" in result

    def test_custom_ad_patterns(self) -> None:
        html = (
            '<html><body><div class="promo-widget">Buy</div>'
            "<p>Content</p></body></html>"
        )
        config = MarkdownEngineConfig(ad_patterns=["promo-widget"])
        result = sanitize_html(html, config=config)
        assert "promo-widget" not in result
        assert "Content" in result

    def test_default_config_used_when_none(self) -> None:
        html = "<html><body><script>x</script><p>Content</p></body></html>"
        result = sanitize_html(html, config=None)
        assert "<script" not in result
        assert "Content" in result


class TestMainContentPreserved:
    """Tests that main content is not removed."""

    def test_preserves_paragraphs(self) -> None:
        html = "<html><body><p>Hello world</p></body></html>"
        result = sanitize_html(html)
        assert "Hello world" in result

    def test_preserves_headings(self) -> None:
        html = "<html><body><h1>Title</h1><h2>Subtitle</h2><p>Text</p></body></html>"
        result = sanitize_html(html)
        assert "Title" in result
        assert "Subtitle" in result
        assert "Text" in result

    def test_preserves_lists(self) -> None:
        html = "<html><body><ul><li>Item 1</li><li>Item 2</li></ul></body></html>"
        result = sanitize_html(html)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_preserves_tables(self) -> None:
        html = (
            "<html><body><table><tr><td>Cell</td></tr></table></body></html>"
        )
        result = sanitize_html(html)
        assert "Cell" in result

    def test_preserves_article_tag(self) -> None:
        html = "<html><body><article><p>Article content</p></article></body></html>"
        result = sanitize_html(html)
        assert "Article content" in result

    def test_preserves_main_tag(self) -> None:
        html = "<html><body><main><p>Main content</p></main></body></html>"
        result = sanitize_html(html)
        assert "Main content" in result

    def test_preserves_links(self) -> None:
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        result = sanitize_html(html)
        assert "Link" in result
        assert "https://example.com" in result

    def test_preserves_images(self) -> None:
        html = '<html><body><img src="photo.jpg" alt="Photo"/></body></html>'
        result = sanitize_html(html)
        assert "photo.jpg" in result


class TestComplexRealWorldHTML:
    """Tests with complex real-world-like HTML structures."""

    def test_full_page_boilerplate_removal(self) -> None:
        html = """
        <html>
        <head>
            <style>body { font-family: sans-serif; }</style>
            <script src="analytics.js"></script>
        </head>
        <body>
            <header>
                <nav>
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                </nav>
                <div class="cookie-notice">
                    <p>We use cookies.</p>
                    <button>Accept</button>
                </div>
            </header>

            <main>
                <article>
                    <h1>Important Article</h1>
                    <p>This is the main content that should be preserved.</p>
                    <ul>
                        <li>Point 1</li>
                        <li>Point 2</li>
                    </ul>
                </article>
            </main>

            <aside>
                <div class="ad-sidebar">
                    <img src="ad.jpg" alt="Advertisement"/>
                </div>
                <div id="google_ads_container">
                    <p>Sponsored content</p>
                </div>
            </aside>

            <div id="consent-popup" style="display:none">
                <p>Cookie consent form</p>
            </div>

            <footer>
                <p>Copyright 2024</p>
                <nav>
                    <a href="/privacy">Privacy</a>
                </nav>
            </footer>

            <noscript>
                <p>Please enable JavaScript</p>
            </noscript>

            <iframe src="https://tracker.example.com"></iframe>

            <script>
                window.dataLayer = window.dataLayer || [];
            </script>
        </body>
        </html>
        """
        result = sanitize_html(html)

        # Boilerplate removed
        assert "<script" not in result
        assert "<style" not in result
        assert "<nav" not in result
        assert "<header" not in result
        assert "<footer" not in result
        assert "<noscript" not in result
        assert "<iframe" not in result
        assert "cookie-notice" not in result
        assert "ad-sidebar" not in result
        assert "google_ads" not in result
        assert "consent-popup" not in result

        # Main content preserved
        assert "Important Article" in result
        assert "main content that should be preserved" in result
        assert "Point 1" in result
        assert "Point 2" in result

    def test_nested_boilerplate(self) -> None:
        """Cookie banner inside a nav inside a header -- all should be removed."""
        html = """
        <html><body>
            <header>
                <nav>
                    <div class="cookie-bar">Accept cookies</div>
                </nav>
            </header>
            <p>Real content</p>
        </body></html>
        """
        result = sanitize_html(html)
        assert "Accept cookies" not in result
        assert "Real content" in result

    def test_mixed_hidden_elements(self) -> None:
        html = """
        <html><body>
            <span aria-hidden="true">Icon glyph</span>
            <div style="display: none;">Hidden form</div>
            <div style="color: red; display:none; margin: 0">Also hidden</div>
            <p>Visible content</p>
        </body></html>
        """
        result = sanitize_html(html)
        assert "Icon glyph" not in result
        assert "Hidden form" not in result
        assert "Also hidden" not in result
        assert "Visible content" in result


class TestRemoveByPatterns:
    """Direct tests for _remove_by_patterns helper."""

    def test_removes_matching_element_by_id(self) -> None:
        soup = BeautifulSoup(
            '<div id="tracking-pixel">T</div><p>Keep</p>', "html.parser"
        )
        _remove_by_patterns(soup, ["tracking"])
        assert "tracking" not in str(soup)
        assert "Keep" in str(soup)

    def test_removes_matching_element_by_class(self) -> None:
        soup = BeautifulSoup(
            '<div class="popup-overlay">O</div><p>Keep</p>', "html.parser"
        )
        _remove_by_patterns(soup, ["popup"])
        assert "popup" not in str(soup)
        assert "Keep" in str(soup)

    def test_no_match_preserves_all(self) -> None:
        soup = BeautifulSoup(
            '<div class="content">Text</div><p>More</p>', "html.parser"
        )
        _remove_by_patterns(soup, ["nonexistent-pattern"])
        assert "Text" in str(soup)
        assert "More" in str(soup)

    def test_empty_patterns_list(self) -> None:
        soup = BeautifulSoup(
            '<div class="anything">Text</div>', "html.parser"
        )
        _remove_by_patterns(soup, [])
        assert "Text" in str(soup)

    def test_element_with_no_id_or_class(self) -> None:
        """Elements without id or class should not crash."""
        soup = BeautifulSoup("<div>Text</div><p>More</p>", "html.parser")
        _remove_by_patterns(soup, ["something"])
        assert "Text" in str(soup)
        assert "More" in str(soup)

    def test_case_insensitive_matching(self) -> None:
        soup = BeautifulSoup(
            '<div class="CookieBanner">C</div><p>Keep</p>', "html.parser"
        )
        _remove_by_patterns(soup, ["cookiebanner"])
        assert "CookieBanner" not in str(soup)
        assert "Keep" in str(soup)

    def test_decomposed_child_skipped(self) -> None:
        """When a parent is decomposed, its children (already in find_all list)
        should be skipped because their attrs become None."""
        soup = BeautifulSoup(
            '<div class="ad-wrapper"><span class="ad-inner">Ad text</span></div>'
            "<p>Keep</p>",
            "html.parser",
        )
        # Both "ad-wrapper" and "ad-inner" match the pattern "ad-".
        # When the parent div is decomposed first, the child span's attrs
        # becomes None. The function must handle this gracefully.
        _remove_by_patterns(soup, ["ad-"])
        assert "Ad text" not in str(soup)
        assert "Keep" in str(soup)


class TestConfigModel:
    """Tests for MarkdownEngineConfig model."""

    def test_default_values(self) -> None:
        config = MarkdownEngineConfig()
        assert config.strip_scripts is True
        assert config.strip_styles is True
        assert config.strip_nav is True
        assert config.strip_footer is True
        assert config.strip_header is True
        assert config.strip_cookie_banners is True
        assert config.strip_ads is True
        assert len(config.cookie_banner_patterns) > 0
        assert len(config.ad_patterns) > 0

    def test_cookie_banner_patterns_defaults(self) -> None:
        config = MarkdownEngineConfig()
        assert "cookie" in config.cookie_banner_patterns
        assert "consent" in config.cookie_banner_patterns
        assert "gdpr" in config.cookie_banner_patterns

    def test_ad_patterns_defaults(self) -> None:
        config = MarkdownEngineConfig()
        assert "ad-" in config.ad_patterns
        assert "sponsored" in config.ad_patterns

    def test_custom_override(self) -> None:
        config = MarkdownEngineConfig(
            strip_scripts=False,
            cookie_banner_patterns=["my-custom"],
            ad_patterns=["my-ad"],
        )
        assert config.strip_scripts is False
        assert config.cookie_banner_patterns == ["my-custom"]
        assert config.ad_patterns == ["my-ad"]

    def test_model_serialization(self) -> None:
        config = MarkdownEngineConfig()
        data = config.model_dump()
        assert "strip_scripts" in data
        assert "cookie_banner_patterns" in data
        restored = MarkdownEngineConfig(**data)
        assert restored == config
