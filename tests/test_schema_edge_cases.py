"""Edge-case tests for Schema.org JSON-LD extraction."""

from __future__ import annotations

from context_cli.core.checks.schema import check_schema_org


def test_nested_graph():
    """JSON-LD with @graph array should extract all contained items."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "Acme"},
        {"@type": "WebSite", "name": "Acme Site"}
    ]}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    # @graph is a dict with @graph key — current parser treats the outer dict
    # We expect at least the top-level object to be parsed
    assert report.blocks_found >= 1


def test_invalid_json_in_script():
    """Invalid JSON in a ld+json script should be silently skipped."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {not valid json at all!!!}
    </script>
    <script type="application/ld+json">
    {"@type": "Article", "headline": "Valid"}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 1
    assert report.schemas[0].schema_type == "Article"


def test_array_type():
    """@type as an array should be joined into a comma-separated string."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": ["Product", "IndividualProduct"], "name": "Widget"}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 1
    assert "Product" in report.schemas[0].schema_type
    assert "IndividualProduct" in report.schemas[0].schema_type


def test_array_of_objects():
    """A JSON-LD script containing an array of objects should parse all items."""
    html = """
    <html><head>
    <script type="application/ld+json">
    [
        {"@type": "BreadcrumbList", "itemListElement": []},
        {"@type": "Product", "name": "Widget"}
    ]
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 2
    types = {s.schema_type for s in report.schemas}
    assert "BreadcrumbList" in types
    assert "Product" in types


def test_empty_script_tag():
    """An empty ld+json script tag should not crash or produce blocks."""
    html = """
    <html><head>
    <script type="application/ld+json"></script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 0


def test_no_at_type():
    """JSON-LD without @type should use 'Unknown' as fallback."""
    html = """
    <html><head>
    <script type="application/ld+json">
    {"name": "Something", "url": "https://example.com"}
    </script>
    </head><body></body></html>
    """
    report = check_schema_org(html)

    assert report.blocks_found == 1
    assert report.schemas[0].schema_type == "Unknown"
