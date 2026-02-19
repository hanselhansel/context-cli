# Contributing to Context CLI

Thanks for your interest in contributing to Context CLI! This guide will help you get set up and submit your first pull request.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git

### Install

```bash
git clone https://github.com/hanselhansel/context-cli.git
cd context-cli
pip install -e ".[dev]"
```

Context CLI uses a headless browser (via [crawl4ai](https://github.com/unclecode/crawl4ai)) for content extraction. After installing, set it up:

```bash
crawl4ai-setup
```

### Verify your setup

```bash
context-cli lint example.com --single
```

## Running Tests

```bash
pytest tests/ -v
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`, so async test functions work without extra decorators.

## Linting

We use [Ruff](https://docs.astral.sh/ruff/) for linting (line-length 100, Python 3.10 target):

```bash
ruff check src/ tests/
```

Fix auto-fixable issues:

```bash
ruff check --fix src/ tests/
```

## Project Architecture

```
src/context_cli/
├── main.py              # Typer CLI (thin wrapper)
├── server.py            # FastMCP server (thin wrapper)
└── core/
    ├── models.py        # Pydantic v2 data contracts
    ├── auditor.py       # Audit orchestration + scoring
    ├── crawler.py       # crawl4ai headless browser wrapper
    └── discovery.py     # Sitemap/spider page discovery
```

Key design principles:

- **`auditor.py`** is the core entry point -- both CLI and MCP server call `audit_url()` / `audit_site()`
- **`models.py`** defines all data contracts as Pydantic models with `Field(description=...)` on every field
- **Async-first** -- core logic is async; the CLI bridges with `asyncio.run()`
- **Errors don't crash** -- all errors are captured in `AuditReport.errors`

## Code Style

- **Ruff** for linting and formatting (config in `pyproject.toml`)
- **Line length**: 100 characters
- **Async-first**: use `async`/`await` for I/O operations
- **Pydantic models**: add `Field(description=...)` on all model fields -- these propagate to MCP tool schemas
- **Type hints**: use modern Python syntax (`list[str]`, `str | None`, not `List[str]`, `Optional[str]`)
- **src-layout**: all source code lives under `src/context_cli/`

## Submitting a Pull Request

1. **Fork** the repository and clone your fork
2. **Create a branch** for your change:
   ```bash
   git checkout -b your-feature-name
   ```
3. **Make your changes** -- keep PRs focused on a single concern
4. **Run tests and lint** before committing:
   ```bash
   pytest tests/ -v
   ruff check src/ tests/
   ```
5. **Commit** with a clear message describing what and why
6. **Push** to your fork and open a Pull Request against `main`

### PR Guidelines

- Keep PRs small and focused -- one feature or fix per PR
- Add tests for new functionality
- Update documentation if your change affects user-facing behavior
- Ensure all tests pass and linting is clean
- Describe what the PR does and why in the PR description

## Adding a New Lint Pillar

If you're adding a new scoring pillar:

1. Add the Pydantic model to `core/models.py`
2. Add the check function to `core/auditor.py`
3. Wire it into `compute_scores()` and update `audit_url()`
4. Add it to the CLI display in `main.py`
5. Add it to the MCP tool response in `server.py`
6. Add tests in `tests/`
7. Update `docs/scoring.md` with the new pillar's methodology

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/hanselhansel/context-cli/issues) with:

- A clear description of the problem or suggestion
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Your Python version and OS

## License

By contributing to Context CLI, you agree that your contributions will be licensed under the MIT License.
