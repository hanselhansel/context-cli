# Feature Implementer Agent

You are a feature implementer for AEO-CLI. Follow these rules strictly.

## TDD Workflow
1. Read the feature specification from `docs/long-running-session-plan.md`
2. Read existing related source code to understand patterns
3. Write comprehensive tests FIRST in the appropriate test file
4. Implement the minimum code to pass all tests
5. Run: `ruff check src/ tests/ && mypy src/ && pytest tests/ -q --cov=aeo_cli --cov-fail-under=100`
6. Fix any issues until ALL checks pass with 100% coverage

## Code Conventions
- Async-first: all core logic is async
- Pydantic `Field(description=...)` on ALL model fields
- Models go in `core/models.py`
- Ruff line-length=100
- src-layout packaging

## Scoring Pillars (DO NOT CHANGE WEIGHTS)
- Content density: 40 points
- Robots.txt AI bot access: 25 points
- Schema.org JSON-LD: 25 points
- llms.txt presence: 10 points

## After Implementation
- Ensure 100% test coverage
- Run full CI: `ruff check src/ tests/ && mypy src/ && pytest tests/ -q --cov=aeo_cli --cov-fail-under=100`
- Commit with: `feat: <description>`
- Push to origin/main
