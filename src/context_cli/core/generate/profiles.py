"""Industry profile registry for generate command prompt tuning."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Profile:
    """Industry profile for generate command prompt tuning."""

    name: str
    display_name: str
    description: str
    schema_types: list[str]
    llms_txt_sections: list[str]
    keywords: list[str] = field(default_factory=list)


GENERIC_PROFILE = Profile(
    name="generic",
    display_name="Generic",
    description="General-purpose profile suitable for most websites.",
    schema_types=["Organization", "WebSite"],
    llms_txt_sections=["Docs", "API", "About"],
)

CPG_PROFILE = Profile(
    name="cpg",
    display_name="Consumer Packaged Goods",
    description="Profile for CPG brands, FMCG companies, and product-driven businesses.",
    schema_types=["Organization", "Product", "Brand"],
    llms_txt_sections=["Products", "Brand Story", "Sustainability", "Where to Buy"],
    keywords=["brand", "product", "consumer", "retail", "sustainability"],
)

SAAS_PROFILE = Profile(
    name="saas",
    display_name="SaaS",
    description="Profile for software-as-a-service products and developer tools.",
    schema_types=["Organization", "SoftwareApplication", "WebApplication"],
    llms_txt_sections=["Docs", "API Reference", "Changelog", "Pricing"],
    keywords=["software", "api", "developer", "cloud", "platform"],
)

ECOMMERCE_PROFILE = Profile(
    name="ecommerce",
    display_name="E-Commerce",
    description="Profile for online stores and marketplace platforms.",
    schema_types=["Organization", "Product", "Offer", "AggregateRating"],
    llms_txt_sections=["Products", "Categories", "Shipping & Returns", "Reviews"],
    keywords=["shop", "buy", "product", "cart", "shipping", "reviews"],
)

BLOG_PROFILE = Profile(
    name="blog",
    display_name="Blog / Publisher",
    description="Profile for blogs, media sites, and content publishers.",
    schema_types=["Organization", "Blog", "Article", "Person"],
    llms_txt_sections=["Featured Posts", "Categories", "About the Author", "Archives"],
    keywords=["blog", "article", "author", "post", "category"],
)

_REGISTRY: dict[str, Profile] = {
    p.name: p
    for p in [GENERIC_PROFILE, CPG_PROFILE, SAAS_PROFILE, ECOMMERCE_PROFILE, BLOG_PROFILE]
}


def get_profile(name: str) -> Profile:
    """Get a profile by name. Raises KeyError if not found."""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(f"Unknown profile '{name}'. Available: {available}")
    return _REGISTRY[name]


def list_profiles() -> list[Profile]:
    """List all registered profiles."""
    return list(_REGISTRY.values())


def register_profile(profile: Profile) -> None:
    """Register a custom profile."""
    _REGISTRY[profile.name] = profile
