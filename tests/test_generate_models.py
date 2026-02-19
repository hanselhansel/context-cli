"""Tests for generate-related Pydantic models."""

from __future__ import annotations

from context_cli.core.models import (
    GenerateConfig,
    GenerateResult,
    LlmsTxtContent,
    LlmsTxtLink,
    LlmsTxtSection,
    ProfileType,
    SchemaJsonLdOutput,
)


class TestLlmsTxtLink:
    def test_create_minimal(self):
        link = LlmsTxtLink(title="Docs", url="https://example.com/docs")
        assert link.title == "Docs"
        assert link.url == "https://example.com/docs"
        assert link.description == ""

    def test_create_with_description(self):
        link = LlmsTxtLink(
            title="API Ref", url="https://example.com/api", description="REST API docs"
        )
        assert link.description == "REST API docs"

    def test_serialization_roundtrip(self):
        link = LlmsTxtLink(title="Home", url="https://example.com", description="Homepage")
        data = link.model_dump()
        restored = LlmsTxtLink.model_validate(data)
        assert restored == link


class TestLlmsTxtSection:
    def test_create_empty_section(self):
        section = LlmsTxtSection(heading="Docs")
        assert section.heading == "Docs"
        assert section.links == []

    def test_create_with_links(self):
        section = LlmsTxtSection(
            heading="API",
            links=[LlmsTxtLink(title="REST", url="https://example.com/api")],
        )
        assert len(section.links) == 1
        assert section.links[0].title == "REST"


class TestLlmsTxtContent:
    def test_create_full(self):
        content = LlmsTxtContent(
            title="Example Corp",
            description="The leading example provider.",
            sections=[
                LlmsTxtSection(
                    heading="Docs",
                    links=[LlmsTxtLink(title="Guide", url="https://example.com/guide")],
                )
            ],
        )
        assert content.title == "Example Corp"
        assert len(content.sections) == 1

    def test_empty_sections_default(self):
        content = LlmsTxtContent(title="Test", description="Test site")
        assert content.sections == []

    def test_json_schema_has_descriptions(self):
        schema = LlmsTxtContent.model_json_schema()
        assert "title" in schema["properties"]
        assert "description" in schema["properties"]["title"]


class TestSchemaJsonLdOutput:
    def test_create(self):
        output = SchemaJsonLdOutput(
            schema_type="Organization",
            json_ld={"@context": "https://schema.org", "@type": "Organization", "name": "Test"},
        )
        assert output.schema_type == "Organization"
        assert output.json_ld["@type"] == "Organization"

    def test_serialization_roundtrip(self):
        output = SchemaJsonLdOutput(
            schema_type="Product",
            json_ld={"@context": "https://schema.org", "@type": "Product", "name": "Widget"},
        )
        data = output.model_dump()
        restored = SchemaJsonLdOutput.model_validate(data)
        assert restored.json_ld == output.json_ld


class TestProfileType:
    def test_all_values(self):
        assert set(ProfileType) == {
            ProfileType.generic,
            ProfileType.cpg,
            ProfileType.saas,
            ProfileType.ecommerce,
            ProfileType.blog,
        }

    def test_string_values(self):
        assert ProfileType.generic.value == "generic"
        assert ProfileType.cpg.value == "cpg"


class TestGenerateConfig:
    def test_defaults(self):
        config = GenerateConfig(url="https://example.com")
        assert config.profile == ProfileType.generic
        assert config.model is None
        assert config.output_dir == "./context-output"

    def test_custom_values(self):
        config = GenerateConfig(
            url="https://shop.com",
            profile=ProfileType.ecommerce,
            model="gpt-4o-mini",
            output_dir="/tmp/output",
        )
        assert config.profile == ProfileType.ecommerce
        assert config.model == "gpt-4o-mini"


class TestGenerateResult:
    def test_create_full(self):
        result = GenerateResult(
            url="https://example.com",
            model_used="gpt-4o-mini",
            profile=ProfileType.generic,
            llms_txt=LlmsTxtContent(title="Test", description="A test"),
            schema_jsonld=SchemaJsonLdOutput(
                schema_type="Organization",
                json_ld={"@context": "https://schema.org", "@type": "Organization"},
            ),
            llms_txt_path="/tmp/llms.txt",
            schema_jsonld_path="/tmp/schema.jsonld",
        )
        assert result.url == "https://example.com"
        assert result.errors == []

    def test_errors_default_empty(self):
        result = GenerateResult(
            url="https://example.com",
            model_used="gpt-4o-mini",
            profile=ProfileType.generic,
            llms_txt=LlmsTxtContent(title="T", description="D"),
            schema_jsonld=SchemaJsonLdOutput(schema_type="X", json_ld={}),
        )
        assert result.errors == []

    def test_paths_default_none(self):
        result = GenerateResult(
            url="https://example.com",
            model_used="gpt-4o-mini",
            profile=ProfileType.generic,
            llms_txt=LlmsTxtContent(title="T", description="D"),
            schema_jsonld=SchemaJsonLdOutput(schema_type="X", json_ld={}),
        )
        assert result.llms_txt_path is None
        assert result.schema_jsonld_path is None
