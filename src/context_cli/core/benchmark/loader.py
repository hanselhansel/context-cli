"""Benchmark prompt loader — CSV and plain text file parsing with validation."""

from __future__ import annotations

import csv
import io

from context_cli.core.models import PromptEntry


def _is_csv_header(first_line: str) -> bool:
    """Check if the first line looks like a CSV header containing 'prompt'."""
    fields = [f.strip().lower() for f in first_line.split(",")]
    return "prompt" in fields


def _parse_csv(content: str) -> list[PromptEntry]:
    """Parse CSV content with prompt,category,intent columns."""
    reader = csv.DictReader(io.StringIO(content))
    prompts: list[PromptEntry] = []
    for row in reader:
        prompt_text = row.get("prompt", "").strip()
        if not prompt_text:
            continue
        category = row.get("category", "").strip() or None
        intent = row.get("intent", "").strip() or None
        prompts.append(
            PromptEntry(prompt=prompt_text, category=category, intent=intent)
        )
    return prompts


def _parse_text(content: str) -> list[PromptEntry]:
    """Parse plain text content with one prompt per line."""
    prompts: list[PromptEntry] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            prompts.append(PromptEntry(prompt=stripped))
    return prompts


def load_prompts(path: str) -> list[PromptEntry]:
    """Load benchmark prompts from a CSV or plain text file.

    CSV format: must have a 'prompt' column header. Optional 'category' and 'intent' columns.
    Text format: one prompt per line (any file without a 'prompt' header).

    Raises FileNotFoundError if the file does not exist.
    """
    with open(path) as f:
        content = f.read()

    if not content.strip():
        return []

    first_line = content.split("\n", 1)[0]
    if _is_csv_header(first_line):
        return _parse_csv(content)
    return _parse_text(content)


def validate_prompts(prompts: list[PromptEntry]) -> list[PromptEntry]:
    """Validate and clean a list of PromptEntry objects.

    - Strips whitespace from prompt, category, and intent fields
    - Filters out entries with empty prompt text after stripping
    - Converts empty-after-strip category/intent to None
    """
    validated: list[PromptEntry] = []
    for entry in prompts:
        prompt_text = entry.prompt.strip()
        if not prompt_text:
            continue
        category = entry.category.strip() if entry.category else None
        if category == "":
            category = None
        intent = entry.intent.strip() if entry.intent else None
        if intent == "":
            intent = None
        validated.append(
            PromptEntry(prompt=prompt_text, category=category, intent=intent)
        )
    return validated
