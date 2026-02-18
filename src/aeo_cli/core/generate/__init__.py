"""AEO asset generation — LLM-powered llms.txt and schema.jsonld compiler."""

from .compiler import generate_assets, render_llms_txt, render_schema_jsonld
from .llm import LLMError, detect_model
from .profiles import get_profile, list_profiles

__all__ = [
    "generate_assets",
    "detect_model",
    "get_profile",
    "list_profiles",
    "render_llms_txt",
    "render_schema_jsonld",
    "LLMError",
]
