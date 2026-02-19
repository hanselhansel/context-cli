"""Configuration file support — loads .aeorc.yml from CWD or home directory."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_CONFIG_FILENAME = ".aeorc.yml"


class AeoConfig(BaseModel):
    """AEO-CLI configuration loaded from .aeorc.yml."""

    timeout: int = Field(default=15, description="HTTP timeout in seconds")
    max_pages: int = Field(default=10, description="Max pages for multi-page audit")
    single: bool = Field(default=False, description="Default to single-page mode")
    verbose: bool = Field(default=False, description="Show verbose output by default")
    save: bool = Field(default=False, description="Auto-save audit results to history")
    regression_threshold: float = Field(
        default=5.0, description="Score drop threshold for regression detection"
    )
    bots: list[str] | None = Field(
        default=None, description="Custom AI bot list (overrides defaults)"
    )
    format: str | None = Field(default=None, description="Default output format")

    model_config = {"extra": "ignore"}


def load_config(
    search_dirs: list[Path] | None = None,
) -> AeoConfig:
    """Load config from .aeorc.yml, searching CWD then home directory.

    Args:
        search_dirs: Directories to search for .aeorc.yml.
            Defaults to [CWD, HOME]. First match wins.

    Returns:
        AeoConfig with values from the file, or defaults if no file found.
    """
    if search_dirs is None:
        search_dirs = [Path.cwd(), Path.home()]

    for directory in search_dirs:
        config_path = directory / _CONFIG_FILENAME
        if config_path.is_file():
            try:
                raw = yaml.safe_load(config_path.read_text())
            except Exception:
                return AeoConfig()
            if not isinstance(raw, dict):
                return AeoConfig()
            return AeoConfig(**raw)

    return AeoConfig()
