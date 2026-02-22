"""Tests for x402 payment signaling config generator module."""

from __future__ import annotations

import json

from context_cli.core.generate.x402_config import (
    _build_headers,
    _build_html_meta,
    _build_json_config,
    generate_x402_config,
)


class TestGenerateX402Config:
    """Tests for the top-level generate_x402_config function."""

    def test_returns_dict_with_three_keys(self) -> None:
        result = generate_x402_config(resource_url="https://example.com/api")
        assert set(result.keys()) == {"headers", "html_meta", "json_config"}

    def test_default_values(self) -> None:
        result = generate_x402_config(resource_url="https://example.com/api")
        assert "0.01" in result["headers"]
        assert "USD" in result["headers"]
        assert "base" in result["headers"]

    def test_custom_values(self) -> None:
        result = generate_x402_config(
            resource_url="https://pay.example.com/v1",
            price="0.50",
            currency="EUR",
            payment_address="0xDEADBEEF",
            network="ethereum",
        )
        assert "0.50" in result["headers"]
        assert "EUR" in result["headers"]
        assert "0xDEADBEEF" in result["headers"]
        assert "ethereum" in result["headers"]

    def test_all_outputs_are_strings(self) -> None:
        result = generate_x402_config(resource_url="https://example.com")
        for key, value in result.items():
            assert isinstance(value, str), f"{key} should be str"


class TestBuildHeaders:
    """Tests for _build_headers."""

    def test_contains_x_payment_required(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        assert "X-Payment: required" in h

    def test_contains_amount(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com",
            price="1.00",
            currency="USD",
            payment_address="",
            network="base",
        )
        assert "X-Payment-Amount: 1.00" in h

    def test_contains_resource_url(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com/api",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        assert "X-Payment-Resource: https://ex.com/api" in h

    def test_includes_address_when_provided(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="0xABC",
            network="base",
        )
        assert "X-Payment-Address: 0xABC" in h

    def test_omits_address_when_empty(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        assert "X-Payment-Address" not in h

    def test_contains_version(self) -> None:
        h = _build_headers(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        assert "X-Payment-Version: 1" in h


class TestBuildHtmlMeta:
    """Tests for _build_html_meta."""

    def test_contains_resource_meta(self) -> None:
        m = _build_html_meta(
            resource_url="https://ex.com/api",
            price="0.01",
            currency="USD",
            payment_address="",
        )
        assert 'x402:resource' in m
        assert "https://ex.com/api" in m

    def test_contains_amount_meta(self) -> None:
        m = _build_html_meta(
            resource_url="https://ex.com",
            price="2.50",
            currency="USD",
            payment_address="",
        )
        assert 'x402:amount' in m
        assert "2.50" in m

    def test_includes_address_when_provided(self) -> None:
        m = _build_html_meta(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="0xABC",
        )
        assert 'x402:address' in m
        assert "0xABC" in m

    def test_omits_address_when_empty(self) -> None:
        m = _build_html_meta(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
        )
        assert "x402:address" not in m


class TestBuildJsonConfig:
    """Tests for _build_json_config."""

    def test_valid_json(self) -> None:
        j = _build_json_config(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        data = json.loads(j)
        assert data["version"] == 1

    def test_contains_resource(self) -> None:
        j = _build_json_config(
            resource_url="https://ex.com/api",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        data = json.loads(j)
        assert data["resource"] == "https://ex.com/api"

    def test_payment_fields(self) -> None:
        j = _build_json_config(
            resource_url="https://ex.com",
            price="5.00",
            currency="EUR",
            payment_address="",
            network="ethereum",
        )
        data = json.loads(j)
        assert data["payment"]["amount"] == "5.00"
        assert data["payment"]["currency"] == "EUR"
        assert data["payment"]["network"] == "ethereum"

    def test_includes_address_when_provided(self) -> None:
        j = _build_json_config(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="0xDEAD",
            network="base",
        )
        data = json.loads(j)
        assert data["payment"]["address"] == "0xDEAD"

    def test_omits_address_when_empty(self) -> None:
        j = _build_json_config(
            resource_url="https://ex.com",
            price="0.01",
            currency="USD",
            payment_address="",
            network="base",
        )
        data = json.loads(j)
        assert "address" not in data["payment"]
