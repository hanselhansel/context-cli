"""Context CLI: LLM Readiness Linter."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("context-cli")
except PackageNotFoundError:
    __version__ = "0.0.0"
