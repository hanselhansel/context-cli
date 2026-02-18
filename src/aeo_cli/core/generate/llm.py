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


def _check_ollama_running() -> bool:
    """Check if Ollama is running locally on port 11434."""
    import httpx

    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
