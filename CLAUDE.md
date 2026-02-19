# AEO-CLI v0.12.0 — CRITICAL CONTEXT

Scoring: Content=40 | Robots=25 | Schema=25 | llms.txt=10 (total=100)
Bots: GPTBot, ChatGPT-User, Google-Extended, ClaudeBot, PerplexityBot, Amazonbot, OAI-SearchBot + 6 more
Commands: `pytest` | `ruff check src/ tests/` | `mypy src/` | `make ci`
CURRENT PHASE: 1.0.0 (GA — all features complete)
AGENT TEAMS: MANDATORY for ALL phases. No exceptions. See "Agent Teams" section below.

## Session Workflow (MANDATORY — enforced by hooks)
1. **TEST** — Write comprehensive tests FIRST (TDD, 100% coverage)
2. **CODE** — Implement minimum to pass tests
3. **REFACTOR** — Clean up: split large files (>300 LOC), extract modules, simplify
4. **LINT** — Auto-lint via PostToolUse hook on every file change
5. **VERIFY** — `pytest --cov=aeo_cli --cov-fail-under=100` (100% mandatory)
6. **COMMIT** — `git add` + `git commit` + `git push origin main` (every green feature)
6.5. **README** — If releasing a version: update README Features, CLI Usage, and Bots sections
7. **VERSION** — Patch bump + tag + push when feature is significant
8. **CONTEXT** — Check /context; if >70% → `/compact`
8.5. **AGENTS** — If session resumes with active worktrees: check agent branches for commits, merge completed work, clean up worktrees

## Versioning
Minor bump per phase: 0.3.0(A1) → 0.4.0(A2) → 0.5.0(A3) → 0.6.0(A4) → 0.7.0(B0) → 0.8.0(B1) → 0.9.0(B2) → 0.10.0(B3) → 0.11.0(B4) → 0.12.0(B5) → 1.0.0
Patch within phases (0.3.1, 0.3.2, ...). Every `v*` tag auto-publishes to PyPI.

--- END CRITICAL HEADER (above MUST survive compaction) ---

## Tech Stack
- **Language**: Python 3.10+
- **CLI**: Typer + Rich
- **HTTP**: httpx (async) with retry logic
- **HTML parsing**: BeautifulSoup4
- **Crawling**: crawl4ai (headless browser)
- **Data models**: Pydantic v2
- **MCP server**: FastMCP
- **Testing**: pytest + pytest-asyncio + pytest-cov
- **Linting**: Ruff (line-length=100)
- **Type checking**: mypy (with Pydantic plugin)
- **CI**: GitHub Actions (test + lint + mypy, Python 3.10/3.11/3.12 matrix)

## Architecture
```
CLI (main.py)  ←→  MCP Server (server.py)
      └────────┬───────────┘
         audit_url() in auditor.py
        ╱       │       ╲
  crawler.py  auditor.py  models.py
                │
  formatters/   core/
  ├── csv.py    ├── cache.py     # Robots.txt caching
  └── markdown  ├── retry.py     # HTTP retry with backoff
                └── discovery.py
```
- `models.py` defines ALL data contracts (Pydantic) + OutputFormat enum + RetryConfig
- `auditor.py` is the core entry point: `audit_url(url) → AuditReport`
- `main.py` and `server.py` are thin wrappers around `audit_url()`
- `formatters/` provides CSV and Markdown output alternatives

## Project Structure
```
src/aeo_cli/
├── __init__.py          # Package version
├── py.typed             # PEP 561 typed marker
├── main.py              # Typer CLI (entry point: aeo-cli)
├── server.py            # FastMCP server
├── formatters/
│   ├── csv.py           # CSV output formatter
│   └── markdown.py      # Markdown output formatter
└── core/
    ├── models.py        # Pydantic models + enums
    ├── auditor.py       # Audit orchestration + scoring
    ├── crawler.py       # crawl4ai wrapper
    ├── cache.py         # Robots.txt caching
    ├── retry.py         # HTTP retry with backoff
    └── discovery.py     # Sitemap/spider page discovery
tests/
├── test_*.py            # Unit + integration tests
├── fixtures/
│   ├── retail/          # Real HTML from Shopee, Lazada, etc.
│   └── audit/           # Real robots.txt, llms.txt, schema.org snapshots
docs/
├── scoring.md           # Scoring methodology
├── mcp-integration.md   # MCP server usage guide
└── long-running-session-plan.md  # Full roadmap (source of truth)
```

## Conventions
- Async-first: core logic is async, CLI bridges with `asyncio.run()`
- All errors captured in `AuditReport.errors`, never crash the audit
- Pydantic `Field(description=...)` on all model fields (propagates to MCP schemas)
- src-layout packaging
- Ruff for linting (line-length=100)
- mypy for type checking (check_untyped_defs=true)
- pytest-cov for coverage reporting (100% mandatory)

## Commands
```bash
pip install -e ".[dev]"              # Install with dev deps
crawl4ai-setup                       # Install browser for crawl4ai
pytest                               # Run tests (with coverage)
ruff check src/ tests/               # Lint
mypy src/                            # Type check
make ci                              # Run lint + typecheck + tests
aeo-cli audit <url>                  # Multi-page site audit (Rich output)
aeo-cli audit <url> --single         # Single-page audit
aeo-cli audit <url> --json           # JSON output
aeo-cli audit <url> --format csv     # CSV output
aeo-cli audit <url> --format markdown # Markdown output
aeo-cli audit <url> --verbose        # Detailed pillar breakdown
aeo-cli audit <url> --quiet          # Silent mode (exit code only)
aeo-cli mcp                          # Start MCP stdio server
```

## Hook Infrastructure
| Hook | Event | Purpose |
|------|-------|---------|
| `auto-lint.sh` | PostToolUse (Edit\|Write) | Ruff auto-fix on every Python file change |
| `commit-push-reminder.sh` | PostToolUse (Bash) | Reminds to push after git commit |
| `stop-gate.sh` | Stop | Full CI gate: lint + types + tests + 100% coverage + committed + pushed |
| `task-complete-gate.sh` | TaskCompleted | CI gate before marking tasks done |
| `session-start.sh` | SessionStart | Load version, branch, phase context |
| `pre-compact.sh` | PreCompact | Re-inject critical context before compaction |
| `teammate-idle-gate.sh` | TeammateIdle | Quality gate for agent team members |

## Commit Format
```
<type>: <short description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`

## Version Bump Workflow
1. Update `version` in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `chore: release v{version}`
4. Tag: `git tag v{version}`
5. Push: `git push origin main --tags`
6. GitHub Actions auto-publishes to PyPI + creates GitHub Release

## Phase Roadmap
| Phase | Version | Status | Description |
|-------|---------|--------|-------------|
| A1 | 0.3.0 | DONE | Strengthen core: new bots, llms-full.txt, schema weighting, readability, batch |
| A2 | 0.4.0 | DONE | Intelligence: RSL, IETF, E-E-A-T, compare, SQLite history, regression |
| A3 | 0.5.0 | DONE | Ecosystem: config file, MCP expansion, plugin arch, webhooks, HTML report, watch |
| A4 | 0.6.0 | DONE | Polish: docs, CHANGELOG, benchmarks, Docker |
| B0 | 0.7.0 | DONE | Shared infra: core/llm.py, core/cost.py |
| B1 | 0.8.0 | DONE | CI/CD: per-pillar thresholds, baselines, webhooks |
| B2 | 0.9.0 | DONE | Batch generate: llms.txt + JSON-LD generation |
| B3 | 0.10.0 | DONE | Citation radar: multi-model citation extraction |
| B4 | 0.11.0 | DONE | Benchmark: Share-of-Recommendation tracking |
| B5 | 0.12.0 | DONE | Retail: 8 marketplace parsers, retail scoring |
| Final | 1.0.0 | DONE | All features complete, fully documented |

Details: `docs/long-running-session-plan.md`

## Agent Teams (MANDATORY for ALL phases — NO EXCEPTIONS)
Every phase MUST use agent teams with git worktree isolation. Never go solo.
Decompose work into 2+ independent file domains per phase. If work seems too small
for a team, split it further — the coordination overhead is worth the consistency.

| Phase | Team Size | Division |
|-------|-----------|----------|
| A1 | 3 | bots+llms, schema+content, batch+config |
| A2 | 2-3 | citation+compare, history+regression, RSL+IETF |
| A3 | 2-3 | config+plugin, MCP+webhooks, report+watch |
| A4 | 2 | docs+dockerfile, scoring-docs+ci-docs |
| B0 | 2 | core/llm.py+tests, core/cost.py+tests |
| B1 | 2 | ci/thresholds+tests, ci/baseline+action.yml+tests |
| B2 | 2 | batch-generation+tests, batch-cli+integration |
| B3 | 3 | query+parser, analyzer+domains, CLI+MCP |
| B4 | 3 | loader+dispatcher, judge+metrics, cost+CLI |
| B5 | 4 | 2 parsers each, scoring+auditor, CLI+MCP |

## Agent Team Worktree Protocol
When spawning agent teams, ALWAYS use git worktrees for isolation:
1. Create a worktree per agent: `git worktree add ../aeo-cli-{name} -b {name}/{feature} main`
2. Install deps: `cd ../aeo-cli-{name} && pip install -e ".[dev]"`
3. Spawn each agent as a separate session in its worktree directory
4. Agents commit+push to their own branches only
5. Leader merges branches to main after all agents complete
6. Cleanup: `git worktree remove` + `git worktree prune`
See `.claude/rules/agent-teams.md` for full protocol.
