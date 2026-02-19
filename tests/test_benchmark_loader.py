"""Tests for benchmark loader — CSV/text prompt parsing and validation."""

from __future__ import annotations

import os

import pytest

from context_cli.core.benchmark.loader import load_prompts, validate_prompts
from context_cli.core.models import PromptEntry


class TestLoadPromptsCSV:
    """Tests for loading prompts from CSV files."""

    def test_csv_with_all_columns(self, tmp_path: object) -> None:
        """CSV with prompt,category,intent columns parses correctly."""
        csv_content = (
            "prompt,category,intent\n"
            "What is the best laptop?,comparison,transactional\n"
            "Review of MacBook Pro,review,informational\n"
        )
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert len(prompts) == 2
        assert prompts[0].prompt == "What is the best laptop?"
        assert prompts[0].category == "comparison"
        assert prompts[0].intent == "transactional"
        assert prompts[1].prompt == "Review of MacBook Pro"
        assert prompts[1].category == "review"
        assert prompts[1].intent == "informational"

    def test_csv_prompt_column_only(self, tmp_path: object) -> None:
        """CSV with only prompt column works (category/intent default to None)."""
        csv_content = "prompt\nBest running shoes\nTop headphones 2024\n"
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert len(prompts) == 2
        assert prompts[0].prompt == "Best running shoes"
        assert prompts[0].category is None
        assert prompts[0].intent is None

    def test_csv_with_partial_columns(self, tmp_path: object) -> None:
        """CSV with prompt and category but no intent works."""
        csv_content = "prompt,category\nBest laptop?,comparison\nTop phone?,review\n"
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert len(prompts) == 2
        assert prompts[0].category == "comparison"
        assert prompts[0].intent is None

    def test_csv_empty_values(self, tmp_path: object) -> None:
        """CSV with empty category/intent fields treated as None."""
        csv_content = "prompt,category,intent\nBest laptop?,,\nTop phone?,review,\n"
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert prompts[0].category is None
        assert prompts[0].intent is None
        assert prompts[1].category == "review"
        assert prompts[1].intent is None

    def test_csv_strips_whitespace(self, tmp_path: object) -> None:
        """CSV values are stripped of surrounding whitespace."""
        csv_content = "prompt,category,intent\n  Best laptop?  , comparison , transactional \n"
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert prompts[0].prompt == "Best laptop?"
        assert prompts[0].category == "comparison"
        assert prompts[0].intent == "transactional"

    def test_csv_skips_empty_rows(self, tmp_path: object) -> None:
        """CSV rows with empty prompt are skipped."""
        csv_content = "prompt,category,intent\nBest laptop?,comparison,transactional\n,,\n\n"
        path = os.path.join(str(tmp_path), "prompts.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert len(prompts) == 1
        assert prompts[0].prompt == "Best laptop?"


class TestLoadPromptsText:
    """Tests for loading prompts from plain text files."""

    def test_plain_text_one_per_line(self, tmp_path: object) -> None:
        """Plain text file loads one prompt per line."""
        text_content = "What is the best laptop?\nReview of MacBook Pro\nTop headphones 2024\n"
        path = os.path.join(str(tmp_path), "prompts.txt")
        with open(path, "w") as f:
            f.write(text_content)

        prompts = load_prompts(path)

        assert len(prompts) == 3
        assert prompts[0].prompt == "What is the best laptop?"
        assert prompts[0].category is None
        assert prompts[0].intent is None

    def test_plain_text_strips_whitespace(self, tmp_path: object) -> None:
        """Plain text lines are stripped of whitespace."""
        text_content = "  Best laptop?  \n  Top phone?  \n"
        path = os.path.join(str(tmp_path), "prompts.txt")
        with open(path, "w") as f:
            f.write(text_content)

        prompts = load_prompts(path)

        assert prompts[0].prompt == "Best laptop?"
        assert prompts[1].prompt == "Top phone?"

    def test_plain_text_skips_empty_lines(self, tmp_path: object) -> None:
        """Empty lines in plain text are skipped."""
        text_content = "Best laptop?\n\n\nTop phone?\n"
        path = os.path.join(str(tmp_path), "prompts.txt")
        with open(path, "w") as f:
            f.write(text_content)

        prompts = load_prompts(path)

        assert len(prompts) == 2

    def test_plain_text_skips_whitespace_only_lines(self, tmp_path: object) -> None:
        """Lines with only whitespace are treated as empty."""
        text_content = "Best laptop?\n   \n  \nTop phone?\n"
        path = os.path.join(str(tmp_path), "prompts.txt")
        with open(path, "w") as f:
            f.write(text_content)

        prompts = load_prompts(path)

        assert len(prompts) == 2


class TestLoadPromptsEdgeCases:
    """Edge cases for load_prompts."""

    def test_file_not_found_raises(self) -> None:
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_prompts("/nonexistent/path/prompts.csv")

    def test_empty_file_returns_empty_list(self, tmp_path: object) -> None:
        """Empty file returns empty list."""
        path = os.path.join(str(tmp_path), "empty.csv")
        with open(path, "w") as f:
            f.write("")

        prompts = load_prompts(path)

        assert prompts == []

    def test_csv_header_only_returns_empty(self, tmp_path: object) -> None:
        """CSV with only header row returns empty list."""
        path = os.path.join(str(tmp_path), "header_only.csv")
        with open(path, "w") as f:
            f.write("prompt,category,intent\n")

        prompts = load_prompts(path)

        assert prompts == []

    def test_detects_csv_by_header(self, tmp_path: object) -> None:
        """File with 'prompt' in first line is treated as CSV even without .csv extension."""
        path = os.path.join(str(tmp_path), "prompts.dat")
        with open(path, "w") as f:
            f.write("prompt,category\nBest laptop?,comparison\n")

        prompts = load_prompts(path)

        assert len(prompts) == 1
        assert prompts[0].category == "comparison"

    def test_single_prompt_file(self, tmp_path: object) -> None:
        """File with a single prompt works."""
        path = os.path.join(str(tmp_path), "single.txt")
        with open(path, "w") as f:
            f.write("What is the best laptop?\n")

        prompts = load_prompts(path)

        assert len(prompts) == 1
        assert prompts[0].prompt == "What is the best laptop?"

    def test_csv_with_quoted_fields(self, tmp_path: object) -> None:
        """CSV with quoted fields containing commas parses correctly."""
        csv_content = (
            'prompt,category,intent\n'
            '"Best laptop, phone, or tablet?",comparison,transactional\n'
        )
        path = os.path.join(str(tmp_path), "quoted.csv")
        with open(path, "w") as f:
            f.write(csv_content)

        prompts = load_prompts(path)

        assert len(prompts) == 1
        assert prompts[0].prompt == "Best laptop, phone, or tablet?"


class TestValidatePrompts:
    """Tests for validate_prompts."""

    def test_valid_prompts_pass_through(self) -> None:
        """Valid prompts are returned unchanged."""
        prompts = [
            PromptEntry(prompt="Best laptop?", category="comparison"),
            PromptEntry(prompt="Top phone?"),
        ]
        result = validate_prompts(prompts)

        assert len(result) == 2
        assert result[0].prompt == "Best laptop?"

    def test_strips_whitespace(self) -> None:
        """Validates and strips whitespace from prompt text."""
        prompts = [
            PromptEntry(prompt="  Best laptop?  ", category="  comparison  "),
        ]
        result = validate_prompts(prompts)

        assert result[0].prompt == "Best laptop?"
        assert result[0].category == "comparison"

    def test_filters_empty_prompts(self) -> None:
        """Prompts with empty string after stripping are filtered out."""
        prompts = [
            PromptEntry(prompt="Best laptop?"),
            PromptEntry(prompt=""),
            PromptEntry(prompt="   "),
        ]
        result = validate_prompts(prompts)

        assert len(result) == 1
        assert result[0].prompt == "Best laptop?"

    def test_empty_list_returns_empty(self) -> None:
        """Empty prompt list returns empty list."""
        result = validate_prompts([])

        assert result == []

    def test_strips_intent_whitespace(self) -> None:
        """Intent field whitespace is stripped."""
        prompts = [PromptEntry(prompt="Best?", intent="  transactional  ")]
        result = validate_prompts(prompts)

        assert result[0].intent == "transactional"

    def test_empty_category_becomes_none(self) -> None:
        """Category that becomes empty after stripping is set to None."""
        prompts = [PromptEntry(prompt="Best?", category="   ")]
        result = validate_prompts(prompts)

        assert result[0].category is None

    def test_empty_intent_becomes_none(self) -> None:
        """Intent that becomes empty after stripping is set to None."""
        prompts = [PromptEntry(prompt="Best?", intent="   ")]
        result = validate_prompts(prompts)

        assert result[0].intent is None
