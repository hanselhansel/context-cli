# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
