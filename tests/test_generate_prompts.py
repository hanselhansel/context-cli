"""Tests for prompt builders."""

from __future__ import annotations

from context_cli.core.generate.profiles import GENERIC_PROFILE, SAAS_PROFILE
from context_cli.core.generate.prompts import (
    _MAX_CONTENT_CHARS,
    build_llms_txt_system_prompt,
    build_llms_txt_user_prompt,
    build_schema_system_prompt,
    build_schema_user_prompt,
)


class TestBuildLlmsTxtSystemPrompt:
    def test_includes_llms_txt_spec(self):
        prompt = build_llms_txt_system_prompt(GENERIC_PROFILE)
        assert "llms.txt" in prompt
        assert "# Title" in prompt
        assert "> One-line description" in prompt

    def test_includes_profile_sections(self):
        prompt = build_llms_txt_system_prompt(GENERIC_PROFILE)
        for section in GENERIC_PROFILE.llms_txt_sections:
            assert section in prompt

    def test_includes_profile_description(self):
        prompt = build_llms_txt_system_prompt(SAAS_PROFILE)
        assert SAAS_PROFILE.description in prompt

    def test_different_profiles_produce_different_prompts(self):
        generic = build_llms_txt_system_prompt(GENERIC_PROFILE)
        saas = build_llms_txt_system_prompt(SAAS_PROFILE)
        assert generic != saas


class TestBuildLlmsTxtUserPrompt:
    def test_includes_url(self):
        prompt = build_llms_txt_user_prompt(
            "https://example.com", "Some content", []
        )
        assert "https://example.com" in prompt

    def test_includes_content(self):
        prompt = build_llms_txt_user_prompt(
            "https://example.com", "Hello world content", []
        )
        assert "Hello world content" in prompt

    def test_truncates_long_content(self):
        long_content = "x" * 20000
        prompt = build_llms_txt_user_prompt(
            "https://example.com", long_content, []
        )
        assert "[... content truncated ...]" in prompt
        # Original content should be cut
        assert len(prompt) < len(long_content)

    def test_includes_existing_links(self):
        links = ["https://example.com/page1", "https://example.com/page2"]
        prompt = build_llms_txt_user_prompt(
            "https://example.com", "Content", links
        )
        assert "https://example.com/page1" in prompt
        assert "https://example.com/page2" in prompt

    def test_no_links_section_when_empty(self):
        prompt = build_llms_txt_user_prompt(
            "https://example.com", "Content", []
        )
        assert "Discovered links" not in prompt

    def test_truncation_boundary(self):
        exact_content = "a" * _MAX_CONTENT_CHARS
        prompt = build_llms_txt_user_prompt(
            "https://example.com", exact_content, []
        )
        assert "[... content truncated ...]" not in prompt

        over_content = "a" * (_MAX_CONTENT_CHARS + 1)
        prompt2 = build_llms_txt_user_prompt(
            "https://example.com", over_content, []
        )
        assert "[... content truncated ...]" in prompt2


class TestBuildSchemaSystemPrompt:
    def test_includes_schema_org(self):
        prompt = build_schema_system_prompt(GENERIC_PROFILE)
        assert "Schema.org" in prompt
        assert "JSON-LD" in prompt

    def test_includes_profile_types(self):
        prompt = build_schema_system_prompt(SAAS_PROFILE)
        for schema_type in SAAS_PROFILE.schema_types:
            assert schema_type in prompt

    def test_includes_context_url(self):
        prompt = build_schema_system_prompt(GENERIC_PROFILE)
        assert "https://schema.org" in prompt


class TestBuildSchemaUserPrompt:
    def test_includes_url(self):
        prompt = build_schema_user_prompt(
            "https://example.com", "Content", []
        )
        assert "https://example.com" in prompt

    def test_includes_content(self):
        prompt = build_schema_user_prompt(
            "https://example.com", "My page content here", []
        )
        assert "My page content here" in prompt

    def test_truncates_long_content(self):
        long_content = "y" * 20000
        prompt = build_schema_user_prompt(
            "https://example.com", long_content, []
        )
        assert "[... content truncated ...]" in prompt

    def test_includes_existing_schemas(self):
        existing = [{"@type": "Organization", "name": "Test"}]
        prompt = build_schema_user_prompt(
            "https://example.com", "Content", existing
        )
        assert "Organization" in prompt
        assert "existing" in prompt.lower() or "Existing" in prompt

    def test_no_existing_section_when_empty(self):
        prompt = build_schema_user_prompt(
            "https://example.com", "Content", []
        )
        assert "Existing JSON-LD" not in prompt
