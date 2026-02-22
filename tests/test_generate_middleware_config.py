"""Tests for middleware config generator module."""

from __future__ import annotations

import pytest

from context_cli.core.generate.middleware_config import (
    generate_apache_config,
    generate_caddy_config,
    generate_middleware_config,
    generate_nginx_config,
)


class TestNginxConfig:
    """Tests for generate_nginx_config."""

    def test_contains_accept_check(self) -> None:
        result = generate_nginx_config("http://backend:3000")
        assert "text/markdown" in result

    def test_contains_proxy_pass_upstream(self) -> None:
        result = generate_nginx_config("http://backend:3000")
        assert "proxy_pass http://backend:3000" in result

    def test_uses_custom_port(self) -> None:
        result = generate_nginx_config("http://backend:3000", port=9090)
        assert "127.0.0.1:9090" in result

    def test_default_port_8080(self) -> None:
        result = generate_nginx_config("http://backend:3000")
        assert "127.0.0.1:8080" in result

    def test_contains_nginx_comment(self) -> None:
        result = generate_nginx_config("http://backend:3000")
        assert "Nginx" in result


class TestApacheConfig:
    """Tests for generate_apache_config."""

    def test_contains_rewrite_condition(self) -> None:
        result = generate_apache_config("http://backend:3000")
        assert "RewriteCond" in result
        assert "text/markdown" in result

    def test_contains_proxy_pass(self) -> None:
        result = generate_apache_config("http://backend:3000")
        assert "ProxyPass" in result
        assert "http://backend:3000" in result

    def test_uses_custom_port(self) -> None:
        result = generate_apache_config("http://backend:3000", port=7070)
        assert "127.0.0.1:7070" in result

    def test_contains_apache_comment(self) -> None:
        result = generate_apache_config("http://backend:3000")
        assert "Apache" in result


class TestCaddyConfig:
    """Tests for generate_caddy_config."""

    def test_contains_header_matcher(self) -> None:
        result = generate_caddy_config("http://backend:3000")
        assert "@markdown" in result
        assert "text/markdown" in result

    def test_contains_reverse_proxy(self) -> None:
        result = generate_caddy_config("http://backend:3000")
        assert "reverse_proxy" in result
        assert "http://backend:3000" in result

    def test_uses_custom_port(self) -> None:
        result = generate_caddy_config("http://backend:3000", port=6060)
        assert "127.0.0.1:6060" in result

    def test_contains_caddy_comment(self) -> None:
        result = generate_caddy_config("http://backend:3000")
        assert "Caddy" in result


class TestGenerateMiddlewareConfig:
    """Tests for the unified generate_middleware_config dispatcher."""

    def test_nginx_dispatch(self) -> None:
        result = generate_middleware_config(
            "nginx", "http://backend:3000"
        )
        assert "Nginx" in result
        assert "proxy_pass" in result

    def test_apache_dispatch(self) -> None:
        result = generate_middleware_config(
            "apache", "http://backend:3000"
        )
        assert "Apache" in result
        assert "RewriteCond" in result

    def test_caddy_dispatch(self) -> None:
        result = generate_middleware_config(
            "caddy", "http://backend:3000"
        )
        assert "Caddy" in result
        assert "reverse_proxy" in result

    def test_case_insensitive(self) -> None:
        result = generate_middleware_config(
            "NGINX", "http://backend:3000"
        )
        assert "Nginx" in result

    def test_unknown_server_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported server type"):
            generate_middleware_config("iis", "http://backend:3000")

    def test_unknown_server_type_lists_supported(self) -> None:
        with pytest.raises(ValueError, match="apache, caddy, nginx"):
            generate_middleware_config("lighttpd", "http://backend:3000")

    def test_custom_port_forwarded(self) -> None:
        result = generate_middleware_config(
            "nginx", "http://backend:3000", port=5555
        )
        assert "127.0.0.1:5555" in result
