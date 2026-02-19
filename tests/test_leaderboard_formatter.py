"""Tests for the leaderboard formatter (markdown + JSON)."""

from __future__ import annotations

import json

from context_cli.core.models import (
    AuditReport,
    BotAccessResult,
    ContentReport,
    LintCheck,
    LintResult,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)
from context_cli.formatters.leaderboard import (
    _is_rag_ready,
    _sort_reports,
    format_leaderboard_json,
    format_leaderboard_md,
)

# ── Factory helpers ──────────────────────────────────────────────────────────


def _report(
    url: str = "https://example.com",
    waste: float = 50.0,
    llms_found: bool = True,
    bots_blocked: bool = False,
    raw_tokens: int = 10000,
) -> AuditReport:
    """Create a minimal AuditReport for testing."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=not bots_blocked),
        BotAccessResult(bot="ClaudeBot", allowed=True),
    ]
    clean = int(raw_tokens * (100 - waste) / 100)
    return AuditReport(
        url=url,
        overall_score=55.0,
        robots=RobotsReport(found=True, score=25, detail="OK", bots=bots),
        llms_txt=LlmsTxtReport(
            found=llms_found, score=10 if llms_found else 0, detail="OK"
        ),
        schema_org=SchemaReport(blocks_found=1, score=13, detail="1 block"),
        content=ContentReport(word_count=500, score=17, detail="500 words"),
        lint_result=LintResult(
            checks=[
                LintCheck(
                    name="Token Efficiency",
                    passed=waste < 70,
                    detail=f"{waste}%",
                ),
            ],
            context_waste_pct=waste,
            raw_tokens=raw_tokens,
            clean_tokens=clean,
            passed=waste < 70,
        ),
    )


def _report_no_lint(url: str = "https://nolint.com") -> AuditReport:
    """Create an AuditReport without lint_result."""
    return AuditReport(
        url=url,
        overall_score=40.0,
        robots=RobotsReport(found=True, score=25, detail="OK", bots=[]),
        llms_txt=LlmsTxtReport(found=True, score=10, detail="OK"),
        schema_org=SchemaReport(blocks_found=0, score=0, detail="None"),
        content=ContentReport(word_count=200, score=8, detail="200 words"),
        lint_result=None,
    )


# ── Sorting tests ────────────────────────────────────────────────────────────


def test_sort_by_waste_ascending():
    """Reports should be sorted by context waste % ascending."""
    r1 = _report("https://a.com", waste=80.0)
    r2 = _report("https://b.com", waste=20.0)
    r3 = _report("https://c.com", waste=50.0)

    result = _sort_reports([r1, r2, r3])

    assert result[0].url == "https://b.com"
    assert result[1].url == "https://c.com"
    assert result[2].url == "https://a.com"


def test_sort_no_lint_goes_last():
    """Reports without lint_result should sort last (waste treated as 100%)."""
    r1 = _report("https://a.com", waste=90.0)
    r2 = _report_no_lint("https://nolint.com")

    result = _sort_reports([r1, r2])

    assert result[0].url == "https://a.com"
    assert result[1].url == "https://nolint.com"


def test_sort_single_report():
    """Single report should return unchanged."""
    r = _report("https://single.com", waste=30.0)
    result = _sort_reports([r])
    assert len(result) == 1
    assert result[0].url == "https://single.com"


def test_sort_empty_list():
    """Empty list should return empty list."""
    assert _sort_reports([]) == []


# ── RAG Ready logic tests ───────────────────────────────────────────────────


def test_rag_ready_all_conditions_met():
    """RAG Ready should be True when llms.txt found, bots allowed, waste below threshold."""
    r = _report(waste=40.0, llms_found=True, bots_blocked=False)
    assert _is_rag_ready(r, waste_threshold=70.0) is True


def test_rag_ready_false_when_llms_missing():
    """RAG Ready should be False when llms.txt is not found."""
    r = _report(waste=40.0, llms_found=False, bots_blocked=False)
    assert _is_rag_ready(r, waste_threshold=70.0) is False


def test_rag_ready_false_when_bots_blocked():
    """RAG Ready should be False when any bot is blocked."""
    r = _report(waste=40.0, llms_found=True, bots_blocked=True)
    assert _is_rag_ready(r, waste_threshold=70.0) is False


def test_rag_ready_false_when_waste_above_threshold():
    """RAG Ready should be False when waste >= threshold."""
    r = _report(waste=80.0, llms_found=True, bots_blocked=False)
    assert _is_rag_ready(r, waste_threshold=70.0) is False


def test_rag_ready_false_waste_equals_threshold():
    """RAG Ready should be False when waste exactly equals threshold (strict <)."""
    r = _report(waste=70.0, llms_found=True, bots_blocked=False)
    assert _is_rag_ready(r, waste_threshold=70.0) is False


def test_rag_ready_no_lint_result():
    """RAG Ready with no lint_result: waste_ok defaults to True, depends on other signals."""
    r = _report_no_lint()
    # llms_found=True, bots=[] (no bots to block), no lint_result (waste_ok=True)
    assert _is_rag_ready(r, waste_threshold=70.0) is True


def test_rag_ready_custom_threshold():
    """Custom waste_threshold should be respected."""
    r = _report(waste=55.0, llms_found=True, bots_blocked=False)
    assert _is_rag_ready(r, waste_threshold=50.0) is False
    assert _is_rag_ready(r, waste_threshold=60.0) is True


def test_rag_ready_robots_not_found_bots_ok():
    """When robots.txt not found, bots_ok defaults to True."""
    r = _report(waste=30.0, llms_found=True)
    r.robots = RobotsReport(found=False, score=0, detail="Not found", bots=[])
    assert _is_rag_ready(r, waste_threshold=70.0) is True


# ── Markdown format tests ───────────────────────────────────────────────────


def test_md_header():
    """Markdown output should start with '# Context CLI Leaderboard'."""
    r = _report()
    md = format_leaderboard_md([r])
    assert md.startswith("# Context CLI Leaderboard")


def test_md_summary_line():
    """Summary line should include URL count and threshold."""
    reports = [_report("https://a.com"), _report("https://b.com")]
    md = format_leaderboard_md(reports, waste_threshold=65.0)
    assert "2 URLs audited" in md
    assert "RAG Ready threshold: 65%" in md


def test_md_table_columns():
    """Table should have all expected column headers."""
    md = format_leaderboard_md([_report()])
    assert "| # |" in md
    assert "Target URL" in md
    assert "Raw Tokens" in md
    assert "MD Tokens" in md
    assert "Context Waste %" in md
    assert "llms.txt" in md
    assert "Bots OK" in md
    assert "RAG Ready?" in md


def test_md_reports_numbered():
    """Reports should be numbered starting at 1."""
    reports = [
        _report("https://a.com", waste=10.0),
        _report("https://b.com", waste=20.0),
        _report("https://c.com", waste=30.0),
    ]
    md = format_leaderboard_md(reports)
    assert "| 1 |" in md
    assert "| 2 |" in md
    assert "| 3 |" in md


def test_md_sorted_by_waste():
    """Markdown table rows should be sorted by waste ascending."""
    r1 = _report("https://worst.com", waste=90.0)
    r2 = _report("https://best.com", waste=10.0)
    md = format_leaderboard_md([r1, r2])
    lines = md.split("\n")

    # Find data rows (after header separator)
    data_rows = [
        ln for ln in lines
        if ln.startswith("| ") and "| # |" not in ln and "|--" not in ln
    ]
    assert "best.com" in data_rows[0]
    assert "worst.com" in data_rows[1]


def test_md_token_values_formatted_with_commas():
    """Token values should be formatted with comma separators."""
    r = _report(waste=50.0, raw_tokens=10000)
    md = format_leaderboard_md([r])
    assert "10,000" in md
    assert "5,000" in md


def test_md_waste_percent_formatted():
    """Waste percentage should be formatted as integer with % suffix."""
    r = _report(waste=42.5)
    md = format_leaderboard_md([r])
    # 42.5 formatted with :.0f becomes "42%"
    assert "42%" in md


def test_md_llms_txt_yes():
    """llms.txt should show 'Yes' when found."""
    r = _report(llms_found=True)
    md = format_leaderboard_md([r])
    # Check the data row contains "Yes" for llms.txt
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    assert len(lines) == 1
    parts = lines[0].split("|")
    # llms.txt is the 6th column (index 6 in split since leading | creates empty first)
    assert "Yes" in parts[6].strip()


def test_md_llms_txt_no():
    """llms.txt should show 'No' when not found."""
    r = _report(llms_found=False)
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "No" in parts[6].strip()


def test_md_bots_ok_yes():
    """Bots OK should show 'Yes' when all bots allowed."""
    r = _report(bots_blocked=False)
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "Yes" in parts[7].strip()


def test_md_bots_ok_no():
    """Bots OK should show 'No' when any bot is blocked."""
    r = _report(bots_blocked=True)
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "No" in parts[7].strip()


def test_md_rag_ready_yes():
    """RAG Ready should show 'Yes' when all conditions met."""
    r = _report(waste=30.0, llms_found=True, bots_blocked=False)
    md = format_leaderboard_md([r], waste_threshold=70.0)
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "Yes" in parts[8].strip()


def test_md_rag_ready_no():
    """RAG Ready should show 'No' when conditions not met."""
    r = _report(waste=80.0, llms_found=True, bots_blocked=False)
    md = format_leaderboard_md([r], waste_threshold=70.0)
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "No" in parts[8].strip()


def test_md_no_lint_result_shows_zeros():
    """Report without lint_result should show 0 for tokens and 0% waste."""
    r = _report_no_lint()
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "nolint.com" in ln]
    assert len(lines) == 1
    assert "| 0 |" in lines[0]
    assert "0%" in lines[0]


def test_md_ends_with_newline():
    """Markdown output should end with a trailing newline."""
    md = format_leaderboard_md([_report()])
    assert md.endswith("\n")


def test_md_custom_waste_threshold():
    """Custom waste threshold should appear in the summary line."""
    md = format_leaderboard_md([_report()], waste_threshold=50.0)
    assert "RAG Ready threshold: 50%" in md


# ── JSON format tests ────────────────────────────────────────────────────────


def test_json_valid_output():
    """JSON output should be valid JSON."""
    r = _report()
    output = format_leaderboard_json([r])
    parsed = json.loads(output)
    assert isinstance(parsed, dict)


def test_json_has_leaderboard_key():
    """JSON output should contain a 'leaderboard' key."""
    parsed = json.loads(format_leaderboard_json([_report()]))
    assert "leaderboard" in parsed
    assert isinstance(parsed["leaderboard"], list)


def test_json_has_waste_threshold():
    """JSON output should contain the waste_threshold value."""
    parsed = json.loads(format_leaderboard_json([_report()], waste_threshold=65.0))
    assert parsed["waste_threshold"] == 65.0


def test_json_entry_fields():
    """Each entry should have all required fields."""
    parsed = json.loads(format_leaderboard_json([_report()]))
    entry = parsed["leaderboard"][0]
    expected_fields = {
        "rank", "url", "raw_tokens", "clean_tokens",
        "context_waste_pct", "llms_txt", "bots_ok", "rag_ready",
    }
    assert set(entry.keys()) == expected_fields


def test_json_sorted_by_waste():
    """JSON entries should be sorted by waste ascending."""
    r1 = _report("https://high.com", waste=80.0)
    r2 = _report("https://low.com", waste=20.0)
    parsed = json.loads(format_leaderboard_json([r1, r2]))
    entries = parsed["leaderboard"]
    assert entries[0]["url"] == "https://low.com"
    assert entries[1]["url"] == "https://high.com"


def test_json_rank_sequential():
    """Ranks should be sequential starting at 1."""
    reports = [
        _report("https://a.com", waste=10.0),
        _report("https://b.com", waste=20.0),
        _report("https://c.com", waste=30.0),
    ]
    parsed = json.loads(format_leaderboard_json(reports))
    ranks = [e["rank"] for e in parsed["leaderboard"]]
    assert ranks == [1, 2, 3]


def test_json_token_values():
    """JSON should contain correct raw_tokens and clean_tokens."""
    r = _report(waste=50.0, raw_tokens=10000)
    parsed = json.loads(format_leaderboard_json([r]))
    entry = parsed["leaderboard"][0]
    assert entry["raw_tokens"] == 10000
    assert entry["clean_tokens"] == 5000


def test_json_waste_value():
    """JSON should contain correct context_waste_pct."""
    r = _report(waste=42.5)
    parsed = json.loads(format_leaderboard_json([r]))
    entry = parsed["leaderboard"][0]
    assert entry["context_waste_pct"] == 42.5


def test_json_llms_txt_boolean():
    """llms_txt should be a boolean in JSON."""
    r_yes = _report(llms_found=True)
    r_no = _report("https://no-llms.com", llms_found=False)
    parsed = json.loads(format_leaderboard_json([r_yes, r_no]))
    entries = {e["url"]: e for e in parsed["leaderboard"]}
    assert entries["https://example.com"]["llms_txt"] is True
    assert entries["https://no-llms.com"]["llms_txt"] is False


def test_json_bots_ok_boolean():
    """bots_ok should be a boolean in JSON."""
    r_ok = _report(bots_blocked=False)
    r_blocked = _report("https://blocked.com", bots_blocked=True)
    parsed = json.loads(format_leaderboard_json([r_ok, r_blocked]))
    entries = {e["url"]: e for e in parsed["leaderboard"]}
    assert entries["https://example.com"]["bots_ok"] is True
    assert entries["https://blocked.com"]["bots_ok"] is False


def test_json_rag_ready_boolean():
    """rag_ready should be a boolean in JSON."""
    r_ready = _report(waste=30.0, llms_found=True, bots_blocked=False)
    r_not = _report("https://not-ready.com", waste=80.0)
    parsed = json.loads(format_leaderboard_json([r_ready, r_not]))
    entries = {e["url"]: e for e in parsed["leaderboard"]}
    assert entries["https://example.com"]["rag_ready"] is True
    assert entries["https://not-ready.com"]["rag_ready"] is False


def test_json_no_lint_result():
    """Report without lint_result should have 0 tokens and 0 waste in JSON."""
    r = _report_no_lint()
    parsed = json.loads(format_leaderboard_json([r]))
    entry = parsed["leaderboard"][0]
    assert entry["raw_tokens"] == 0
    assert entry["clean_tokens"] == 0
    assert entry["context_waste_pct"] == 0.0


def test_json_empty_bots_list():
    """When robots bots list is empty, bots_ok should be True."""
    r = _report()
    r.robots = RobotsReport(found=True, score=25, detail="OK", bots=[])
    parsed = json.loads(format_leaderboard_json([r]))
    entry = parsed["leaderboard"][0]
    assert entry["bots_ok"] is True


def test_json_single_report():
    """Single report should produce a leaderboard with one entry."""
    parsed = json.loads(format_leaderboard_json([_report()]))
    assert len(parsed["leaderboard"]) == 1


def test_json_custom_waste_threshold():
    """Custom waste_threshold should be reflected in the output."""
    parsed = json.loads(format_leaderboard_json([_report()], waste_threshold=50.0))
    assert parsed["waste_threshold"] == 50.0


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_md_empty_bots_list():
    """When robots bots list is empty, Bots OK should show 'Yes'."""
    r = _report()
    r.robots = RobotsReport(found=True, score=25, detail="OK", bots=[])
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "Yes" in parts[7].strip()


def test_md_robots_not_found_bots_ok():
    """When robots.txt not found, bots OK should still show 'Yes'."""
    r = _report()
    r.robots = RobotsReport(found=False, score=0, detail="Not found", bots=[])
    md = format_leaderboard_md([r])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    parts = lines[0].split("|")
    assert "Yes" in parts[7].strip()


def test_md_single_report_numbered_one():
    """Single report should be numbered as 1."""
    md = format_leaderboard_md([_report()])
    lines = [ln for ln in md.split("\n") if "example.com" in ln]
    assert "| 1 |" in lines[0]


def test_json_empty_reports():
    """Empty reports list should produce empty leaderboard."""
    parsed = json.loads(format_leaderboard_json([]))
    assert parsed["leaderboard"] == []


def test_md_empty_reports():
    """Empty reports list should produce header-only markdown."""
    md = format_leaderboard_md([])
    assert "# Context CLI Leaderboard" in md
    assert "0 URLs audited" in md
