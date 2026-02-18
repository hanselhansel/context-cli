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


def detect_model() -> str:
    """Auto-detect best available model from environment.

    Order: OPENAI_API_KEY → gpt-4o-mini, ANTHROPIC_API_KEY → claude-3-haiku-20240307,
    Ollama running → ollama/llama3.2, else raise LLMError.
    """
    import os

    if os.environ.get("OPENAI_API_KEY"):
        return "gpt-4o-mini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude-3-haiku-20240307"
    if _check_ollama_running():
        return "ollama/llama3.2"
    raise LLMError(
        "No LLM provider found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY, "
        "or start Ollama locally."
    )
