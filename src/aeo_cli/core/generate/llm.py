"""LLM abstraction layer — model detection and structured output via litellm."""

from __future__ import annotations


class LLMError(Exception):
    """Raised when LLM call fails."""


def ensure_litellm() -> None:
    """Check that litellm is installed, raise clear error if not."""
    try:
        import litellm  # noqa: F401
    except ImportError:
        raise ImportError(
            "litellm is required for the generate command. "
            "Install it with: pip install aeo-cli[generate]"
        )
