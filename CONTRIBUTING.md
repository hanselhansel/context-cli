# Contributing to Context CLI

Thanks for your interest in contributing to Context CLI! This guide will help you get set up and submit your first pull request.

## Philosophy

These principles guide all code in the project:

- **Async-first** — all I/O uses `async`/`await`. The CLI bridges to sync with `asyncio.run()`.
- **Pydantic-first** — every data contract is a Pydantic model with `Field(description=...)` on every field. These propagate to MCP tool schemas automatically.
- **Errors don't crash** — exceptions during audits are captured in `AuditReport.errors`, not raised to the caller.
- **CLI is a thin wrapper** — core logic lives in `core/`. Both the Typer CLI (`main.py`) and the MCP server (`server.py`) are thin wrappers that delegate to the same core functions.

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

Run tests with coverage:

```bash
make coverage
```

Run a single test by name:

```bash
pytest tests/test_auditor.py -k "test_name" -v
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"`, so async test functions work without extra decorators. You do not need to add `@pytest.mark.asyncio` — any `async def test_*` function is automatically detected.

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

### Data Flow

```
CLI input (url)          MCP request (url)
       \                      /
        v                    v
    main.py              server.py
        \                  /
         v                v
       auditor.py  (orchestration)
          |
          v
       discovery.py  (find pages: sitemap, spider)
          |
          v
       crawler.py  (fetch & extract via headless browser)
          |
          v
       auditor.py  (scoring & pillar checks)
          |
          v
       models.py  (AuditReport Pydantic model)
          |
          v
   CLI text output       MCP JSON response
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

## Commit Conventions

Use the format `type: description` (lowercase, imperative mood).

Allowed types:

| Type | Use for |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `ci` | CI/CD configuration |
| `chore` | Maintenance, deps, tooling |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `style` | Formatting, whitespace, linting (no logic change) |
| `perf` | Performance improvement |

Keep commits atomic — one logical change per commit. Write the subject line in imperative mood ("add feature", not "added feature").

## Adding a New Lint Pillar

If you're adding a new scoring pillar:

1. Add the Pydantic model to `core/models.py`
2. Add the check function to `core/auditor.py`
3. Wire it into `compute_scores()` and update `audit_url()`
4. Add it to the CLI display in `main.py`
5. Add it to the MCP tool response in `server.py`
6. Add tests in `tests/`
7. Update `docs/scoring.md` with the new pillar's methodology

## Release Process

Context CLI follows [semantic versioning](https://semver.org/) (major.minor.patch).

1. The canonical version lives in `pyproject.toml` under `[project] version`.
2. To cut a release:
   ```bash
   make release VERSION=x.y.z
   ```
   This bumps the version, creates a git tag, and pushes to origin.
3. Publishing to PyPI is automated via GitHub Actions — a workflow triggers on new version tags and builds + publishes the package.

When choosing a version number:
- **Patch** (0.1.0 -> 0.1.1) — bug fixes, docs, internal refactors
- **Minor** (0.1.1 -> 0.2.0) — new features, new lint pillars, new CLI flags
- **Major** (0.2.0 -> 1.0.0) — breaking changes to CLI interface or MCP tool schemas

## Testing MCP Tools

Context CLI exposes its audit functionality as MCP (Model Context Protocol) tools. To test them locally:

1. Start the MCP server:
   ```bash
   context-cli mcp
   ```
2. Connect with any MCP-compatible client — for example, add it to Claude Desktop's config or use a standalone MCP client.
3. MCP tool definitions live in `server.py`. When you change tool signatures or descriptions, verify that the updated schema appears correctly in the client.

Automated tests for the MCP layer run as part of the normal test suite (`pytest tests/ -v`), but manual testing with a real MCP client is recommended for schema and end-to-end validation.

## Good First Issues

New to the project? Look for issues labeled [`good first issue`](https://github.com/hanselhansel/context-cli/labels/good%20first%20issue) on GitHub. Great starting points include:

- Adding or improving **tests** for existing functionality
- Fixing **typos** or improving **documentation**
- Small **bug fixes** with a clear reproduction path

Pick one, comment that you're working on it, and open a PR when ready.

## Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/hanselhansel/context-cli/issues) with:

- A clear description of the problem or suggestion
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Your Python version and OS

## License

By contributing to Context CLI, you agree that your contributions will be licensed under the MIT License.
