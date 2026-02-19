"""AEO-CLI: Agentic Engine Optimization CLI tool."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("aeo-cli")
except PackageNotFoundError:
    __version__ = "0.0.0"
