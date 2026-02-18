"""Prompt builders for llms.txt and schema.jsonld generation."""

from __future__ import annotations

from .profiles import Profile

_MAX_CONTENT_CHARS = 8000


def build_llms_txt_system_prompt(profile: Profile) -> str:
    """Build system prompt for llms.txt generation.

    Includes llms.txt spec, profile-specific guidance, recommended sections.
    """
    sections_list = ", ".join(f'"{s}"' for s in profile.llms_txt_sections)
    return (
        "You are an expert at creating llms.txt files — a proposed standard that helps "
        "LLMs understand websites. The format is:\n\n"
        "# Title\n"
        "> One-line description\n\n"
        "## Section Name\n"
        "- [Link Title](url): Brief description\n\n"
        "Rules:\n"
        "- Title should be the site/product name\n"
        "- Description should be a concise one-liner\n"
        "- Each section groups related links\n"
        "- Links must use absolute URLs from the site\n"
        "- Descriptions should be brief and informative\n"
        "- Only include links that actually exist on the site\n\n"
        f"Industry context: {profile.description}\n"
        f"Recommended sections: {sections_list}\n"
        "Adapt sections based on what the site actually contains."
    )


def build_llms_txt_user_prompt(
    url: str, markdown_content: str, existing_links: list[str]
) -> str:
    """Build user prompt with crawled page content. Truncate markdown to ~8000 chars."""
    truncated = markdown_content[:_MAX_CONTENT_CHARS]
    if len(markdown_content) > _MAX_CONTENT_CHARS:
        truncated += "\n\n[... content truncated ...]"

    links_section = ""
    if existing_links:
        links_list = "\n".join(f"- {link}" for link in existing_links[:50])
        links_section = f"\n\nDiscovered links on the site:\n{links_list}"

    return (
        f"Generate an llms.txt file for: {url}\n\n"
        f"Page content (markdown):\n---\n{truncated}\n---\n"
        f"{links_section}\n\n"
        "Return a JSON object with fields: title, description, sections (array of "
        "{heading, links: [{title, url, description}]})"
    )


def build_schema_system_prompt(profile: Profile) -> str:
    """Build system prompt for Schema.org JSON-LD generation.

    Includes schema.org best practices, profile-specific types to use.
    """
    types_list = ", ".join(profile.schema_types)
    return (
        "You are an expert at creating Schema.org JSON-LD structured data for websites. "
        "JSON-LD is embedded in HTML <script type=\"application/ld+json\"> tags and helps "
        "search engines and AI systems understand page content.\n\n"
        "Rules:\n"
        "- Use @context: https://schema.org\n"
        "- Include @type matching the page content\n"
        "- Fill in as many relevant properties as the content supports\n"
        "- Use absolute URLs for url, image, and logo properties\n"
        "- Ensure the JSON-LD is valid and complete\n"
        "- Do not invent data not present in the page content\n\n"
        f"Industry context: {profile.description}\n"
        f"Recommended Schema.org types: {types_list}\n"
        "Choose the most appropriate type based on the actual page content."
    )


def build_schema_user_prompt(
    url: str, markdown_content: str, existing_schemas: list[dict]
) -> str:
    """Build user prompt with crawled page content and existing schemas.

    Truncate markdown to ~8000 chars.
    """
    import json

    truncated = markdown_content[:_MAX_CONTENT_CHARS]
    if len(markdown_content) > _MAX_CONTENT_CHARS:
        truncated += "\n\n[... content truncated ...]"

    existing_section = ""
    if existing_schemas:
        schemas_str = json.dumps(existing_schemas, indent=2)[:2000]
        existing_section = (
            f"\n\nExisting JSON-LD found on the page (improve or complement these):\n"
            f"{schemas_str}"
        )

    return (
        f"Generate Schema.org JSON-LD for: {url}\n\n"
        f"Page content (markdown):\n---\n{truncated}\n---\n"
        f"{existing_section}\n\n"
        "Return a JSON object with fields: schema_type (the primary @type string), "
        "json_ld (the complete JSON-LD object)."
    )
