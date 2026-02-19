"""LLM-as-judge — structured JSON classification of benchmark responses."""

from __future__ import annotations

import asyncio
import json

from context_cli.core.models import JudgeResult, PromptBenchmarkResult

_SYSTEM_PROMPT_TEMPLATE = (
    "You are an expert brand analyst. Analyze the following AI-generated response "
    "and produce a JSON object with these fields:\n"
    "- brands_mentioned: list of brand names found in the response\n"
    "- recommended_brand: the brand that is most recommended (null if none)\n"
    "- target_brand_position: position of '{brand}' in any ranking (1-based, null if unranked)\n"
    "- sentiment: sentiment toward '{brand}' — one of: positive, neutral, negative\n\n"
    "Target brand: {brand}\n"
    "Competitors: {competitors}\n\n"
    "Respond ONLY with valid JSON. No additional text."
)


async def judge_response(
    response_text: str,
    brand: str,
    competitors: list[str],
    model: str = "gpt-4o-mini",
) -> JudgeResult:
    """Use an LLM to classify a benchmark response as structured JSON.

    Sends the response to the judge model and parses the JSON output into a JudgeResult.
    On any exception (API error, invalid JSON), returns a JudgeResult with empty defaults.
    """
    import litellm

    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        brand=brand,
        competitors=", ".join(competitors) if competitors else "none",
    )

    try:
        completion = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": response_text},
            ],
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content
        data = json.loads(raw)
        return JudgeResult(
            brands_mentioned=data.get("brands_mentioned", []),
            recommended_brand=data.get("recommended_brand"),
            target_brand_position=data.get("target_brand_position"),
            sentiment=data.get("sentiment", "neutral"),
        )
    except Exception:
        return JudgeResult()


async def judge_all(
    results: list[PromptBenchmarkResult],
    brand: str,
    competitors: list[str],
    judge_model: str = "gpt-4o-mini",
) -> list[PromptBenchmarkResult]:
    """Run judge_response on all results, skipping those with errors.

    Uses asyncio.gather with a Semaphore(5) for rate limiting.
    Sets judge_result field on each successful result.
    """
    if not results:
        return results

    sem = asyncio.Semaphore(5)

    async def _judge_one(result: PromptBenchmarkResult) -> None:
        if result.error:
            return
        async with sem:
            result.judge_result = await judge_response(
                response_text=result.response_text,
                brand=brand,
                competitors=competitors,
                model=judge_model,
            )

    await asyncio.gather(*[_judge_one(r) for r in results])
    return results
