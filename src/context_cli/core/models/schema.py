"""Schema.org JSON-LD analysis models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SchemaOrgResult(BaseModel):
    """A single JSON-LD structured data block found in the page."""

    schema_type: str = Field(description="The @type value (e.g., Organization, Article)")
    properties: list[str] = Field(
        default_factory=list, description="Top-level property names found"
    )


class SchemaReport(BaseModel):
    """Aggregated Schema.org JSON-LD analysis. Max 25 points."""

    blocks_found: int = Field(default=0, description="Number of JSON-LD blocks found")
    schemas: list[SchemaOrgResult] = Field(
        default_factory=list, description="Parsed JSON-LD blocks"
    )
    score: float = Field(default=0, description="Schema pillar score (0-25)")
    detail: str = Field(default="", description="Summary of schema findings")
