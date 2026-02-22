"""Tests for V3 scoring mode with agent readiness pillar."""

from __future__ import annotations

from context_cli.core.models import (
    AgentReadinessReport,
    AgentsMdReport,
    BotAccessResult,
    ContentReport,
    LlmsTxtReport,
    MarkdownAcceptReport,
    McpEndpointReport,
    NlwebReport,
    RobotsReport,
    SchemaOrgResult,
    SchemaReport,
    SemanticHtmlReport,
    X402Report,
)
from context_cli.core.scoring import (
    CONTENT_MAX,
    LLMS_TXT_MAX,
    ROBOTS_MAX,
    SCHEMA_MAX,
    V3_AGENT_READINESS_MAX,
    V3_CONTENT_MAX,
    V3_LLMS_TXT_MAX,
    V3_ROBOTS_MAX,
    V3_SCHEMA_MAX,
    compute_agent_readiness,
    compute_lint_results,
    compute_scores,
)

# ── Helper factories ─────────────────────────────────────────────────────────

AI_BOT_NAMES = [
    "GPTBot", "ChatGPT-User", "Google-Extended",
    "ClaudeBot", "PerplexityBot", "Amazonbot", "OAI-SearchBot",
    "DeepSeek-AI", "Grok", "Meta-ExternalAgent",
    "cohere-ai", "AI2Bot", "ByteSpider",
]


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
    word_count: int = 200,
    has_headings: bool = False,
    has_lists: bool = False,
    has_code_blocks: bool = False,
    waste_pct: float = 50.0,
    raw_tokens: int = 1000,
    clean_tokens: int = 500,
) -> ContentReport:
    return ContentReport(
        word_count=word_count,
        has_headings=has_headings,
        has_lists=has_lists,
        has_code_blocks=has_code_blocks,
        context_waste_pct=waste_pct,
        estimated_raw_tokens=raw_tokens,
        estimated_clean_tokens=clean_tokens,
    )


def _agent_readiness(
    agents_md_score: float = 0,
    markdown_accept_score: float = 0,
    mcp_score: float = 0,
    semantic_score: float = 0,
    x402_score: float = 0,
    nlweb_score: float = 0,
) -> AgentReadinessReport:
    return AgentReadinessReport(
        agents_md=AgentsMdReport(score=agents_md_score),
        markdown_accept=MarkdownAcceptReport(score=markdown_accept_score),
        mcp_endpoint=McpEndpointReport(score=mcp_score),
        semantic_html=SemanticHtmlReport(score=semantic_score),
        x402=X402Report(score=x402_score),
        nlweb=NlwebReport(score=nlweb_score),
    )


# ── V3 Constants ─────────────────────────────────────────────────────────────


def test_v3_constants_values():
    """V3 constants should have the correct values summing to 100."""
    assert V3_CONTENT_MAX == 35
    assert V3_ROBOTS_MAX == 20
    assert V3_SCHEMA_MAX == 20
    assert V3_AGENT_READINESS_MAX == 20
    assert V3_LLMS_TXT_MAX == 5
    # Sum of all V3 maximums should be 100
    total = (
        V3_CONTENT_MAX + V3_ROBOTS_MAX + V3_SCHEMA_MAX
        + V3_AGENT_READINESS_MAX + V3_LLMS_TXT_MAX
    )
    assert total == 100


def test_v2_constants_unchanged():
    """V2 constants remain at their original values."""
    assert CONTENT_MAX == 40
    assert ROBOTS_MAX == 25
    assert SCHEMA_MAX == 25
    assert LLMS_TXT_MAX == 10


# ── compute_agent_readiness() ────────────────────────────────────────────────


def test_compute_agent_readiness_all_scores():
    """All sub-scores populated → correct aggregate score and detail."""
    ar = _agent_readiness(
        agents_md_score=5,
        markdown_accept_score=5,
        mcp_score=4,
        semantic_score=3,
        x402_score=2,
        nlweb_score=1,
    )
    result = compute_agent_readiness(ar)
    assert result.score == 20  # 5+5+4+3+2+1 = 20, capped at 20
    assert "AGENTS.md=5" in result.detail
    assert "MD-Accept=5" in result.detail
    assert "MCP=4" in result.detail
    assert "Semantic=3" in result.detail
    assert "x402=2" in result.detail
    assert "NLWeb=1" in result.detail


def test_compute_agent_readiness_some_scores():
    """Only some sub-scores populated → only those appear in detail."""
    ar = _agent_readiness(agents_md_score=5, mcp_score=4)
    result = compute_agent_readiness(ar)
    assert result.score == 9
    assert "AGENTS.md=5" in result.detail
    assert "MCP=4" in result.detail
    assert "MD-Accept" not in result.detail
    assert "Semantic" not in result.detail
    assert "x402" not in result.detail
    assert "NLWeb" not in result.detail


def test_compute_agent_readiness_none_scores():
    """All sub-scores zero → score is 0 and detail says no signals."""
    ar = _agent_readiness()
    result = compute_agent_readiness(ar)
    assert result.score == 0
    assert result.detail == "No agent readiness signals detected"


def test_compute_agent_readiness_capped_at_max():
    """Sub-scores exceeding max → capped at V3_AGENT_READINESS_MAX."""
    ar = _agent_readiness(
        agents_md_score=5,
        markdown_accept_score=5,
        mcp_score=4,
        semantic_score=3,
        x402_score=2,
        nlweb_score=1,
    )
    # Total = 20, exactly at cap
    result = compute_agent_readiness(ar)
    assert result.score == 20

    # Make total exceed 20 by inflating a sub-score
    ar2 = _agent_readiness(
        agents_md_score=5,
        markdown_accept_score=5,
        mcp_score=4,
        semantic_score=3,
        x402_score=2,
        nlweb_score=1,
    )
    ar2.agents_md.score = 10  # Total would be 25 without cap
    result2 = compute_agent_readiness(ar2)
    assert result2.score == 20  # Capped


def test_compute_agent_readiness_returns_same_object():
    """compute_agent_readiness returns the same report object (mutated in-place)."""
    ar = _agent_readiness(agents_md_score=3)
    result = compute_agent_readiness(ar)
    assert result is ar


def test_compute_agent_readiness_single_subscore():
    """Only one sub-score set → detail shows only that one."""
    ar = _agent_readiness(x402_score=2)
    result = compute_agent_readiness(ar)
    assert result.score == 2
    assert result.detail == "x402=2.0"


def test_compute_agent_readiness_float_subscores():
    """Sub-scores can be floats (not just ints)."""
    ar = _agent_readiness(agents_md_score=2.5, mcp_score=1.5)
    result = compute_agent_readiness(ar)
    assert result.score == 4.0
    assert "AGENTS.md=2.5" in result.detail
    assert "MCP=1.5" in result.detail


# ── compute_scores() V2 default unchanged ────────────────────────────────────


def test_v2_default_unchanged_perfect_score():
    """V2 default: all pillars maxed → overall=100, identical to existing behavior."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True, url="https://example.com/llms.txt")
    schema_org = SchemaReport(
        blocks_found=4,
        schemas=[
            SchemaOrgResult(schema_type="Organization", properties=["name"]),
            SchemaOrgResult(schema_type="Article", properties=["headline"]),
            SchemaOrgResult(schema_type="Product", properties=["name"]),
            SchemaOrgResult(schema_type="FAQPage", properties=["mainEntity"]),
        ],
    )
    content = ContentReport(
        word_count=2000,
        has_headings=True,
        has_lists=True,
        has_code_blocks=True,
    )

    r, lt, s, c, overall = compute_scores(robots, llms_txt, schema_org, content)

    assert r.score == 25
    assert lt.score == 10
    assert s.score == 25
    assert c.score == 40
    assert overall == 100


def test_v2_default_zero_score():
    """V2 default: everything missing → overall=0."""
    r, lt, s, c, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
    )
    assert r.score == 0
    assert lt.score == 0
    assert s.score == 0
    assert c.score == 0
    assert overall == 0


def test_v2_default_explicit_param():
    """Passing scoring_version='v2' explicitly is same as default."""
    robots = _robots()
    llms_txt = _llms()
    schema_org = _schema()
    content = _content(word_count=500, has_headings=True)

    r1, lt1, s1, c1, o1 = compute_scores(robots, llms_txt, schema_org, content)
    # Reset scores so we can recompute
    robots2 = _robots()
    llms_txt2 = _llms()
    schema_org2 = _schema()
    content2 = _content(word_count=500, has_headings=True)
    r2, lt2, s2, c2, o2 = compute_scores(
        robots2, llms_txt2, schema_org2, content2, scoring_version="v2"
    )

    assert r1.score == r2.score
    assert lt1.score == lt2.score
    assert s1.score == s2.score
    assert c1.score == c2.score
    assert o1 == o2


def test_v2_ignores_agent_readiness():
    """V2 mode ignores agent_readiness param even if provided."""
    ar = _agent_readiness(agents_md_score=5, mcp_score=4)
    r, lt, s, c, overall = compute_scores(
        _robots(),
        _llms(),
        _schema(),
        _content(word_count=500, has_headings=True),
        scoring_version="v2",
        agent_readiness=ar,
    )
    # Agent readiness should NOT be included in overall
    expected = r.score + lt.score + s.score + c.score
    assert overall == expected


# ── compute_scores() V3 mode ─────────────────────────────────────────────────


def test_v3_perfect_score():
    """V3 mode: all pillars maxed → overall=100."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True, url="https://example.com/llms.txt")
    schema_org = SchemaReport(
        blocks_found=4,
        schemas=[
            SchemaOrgResult(schema_type="Organization", properties=["name"]),
            SchemaOrgResult(schema_type="Article", properties=["headline"]),
            SchemaOrgResult(schema_type="Product", properties=["name"]),
            SchemaOrgResult(schema_type="FAQPage", properties=["mainEntity"]),
        ],
    )
    content = ContentReport(
        word_count=2000,
        has_headings=True,
        has_lists=True,
        has_code_blocks=True,
    )
    ar = _agent_readiness(
        agents_md_score=5,
        markdown_accept_score=5,
        mcp_score=4,
        semantic_score=3,
        x402_score=2,
        nlweb_score=1,
    )
    compute_agent_readiness(ar)

    r, lt, s, c, overall = compute_scores(
        robots, llms_txt, schema_org, content,
        scoring_version="v3",
        agent_readiness=ar,
    )

    # V2 raw scores: robots=25, llms=10, schema=25, content=40
    # V3 scaled: robots=20, llms=5, schema=20, content=35, agent_readiness=20
    assert r.score == 25  # V2 raw unchanged on the report object
    assert lt.score == 10
    assert s.score == 25
    assert c.score == 40
    assert overall == 100


def test_v3_zero_score():
    """V3 mode: everything zero → overall=0."""
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    r, lt, s, c, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    assert overall == 0


def test_v3_scaling_content():
    """V3 scales content from V2 max (40) to V3 max (35)."""
    content = ContentReport(
        word_count=1500,
        has_headings=True,
        has_lists=False,
        has_code_blocks=False,
    )
    # V2 content: 25 (tier) + 7 (heading) = 32
    _, _, _, c, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        content,
    )
    assert c.score == 32

    # Reset content
    content2 = ContentReport(
        word_count=1500,
        has_headings=True,
        has_lists=False,
        has_code_blocks=False,
    )
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    _, _, _, c2, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        content2,
        scoring_version="v3",
        agent_readiness=ar,
    )
    # V3 content scaled: round(32/40 * 35, 1) = 28.0
    assert overall == 28.0


def test_v3_scaling_robots():
    """V3 scales robots from V2 max (25) to V3 max (20)."""
    bots = [
        BotAccessResult(bot="GPTBot", allowed=True, detail=""),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail=""),
    ]
    robots = RobotsReport(found=True, bots=bots)

    r, _, _, _, _ = compute_scores(
        robots,
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
    )
    # V2: round(25 * 1/2, 1) = 12.5
    assert r.score == 12.5

    # Reset
    robots2 = RobotsReport(found=True, bots=[
        BotAccessResult(bot="GPTBot", allowed=True, detail=""),
        BotAccessResult(bot="ClaudeBot", allowed=False, detail=""),
    ])
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        robots2,
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    # V3 robots scaled: round(12.5/25 * 20, 1) = 10.0
    assert overall == 10.0


def test_v3_scaling_schema():
    """V3 scales schema from V2 max (25) to V3 max (20)."""
    schema_org = SchemaReport(
        blocks_found=1,
        schemas=[SchemaOrgResult(schema_type="Article", properties=["headline"])],
    )
    _, _, s, _, _ = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org,
        ContentReport(),
    )
    # V2: base 8 + high_value 5 = 13
    assert s.score == 13

    # Reset
    schema_org2 = SchemaReport(
        blocks_found=1,
        schemas=[SchemaOrgResult(schema_type="Article", properties=["headline"])],
    )
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        schema_org2,
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    # V3 schema scaled: round(13/25 * 20, 1) = 10.4
    assert overall == 10.4


def test_v3_scaling_llms_txt():
    """V3 scales llms.txt from V2 max (10) to V3 max (5)."""
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=True),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    # V2 llms=10, V3 llms: round(10/10 * 5, 1) = 5.0
    assert overall == 5.0


def test_v3_overall_is_sum_of_scaled_pillars():
    """V3 overall = scaled(content) + scaled(robots) + scaled(schema) + scaled(llms) + AR."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True)
    schema_org = SchemaReport(
        blocks_found=1,
        schemas=[SchemaOrgResult(schema_type="Article", properties=["headline"])],
    )
    content = ContentReport(word_count=500, has_headings=True)
    ar = _agent_readiness(agents_md_score=3, mcp_score=2)
    compute_agent_readiness(ar)

    r, lt, s, c, overall = compute_scores(
        robots, llms_txt, schema_org, content,
        scoring_version="v3",
        agent_readiness=ar,
    )

    # Compute expected V3 scores from V2 raw scores
    v3_robots = round(r.score / ROBOTS_MAX * V3_ROBOTS_MAX, 1)
    v3_llms = round(lt.score / LLMS_TXT_MAX * V3_LLMS_TXT_MAX, 1)
    v3_schema = round(s.score / SCHEMA_MAX * V3_SCHEMA_MAX, 1)
    v3_content = round(c.score / CONTENT_MAX * V3_CONTENT_MAX, 1)
    expected = v3_robots + v3_llms + v3_schema + v3_content + ar.score
    assert overall == expected


def test_v3_with_agent_readiness_none():
    """V3 with agent_readiness=None → agent readiness contributes 0."""
    _, _, _, _, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=True),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=None,
    )
    # Only llms.txt contributes: round(10/10 * 5, 1) = 5.0
    assert overall == 5.0


def test_v3_agent_readiness_included_in_overall():
    """V3 overall includes agent readiness score."""
    ar = _agent_readiness(agents_md_score=5, mcp_score=4)
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    # Only AR contributes: 5 + 4 = 9
    assert overall == 9


def test_v3_max_scores_sum_to_100():
    """When all pillars are at their V2 max, V3 overall should be 100."""
    bots = [BotAccessResult(bot=name, allowed=True, detail="Allowed") for name in AI_BOT_NAMES]
    robots = RobotsReport(found=True, bots=bots)
    llms_txt = LlmsTxtReport(found=True)
    schema_org = SchemaReport(
        blocks_found=4,
        schemas=[
            SchemaOrgResult(schema_type="Article", properties=[]),
            SchemaOrgResult(schema_type="FAQPage", properties=[]),
            SchemaOrgResult(schema_type="Product", properties=[]),
            SchemaOrgResult(schema_type="Organization", properties=[]),
        ],
    )
    content = ContentReport(
        word_count=2000,
        has_headings=True,
        has_lists=True,
        has_code_blocks=True,
    )
    ar = _agent_readiness(
        agents_md_score=5,
        markdown_accept_score=5,
        mcp_score=4,
        semantic_score=3,
        x402_score=2,
        nlweb_score=1,
    )
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        robots, llms_txt, schema_org, content,
        scoring_version="v3",
        agent_readiness=ar,
    )
    assert overall == 100


# ── compute_lint_results() V3 ────────────────────────────────────────────────


def test_lint_v2_default_no_agent_readiness_check():
    """V2 lint: no Agent Readiness check in the list."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0)
    )
    names = [c.name for c in result.checks]
    assert "Agent Readiness" not in names
    assert len(result.checks) == 4


def test_lint_v3_with_agent_readiness_pass():
    """V3 lint: Agent Readiness check is added when score > 0."""
    ar = _agent_readiness(agents_md_score=5, mcp_score=4)
    compute_agent_readiness(ar)

    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v3",
        agent_readiness=ar,
    )
    names = [c.name for c in result.checks]
    assert "Agent Readiness" in names
    ar_check = next(c for c in result.checks if c.name == "Agent Readiness")
    assert ar_check.passed is True
    assert ar_check.severity == "pass"
    assert "AGENTS.md=5" in ar_check.detail


def test_lint_v3_with_agent_readiness_fail():
    """V3 lint: Agent Readiness check is warn when score is 0."""
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v3",
        agent_readiness=ar,
    )
    ar_check = next(c for c in result.checks if c.name == "Agent Readiness")
    assert ar_check.passed is False
    assert ar_check.severity == "warn"
    assert "No agent readiness signals detected" in ar_check.detail


def test_lint_v3_agent_readiness_none():
    """V3 lint: agent_readiness=None → no Agent Readiness check added."""
    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v3",
        agent_readiness=None,
    )
    names = [c.name for c in result.checks]
    assert "Agent Readiness" not in names
    assert len(result.checks) == 4


def test_lint_v3_has_5_checks_with_ar():
    """V3 lint with agent_readiness → 5 checks total."""
    ar = _agent_readiness(agents_md_score=5)
    compute_agent_readiness(ar)

    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v3",
        agent_readiness=ar,
    )
    assert len(result.checks) == 5


def test_lint_v2_explicit_no_agent_readiness():
    """V2 lint explicitly: no Agent Readiness check even if AR provided."""
    ar = _agent_readiness(agents_md_score=5)
    compute_agent_readiness(ar)

    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v2",
        agent_readiness=ar,
    )
    names = [c.name for c in result.checks]
    assert "Agent Readiness" not in names
    assert len(result.checks) == 4


def test_lint_v3_passed_considers_agent_readiness():
    """V3 lint: overall passed reflects Agent Readiness check too."""
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    result = compute_lint_results(
        _robots(), _llms(), _schema(), _content(waste_pct=30.0),
        scoring_version="v3",
        agent_readiness=ar,
    )
    # Agent Readiness fails (score=0), so overall should fail
    assert result.passed is False


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_v3_zero_v2_scores_only_ar_contributes():
    """V3 with all V2 pillars zero but AR populated → only AR contributes."""
    ar = _agent_readiness(agents_md_score=5, semantic_score=3)
    compute_agent_readiness(ar)

    _, _, _, _, overall = compute_scores(
        RobotsReport(found=False),
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    assert overall == 8  # 5 + 3


def test_v3_partial_robots_scaling():
    """V3: partial robots score scales proportionally."""
    # 7 of 13 bots allowed
    bots = [
        BotAccessResult(bot=AI_BOT_NAMES[i], allowed=(i < 7), detail="test")
        for i in range(13)
    ]
    robots = RobotsReport(found=True, bots=bots)
    ar = _agent_readiness()
    compute_agent_readiness(ar)

    r, _, _, _, overall = compute_scores(
        robots,
        LlmsTxtReport(found=False),
        SchemaReport(),
        ContentReport(),
        scoring_version="v3",
        agent_readiness=ar,
    )
    v2_robots = round(25 * 7 / 13, 1)
    assert r.score == v2_robots
    v3_robots = round(v2_robots / ROBOTS_MAX * V3_ROBOTS_MAX, 1)
    assert overall == v3_robots
