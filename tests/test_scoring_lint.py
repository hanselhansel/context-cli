"""Tests for compute_lint_results() in scoring.py."""

from __future__ import annotations

from context_cli.core.models import (
    BotAccessResult,
    ContentReport,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
)
from context_cli.core.scoring import compute_lint_results

# ── Helper factories ─────────────────────────────────────────────────────────


def _robots(found: bool = True, bots: list[BotAccessResult] | None = None) -> RobotsReport:
    if bots is None:
        bots = [BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed")]
    return RobotsReport(found=found, bots=bots)


def _llms(found: bool = True, llms_full: bool = False) -> LlmsTxtReport:
    return LlmsTxtReport(found=found, llms_full_found=llms_full)


def _schema(blocks: int = 1, types: list[str] | None = None) -> SchemaReport:
    if types is None:
        types = ["Organization"]
    schemas = [SchemaOrgResult(schema_type=t, properties=["name"]) for t in types[:blocks]]
    return SchemaReport(blocks_found=blocks, schemas=schemas)


def _content(
    waste_pct: float = 50.0,
    raw_tokens: int = 1000,
    clean_tokens: int = 500,
) -> ContentReport:
    return ContentReport(
        word_count=200,
        context_waste_pct=waste_pct,
        estimated_raw_tokens=raw_tokens,
        estimated_clean_tokens=clean_tokens,
    )


# ── All checks pass ─────────────────────────────────────────────────────────


def test_all_checks_pass():
    """When everything is present and efficient, all checks pass."""
    result = compute_lint_results(
        _robots(),
        _llms(),
        _schema(),
        _content(waste_pct=30.0),
    )
    assert isinstance(result, LintResult)
    assert result.passed is True
    assert len(result.checks) == 4
    assert all(c.passed for c in result.checks)
    assert result.context_waste_pct == 30.0
    assert result.raw_tokens == 1000
    assert result.clean_tokens == 500


# ── AI Primitives check ─────────────────────────────────────────────────────


def test_ai_primitives_pass_with_llms_txt():
    """llms.txt found → AI Primitives passes."""
    result = compute_lint_results(_robots(), _llms(found=True), _schema(), _content())
    ai_check = next(c for c in result.checks if c.name == "AI Primitives")
    assert ai_check.passed is True
    assert "llms.txt found" in ai_check.detail


def test_ai_primitives_pass_with_llms_full():
    """llms-full.txt found (even without llms.txt) → AI Primitives passes."""
    result = compute_lint_results(
        _robots(), _llms(found=False, llms_full=True), _schema(), _content()
    )
    ai_check = next(c for c in result.checks if c.name == "AI Primitives")
    assert ai_check.passed is True


def test_ai_primitives_fail():
    """Neither llms.txt nor llms-full.txt → AI Primitives fails."""
    result = compute_lint_results(
        _robots(), _llms(found=False, llms_full=False), _schema(), _content()
    )
    ai_check = next(c for c in result.checks if c.name == "AI Primitives")
    assert ai_check.passed is False
    assert "No llms.txt found" in ai_check.detail


# ── Bot Access check ─────────────────────────────────────────────────────────


def test_bot_access_all_allowed():
    """All bots allowed → Bot Access passes."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=True, detail="Allowed"),
    ]
    result = compute_lint_results(_robots(bots=bots), _llms(), _schema(), _content())
    bot_check = next(c for c in result.checks if c.name == "Bot Access")
    assert bot_check.passed is True
    assert "2/2 AI bots allowed" in bot_check.detail


def test_bot_access_some_blocked():
    """Some bots blocked → Bot Access fails with detail listing blocked bots."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail="Allowed"),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail="Blocked"),
        BotAccessResult(bot="PerplexityBot", allowed=False, detail="Blocked"),
    ]
    result = compute_lint_results(_robots(bots=bots), _llms(), _schema(), _content())
    bot_check = next(c for c in result.checks if c.name == "Bot Access")
    assert bot_check.passed is False
    assert "1/3 AI bots allowed" in bot_check.detail
    assert "ClaudeBot" in bot_check.detail
    assert "PerplexityBot" in bot_check.detail


def test_bot_access_no_robots_txt():
    """robots.txt not found → Bot Access passes (default open)."""
    result = compute_lint_results(
        _robots(found=False, bots=[]), _llms(), _schema(), _content()
    )
    bot_check = next(c for c in result.checks if c.name == "Bot Access")
    assert bot_check.passed is True
    assert "No robots.txt found" in bot_check.detail


def test_bot_access_robots_found_no_bots():
    """robots.txt found but no bots listed → default detail."""
    result = compute_lint_results(
        RobotsReport(found=True, bots=[]), _llms(), _schema(), _content()
    )
    bot_check = next(c for c in result.checks if c.name == "Bot Access")
    assert bot_check.passed is True
    assert "No robots.txt found" in bot_check.detail


def test_bot_access_blocked_truncation():
    """When >3 bots blocked, detail shows at most 3."""
    bots = [
        BotAccessResult(bot=f"Bot{i}", allowed=False, detail="Blocked")
        for i in range(5)
    ]
    result = compute_lint_results(_robots(bots=bots), _llms(), _schema(), _content())
    bot_check = next(c for c in result.checks if c.name == "Bot Access")
    assert bot_check.passed is False
    # Only first 3 blocked bots should appear in detail
    assert "Bot0" in bot_check.detail
    assert "Bot1" in bot_check.detail
    assert "Bot2" in bot_check.detail
    # Bot3 and Bot4 should NOT appear
    assert "Bot3" not in bot_check.detail
    assert "Bot4" not in bot_check.detail


# ── Data Structuring check ───────────────────────────────────────────────────


def test_data_structuring_pass():
    """Schema blocks found → Data Structuring passes."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(blocks=2, types=["Article", "FAQPage"]), _content()
    )
    schema_check = next(c for c in result.checks if c.name == "Data Structuring")
    assert schema_check.passed is True
    assert "2 JSON-LD blocks" in schema_check.detail
    assert "Article" in schema_check.detail
    assert "FAQPage" in schema_check.detail


def test_data_structuring_fail():
    """No schema blocks → Data Structuring fails."""
    result = compute_lint_results(
        _robots(), _llms(), SchemaReport(blocks_found=0), _content()
    )
    schema_check = next(c for c in result.checks if c.name == "Data Structuring")
    assert schema_check.passed is False
    assert "0 JSON-LD blocks" in schema_check.detail


def test_data_structuring_many_types_truncated():
    """When >3 schema types, detail shows at most 3."""
    types = ["Article", "FAQPage", "Product", "Organization", "BreadcrumbList"]
    schemas = [SchemaOrgResult(schema_type=t, properties=[]) for t in types]
    report = SchemaReport(blocks_found=5, schemas=schemas)
    result = compute_lint_results(_robots(), _llms(), report, _content())
    schema_check = next(c for c in result.checks if c.name == "Data Structuring")
    # Only first 3 types in the detail
    assert "Article" in schema_check.detail
    assert "FAQPage" in schema_check.detail
    assert "Product" in schema_check.detail
    assert "Organization" not in schema_check.detail


# ── Token Efficiency check ───────────────────────────────────────────────────


def test_token_efficiency_pass():
    """Context waste <70% → Token Efficiency passes."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=45.0)
    )
    eff_check = next(c for c in result.checks if c.name == "Token Efficiency")
    assert eff_check.passed is True
    assert "45% Context Waste" in eff_check.detail


def test_token_efficiency_fail():
    """Context waste >=70% → Token Efficiency fails."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=85.0)
    )
    eff_check = next(c for c in result.checks if c.name == "Token Efficiency")
    assert eff_check.passed is False
    assert "85% Context Waste" in eff_check.detail


def test_token_efficiency_at_boundary():
    """Context waste exactly 70% → Token Efficiency fails (not <70)."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=70.0)
    )
    eff_check = next(c for c in result.checks if c.name == "Token Efficiency")
    assert eff_check.passed is False


def test_token_efficiency_zero_tokens():
    """Zero raw tokens → 0% waste, no token detail in message."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(),
        _content(waste_pct=0.0, raw_tokens=0, clean_tokens=0),
    )
    eff_check = next(c for c in result.checks if c.name == "Token Efficiency")
    assert eff_check.passed is True
    assert "0% Context Waste" in eff_check.detail
    # No "raw -> clean tokens" detail when raw_tokens is 0
    assert "raw" not in eff_check.detail


def test_token_efficiency_detail_with_tokens():
    """When raw_tokens > 0, detail includes token breakdown."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(),
        _content(waste_pct=60.0, raw_tokens=10000, clean_tokens=4000),
    )
    eff_check = next(c for c in result.checks if c.name == "Token Efficiency")
    assert "10,000 raw" in eff_check.detail
    assert "4,000 clean tokens" in eff_check.detail


# ── LintResult aggregate ────────────────────────────────────────────────────


def test_lint_result_passed_false_when_any_fails():
    """LintResult.passed is False when any check fails."""
    result = compute_lint_results(
        _robots(), _llms(found=False), _schema(), _content(waste_pct=30.0)
    )
    assert result.passed is False  # AI Primitives fails


def test_lint_result_token_fields():
    """LintResult carries through token metrics from content."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(),
        _content(waste_pct=55.5, raw_tokens=8000, clean_tokens=3600),
    )
    assert result.context_waste_pct == 55.5
    assert result.raw_tokens == 8000
    assert result.clean_tokens == 3600


# ── Edge cases ──────────────────────────────────────────────────────────────


def test_all_checks_fail():
    """All four checks fail → passed is False, all check.passed are False."""
    bots = [BotAccessResult(bot="GPTBot", allowed=False, detail="Blocked")]
    result = compute_lint_results(
        _robots(found=True, bots=bots),
        _llms(found=False),
        SchemaReport(blocks_found=0),
        _content(waste_pct=90.0),
    )
    assert result.passed is False
    assert all(not c.passed for c in result.checks)


def test_lint_check_model():
    """LintCheck model can be instantiated and serialized."""
    check = LintCheck(name="Test", passed=True, detail="OK")
    assert check.name == "Test"
    assert check.passed is True
    assert check.detail == "OK"
    data = check.model_dump()
    assert data["name"] == "Test"


def test_lint_result_model_defaults():
    """LintResult defaults are correct."""
    result = LintResult()
    assert result.checks == []
    assert result.context_waste_pct == 0.0
    assert result.raw_tokens == 0
    assert result.clean_tokens == 0
    assert result.passed is True


def test_lint_result_json_roundtrip():
    """LintResult survives JSON serialization/deserialization."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=42.0)
    )
    json_str = result.model_dump_json()
    restored = LintResult.model_validate_json(json_str)
    assert restored == result
    assert len(restored.checks) == 4


# ── Verdict rendering ──────────────────────────────────────────────────────


def test_render_verdict_in_single_report():
    """render_single_report() outputs a RESULT verdict line with correct counts."""
    from io import StringIO

    from rich.console import Console

    from context_cli.core.models import AuditReport
    from context_cli.formatters.rich_output import render_single_report

    # waste=50 → Token Efficiency severity=warn (30-70 range)
    # AI Primitives → fail (no llms.txt), Bot Access → pass, Data Structuring → pass
    # So: 2 passed, 1 failed, 1 warning
    lr = compute_lint_results(
        _robots(),
        _llms(found=False),
        _schema(),
        _content(waste_pct=50),
    )
    report = AuditReport(
        url="https://example.com",
        robots=_robots(),
        llms_txt=_llms(found=False),
        schema_org=_schema(),
        content=_content(waste_pct=50),
        lint_result=lr,
    )

    buf = StringIO()
    console = Console(file=buf, no_color=True, width=120)
    render_single_report(report, console)
    output = buf.getvalue()

    assert "RESULT:" in output
    assert "2 passed" in output
    assert "1 failed" in output
    assert "1 warning" in output


def test_render_verdict_all_pass():
    """When all checks pass and no warnings, verdict shows 4 passed, 0 failed."""
    from io import StringIO

    from rich.console import Console

    from context_cli.core.models import AuditReport
    from context_cli.formatters.rich_output import render_single_report

    # waste=10 → Token Efficiency severity=pass (<30)
    lr = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=10),
    )
    report = AuditReport(
        url="https://example.com",
        robots=_robots(),
        llms_txt=_llms(),
        schema_org=_schema(),
        content=_content(waste_pct=10),
        lint_result=lr,
    )

    buf = StringIO()
    console = Console(file=buf, no_color=True, width=120)
    render_single_report(report, console)
    output = buf.getvalue()

    assert "RESULT:" in output
    assert "4 passed" in output
    assert "0 failed" in output


def test_render_verdict_with_warnings():
    """Verdict counts warn-severity checks separately as warnings."""
    from io import StringIO

    from rich.console import Console

    from context_cli.core.models import AuditReport
    from context_cli.formatters.rich_output import render_single_report

    # waste=10 → severity=pass; then we inject an extra warn check
    lr = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=10),
    )
    lr.checks.append(LintCheck(name="TestWarn", passed=True, detail="ok", severity="warn"))

    report = AuditReport(
        url="https://example.com",
        robots=_robots(),
        llms_txt=_llms(),
        schema_org=_schema(),
        content=_content(waste_pct=10),
        lint_result=lr,
    )

    buf = StringIO()
    console = Console(file=buf, no_color=True, width=120)
    render_single_report(report, console)
    output = buf.getvalue()

    assert "RESULT:" in output
    assert "4 passed" in output
    assert "0 failed" in output
    assert "1 warning" in output
