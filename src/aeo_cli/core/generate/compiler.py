"""Orchestrator — renders generated assets and coordinates the generate pipeline."""

from __future__ import annotations

from aeo_cli.core.models import (
    GenerateConfig,
    GenerateResult,
    LlmsTxtContent,
    SchemaJsonLdOutput,
)


def render_llms_txt(content: LlmsTxtContent) -> str:
    """Render LlmsTxtContent to llms.txt format string.

    Format:
    # Title
    > Description

    ## Section
    - [Link Title](url): Description
    """
    lines: list[str] = []
    lines.append(f"# {content.title}")
    lines.append(f"> {content.description}")

    for section in content.sections:
        lines.append("")
        lines.append(f"## {section.heading}")
        for link in section.links:
            if link.description:
                lines.append(f"- [{link.title}]({link.url}): {link.description}")
            else:
                lines.append(f"- [{link.title}]({link.url})")

    return "\n".join(lines) + "\n"


def render_schema_jsonld(output: SchemaJsonLdOutput) -> str:
    """Render SchemaJsonLdOutput to pretty-printed JSON string."""
    import json

    return json.dumps(output.json_ld, indent=2) + "\n"


async def generate_assets(config: GenerateConfig) -> GenerateResult:
    """Main orchestrator:
    1. Crawl URL with extract_page()
    2. Detect or use specified model
    3. Get profile
    4. Build prompts and call LLM for llms.txt content
    5. Build prompts and call LLM for schema.jsonld
    6. Write files to output_dir
    7. Return GenerateResult
    """
    import os

    from aeo_cli.core.crawler import extract_page

    from .llm import call_llm_structured, detect_model
    from .profiles import get_profile
    from .prompts import (
        build_llms_txt_system_prompt,
        build_llms_txt_user_prompt,
        build_schema_system_prompt,
        build_schema_user_prompt,
    )

    errors: list[str] = []

    # 1. Crawl
    crawl_result = await extract_page(config.url)
    if not crawl_result.success:
        raise RuntimeError(f"Failed to crawl {config.url}: {crawl_result.error}")

    # 2. Model
    model = config.model or detect_model()

    # 3. Profile
    profile = get_profile(config.profile.value)

    # 4. Generate llms.txt
    llms_system = build_llms_txt_system_prompt(profile)
    existing_links = crawl_result.internal_links or []
    llms_user = build_llms_txt_user_prompt(config.url, crawl_result.markdown, existing_links)

    llms_data = await call_llm_structured(
        messages=[
            {"role": "system", "content": llms_system},
            {"role": "user", "content": llms_user},
        ],
        model=model,
        response_model=LlmsTxtContent,
    )
    llms_txt = LlmsTxtContent.model_validate(llms_data)

    # 5. Generate schema.jsonld
    schema_system = build_schema_system_prompt(profile)
    schema_user = build_schema_user_prompt(config.url, crawl_result.markdown, [])

    schema_data = await call_llm_structured(
        messages=[
            {"role": "system", "content": schema_system},
            {"role": "user", "content": schema_user},
        ],
        model=model,
        response_model=SchemaJsonLdOutput,
    )
    schema_jsonld = SchemaJsonLdOutput.model_validate(schema_data)

    # 6. Write files
    os.makedirs(config.output_dir, exist_ok=True)

    llms_path = os.path.join(config.output_dir, "llms.txt")
    schema_path = os.path.join(config.output_dir, "schema.jsonld")

    with open(llms_path, "w") as f:
        f.write(render_llms_txt(llms_txt))

    with open(schema_path, "w") as f:
        f.write(render_schema_jsonld(schema_jsonld))

    # 7. Return result
    return GenerateResult(
        url=config.url,
        model_used=model,
        profile=config.profile,
        llms_txt=llms_txt,
        schema_jsonld=schema_jsonld,
        llms_txt_path=llms_path,
        schema_jsonld_path=schema_path,
        errors=errors,
    )
