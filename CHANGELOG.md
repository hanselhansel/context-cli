# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-19

### Added

- **AEO Compiler (`generate` command)**: LLM-powered generation of `llms.txt` and `schema.jsonld` files from any URL
  - Auto-detects LLM provider from environment (OpenAI, Anthropic, Ollama)
  - Industry profiles for prompt tuning: generic, cpg, saas, ecommerce, blog
  - `--model`, `--profile`, `--output-dir`, and `--json` options
  - Available as optional dependency: `pip install aeo-cli[generate]`
- **CI/CD Integration**:
  - `--fail-under N` flag: exit code 1 if score < N
  - `--fail-on-blocked-bots` flag: exit code 2 if any AI bot is blocked
  - Automatic GitHub Step Summary when `$GITHUB_STEP_SUMMARY` is set
  - Backwards-compatible `--quiet` mode (default threshold 50)
- **GitHub Action** (`action.yml`): Composite action for CI pipelines with inputs for url, fail-under, python-version, max-pages
- **MCP generate tool**: Exposes `generate_assets()` as an MCP tool for AI agent integration
- **CI summary formatter** (`formatters/ci_summary.py`): Markdown table output for GitHub Step Summary
- Example workflows in `.github/examples/` for basic, preview deploy, and inline usage
- Comprehensive CI integration documentation in `docs/ci-integration.md`

### Fixed

- **CI failure**: FastMCP version compatibility in `test_mcp_server.py` — `@mcp.tool` returns either a `FunctionTool` wrapper (with `.fn`) or the raw function depending on version; added `hasattr` guard to work with all FastMCP 2.x releases

### Changed

- Refactored audit command into `_run_audit()`, `_render_output()`, `_check_exit_conditions()` helpers for cleaner CI integration
- Test suite expanded from 239 to 308 tests, achieving **100% code coverage** across all 18 source files

## [0.1.0] - 2026-02-18

### Added

- Core audit engine with 4-pillar scoring: content density, robots.txt AI bot access, schema.org JSON-LD, and llms.txt presence
- Multi-page site audit with sitemap/spider discovery and depth-weighted score aggregation
- CLI via Typer with Rich output, including `--json`, `--format` (csv/markdown), `--verbose`, `--quiet`, and `--single` flags
- FastMCP server for AI agent integration via stdio transport
- HTTP retry with exponential backoff for resilient network requests
- Robots.txt response caching across multi-page audits
- Comprehensive test suite with edge-case coverage for all scoring pillars
- CI via GitHub Actions with Python 3.10/3.11/3.12 matrix, ruff linting, mypy type checking, and pytest with coverage
- Full type annotations across all modules with PEP 561 `py.typed` marker
- Documentation: scoring methodology, MCP integration guide, and CONTRIBUTING.md
- Pre-commit hooks configuration for code quality
- MIT license and PyPI-ready `pyproject.toml` metadata
