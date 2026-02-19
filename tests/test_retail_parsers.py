"""Tests for retail marketplace parsers: registry, base, and 7 parsers."""

from __future__ import annotations

import json

import pytest

from context_cli.core.models import MarketplaceType, ProductData
from context_cli.core.retail.parsers import detect_marketplace, get_parser
from context_cli.core.retail.parsers.amazon import AmazonParser
from context_cli.core.retail.parsers.base import BaseParser
from context_cli.core.retail.parsers.blibli import BlibliParser
from context_cli.core.retail.parsers.lazada import LazadaParser
from context_cli.core.retail.parsers.shopee import ShopeeParser
from context_cli.core.retail.parsers.tiktok_shop import TiktokShopParser
from context_cli.core.retail.parsers.tokopedia import TokopediaParser
from context_cli.core.retail.parsers.zalora import ZaloraParser

# ── ProductData model tests ──────────────────────────────────────────────────


class TestProductDataModel:
    """Tests for the ProductData Pydantic model."""

    def test_default_values(self) -> None:
        data = ProductData()
        assert data.title is None
        assert data.description is None
        assert data.price is None
        assert data.currency is None
        assert data.availability is None
        assert data.image_urls == []
        assert data.brand is None
        assert data.rating is None
        assert data.review_count is None
        assert data.bullet_points == []
        assert data.specifications == {}
        assert data.has_video is False
        assert data.has_aplus_content is False
        assert data.qa_count is None
        assert data.schema_org == {}
        assert data.marketplace == MarketplaceType.GENERIC
        assert data.url == ""
        assert data.alt_texts == []

    def test_full_values(self) -> None:
        data = ProductData(
            title="Test Product",
            description="A great product",
            price="29.99",
            currency="USD",
            availability="In Stock",
            image_urls=["https://img.example.com/1.jpg"],
            brand="TestBrand",
            rating=4.5,
            review_count=123,
            bullet_points=["Feature 1", "Feature 2"],
            specifications={"Color": "Red"},
            has_video=True,
            has_aplus_content=True,
            qa_count=10,
            schema_org={"@type": "Product"},
            marketplace=MarketplaceType.AMAZON,
            url="https://amazon.com/dp/123",
            alt_texts=["Product image 1"],
        )
        assert data.title == "Test Product"
        assert data.rating == 4.5
        assert data.marketplace == MarketplaceType.AMAZON
        assert len(data.bullet_points) == 2


class TestMarketplaceType:
    """Tests for MarketplaceType enum."""

    def test_all_types_exist(self) -> None:
        assert MarketplaceType.AMAZON == "amazon"
        assert MarketplaceType.SHOPEE == "shopee"
        assert MarketplaceType.LAZADA == "lazada"
        assert MarketplaceType.TOKOPEDIA == "tokopedia"
        assert MarketplaceType.TIKTOK_SHOP == "tiktok_shop"
        assert MarketplaceType.BLIBLI == "blibli"
        assert MarketplaceType.ZALORA == "zalora"
        assert MarketplaceType.GENERIC == "generic"


# ── Registry tests ───────────────────────────────────────────────────────────


class TestDetectMarketplace:
    """Tests for detect_marketplace() URL matching."""

    # Amazon TLDs
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.amazon.com/dp/B01234",
            "https://amazon.com/dp/B01234",
            "https://www.amazon.co.uk/dp/B01234",
            "https://www.amazon.de/dp/B01234",
            "https://www.amazon.co.jp/dp/B01234",
            "https://www.amazon.fr/dp/B01234",
            "https://www.amazon.it/dp/B01234",
            "https://www.amazon.es/dp/B01234",
            "https://www.amazon.ca/dp/B01234",
            "https://www.amazon.com.au/dp/B01234",
            "https://www.amazon.in/dp/B01234",
            "https://www.amazon.com.br/dp/B01234",
            "https://www.amazon.sg/dp/B01234",
        ],
    )
    def test_amazon_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.AMAZON

    # Shopee TLDs
    @pytest.mark.parametrize(
        "url",
        [
            "https://shopee.sg/product/123",
            "https://shopee.co.id/product/123",
            "https://shopee.com.my/product/123",
            "https://shopee.co.th/product/123",
            "https://shopee.vn/product/123",
            "https://shopee.ph/product/123",
            "https://shopee.com.br/product/123",
            "https://shopee.tw/product/123",
        ],
    )
    def test_shopee_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.SHOPEE

    # Lazada TLDs
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.lazada.sg/products/item-123.html",
            "https://www.lazada.co.id/products/item-123.html",
            "https://www.lazada.com.my/products/item-123.html",
            "https://www.lazada.co.th/products/item-123.html",
            "https://www.lazada.vn/products/item-123.html",
            "https://www.lazada.com.ph/products/item-123.html",
        ],
    )
    def test_lazada_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.LAZADA

    # Tokopedia
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.tokopedia.com/shop/product-123",
            "https://tokopedia.com/shop/product-123",
        ],
    )
    def test_tokopedia_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.TOKOPEDIA

    # TikTok Shop
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.tiktok.com/shop/product/123",
            "https://tiktok.com/shop/product/123",
        ],
    )
    def test_tiktok_shop_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.TIKTOK_SHOP

    # Blibli
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.blibli.com/p/product-123",
            "https://blibli.com/p/product-123",
        ],
    )
    def test_blibli_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.BLIBLI

    # Zalora
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.zalora.sg/product/123",
            "https://www.zalora.co.id/product/123",
            "https://www.zalora.com.my/product/123",
            "https://www.zalora.co.th/product/123",
            "https://www.zalora.vn/product/123",
            "https://www.zalora.com.ph/product/123",
            "https://www.zalora.com.hk/product/123",
            "https://www.zalora.com.tw/product/123",
            "https://www.zalora.com/product/123",
        ],
    )
    def test_zalora_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.ZALORA

    # Unknown/Generic
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.example.com/product",
            "https://www.ebay.com/itm/123",
            "https://www.walmart.com/ip/123",
            "",
        ],
    )
    def test_generic_urls(self, url: str) -> None:
        assert detect_marketplace(url) == MarketplaceType.GENERIC

    def test_case_insensitive(self) -> None:
        assert detect_marketplace("https://www.AMAZON.COM/dp/B123") == MarketplaceType.AMAZON
        assert detect_marketplace("https://SHOPEE.SG/product/1") == MarketplaceType.SHOPEE


class TestGetParser:
    """Tests for get_parser() factory function."""

    def test_amazon_parser(self) -> None:
        parser = get_parser(MarketplaceType.AMAZON)
        assert isinstance(parser, AmazonParser)

    def test_shopee_parser(self) -> None:
        parser = get_parser(MarketplaceType.SHOPEE)
        assert isinstance(parser, ShopeeParser)

    def test_lazada_parser(self) -> None:
        parser = get_parser(MarketplaceType.LAZADA)
        assert isinstance(parser, LazadaParser)

    def test_tokopedia_parser(self) -> None:
        parser = get_parser(MarketplaceType.TOKOPEDIA)
        assert isinstance(parser, TokopediaParser)

    def test_generic_returns_base_parser(self) -> None:
        parser = get_parser(MarketplaceType.GENERIC)
        assert isinstance(parser, BaseParser)

    def test_tiktok_shop_parser(self) -> None:
        parser = get_parser(MarketplaceType.TIKTOK_SHOP)
        assert isinstance(parser, TiktokShopParser)

    def test_blibli_parser(self) -> None:
        parser = get_parser(MarketplaceType.BLIBLI)
        assert isinstance(parser, BlibliParser)

    def test_zalora_parser(self) -> None:
        parser = get_parser(MarketplaceType.ZALORA)
        assert isinstance(parser, ZaloraParser)

    def test_parser_is_subclass_of_base(self) -> None:
        for mp_type in [
            MarketplaceType.AMAZON,
            MarketplaceType.SHOPEE,
            MarketplaceType.LAZADA,
            MarketplaceType.TOKOPEDIA,
            MarketplaceType.TIKTOK_SHOP,
            MarketplaceType.BLIBLI,
            MarketplaceType.ZALORA,
        ]:
            parser = get_parser(mp_type)
            assert isinstance(parser, BaseParser)


# ── BaseParser tests ─────────────────────────────────────────────────────────


class TestBaseParser:
    """Tests for the BaseParser default parse implementation."""

    def test_base_parser_returns_empty_product_data(self) -> None:
        parser = BaseParser()
        result = parser.parse("<html><body>Hello</body></html>")
        assert isinstance(result, ProductData)
        assert result.title is None

    def test_base_parser_extracts_schema_org(self) -> None:
        html = """<html><head>
        <script type="application/ld+json">
        {"@type": "Product", "name": "Widget"}
        </script>
        </head><body></body></html>"""
        parser = BaseParser()
        result = parser.parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_base_parser_empty_html(self) -> None:
        parser = BaseParser()
        result = parser.parse("")
        assert isinstance(result, ProductData)

    def test_base_parser_marketplace_property(self) -> None:
        parser = BaseParser()
        assert parser.marketplace == MarketplaceType.GENERIC


# ── Amazon parser tests ──────────────────────────────────────────────────────


def _make_amazon_html(
    title: str = "Test Product",
    price: str = "$29.99",
    brand: str = "TestBrand",
    rating: str = "4.5 out of 5 stars",
    review_count: str = "1,234 ratings",
    bullet_points: list[str] | None = None,
    specs: dict[str, str] | None = None,
    images: list[str] | None = None,
    alt_texts: list[str] | None = None,
    has_video: bool = False,
    has_aplus: bool = False,
    qa_count: str | None = None,
    schema_org: dict | None = None,
    description: str = "A great product description.",
    availability: str = "In Stock.",
) -> str:
    """Build synthetic Amazon product HTML."""
    if bullet_points is None:
        bullet_points = ["Feature 1", "Feature 2"]
    if specs is None:
        specs = {"Color": "Red", "Size": "Medium"}
    if images is None:
        images = ["https://images-na.ssl-images-amazon.com/images/I/img1.jpg"]
    if alt_texts is None:
        alt_texts = ["Product image"]

    bp_html = "\n".join(f'<span class="a-list-item">{bp}</span>' for bp in bullet_points)
    spec_rows = "\n".join(
        f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in specs.items()
    )
    img_html = "\n".join(
        f'<img class="a-dynamic-image" src="{url}" alt="{alt}">'
        for url, alt in zip(images, alt_texts)
    )
    video_html = '<div class="a-video-player">Video</div>' if has_video else ""
    aplus_html = '<div id="aplus">Enhanced content</div>' if has_aplus else ""
    qa_html = f'<span id="askATFLink">{qa_count} answered questions</span>' if qa_count else ""
    schema_html = ""
    if schema_org:
        schema_html = (
            '<script type="application/ld+json">'
            + json.dumps(schema_org)
            + "</script>"
        )

    return f"""<html><head>{schema_html}</head><body>
    <span id="productTitle">{title}</span>
    <span class="a-price-whole">{price}</span>
    <a id="bylineInfo">{brand}</a>
    <span id="acrPopover" title="{rating}"></span>
    <span id="acrCustomerReviewText">{review_count}</span>
    <div id="availability"><span>{availability}</span></div>
    <div id="feature-bullets"><ul>{bp_html}</ul></div>
    <table id="productDetails_techSpec_section_1">{spec_rows}</table>
    <div id="productDescription"><p>{description}</p></div>
    <div id="altImages">{img_html}</div>
    {video_html}
    {aplus_html}
    {qa_html}
    </body></html>"""


class TestAmazonParser:
    """Tests for AmazonParser."""

    def test_marketplace_type(self) -> None:
        parser = AmazonParser()
        assert parser.marketplace == MarketplaceType.AMAZON

    def test_parse_title(self) -> None:
        html = _make_amazon_html(title="Amazing Widget Pro")
        result = AmazonParser().parse(html)
        assert result.title == "Amazing Widget Pro"

    def test_parse_price(self) -> None:
        html = _make_amazon_html(price="$49.99")
        result = AmazonParser().parse(html)
        assert result.price is not None
        assert "49.99" in result.price

    def test_parse_brand(self) -> None:
        html = _make_amazon_html(brand="Visit the Acme Store")
        result = AmazonParser().parse(html)
        assert result.brand is not None
        assert "Acme" in result.brand

    def test_parse_rating(self) -> None:
        html = _make_amazon_html(rating="4.3 out of 5 stars")
        result = AmazonParser().parse(html)
        assert result.rating == 4.3

    def test_parse_review_count(self) -> None:
        html = _make_amazon_html(review_count="2,345 ratings")
        result = AmazonParser().parse(html)
        assert result.review_count == 2345

    def test_parse_bullet_points(self) -> None:
        html = _make_amazon_html(bullet_points=["Durable", "Lightweight", "Portable"])
        result = AmazonParser().parse(html)
        assert len(result.bullet_points) == 3
        assert "Durable" in result.bullet_points

    def test_parse_specifications(self) -> None:
        html = _make_amazon_html(specs={"Weight": "500g", "Material": "Steel"})
        result = AmazonParser().parse(html)
        assert result.specifications.get("Weight") == "500g"
        assert result.specifications.get("Material") == "Steel"

    def test_parse_images(self) -> None:
        html = _make_amazon_html(
            images=["https://img.com/1.jpg", "https://img.com/2.jpg"],
            alt_texts=["Front view", "Side view"],
        )
        result = AmazonParser().parse(html)
        assert len(result.image_urls) == 2
        assert len(result.alt_texts) == 2
        assert "Front view" in result.alt_texts

    def test_parse_video(self) -> None:
        html = _make_amazon_html(has_video=True)
        result = AmazonParser().parse(html)
        assert result.has_video is True

    def test_parse_no_video(self) -> None:
        html = _make_amazon_html(has_video=False)
        result = AmazonParser().parse(html)
        assert result.has_video is False

    def test_parse_aplus_content(self) -> None:
        html = _make_amazon_html(has_aplus=True)
        result = AmazonParser().parse(html)
        assert result.has_aplus_content is True

    def test_parse_no_aplus(self) -> None:
        html = _make_amazon_html(has_aplus=False)
        result = AmazonParser().parse(html)
        assert result.has_aplus_content is False

    def test_parse_qa_count(self) -> None:
        html = _make_amazon_html(qa_count="42")
        result = AmazonParser().parse(html)
        assert result.qa_count == 42

    def test_parse_schema_org(self) -> None:
        schema = {"@context": "https://schema.org", "@type": "Product", "name": "Widget"}
        html = _make_amazon_html(schema_org=schema)
        result = AmazonParser().parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_parse_description(self) -> None:
        html = _make_amazon_html(description="Super detailed product description here.")
        result = AmazonParser().parse(html)
        assert result.description is not None
        assert "Super detailed" in result.description

    def test_parse_availability(self) -> None:
        html = _make_amazon_html(availability="In Stock.")
        result = AmazonParser().parse(html)
        assert result.availability is not None
        assert "In Stock" in result.availability

    def test_parse_empty_html(self) -> None:
        result = AmazonParser().parse("<html><body></body></html>")
        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.AMAZON

    def test_parse_missing_fields(self) -> None:
        html = "<html><body><span id='productTitle'>Only Title</span></body></html>"
        result = AmazonParser().parse(html)
        assert result.title == "Only Title"
        assert result.price is None
        assert result.rating is None

    def test_currency_usd(self) -> None:
        html = _make_amazon_html(price="$29.99")
        result = AmazonParser().parse(html)
        assert result.currency == "USD"

    def test_currency_gbp(self) -> None:
        html = '<html><body><span class="a-price-whole">\u00a329.99</span></body></html>'
        result = AmazonParser().parse(html)
        assert result.currency == "GBP"

    def test_currency_eur(self) -> None:
        html = '<html><body><span class="a-price-whole">\u20ac29.99</span></body></html>'
        result = AmazonParser().parse(html)
        assert result.currency == "EUR"

    def test_currency_jpy(self) -> None:
        html = '<html><body><span class="a-price-whole">\u00a52999</span></body></html>'
        result = AmazonParser().parse(html)
        assert result.currency == "JPY"

    def test_currency_unknown(self) -> None:
        html = '<html><body><span class="a-price-whole">29.99</span></body></html>'
        result = AmazonParser().parse(html)
        assert result.currency is None


# ── Shopee parser tests ──────────────────────────────────────────────────────


def _make_shopee_html(
    title: str = "Shopee Product",
    price: str = "29.99",
    currency_symbol: str = "$",
    brand: str = "ShopeeBrand",
    rating: str = "4.7",
    review_count: str = "567",
    description: str = "Shopee product description",
    images: list[str] | None = None,
    alt_texts: list[str] | None = None,
    has_video: bool = False,
    specs: dict[str, str] | None = None,
    schema_org: dict | None = None,
) -> str:
    """Build synthetic Shopee product HTML."""
    if images is None:
        images = ["https://cf.shopee.sg/file/img1"]
    if alt_texts is None:
        alt_texts = ["Product photo"]
    if specs is None:
        specs = {}

    img_html = "\n".join(
        f'<div class="shopee-image"><img src="{url}" alt="{alt}"></div>'
        for url, alt in zip(images, alt_texts)
    )
    spec_html = "\n".join(
        f'<div class="product-detail"><label>{k}</label><span>{v}</span></div>'
        for k, v in specs.items()
    )
    video_html = '<div class="shopee-video">Video</div>' if has_video else ""
    schema_html = ""
    if schema_org:
        schema_html = (
            '<script type="application/ld+json">'
            + json.dumps(schema_org)
            + "</script>"
        )

    return f"""<html><head>{schema_html}</head><body>
    <div class="product-briefing">
        <div class="product-title"><span>{title}</span></div>
        <div class="product-price"><span>{currency_symbol}{price}</span></div>
        <div class="product-brand"><a>{brand}</a></div>
        <div class="product-rating">
            <div class="shopee-rating-stars__stars" data-rating="{rating}">
                <span>{rating}</span>
            </div>
        </div>
        <div class="product-review-count"><span>{review_count}</span></div>
    </div>
    <div class="product-detail-section">
        <div class="product-description">{description}</div>
        {spec_html}
    </div>
    <div class="product-images">{img_html}</div>
    {video_html}
    </body></html>"""


class TestShopeeParser:
    """Tests for ShopeeParser."""

    def test_marketplace_type(self) -> None:
        parser = ShopeeParser()
        assert parser.marketplace == MarketplaceType.SHOPEE

    def test_parse_title(self) -> None:
        html = _make_shopee_html(title="Shopee Gadget X")
        result = ShopeeParser().parse(html)
        assert result.title == "Shopee Gadget X"

    def test_parse_price(self) -> None:
        html = _make_shopee_html(price="15.50", currency_symbol="S$")
        result = ShopeeParser().parse(html)
        assert result.price is not None
        assert "15.50" in result.price

    def test_parse_brand(self) -> None:
        html = _make_shopee_html(brand="TechCo")
        result = ShopeeParser().parse(html)
        assert result.brand == "TechCo"

    def test_parse_rating(self) -> None:
        html = _make_shopee_html(rating="4.8")
        result = ShopeeParser().parse(html)
        assert result.rating == 4.8

    def test_parse_review_count(self) -> None:
        html = _make_shopee_html(review_count="890")
        result = ShopeeParser().parse(html)
        assert result.review_count == 890

    def test_parse_description(self) -> None:
        html = _make_shopee_html(description="Detailed product info here")
        result = ShopeeParser().parse(html)
        assert result.description is not None
        assert "Detailed product info" in result.description

    def test_parse_images(self) -> None:
        html = _make_shopee_html(
            images=["https://cf.shopee.sg/img1", "https://cf.shopee.sg/img2"],
            alt_texts=["Photo 1", "Photo 2"],
        )
        result = ShopeeParser().parse(html)
        assert len(result.image_urls) == 2
        assert len(result.alt_texts) == 2

    def test_parse_video(self) -> None:
        html = _make_shopee_html(has_video=True)
        result = ShopeeParser().parse(html)
        assert result.has_video is True

    def test_parse_specifications(self) -> None:
        html = _make_shopee_html(specs={"Brand": "Nike", "Size": "L"})
        result = ShopeeParser().parse(html)
        assert result.specifications.get("Brand") == "Nike"

    def test_parse_schema_org(self) -> None:
        schema = {"@type": "Product", "name": "Gadget"}
        html = _make_shopee_html(schema_org=schema)
        result = ShopeeParser().parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_parse_empty_html(self) -> None:
        result = ShopeeParser().parse("<html><body></body></html>")
        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.SHOPEE

    def test_parse_missing_fields(self) -> None:
        html = """<html><body>
        <div class="product-briefing">
            <div class="product-title"><span>Minimal</span></div>
        </div>
        </body></html>"""
        result = ShopeeParser().parse(html)
        assert result.title == "Minimal"
        assert result.price is None


# ── Lazada parser tests ──────────────────────────────────────────────────────


def _make_lazada_html(
    title: str = "Lazada Product",
    price: str = "39.99",
    currency_symbol: str = "S$",
    brand: str = "LazadaBrand",
    rating: str = "4.2",
    review_count: str = "345",
    description: str = "Lazada product description",
    images: list[str] | None = None,
    alt_texts: list[str] | None = None,
    has_video: bool = False,
    specs: dict[str, str] | None = None,
    schema_org: dict | None = None,
) -> str:
    """Build synthetic Lazada product HTML."""
    if images is None:
        images = ["https://sg-live.slatic.net/img1.jpg"]
    if alt_texts is None:
        alt_texts = ["Product"]
    if specs is None:
        specs = {}

    img_html = "\n".join(
        f'<div class="gallery-preview-panel__content"><img src="{url}" alt="{alt}"></div>'
        for url, alt in zip(images, alt_texts)
    )
    spec_html = "\n".join(
        f'<li class="specification-key"><span class="key-title">{k}</span>'
        f'<span class="key-value">{v}</span></li>'
        for k, v in specs.items()
    )
    video_html = '<div class="pdp-video-player">Video</div>' if has_video else ""
    schema_html = ""
    if schema_org:
        schema_html = (
            '<script type="application/ld+json">'
            + json.dumps(schema_org)
            + "</script>"
        )

    return f"""<html><head>{schema_html}</head><body>
    <div class="pdp-mod-product-badge-wrapper">
        <h1 class="pdp-mod-product-badge-title">{title}</h1>
        <span class="pdp-price pdp-price_type_normal pdp-price_color_orange
         pdp-price_size_xl">{currency_symbol} {price}</span>
        <a class="pdp-product-brand__brand-link">{brand}</a>
        <span class="score-average">{rating}</span>
        <span class="pdp-review-summary__link">{review_count} Ratings</span>
    </div>
    <div class="pdp-product-desc">
        <div class="detail-content">{description}</div>
    </div>
    <ul class="specification-keys">{spec_html}</ul>
    <div class="gallery-preview-panel">{img_html}</div>
    {video_html}
    </body></html>"""


class TestLazadaParser:
    """Tests for LazadaParser."""

    def test_marketplace_type(self) -> None:
        parser = LazadaParser()
        assert parser.marketplace == MarketplaceType.LAZADA

    def test_parse_title(self) -> None:
        html = _make_lazada_html(title="Lazada Super Gadget")
        result = LazadaParser().parse(html)
        assert result.title == "Lazada Super Gadget"

    def test_parse_price(self) -> None:
        html = _make_lazada_html(price="55.00", currency_symbol="S$")
        result = LazadaParser().parse(html)
        assert result.price is not None
        assert "55.00" in result.price

    def test_parse_brand(self) -> None:
        html = _make_lazada_html(brand="BrandCo")
        result = LazadaParser().parse(html)
        assert result.brand == "BrandCo"

    def test_parse_rating(self) -> None:
        html = _make_lazada_html(rating="3.9")
        result = LazadaParser().parse(html)
        assert result.rating == 3.9

    def test_parse_review_count(self) -> None:
        html = _make_lazada_html(review_count="1234")
        result = LazadaParser().parse(html)
        assert result.review_count == 1234

    def test_parse_description(self) -> None:
        html = _make_lazada_html(description="Very detailed Lazada description")
        result = LazadaParser().parse(html)
        assert result.description is not None
        assert "Very detailed" in result.description

    def test_parse_images(self) -> None:
        html = _make_lazada_html(
            images=["https://img1.lazada.com/1.jpg", "https://img2.lazada.com/2.jpg"],
            alt_texts=["View 1", "View 2"],
        )
        result = LazadaParser().parse(html)
        assert len(result.image_urls) == 2

    def test_parse_video(self) -> None:
        html = _make_lazada_html(has_video=True)
        result = LazadaParser().parse(html)
        assert result.has_video is True

    def test_parse_specifications(self) -> None:
        html = _make_lazada_html(specs={"Weight": "300g", "Color": "Black"})
        result = LazadaParser().parse(html)
        assert result.specifications.get("Weight") == "300g"
        assert result.specifications.get("Color") == "Black"

    def test_parse_schema_org(self) -> None:
        schema = {"@type": "Product", "name": "Lazada Item"}
        html = _make_lazada_html(schema_org=schema)
        result = LazadaParser().parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_parse_empty_html(self) -> None:
        result = LazadaParser().parse("<html><body></body></html>")
        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.LAZADA

    def test_parse_missing_fields(self) -> None:
        html = """<html><body>
        <h1 class="pdp-mod-product-badge-title">Only Title</h1>
        </body></html>"""
        result = LazadaParser().parse(html)
        assert result.title == "Only Title"
        assert result.price is None


# ── Tokopedia parser tests ───────────────────────────────────────────────────


def _make_tokopedia_html(
    title: str = "Tokopedia Product",
    price: str = "Rp199.000",
    brand: str = "",
    rating: str = "4.6",
    review_count: str = "789",
    description: str = "Tokopedia product description",
    images: list[str] | None = None,
    alt_texts: list[str] | None = None,
    has_video: bool = False,
    specs: dict[str, str] | None = None,
    schema_org: dict | None = None,
) -> str:
    """Build synthetic Tokopedia product HTML."""
    if images is None:
        images = ["https://images.tokopedia.net/img1.jpg"]
    if alt_texts is None:
        alt_texts = ["Product photo"]
    if specs is None:
        specs = {}

    img_html = "\n".join(
        f'<div class="css-image"><img src="{url}" alt="{alt}"></div>'
        for url, alt in zip(images, alt_texts)
    )
    spec_html = "\n".join(
        f'<li class="css-spec" data-testid="lblPDPInfoProduk">'
        f'<span>{k}</span><span>{v}</span></li>'
        for k, v in specs.items()
    )
    brand_html = f'<a data-testid="llbPDPFooterShopName">{brand}</a>' if brand else ""
    video_html = '<div data-testid="pdpVideoPlayer">Video</div>' if has_video else ""
    schema_html = ""
    if schema_org:
        schema_html = (
            '<script type="application/ld+json">'
            + json.dumps(schema_org)
            + "</script>"
        )

    return f"""<html><head>{schema_html}</head><body>
    <h1 data-testid="lblPDPDetailProductName">{title}</h1>
    <div data-testid="lblPDPDetailProductPrice">{price}</div>
    {brand_html}
    <span data-testid="lblPDPDetailProductRatingNumber">{rating}</span>
    <span data-testid="lblPDPDetailProductRatingCounter">({review_count} ulasan)</span>
    <div data-testid="lblPDPDescriptionProduk">{description}</div>
    <ul class="product-specifications">{spec_html}</ul>
    <div class="product-images">{img_html}</div>
    {video_html}
    </body></html>"""


class TestTokopediaParser:
    """Tests for TokopediaParser."""

    def test_marketplace_type(self) -> None:
        parser = TokopediaParser()
        assert parser.marketplace == MarketplaceType.TOKOPEDIA

    def test_parse_title(self) -> None:
        html = _make_tokopedia_html(title="Tokopedia Widget Z")
        result = TokopediaParser().parse(html)
        assert result.title == "Tokopedia Widget Z"

    def test_parse_price(self) -> None:
        html = _make_tokopedia_html(price="Rp299.000")
        result = TokopediaParser().parse(html)
        assert result.price is not None
        assert "299" in result.price

    def test_parse_brand(self) -> None:
        html = _make_tokopedia_html(brand="TokoShop")
        result = TokopediaParser().parse(html)
        assert result.brand == "TokoShop"

    def test_parse_rating(self) -> None:
        html = _make_tokopedia_html(rating="4.9")
        result = TokopediaParser().parse(html)
        assert result.rating == 4.9

    def test_parse_review_count(self) -> None:
        html = _make_tokopedia_html(review_count="456")
        result = TokopediaParser().parse(html)
        assert result.review_count == 456

    def test_parse_description(self) -> None:
        html = _make_tokopedia_html(description="Very nice product for sale")
        result = TokopediaParser().parse(html)
        assert result.description is not None
        assert "Very nice product" in result.description

    def test_parse_images(self) -> None:
        html = _make_tokopedia_html(
            images=["https://images.tokopedia.net/1.jpg"],
            alt_texts=["Main"],
        )
        result = TokopediaParser().parse(html)
        assert len(result.image_urls) == 1

    def test_parse_video(self) -> None:
        html = _make_tokopedia_html(has_video=True)
        result = TokopediaParser().parse(html)
        assert result.has_video is True

    def test_parse_specifications(self) -> None:
        html = _make_tokopedia_html(specs={"Berat": "500g", "Warna": "Merah"})
        result = TokopediaParser().parse(html)
        assert result.specifications.get("Berat") == "500g"

    def test_parse_schema_org(self) -> None:
        schema = {"@type": "Product", "name": "Toko Item"}
        html = _make_tokopedia_html(schema_org=schema)
        result = TokopediaParser().parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_parse_empty_html(self) -> None:
        result = TokopediaParser().parse("<html><body></body></html>")
        assert isinstance(result, ProductData)
        assert result.marketplace == MarketplaceType.TOKOPEDIA

    def test_parse_missing_fields(self) -> None:
        html = """<html><body>
        <h1 data-testid="lblPDPDetailProductName">Just Title</h1>
        </body></html>"""
        result = TokopediaParser().parse(html)
        assert result.title == "Just Title"
        assert result.price is None
        assert result.rating is None

    def test_parse_currency_idr(self) -> None:
        html = _make_tokopedia_html(price="Rp199.000")
        result = TokopediaParser().parse(html)
        assert result.currency == "IDR"

    def test_no_brand(self) -> None:
        html = _make_tokopedia_html(brand="")
        result = TokopediaParser().parse(html)
        assert result.brand is None

    def test_currency_non_rp(self) -> None:
        """Non-Rp price should not detect currency."""
        html = """<html><body>
        <div data-testid="lblPDPDetailProductPrice">$50.00</div>
        </body></html>"""
        result = TokopediaParser().parse(html)
        assert result.currency is None


# ── Edge case tests ──────────────────────────────────────────────────────────


class TestParserEdgeCases:
    """Edge cases across all parsers."""

    def test_malformed_json_ld(self) -> None:
        """Invalid JSON-LD should not crash parsers."""
        html = """<html><head>
        <script type="application/ld+json">NOT JSON AT ALL</script>
        </head><body></body></html>"""
        for parser_cls in [
            AmazonParser, ShopeeParser, LazadaParser, TokopediaParser,
            TiktokShopParser, BlibliParser, ZaloraParser,
        ]:
            result = parser_cls().parse(html)
            assert isinstance(result, ProductData)
            assert result.schema_org == {}

    def test_multiple_json_ld_blocks(self) -> None:
        """First valid Product JSON-LD should be used."""
        html = """<html><head>
        <script type="application/ld+json">{"@type": "BreadcrumbList"}</script>
        <script type="application/ld+json">{"@type": "Product", "name": "W"}</script>
        </head><body>
        <span id="productTitle">Title</span>
        </body></html>"""
        result = AmazonParser().parse(html)
        assert result.schema_org.get("@type") == "Product"

    def test_whitespace_only_title(self) -> None:
        """Whitespace-only title should be treated as None."""
        html = '<html><body><span id="productTitle">   </span></body></html>'
        result = AmazonParser().parse(html)
        assert result.title is None

    def test_invalid_rating_not_a_number(self) -> None:
        """Non-numeric rating should not crash."""
        html = _make_amazon_html(rating="not-a-number")
        result = AmazonParser().parse(html)
        assert result.rating is None

    def test_invalid_review_count(self) -> None:
        """Non-numeric review count should not crash."""
        html = _make_amazon_html(review_count="many reviews")
        result = AmazonParser().parse(html)
        assert result.review_count is None

    def test_completely_empty_html(self) -> None:
        """Completely empty string should not crash any parser."""
        for parser_cls in [
            AmazonParser, ShopeeParser, LazadaParser, TokopediaParser,
            TiktokShopParser, BlibliParser, ZaloraParser,
        ]:
            result = parser_cls().parse("")
            assert isinstance(result, ProductData)

    def test_html_with_only_doctype(self) -> None:
        """Minimal HTML should not crash parsers."""
        html = "<!DOCTYPE html><html><head></head><body></body></html>"
        for parser_cls in [
            AmazonParser, ShopeeParser, LazadaParser, TokopediaParser,
            TiktokShopParser, BlibliParser, ZaloraParser,
        ]:
            result = parser_cls().parse(html)
            assert isinstance(result, ProductData)

    def test_registry_roundtrip(self) -> None:
        """detect_marketplace -> get_parser -> parse should work end to end."""
        url = "https://www.amazon.com/dp/B01234"
        marketplace = detect_marketplace(url)
        parser = get_parser(marketplace)
        html = _make_amazon_html(title="End-to-End Test")
        result = parser.parse(html)
        assert result.title == "End-to-End Test"
        assert result.marketplace == MarketplaceType.AMAZON
