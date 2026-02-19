"""Shared LLM abstraction layer — model detection and structured output via litellm."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel


class LLMError(Exception):
    """Raised when LLM call fails."""


def ensure_litellm() -> None:
    """Check that litellm is installed, raise clear error if not."""
    try:
        import litellm  # noqa: F401
    except ImportError:
        raise ImportError(
            "litellm is required for the generate command. "
            "Install it with: pip install context-cli[generate]"
        )


def _check_ollama_running() -> bool:
    """Check if Ollama is running locally on port 11434."""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def detect_model() -> str:
    """Auto-detect best available model from environment.

    Order: OPENAI_API_KEY -> gpt-4o-mini, ANTHROPIC_API_KEY -> claude-3-haiku-20240307,
    Ollama running -> ollama/llama3.2, else raise LLMError.
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


def _build_response_format(model_class: type[BaseModel]) -> dict[str, Any]:
    """Build litellm response_format from a Pydantic model class."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model_class.__name__,
            "schema": model_class.model_json_schema(),
            "strict": False,
        },
    }


def _is_format_error(error: Exception) -> bool:
    """Check if an error is a structured output format error (for fallback)."""
    msg = str(error).lower()
    return any(
        phrase in msg
        for phrase in [
            "response_format",
            "json_schema",
            "structured output",
            "not supported",
            "does not support",
        ]
    )


async def _fallback_json_mode(
    messages: list[dict[str, str]], model: str, model_class: type[BaseModel]
) -> dict[str, Any]:
    """Fallback: use json_mode instead of structured output, parse manually."""
    import json

    import litellm

    json_messages = [
        *messages,
        {
            "role": "user",
            "content": (
                f"Respond with valid JSON matching this schema:\n"
                f"{json.dumps(model_class.model_json_schema(), indent=2)}"
            ),
        },
    ]
    response = await litellm.acompletion(
        model=model,
        messages=json_messages,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    return json.loads(raw)  # type: ignore[no-any-return]


async def call_llm_structured(
    messages: list[dict[str, str]],
    model: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    """Call LLM with structured output. Falls back to json_mode on format errors.

    Uses litellm.acompletion(). Returns parsed dict matching response_model schema.
    """
    import json

    import litellm

    ensure_litellm()

    try:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            response_format=_build_response_format(response_model),
        )
        raw = response.choices[0].message.content
        return json.loads(raw)  # type: ignore[no-any-return]
    except Exception as exc:
        if _is_format_error(exc):
            return await _fallback_json_mode(messages, model, response_model)
        raise LLMError(f"LLM call failed: {exc}") from exc
