"""Check for x402 payment signaling support."""

from __future__ import annotations

import httpx

from context_cli.core.models import X402Report

PAYMENT_HEADERS: list[str] = [
    "x-payment",
    "x-payment-required",
    "x-402-receipt",
    "pay",
    "payment-address",
]

DEFAULT_TIMEOUT: int = 15


async def check_x402(url: str, client: httpx.AsyncClient) -> X402Report:
    """Check if a URL signals x402 payment support.

    Checks for HTTP 402 status code and payment-related headers.
    """
    try:
        resp = await client.head(url, follow_redirects=True)

        has_402 = resp.status_code == 402

        resp_headers_lower = {k.lower(): v for k, v in resp.headers.items()}
        has_payment = any(h in resp_headers_lower for h in PAYMENT_HEADERS)

        score = 0.0
        if has_402:
            score += 1
        if has_payment:
            score += 1

        found = has_402 or has_payment

        if not found:
            return X402Report(
                found=False,
                score=0,
                detail="No x402 payment signaling detected",
            )

        parts: list[str] = []
        if has_402:
            parts.append("HTTP 402 status")
        if has_payment:
            detected = [h for h in PAYMENT_HEADERS if h in resp_headers_lower]
            parts.append(f"headers: {', '.join(detected)}")

        return X402Report(
            found=True,
            has_402_status=has_402,
            has_payment_header=has_payment,
            score=score,
            detail=f"x402 detected: {'; '.join(parts)}",
        )

    except httpx.HTTPError as e:
        return X402Report(
            found=False,
            score=0,
            detail=f"Failed to check x402: {e}",
        )
