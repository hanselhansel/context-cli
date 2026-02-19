"""OpenAI Product Feed Spec field compliance checker.

Checks which required and recommended fields from the OpenAI Product Feed
specification are present in parsed product data.
"""

from __future__ import annotations

from context_cli.core.models import FeedComplianceReport, ProductData

REQUIRED_FIELDS: list[str] = [
    "title",
    "description",
    "url",
    "price",
    "currency",
    "availability",
    "image_url",
    "brand",
]

RECOMMENDED_FIELDS: list[str] = [
    "reviews_count",
    "average_rating",
    "variants",
    "shipping_info",
    "category",
    "gtin",
]


def _field_mapping(data: ProductData) -> dict[str, bool]:
    """Map feed spec field names to whether they are present in product data.

    The feed spec field names don't always match ProductData attribute names,
    so this function provides the mapping.
    """
    return {
        # Required fields
        "title": data.title is not None and len(data.title) > 0,
        "description": data.description is not None and len(data.description) > 0,
        "url": len(data.url) > 0,
        "price": data.price is not None and len(data.price) > 0,
        "currency": data.currency is not None and len(data.currency) > 0,
        "availability": data.availability is not None and len(data.availability) > 0,
        "image_url": len(data.image_urls) > 0,
        "brand": data.brand is not None and len(data.brand) > 0,
        # Recommended fields
        "reviews_count": data.review_count is not None and data.review_count > 0,
        "average_rating": data.rating is not None and data.rating > 0,
        "variants": False,  # Not tracked in ProductData currently
        "shipping_info": False,  # Not tracked in ProductData currently
        "category": False,  # Not tracked in ProductData currently
        "gtin": False,  # Not tracked in ProductData currently
    }


def check_feed_compliance(data: ProductData) -> FeedComplianceReport:
    """Check product data against OpenAI Product Feed Spec fields.

    Evaluates which required fields are present and computes a compliance
    rate and score (0-10 points) based on the fraction of required fields
    that are populated.

    Args:
        data: Parsed product data to evaluate.

    Returns:
        FeedComplianceReport with present/missing fields, rate, and score.
    """
    mapping = _field_mapping(data)

    present: list[str] = []
    missing: list[str] = []

    for field in REQUIRED_FIELDS:
        if mapping.get(field, False):
            present.append(field)
        else:
            missing.append(field)

    # Also track present recommended fields (for reporting)
    for field in RECOMMENDED_FIELDS:
        if mapping.get(field, False):
            present.append(field)

    # Compliance rate is fraction of required fields present
    required_present = [f for f in present if f in REQUIRED_FIELDS]
    total_required = len(REQUIRED_FIELDS)
    compliance_rate = len(required_present) / total_required if total_required > 0 else 0.0

    # Score is proportional to compliance rate, max 10 points
    score = min(compliance_rate * 10.0, 10.0)

    return FeedComplianceReport(
        score=score,
        present_fields=present,
        missing_fields=missing,
        compliance_rate=compliance_rate,
    )
