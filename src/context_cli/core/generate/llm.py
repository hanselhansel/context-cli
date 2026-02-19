"""LLM abstraction layer — re-exports from core/llm.py for backward compatibility."""

from context_cli.core.llm import (
    LLMError,
    _build_response_format,
    _check_ollama_running,
    _fallback_json_mode,
    _is_format_error,
    call_llm_structured,
    detect_model,
    ensure_litellm,
)

__all__ = [
    "LLMError",
    "call_llm_structured",
    "detect_model",
    "ensure_litellm",
    "_build_response_format",
    "_check_ollama_running",
    "_fallback_json_mode",
    "_is_format_error",
]
