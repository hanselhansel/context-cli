"""Plugin result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PluginResult(BaseModel):
    """Result returned by an audit plugin check."""

    plugin_name: str = Field(description="Name of the plugin")
    score: float = Field(description="Score awarded by plugin")
    max_score: float = Field(description="Maximum possible score")
    detail: str = Field(description="Human-readable detail")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional plugin-specific data"
    )
