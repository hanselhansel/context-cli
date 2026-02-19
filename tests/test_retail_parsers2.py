"""Tests for retail parsers batch 2: TikTok Shop, Blibli, Zalora, Generic."""

from __future__ import annotations

import json

from aeo_cli.core.models import MarketplaceType, ProductData
from aeo_cli.core.retail.parsers.base import BaseParser
from aeo_cli.core.retail.parsers.blibli import BlibliParser
from aeo_cli.core.retail.parsers.generic import GenericParser
from aeo_cli.core.retail.parsers.tiktok_shop import TiktokShopParser
from aeo_cli.core.retail.parsers.zalora import ZaloraParser

# ---------------------------------------------------------------------------
# Helpers to build synthetic HTML
# ---------------------------------------------------------------------------


def _wrap_html(body: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


def _schema_org_script(data: dict) -> str:
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


# ---------------------------------------------------------------------------
# TikTok Shop fixtures
# ---------------------------------------------------------------------------

TIKTOK_HTML_FULL = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "TikTok Viral Serum",
            "description": "Best serum on TikTok",
            "offers": {"price": "12.99", "priceCurrency": "USD", "availability": "InStock"},
            "brand": {"name": "TikBeauty"},
            "aggregateRating": {"ratingValue": "4.8", "reviewCount": "320"},
        }
    ),
    body="""
    <h1 data-testid="product-title">TikTok Viral Serum</h1>
    <div class="product-price"><span>$12.99</span></div>
    <div class="product-description">Best serum on TikTok</div>
    <div class="product-rating">
        <span data-testid="rating-value">4.8</span>
        <span data-testid="review-count">320 reviews</span>
    </div>
    <div class="product-brand">TikBeauty</div>
    <img class="product-image" src="https://img.tiktok.com/serum1.jpg" alt="Serum front view" />
    <img class="product-image" src="https://img.tiktok.com/serum2.jpg" alt="Serum side view" />
    <video src="https://v.tiktok.com/demo.mp4"></video>
    <div class="product-specs">
        <div class="spec-item">
            <span class="spec-label">Volume</span>
            <span class="spec-value">30ml</span>
        </div>
        <div class="spec-item">
            <span class="spec-label">Type</span>
            <span class="spec-value">Serum</span>
        </div>
    </div>
    <ul class="product-features">
        <li>Hydrating formula</li>
        <li>Vitamin C enriched</li>
    </ul>
    """,
)

TIKTOK_HTML_MINIMAL = _wrap_html(
    body="""
    <h1 data-testid="product-title">Simple TikTok Item</h1>
    """
)


# ---------------------------------------------------------------------------
# Blibli fixtures
# ---------------------------------------------------------------------------

BLIBLI_HTML_FULL = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Samsung Galaxy A54",
            "description": "Latest Samsung phone",
            "offers": {"price": "4999000", "priceCurrency": "IDR", "availability": "InStock"},
            "brand": {"name": "Samsung"},
            "aggregateRating": {"ratingValue": "4.5", "reviewCount": "150"},
        }
    ),
    body="""
    <h1 class="product-title" data-testid="lblPDPDetailProductName">Samsung Galaxy A54</h1>
    <div class="product-price" data-testid="lblPDPDetailProductPrice">Rp4.999.000</div>
    <div class="product-description" data-testid="lblPDPDetailProductDescription">
        Latest Samsung phone with great camera
    </div>
    <div class="product-rating">
        <span data-testid="lblPDPDetailProductRating">4.5</span>
        <span data-testid="lblPDPDetailReviewCount">150 ulasan</span>
    </div>
    <div class="product-brand" data-testid="lblPDPDetailBrandName">Samsung</div>
    <img class="product-image"
        src="https://static-src.com/s1.jpg" alt="A54 front" />
    <img class="product-image"
        src="https://static-src.com/s2.jpg" alt="A54 back" />
    <div class="product-specs">
        <div class="spec-row">
            <span class="spec-key">RAM</span>
            <span class="spec-val">8GB</span>
        </div>
        <div class="spec-row">
            <span class="spec-key">Storage</span>
            <span class="spec-val">128GB</span>
        </div>
    </div>
    <ul class="product-features">
        <li>Water resistant IP67</li>
        <li>5000mAh battery</li>
    </ul>
    <div class="qa-section">
        <div class="qa-item">Q&A 1</div>
        <div class="qa-item">Q&A 2</div>
        <div class="qa-item">Q&A 3</div>
    </div>
    """,
)

BLIBLI_HTML_MINIMAL = _wrap_html(
    body="""
    <h1 data-testid="lblPDPDetailProductName">Minimal Blibli Item</h1>
    """
)


# ---------------------------------------------------------------------------
# Zalora fixtures
# ---------------------------------------------------------------------------

ZALORA_HTML_FULL = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Nike Air Max 90",
            "description": "Classic Nike sneaker",
            "offers": {"price": "159.00", "priceCurrency": "SGD", "availability": "InStock"},
            "brand": {"name": "Nike"},
            "aggregateRating": {"ratingValue": "4.6", "reviewCount": "89"},
        }
    ),
    body="""
    <h1 class="product-title" data-testid="productTitle">Nike Air Max 90</h1>
    <div class="product-price" data-testid="productPrice">S$159.00</div>
    <div class="product-description" data-testid="productDescription">
        Classic Nike sneaker for everyday wear
    </div>
    <div class="product-brand" data-testid="productBrand">Nike</div>
    <div class="product-rating">
        <span data-testid="ratingValue">4.6</span>
        <span data-testid="reviewCount">89 reviews</span>
    </div>
    <img class="product-gallery-image"
        src="https://img.zalora.com/n1.jpg" alt="AM90 side" />
    <img class="product-gallery-image"
        src="https://img.zalora.com/n2.jpg" alt="AM90 top" />
    <img class="product-gallery-image"
        src="https://img.zalora.com/n3.jpg" alt="AM90 bottom" />
    <div class="product-size-list">
        <div class="size-option">US 8</div>
        <div class="size-option">US 9</div>
        <div class="size-option">US 10</div>
    </div>
    <div class="product-specs">
        <div class="spec-entry">
            <span class="spec-name">Material</span>
            <span class="spec-detail">Leather/Mesh</span>
        </div>
        <div class="spec-entry">
            <span class="spec-name">Color</span>
            <span class="spec-detail">White/Black</span>
        </div>
    </div>
    <ul class="product-highlights">
        <li>Air Max cushioning</li>
        <li>Rubber outsole</li>
    </ul>
    """,
)

ZALORA_HTML_MINIMAL = _wrap_html(
    body="""
    <h1 data-testid="productTitle">Minimal Zalora Dress</h1>
    """
)


# ---------------------------------------------------------------------------
# Generic parser fixtures
# ---------------------------------------------------------------------------

GENERIC_SCHEMA_ORG_HTML = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Schema Product",
            "description": "A product from Schema.org",
            "offers": {
                "price": "29.99",
                "priceCurrency": "EUR",
                "availability": "https://schema.org/InStock",
            },
            "brand": {"name": "SchemaBrand"},
            "aggregateRating": {"ratingValue": "3.9", "reviewCount": "42"},
            "image": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
        }
    ),
    body="<h1>Schema Product</h1>",
)

GENERIC_OPENGRAPH_HTML = _wrap_html(
    head="""
    <meta property="og:title" content="OG Product Title" />
    <meta property="og:description" content="OG Product Description" />
    <meta property="og:image" content="https://example.com/og-img.jpg" />
    <meta property="og:price:amount" content="19.99" />
    <meta property="og:price:currency" content="GBP" />
    <meta property="product:availability" content="in stock" />
    <meta property="product:brand" content="OGBrand" />
    """,
    body="<h1>OG Product</h1>",
)

GENERIC_BOTH_HTML = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Schema Name Wins",
            "description": "Schema description",
            "offers": {"price": "50.00", "priceCurrency": "USD"},
            "brand": {"name": "SchemaBrand"},
        }
    )
    + """
    <meta property="og:title" content="OG Name Loses" />
    <meta property="og:description" content="OG description" />
    <meta property="og:image" content="https://example.com/og-fallback.jpg" />
    """,
    body="<h1>Both Sources</h1>",
)

GENERIC_META_TAGS_HTML = _wrap_html(
    head="""
    <title>Meta Product Title</title>
    <meta name="description" content="Meta product description" />
    """,
    body='<img src="https://example.com/meta-img.jpg" alt="Product shot" /><h1>Meta Product</h1>',
)

GENERIC_SCHEMA_LIST_HTML = _wrap_html(
    head=_schema_org_script(
        [
            {"@type": "WebPage", "name": "Not a product"},
            {
                "@type": "Product",
                "name": "Product In List",
                "offers": {"price": "10.00", "priceCurrency": "CAD"},
            },
        ]
    ),
    body="<h1>Product In List</h1>",
)

GENERIC_SCHEMA_GRAPH_HTML = _wrap_html(
    head=_schema_org_script(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "name": "My Site"},
                {
                    "@type": "Product",
                    "name": "Graph Product",
                    "offers": {"price": "15.00", "priceCurrency": "AUD"},
                    "brand": {"name": "GraphBrand"},
                },
            ],
        }
    ),
    body="<h1>Graph Product</h1>",
)


# ===========================================================================
# TikTok Shop Parser Tests
# ===========================================================================


class TestTiktokShopParser:
    """Tests for TiktokShopParser."""

    def test_is_base_parser(self) -> None:
        parser = TiktokShopParser()
        assert isinstance(parser, BaseParser)

    def test_parse_full_html(self) -> None:
        parser = TiktokShopParser()
        result = parser.parse(TIKTOK_HTML_FULL)

        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.TIKTOK_SHOP
        assert result.title == "TikTok Viral Serum"
        assert result.price == "12.99"
        assert result.currency == "USD"
        assert result.description is not None
        assert "serum" in result.description.lower()
        assert result.brand == "TikBeauty"
        assert result.rating == 4.8
        assert result.review_count == 320
        assert len(result.image_urls) >= 2
        assert result.has_video is True
        assert len(result.specifications) >= 2
        assert "Volume" in result.specifications
        assert len(result.bullet_points) >= 2
        assert len(result.alt_texts) >= 2
        assert result.schema_org  # Non-empty schema.org data

    def test_parse_minimal_html(self) -> None:
        parser = TiktokShopParser()
        result = parser.parse(TIKTOK_HTML_MINIMAL)

        assert result.marketplace == MarketplaceType.TIKTOK_SHOP
        assert result.title == "Simple TikTok Item"
        assert result.price is None
        assert result.currency is None
        assert result.description is None
        assert result.brand is None
        assert result.rating is None
        assert result.review_count is None
        assert result.image_urls == []
        assert result.has_video is False

    def test_parse_empty_html(self) -> None:
        parser = TiktokShopParser()
        result = parser.parse("")

        assert result.marketplace == MarketplaceType.TIKTOK_SHOP
        assert result.title is None
        assert result.price is None

    def test_parse_malformed_html(self) -> None:
        parser = TiktokShopParser()
        result = parser.parse("<div><h1>Not closed properly<span>")

        assert result.marketplace == MarketplaceType.TIKTOK_SHOP
        assert isinstance(result, ProductData)

    def test_schema_org_extraction(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Schema TikTok",
                    "offers": {"price": "9.99", "priceCurrency": "SGD"},
                }
            ),
            body='<h1 data-testid="product-title">Schema TikTok</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)

        assert result.title == "Schema TikTok"
        assert result.price == "9.99"
        assert result.currency == "SGD"

    def test_availability_from_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Avail Test",
                    "offers": {"availability": "InStock"},
                }
            ),
            body='<h1 data-testid="product-title">Avail Test</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.availability is not None
        assert "instock" in result.availability.lower()

    def test_no_video_when_absent(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">No Video Product</h1>
            <img class="product-image" src="https://img.tiktok.com/test.jpg" alt="test" />
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.has_video is False

    def test_malformed_json_in_schema_script(self) -> None:
        """Malformed JSON in ld+json should not crash."""
        html = _wrap_html(
            head='<script type="application/ld+json">{not valid json</script>',
            body='<h1 data-testid="product-title">Malformed Schema</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.title == "Malformed Schema"
        assert result.schema_org == {}

    def test_offers_as_list(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "List Offers",
                    "offers": [{"price": "5.00", "priceCurrency": "USD"}],
                }
            ),
            body='<h1 data-testid="product-title">List Offers</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.price == "5.00"
        assert result.currency == "USD"

    def test_price_from_dom_without_schema(self) -> None:
        """Price from DOM when schema has no price."""
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">DOM Price</h1>
            <div class="product-price"><span>$25.50</span></div>
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.price == "25.50"

    def test_description_from_dom(self) -> None:
        """Description from DOM when schema has no description."""
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">DOM Desc</h1>
            <div class="product-description">A great product from DOM</div>
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.description == "A great product from DOM"

    def test_brand_as_string_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "String Brand", "brand": "DirectBrand"}
            ),
            body='<h1 data-testid="product-title">String Brand</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.brand == "DirectBrand"

    def test_brand_from_dom(self) -> None:
        """Brand from DOM when schema has no brand."""
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">DOM Brand</h1>
            <div class="product-brand">DOMBrand</div>
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.brand == "DOMBrand"

    def test_invalid_rating_in_schema(self) -> None:
        """Invalid rating value should not crash."""
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Bad Rating",
                    "aggregateRating": {"ratingValue": "not-a-number", "reviewCount": "bad"},
                }
            ),
            body='<h1 data-testid="product-title">Bad Rating</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_rating_from_dom(self) -> None:
        """Rating/reviews from DOM elements (no schema rating)."""
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">DOM Rating</h1>
            <span data-testid="rating-value">4.2</span>
            <span data-testid="review-count">55 reviews</span>
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.rating == 4.2
        assert result.review_count == 55

    def test_invalid_rating_in_dom(self) -> None:
        """Invalid rating in DOM element should not crash."""
        html = _wrap_html(
            body="""
            <h1 data-testid="product-title">Bad DOM Rating</h1>
            <span data-testid="rating-value">not-a-number</span>
            <span data-testid="review-count">no-number-here</span>
            """
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_h1_fallback_title(self) -> None:
        """Title from bare h1 when no data-testid or schema."""
        html = _wrap_html(body="<h1>Bare H1 Title</h1>")
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.title == "Bare H1 Title"

    def test_no_availability_in_schema(self) -> None:
        """No availability field in schema offers."""
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "No Avail", "offers": {"price": "10"}}
            ),
            body='<h1 data-testid="product-title">No Avail</h1>',
        )
        parser = TiktokShopParser()
        result = parser.parse(html)
        assert result.availability is None


# ===========================================================================
# Blibli Parser Tests
# ===========================================================================


class TestBlibliParser:
    """Tests for BlibliParser."""

    def test_is_base_parser(self) -> None:
        parser = BlibliParser()
        assert isinstance(parser, BaseParser)

    def test_parse_full_html(self) -> None:
        parser = BlibliParser()
        result = parser.parse(BLIBLI_HTML_FULL)

        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.BLIBLI
        assert result.title == "Samsung Galaxy A54"
        assert result.price == "4999000"
        assert result.currency == "IDR"
        assert result.description is not None
        assert "samsung" in result.description.lower()
        assert result.brand == "Samsung"
        assert result.rating == 4.5
        assert result.review_count == 150
        assert len(result.image_urls) >= 2
        assert len(result.specifications) >= 2
        assert "RAM" in result.specifications
        assert len(result.bullet_points) >= 2
        assert len(result.alt_texts) >= 2
        assert result.schema_org
        assert result.qa_count == 3

    def test_parse_minimal_html(self) -> None:
        parser = BlibliParser()
        result = parser.parse(BLIBLI_HTML_MINIMAL)

        assert result.marketplace == MarketplaceType.BLIBLI
        assert result.title == "Minimal Blibli Item"
        assert result.price is None
        assert result.description is None
        assert result.brand is None
        assert result.rating is None
        assert result.review_count is None

    def test_parse_empty_html(self) -> None:
        parser = BlibliParser()
        result = parser.parse("")

        assert result.marketplace == MarketplaceType.BLIBLI
        assert result.title is None

    def test_parse_malformed_html(self) -> None:
        parser = BlibliParser()
        result = parser.parse("<div><span>broken<")

        assert result.marketplace == MarketplaceType.BLIBLI
        assert isinstance(result, ProductData)

    def test_schema_org_extraction(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Blibli Schema Product",
                    "offers": {"price": "250000", "priceCurrency": "IDR"},
                    "brand": {"name": "TestBrand"},
                }
            ),
            body='<h1 data-testid="lblPDPDetailProductName">Blibli Schema Product</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)

        assert result.title == "Blibli Schema Product"
        assert result.price == "250000"
        assert result.currency == "IDR"
        assert result.brand == "TestBrand"

    def test_no_qa_when_absent(self) -> None:
        html = _wrap_html(
            body='<h1 data-testid="lblPDPDetailProductName">No QA</h1>'
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.qa_count is None or result.qa_count == 0

    def test_malformed_json_in_schema_script(self) -> None:
        html = _wrap_html(
            head='<script type="application/ld+json">{invalid json!!!</script>',
            body='<h1 data-testid="lblPDPDetailProductName">Bad JSON</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.title == "Bad JSON"
        assert result.schema_org == {}

    def test_offers_as_list(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "List Offers Blibli",
                    "offers": [{"price": "100000", "priceCurrency": "IDR"}],
                }
            ),
            body='<h1 data-testid="lblPDPDetailProductName">List Offers Blibli</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.price == "100000"
        assert result.currency == "IDR"

    def test_price_from_dom_without_schema(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="lblPDPDetailProductName">DOM Price</h1>
            <div data-testid="lblPDPDetailProductPrice">Rp1.500.000</div>
            """
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.price is not None

    def test_description_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="lblPDPDetailProductName">DOM Desc</h1>
            <div data-testid="lblPDPDetailProductDescription">Blibli description</div>
            """
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.description == "Blibli description"

    def test_brand_as_string_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "Str Brand", "brand": "BlibliDirect"}
            ),
            body='<h1 data-testid="lblPDPDetailProductName">Str Brand</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.brand == "BlibliDirect"

    def test_brand_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="lblPDPDetailProductName">DOM Brand</h1>
            <div data-testid="lblPDPDetailBrandName">DOMBlibli</div>
            """
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.brand == "DOMBlibli"

    def test_invalid_rating_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Bad Rating",
                    "aggregateRating": {"ratingValue": "bad", "reviewCount": "bad"},
                }
            ),
            body='<h1 data-testid="lblPDPDetailProductName">Bad Rating</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_rating_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="lblPDPDetailProductName">DOM Rating</h1>
            <span data-testid="lblPDPDetailProductRating">3.8</span>
            <span data-testid="lblPDPDetailReviewCount">200 ulasan</span>
            """
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.rating == 3.8
        assert result.review_count == 200

    def test_invalid_rating_in_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="lblPDPDetailProductName">Bad DOM Rating</h1>
            <span data-testid="lblPDPDetailProductRating">bad</span>
            <span data-testid="lblPDPDetailReviewCount">no-num</span>
            """
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_h1_fallback_title(self) -> None:
        html = _wrap_html(body="<h1>Bare Blibli H1</h1>")
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.title == "Bare Blibli H1"

    def test_no_availability_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "No Avail", "offers": {"price": "5"}}
            ),
            body='<h1 data-testid="lblPDPDetailProductName">No Avail</h1>',
        )
        parser = BlibliParser()
        result = parser.parse(html)
        assert result.availability is None


# ===========================================================================
# Zalora Parser Tests
# ===========================================================================


class TestZaloraParser:
    """Tests for ZaloraParser."""

    def test_is_base_parser(self) -> None:
        parser = ZaloraParser()
        assert isinstance(parser, BaseParser)

    def test_parse_full_html(self) -> None:
        parser = ZaloraParser()
        result = parser.parse(ZALORA_HTML_FULL)

        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.ZALORA
        assert result.title == "Nike Air Max 90"
        assert result.price == "159.00"
        assert result.currency == "SGD"
        assert result.description is not None
        assert "nike" in result.description.lower()
        assert result.brand == "Nike"
        assert result.rating == 4.6
        assert result.review_count == 89
        assert len(result.image_urls) >= 3
        assert len(result.specifications) >= 2
        assert "Material" in result.specifications
        assert len(result.bullet_points) >= 2
        assert len(result.alt_texts) >= 3
        assert result.schema_org

    def test_parse_minimal_html(self) -> None:
        parser = ZaloraParser()
        result = parser.parse(ZALORA_HTML_MINIMAL)

        assert result.marketplace == MarketplaceType.ZALORA
        assert result.title == "Minimal Zalora Dress"
        assert result.price is None
        assert result.description is None
        assert result.brand is None
        assert result.rating is None
        assert result.review_count is None

    def test_parse_empty_html(self) -> None:
        parser = ZaloraParser()
        result = parser.parse("")

        assert result.marketplace == MarketplaceType.ZALORA
        assert result.title is None

    def test_parse_malformed_html(self) -> None:
        parser = ZaloraParser()
        result = parser.parse("<html><body><div>not closed")

        assert result.marketplace == MarketplaceType.ZALORA
        assert isinstance(result, ProductData)

    def test_schema_org_extraction(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Zalora Schema Dress",
                    "offers": {"price": "89.90", "priceCurrency": "MYR"},
                    "brand": {"name": "ZaloraBrand"},
                    "aggregateRating": {"ratingValue": "4.2", "reviewCount": "30"},
                }
            ),
            body='<h1 data-testid="productTitle">Zalora Schema Dress</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)

        assert result.title == "Zalora Schema Dress"
        assert result.price == "89.90"
        assert result.currency == "MYR"
        assert result.brand == "ZaloraBrand"
        assert result.rating == 4.2
        assert result.review_count == 30

    def test_size_specs_captured(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">Size Test</h1>
            <div class="product-size-list">
                <div class="size-option">S</div>
                <div class="size-option">M</div>
                <div class="size-option">L</div>
            </div>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        # Sizes should be captured in specifications
        assert "Sizes" in result.specifications
        assert "S" in result.specifications["Sizes"]

    def test_malformed_json_in_schema_script(self) -> None:
        html = _wrap_html(
            head='<script type="application/ld+json">{broken json</script>',
            body='<h1 data-testid="productTitle">Bad JSON</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.title == "Bad JSON"
        assert result.schema_org == {}

    def test_offers_as_list(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "List Offers Zalora",
                    "offers": [{"price": "80.00", "priceCurrency": "SGD"}],
                }
            ),
            body='<h1 data-testid="productTitle">List Offers Zalora</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.price == "80.00"
        assert result.currency == "SGD"

    def test_price_from_dom_without_schema(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">DOM Price</h1>
            <div data-testid="productPrice">S$120.00</div>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.price is not None

    def test_description_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">DOM Desc</h1>
            <div data-testid="productDescription">Zalora product description</div>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.description == "Zalora product description"

    def test_brand_as_string_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "Str Brand", "brand": "ZaloraDirect"}
            ),
            body='<h1 data-testid="productTitle">Str Brand</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.brand == "ZaloraDirect"

    def test_brand_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">DOM Brand</h1>
            <div data-testid="productBrand">DOMZalora</div>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.brand == "DOMZalora"

    def test_invalid_rating_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Bad Rating",
                    "aggregateRating": {"ratingValue": "bad", "reviewCount": "bad"},
                }
            ),
            body='<h1 data-testid="productTitle">Bad Rating</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_rating_from_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">DOM Rating</h1>
            <span data-testid="ratingValue">4.0</span>
            <span data-testid="reviewCount">75 reviews</span>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.rating == 4.0
        assert result.review_count == 75

    def test_invalid_rating_in_dom(self) -> None:
        html = _wrap_html(
            body="""
            <h1 data-testid="productTitle">Bad DOM Rating</h1>
            <span data-testid="ratingValue">invalid</span>
            <span data-testid="reviewCount">no-num</span>
            """
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_h1_fallback_title(self) -> None:
        html = _wrap_html(body="<h1>Bare Zalora H1</h1>")
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.title == "Bare Zalora H1"

    def test_no_availability_in_schema(self) -> None:
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "No Avail", "offers": {"price": "10"}}
            ),
            body='<h1 data-testid="productTitle">No Avail</h1>',
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert result.availability is None

    def test_no_sizes(self) -> None:
        html = _wrap_html(
            body='<h1 data-testid="productTitle">No Sizes</h1>'
        )
        parser = ZaloraParser()
        result = parser.parse(html)
        assert "Sizes" not in result.specifications


# ===========================================================================
# Generic Parser Tests
# ===========================================================================


class TestGenericParser:
    """Tests for GenericParser (fallback parser)."""

    def test_is_base_parser(self) -> None:
        parser = GenericParser()
        assert isinstance(parser, BaseParser)

    def test_parse_schema_org(self) -> None:
        parser = GenericParser()
        result = parser.parse(GENERIC_SCHEMA_ORG_HTML)

        assert result.marketplace == MarketplaceType.GENERIC
        assert result.title == "Schema Product"
        assert result.description == "A product from Schema.org"
        assert result.price == "29.99"
        assert result.currency == "EUR"
        assert result.brand == "SchemaBrand"
        assert result.rating == 3.9
        assert result.review_count == 42
        assert "InStock" in (result.availability or "")
        assert len(result.image_urls) >= 2
        assert result.schema_org

    def test_parse_opengraph(self) -> None:
        parser = GenericParser()
        result = parser.parse(GENERIC_OPENGRAPH_HTML)

        assert result.marketplace == MarketplaceType.GENERIC
        assert result.title == "OG Product Title"
        assert result.description == "OG Product Description"
        assert result.price == "19.99"
        assert result.currency == "GBP"
        assert result.brand == "OGBrand"
        assert "https://example.com/og-img.jpg" in result.image_urls

    def test_schema_org_takes_priority_over_opengraph(self) -> None:
        parser = GenericParser()
        result = parser.parse(GENERIC_BOTH_HTML)

        # Schema.org should take priority
        assert result.title == "Schema Name Wins"
        assert result.description == "Schema description"
        assert result.brand == "SchemaBrand"
        assert result.price == "50.00"
        assert result.currency == "USD"
        # OG image should still be used as fallback
        assert len(result.image_urls) >= 1

    def test_meta_tags_fallback(self) -> None:
        parser = GenericParser()
        result = parser.parse(GENERIC_META_TAGS_HTML)

        assert result.marketplace == MarketplaceType.GENERIC
        assert result.title == "Meta Product Title"
        assert result.description == "Meta product description"
        # Images from body
        assert "https://example.com/meta-img.jpg" in result.image_urls

    def test_parse_empty_html(self) -> None:
        parser = GenericParser()
        result = parser.parse("")

        assert result.marketplace == MarketplaceType.GENERIC
        assert result.title is None
        assert result.price is None
        assert result.description is None

    def test_parse_malformed_html(self) -> None:
        parser = GenericParser()
        result = parser.parse("<div><span>unclosed tags<")

        assert result.marketplace == MarketplaceType.GENERIC
        assert isinstance(result, ProductData)

    def test_schema_org_list_format(self) -> None:
        """Schema.org JSON-LD can be a list instead of a single object."""
        parser = GenericParser()
        result = parser.parse(GENERIC_SCHEMA_LIST_HTML)

        assert result.title == "Product In List"
        assert result.price == "10.00"
        assert result.currency == "CAD"

    def test_schema_org_graph_format(self) -> None:
        """Schema.org JSON-LD with @graph array."""
        parser = GenericParser()
        result = parser.parse(GENERIC_SCHEMA_GRAPH_HTML)

        assert result.title == "Graph Product"
        assert result.price == "15.00"
        assert result.currency == "AUD"
        assert result.brand == "GraphBrand"

    def test_opengraph_availability(self) -> None:
        parser = GenericParser()
        result = parser.parse(GENERIC_OPENGRAPH_HTML)
        assert result.availability is not None
        assert "in stock" in result.availability.lower()

    def test_no_schema_no_og_no_meta(self) -> None:
        """Pure body-only HTML with nothing structured."""
        html = _wrap_html(body="<p>Just some text</p>")
        parser = GenericParser()
        result = parser.parse(html)

        assert result.marketplace == MarketplaceType.GENERIC
        assert result.title is None
        assert result.price is None

    def test_schema_org_image_as_string(self) -> None:
        """Schema.org image can be a string instead of a list."""
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Single Image",
                    "image": "https://example.com/single.jpg",
                }
            ),
            body="<h1>Single Image</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert "https://example.com/single.jpg" in result.image_urls

    def test_schema_org_brand_as_string(self) -> None:
        """Schema.org brand can be a string instead of an object."""
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "String Brand",
                    "brand": "DirectBrandName",
                }
            ),
            body="<h1>String Brand</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.brand == "DirectBrandName"

    def test_alt_texts_from_body_images(self) -> None:
        """Generic parser should extract alt text from body images."""
        html = _wrap_html(
            body="""
            <img src="https://example.com/a.jpg" alt="Product angle A" />
            <img src="https://example.com/b.jpg" alt="Product angle B" />
            <img src="https://example.com/c.jpg" />
            """
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert "Product angle A" in result.alt_texts
        assert "Product angle B" in result.alt_texts

    def test_multiple_schema_scripts(self) -> None:
        """Page with multiple ld+json scripts, only one is Product."""
        html = _wrap_html(
            head=(
                _schema_org_script({"@type": "Organization", "name": "Org"})
                + _schema_org_script(
                    {"@type": "Product", "name": "Multi Script Product", "offers": {"price": "5"}}
                )
            ),
            body="<h1>Multi Script</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.title == "Multi Script Product"
        assert result.price == "5"

    def test_schema_offers_as_list(self) -> None:
        """Offers can be a list; use the first one."""
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Multi Offer",
                    "offers": [
                        {"price": "100", "priceCurrency": "USD"},
                        {"price": "200", "priceCurrency": "USD"},
                    ],
                }
            ),
            body="<h1>Multi Offer</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.price == "100"
        assert result.currency == "USD"

    def test_video_detection(self) -> None:
        """Generic parser detects video elements."""
        html = _wrap_html(
            body="""
            <h1>Video Product</h1>
            <video src="https://example.com/demo.mp4"></video>
            """
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.has_video is True

    def test_no_video(self) -> None:
        html = _wrap_html(body="<h1>No Video</h1>")
        parser = GenericParser()
        result = parser.parse(html)
        assert result.has_video is False

    def test_malformed_json_in_schema_script(self) -> None:
        """Malformed JSON in ld+json should be ignored."""
        html = _wrap_html(
            head='<script type="application/ld+json">{bad json here!!!</script>',
            body="<h1>Malformed</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.schema_org == {}
        assert result.title is None  # No schema, no meta, no OG

    def test_invalid_rating_in_schema(self) -> None:
        """Invalid rating/review values in schema should not crash."""
        html = _wrap_html(
            head=_schema_org_script(
                {
                    "@type": "Product",
                    "name": "Bad Rating",
                    "aggregateRating": {
                        "ratingValue": "not-a-float",
                        "reviewCount": "not-an-int",
                    },
                }
            ),
            body="<h1>Bad Rating</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.rating is None
        assert result.review_count is None

    def test_empty_brand_dict_returns_none(self) -> None:
        """Brand dict with empty name returns None."""
        html = _wrap_html(
            head=_schema_org_script(
                {"@type": "Product", "name": "Empty Brand", "brand": {"name": ""}}
            ),
            body="<h1>Empty Brand</h1>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.brand is None

    def test_meta_description_empty_content(self) -> None:
        """Meta description with empty content returns None."""
        html = _wrap_html(
            head='<meta name="description" content="" />',
            body="<p>Content</p>",
        )
        parser = GenericParser()
        result = parser.parse(html)
        assert result.description is None

    def test_title_tag_empty(self) -> None:
        """Empty title tag returns None."""
        html = _wrap_html(head="<title></title>", body="<p>Content</p>")
        parser = GenericParser()
        result = parser.parse(html)
        assert result.title is None
