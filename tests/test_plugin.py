"""Tests for the plugin architecture — ABC, registry, MetaTagsPlugin, discovery."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from context_cli.core.models import PluginResult
from context_cli.core.plugin import (
    AuditPlugin,
    MetaTagsPlugin,
    clear_plugins,
    discover_plugins,
    get_plugins,
    register_plugin,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_registry() -> None:  # type: ignore[misc]
    """Ensure plugin registry is clean before and after each test."""
    clear_plugins()
    yield  # type: ignore[misc]
    clear_plugins()


# ── PluginResult model tests ────────────────────────────────────────────────


class TestPluginResult:
    def test_create_plugin_result(self) -> None:
        result = PluginResult(
            plugin_name="Test Plugin",
            score=5.0,
            max_score=10.0,
            detail="Found 1 of 2 items",
        )
        assert result.plugin_name == "Test Plugin"
        assert result.score == 5.0
        assert result.max_score == 10.0
        assert result.detail == "Found 1 of 2 items"
        assert result.metadata == {}

    def test_plugin_result_with_metadata(self) -> None:
        result = PluginResult(
            plugin_name="Test",
            score=10.0,
            max_score=10.0,
            detail="All good",
            metadata={"found_tags": ["og:title", "og:description"]},
        )
        assert result.metadata == {"found_tags": ["og:title", "og:description"]}

    def test_plugin_result_serialization(self) -> None:
        result = PluginResult(
            plugin_name="Meta",
            score=7.5,
            max_score=10.0,
            detail="Partial",
            metadata={"key": "value"},
        )
        data = result.model_dump()
        assert data["plugin_name"] == "Meta"
        assert data["score"] == 7.5
        assert data["metadata"] == {"key": "value"}

        # Round-trip
        restored = PluginResult(**data)
        assert restored == result


# ── ABC tests ───────────────────────────────────────────────────────────────


class TestAuditPluginABC:
    def test_cannot_instantiate_abc_directly(self) -> None:
        with pytest.raises(TypeError):
            AuditPlugin()  # type: ignore[abstract]

    def test_subclass_must_implement_all_methods(self) -> None:
        class IncompletePlugin(AuditPlugin):
            @property
            def name(self) -> str:
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompletePlugin()  # type: ignore[abstract]


# ── Registry tests ──────────────────────────────────────────────────────────


class TestPluginRegistry:
    def test_register_plugin_adds_to_registry(self) -> None:
        plugin = MetaTagsPlugin()
        register_plugin(plugin)
        assert len(get_plugins()) == 1
        assert get_plugins()[0] is plugin

    def test_get_plugins_returns_registered_plugins(self) -> None:
        p1 = MetaTagsPlugin()
        p2 = MetaTagsPlugin()
        register_plugin(p1)
        register_plugin(p2)
        plugins = get_plugins()
        assert len(plugins) == 2
        assert plugins[0] is p1
        assert plugins[1] is p2

    def test_clear_plugins_empties_registry(self) -> None:
        register_plugin(MetaTagsPlugin())
        assert len(get_plugins()) == 1
        clear_plugins()
        assert len(get_plugins()) == 0

    def test_get_plugins_returns_copy(self) -> None:
        register_plugin(MetaTagsPlugin())
        plugins = get_plugins()
        plugins.clear()
        # Original registry should be unaffected
        assert len(get_plugins()) == 1


# ── MetaTagsPlugin tests ───────────────────────────────────────────────────


class TestMetaTagsPlugin:
    def test_plugin_name(self) -> None:
        plugin = MetaTagsPlugin()
        assert plugin.name == "Meta Tags"

    def test_plugin_max_score(self) -> None:
        plugin = MetaTagsPlugin()
        assert plugin.max_score == 10.0

    @pytest.mark.asyncio
    async def test_full_score_with_both_og_tags(self) -> None:
        html = """
        <html><head>
            <meta property="og:title" content="Test Page">
            <meta property="og:description" content="A test page description">
        </head><body>Hello</body></html>
        """
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", html, {})
        assert result.score == 10.0
        assert result.max_score == 10.0
        assert "og:title" in result.detail
        assert "og:description" in result.detail

    @pytest.mark.asyncio
    async def test_zero_score_with_no_og_tags(self) -> None:
        html = "<html><head><title>No OG</title></head><body>Hello</body></html>"
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", html, {})
        assert result.score == 0.0
        assert result.plugin_name == "Meta Tags"

    @pytest.mark.asyncio
    async def test_half_score_with_only_og_title(self) -> None:
        html = """
        <html><head>
            <meta property="og:title" content="Only Title">
        </head><body>Hello</body></html>
        """
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", html, {})
        assert result.score == 5.0

    @pytest.mark.asyncio
    async def test_half_score_with_only_og_description(self) -> None:
        html = """
        <html><head>
            <meta property="og:description" content="Only Description">
        </head><body>Hello</body></html>
        """
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", html, {})
        assert result.score == 5.0

    @pytest.mark.asyncio
    async def test_metadata_includes_found_tags(self) -> None:
        html = """
        <html><head>
            <meta property="og:title" content="Title">
        </head><body>Hello</body></html>
        """
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", html, {})
        assert "og:title" in result.metadata["found_tags"]
        assert "og:description" not in result.metadata["found_tags"]

    @pytest.mark.asyncio
    async def test_empty_html(self) -> None:
        plugin = MetaTagsPlugin()
        result = await plugin.check("https://example.com", "", {})
        assert result.score == 0.0


# ── Discovery tests ─────────────────────────────────────────────────────────


class TestDiscoverPlugins:
    def test_discover_plugins_with_mock_entry_points(self) -> None:
        """Test discover_plugins loads from entry_points group."""

        class FakeEntryPoint:
            name = "fake-plugin"

            def load(self) -> type:
                return MetaTagsPlugin

        fake_eps: dict[str, list[Any]] = {"context_cli.plugins": [FakeEntryPoint()]}

        with patch("context_cli.core.plugin.entry_points", return_value=fake_eps):
            discover_plugins()

        plugins = get_plugins()
        assert len(plugins) == 1
        assert isinstance(plugins[0], MetaTagsPlugin)

    def test_discover_plugins_with_no_entry_points(self) -> None:
        """Test discover_plugins with no plugins installed."""
        with patch(
            "context_cli.core.plugin.entry_points",
            return_value={"context_cli.plugins": []},
        ):
            discover_plugins()

        assert len(get_plugins()) == 0

    def test_discover_plugins_missing_group(self) -> None:
        """Test discover_plugins when the entry_points group doesn't exist."""
        with patch("context_cli.core.plugin.entry_points", return_value={}):
            discover_plugins()

        assert len(get_plugins()) == 0

    def test_discover_plugins_handles_load_error(self) -> None:
        """Test discover_plugins gracefully handles entry point load errors."""

        class BadEntryPoint:
            name = "broken-plugin"

            def load(self) -> type:
                raise ImportError("Module not found")

        with patch(
            "context_cli.core.plugin.entry_points",
            return_value={"context_cli.plugins": [BadEntryPoint()]},
        ):
            # Should not raise, just skip the broken plugin
            discover_plugins()

        assert len(get_plugins()) == 0
