"""Benchmark query dispatcher — async multi-model query execution with concurrency control."""

from __future__ import annotations

import asyncio

from aeo_cli.core.models import BenchmarkConfig, PromptBenchmarkResult, PromptEntry

_SYSTEM_PROMPT = (
    "You are a helpful assistant. When recommending products or services, "
    "be specific about brands and explain your reasoning."
)

_MAX_CONCURRENCY = 5


async def _query_single(
    prompt: PromptEntry,
    model: str,
    run_index: int,
    semaphore: asyncio.Semaphore,
) -> PromptBenchmarkResult:
    """Send a single prompt to a model and return the result.

    Uses litellm.acompletion (lazy import). On error, captures exception
    in the error field and sets response_text to empty string.
    """
    import litellm

    async with semaphore:
        try:
            response = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt.prompt},
                ],
            )
            text: str = response.choices[0].message.content
            return PromptBenchmarkResult(
                prompt=prompt,
                model=model,
                run_index=run_index,
                response_text=text,
            )
        except Exception as exc:
            return PromptBenchmarkResult(
                prompt=prompt,
                model=model,
                run_index=run_index,
                response_text="",
                error=str(exc),
            )


async def dispatch_queries(config: BenchmarkConfig) -> list[PromptBenchmarkResult]:
    """Dispatch all benchmark queries across prompts, models, and runs.

    Creates tasks for every combination of (prompt x model x run_index)
    and executes them concurrently with a semaphore limiting to 5 parallel requests.

    Returns a flat list of PromptBenchmarkResult with response_text populated
    and judge_result=None (to be filled by the judge agent later).
    """
    if not config.prompts:
        return []

    semaphore = asyncio.Semaphore(_MAX_CONCURRENCY)
    tasks = [
        _query_single(prompt, model, run_idx, semaphore)
        for prompt in config.prompts
        for model in config.models
        for run_idx in range(config.runs_per_model)
    ]
    results: list[PromptBenchmarkResult] = list(await asyncio.gather(*tasks))
    return results
