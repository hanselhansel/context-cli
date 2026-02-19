"""Prompt loader — reads prompts from CSV or text files."""

from __future__ import annotations

from aeo_cli.core.models import PromptEntry


def load_prompts(path: str) -> list[PromptEntry]:
    """Load prompts from a CSV or text file.

    Raises NotImplementedError until fully implemented by another agent.
    """
    raise NotImplementedError("Stub — loader not yet implemented")
