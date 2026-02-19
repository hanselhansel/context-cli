"""Query dispatcher — send prompts to LLMs and collect responses."""

from __future__ import annotations

import asyncio

from aeo_cli.core.models import ModelRadarResult, RadarConfig
from aeo_cli.core.radar.parser import parse_citations

_SYSTEM_PROMPT = (
    "You are a helpful assistant. When answering, cite your sources with URLs when possible."
)


async def query_model(prompt: str, model: str) -> ModelRadarResult:
    """Send a prompt to a single model and return the raw result.

    Uses litellm.acompletion for model-agnostic querying.
    Catches exceptions and returns error in ModelRadarResult.
    """
    import litellm

    try:
        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        text: str = response.choices[0].message.content
        citations = parse_citations(text, model=model)
        return ModelRadarResult(
            model=model,
            response_text=text,
            citations=citations,
        )
    except Exception as exc:
        return ModelRadarResult(
            model=model,
            response_text="",
            error=str(exc),
        )


def _detect_brands(text: str, brands: list[str]) -> list[str]:
    """Find which brands are mentioned in the response text (case-insensitive)."""
    lower = text.lower()
    return [b for b in brands if b.lower() in lower]


async def query_models(config: RadarConfig) -> list[ModelRadarResult]:
    """Query all configured models, with runs_per_model repetitions.

    Uses asyncio.gather for concurrent querying.
    Returns flat list of ModelRadarResult (one per model per run).
    """
    tasks = [
        query_model(config.prompt, model)
        for model in config.models
        for _ in range(config.runs_per_model)
    ]
    results: list[ModelRadarResult] = list(await asyncio.gather(*tasks))

    # Post-process: detect brand mentions
    if config.brands:
        for result in results:
            if result.response_text:
                result.brands_mentioned = _detect_brands(
                    result.response_text, config.brands
                )

    return results
