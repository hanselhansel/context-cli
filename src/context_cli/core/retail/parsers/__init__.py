"""Parser registry: URL detection and parser factory."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from context_cli.core.models import MarketplaceType
from context_cli.core.retail.parsers.amazon import AmazonParser
from context_cli.core.retail.parsers.base import BaseParser
from context_cli.core.retail.parsers.blibli import BlibliParser
from context_cli.core.retail.parsers.lazada import LazadaParser
from context_cli.core.retail.parsers.shopee import ShopeeParser
from context_cli.core.retail.parsers.tiktok_shop import TiktokShopParser
from context_cli.core.retail.parsers.tokopedia import TokopediaParser
from context_cli.core.retail.parsers.zalora import ZaloraParser

# URL pattern -> MarketplaceType mapping
_MARKETPLACE_PATTERNS: list[tuple[re.Pattern[str], MarketplaceType]] = [
    (re.compile(r"amazon\.(com|co\.uk|de|co\.jp|fr|it|es|ca|com\.au|in|com\.br|sg|nl|sa|ae|pl|se|com\.mx|com\.tr|cn)"), MarketplaceType.AMAZON),  # noqa: E501
    (re.compile(r"shopee\.(sg|co\.id|com\.my|co\.th|vn|ph|com\.br|tw|com\.co|cl|com\.mx)"), MarketplaceType.SHOPEE),  # noqa: E501
    (re.compile(r"lazada\.(sg|co\.id|com\.my|co\.th|vn|com\.ph)"), MarketplaceType.LAZADA),
    (re.compile(r"tokopedia\.com"), MarketplaceType.TOKOPEDIA),
    (re.compile(r"tiktok\.com"), MarketplaceType.TIKTOK_SHOP),
    (re.compile(r"blibli\.com"), MarketplaceType.BLIBLI),
    (re.compile(r"zalora\.(sg|co\.id|com\.my|co\.th|vn|com\.ph|com\.hk|com\.tw|com)"), MarketplaceType.ZALORA),  # noqa: E501
]

# MarketplaceType -> parser class mapping
_PARSER_MAP: dict[MarketplaceType, type[BaseParser]] = {
    MarketplaceType.AMAZON: AmazonParser,
    MarketplaceType.SHOPEE: ShopeeParser,
    MarketplaceType.LAZADA: LazadaParser,
    MarketplaceType.TOKOPEDIA: TokopediaParser,
    MarketplaceType.TIKTOK_SHOP: TiktokShopParser,
    MarketplaceType.BLIBLI: BlibliParser,
    MarketplaceType.ZALORA: ZaloraParser,
}


def detect_marketplace(url: str) -> MarketplaceType:
    """Detect the marketplace from a product URL.

    Matches the URL's hostname against known marketplace domain patterns.
    Returns ``MarketplaceType.GENERIC`` for unrecognised URLs.
    """
    if not url:
        return MarketplaceType.GENERIC

    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
    except Exception:  # pragma: no cover
        return MarketplaceType.GENERIC

    for pattern, marketplace in _MARKETPLACE_PATTERNS:
        if pattern.search(hostname):
            return marketplace

    return MarketplaceType.GENERIC


def get_parser(marketplace: MarketplaceType) -> BaseParser:
    """Return the appropriate parser for a marketplace type.

    Falls back to ``BaseParser`` for unregistered marketplace types.
    """
    parser_cls = _PARSER_MAP.get(marketplace, BaseParser)
    return parser_cls()


__all__ = [
    "detect_marketplace",
    "get_parser",
    "BaseParser",
    "AmazonParser",
    "ShopeeParser",
    "LazadaParser",
    "TokopediaParser",
    "TiktokShopParser",
    "BlibliParser",
    "ZaloraParser",
]
