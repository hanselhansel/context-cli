"""Configuration model for the markdown conversion pipeline."""

from pydantic import BaseModel, Field


class MarkdownEngineConfig(BaseModel):
    """Configuration for the markdown conversion pipeline."""

    strip_scripts: bool = Field(
        default=True, description="Remove <script> elements"
    )
    strip_styles: bool = Field(
        default=True, description="Remove <style> elements"
    )
    strip_nav: bool = Field(
        default=True, description="Remove <nav> elements"
    )
    strip_footer: bool = Field(
        default=True, description="Remove <footer> elements"
    )
    strip_header: bool = Field(
        default=True, description="Remove <header> elements"
    )
    strip_cookie_banners: bool = Field(
        default=True, description="Remove cookie consent elements"
    )
    strip_ads: bool = Field(
        default=True, description="Remove ad containers"
    )
    cookie_banner_patterns: list[str] = Field(
        default_factory=lambda: [
            "cookie",
            "consent",
            "gdpr",
            "privacy-banner",
            "cc-banner",
            "cookie-notice",
            "cookieConsent",
        ],
        description="CSS class/id patterns for cookie banners",
    )
    ad_patterns: list[str] = Field(
        default_factory=lambda: [
            "ad-",
            "ads-",
            "advert",
            "banner-ad",
            "google_ads",
            "sponsored",
            "dfp-",
            "gpt-ad",
        ],
        description="CSS class/id patterns for ad containers",
    )
