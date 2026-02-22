"""x402 payment signaling config generator -- HTTP headers, HTML meta, JSON config."""

from __future__ import annotations

import json


def generate_x402_config(
    *,
    resource_url: str,
    price: str = "0.01",
    currency: str = "USD",
    payment_address: str = "",
    network: str = "base",
) -> dict[str, str]:
    """Generate x402 payment signaling configuration.

    Returns:
        Dict with keys: "headers" (HTTP header config), "html_meta" (meta tag),
        "json_config" (JSON config file content for /.well-known/x402.json).
    """
    headers = _build_headers(
        resource_url=resource_url,
        price=price,
        currency=currency,
        payment_address=payment_address,
        network=network,
    )
    html_meta = _build_html_meta(
        resource_url=resource_url,
        price=price,
        currency=currency,
        payment_address=payment_address,
    )
    json_config = _build_json_config(
        resource_url=resource_url,
        price=price,
        currency=currency,
        payment_address=payment_address,
        network=network,
    )
    return {
        "headers": headers,
        "html_meta": html_meta,
        "json_config": json_config,
    }


def _build_headers(
    *,
    resource_url: str,
    price: str,
    currency: str,
    payment_address: str,
    network: str,
) -> str:
    """Build HTTP header lines for x402 payment signaling."""
    lines = [
        "# x402 Payment Signaling HTTP Headers",
        "# Return these headers with HTTP 402 responses",
        "X-Payment: required",
        f"X-Payment-Amount: {price}",
        f"X-Payment-Currency: {currency}",
        f"X-Payment-Resource: {resource_url}",
        f"X-Payment-Network: {network}",
    ]
    if payment_address:
        lines.append(f"X-Payment-Address: {payment_address}")
    lines.append("X-Payment-Version: 1")
    return "\n".join(lines) + "\n"


def _build_html_meta(
    *,
    resource_url: str,
    price: str,
    currency: str,
    payment_address: str,
) -> str:
    """Build HTML meta tags for x402 payment discovery."""
    lines = [
        "<!-- x402 Payment Signaling Meta Tags -->",
        f'<meta name="x402:resource" content="{resource_url}">',
        f'<meta name="x402:amount" content="{price}">',
        f'<meta name="x402:currency" content="{currency}">',
    ]
    if payment_address:
        lines.append(
            f'<meta name="x402:address" content="{payment_address}">'
        )
    return "\n".join(lines) + "\n"


def _build_json_config(
    *,
    resource_url: str,
    price: str,
    currency: str,
    payment_address: str,
    network: str,
) -> str:
    """Build JSON config for /.well-known/x402.json."""
    config = {
        "version": 1,
        "resource": resource_url,
        "payment": {
            "amount": price,
            "currency": currency,
            "network": network,
        },
    }
    if payment_address:
        config["payment"]["address"] = payment_address  # type: ignore[index]
    return json.dumps(config, indent=2) + "\n"
