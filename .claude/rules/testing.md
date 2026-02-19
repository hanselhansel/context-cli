# Testing Rules

## TDD Cycle (Mandatory)
1. Write comprehensive tests FIRST for every new feature
2. Implement minimum code to pass all tests
3. Verify: `pytest tests/ -q --cov=aeo_cli --cov-fail-under=100`
4. If coverage < 100%, write more tests before proceeding

## Coverage Requirements
- 100% test coverage is mandatory — enforced by Stop and TaskCompleted hooks
- Every new function, class, and feature MUST have corresponding tests
- Test edge cases, error paths, and boundary conditions
- If adding code drops coverage below 100%, write additional tests before moving on

## Browser Verification (Claude in Chrome)
Use `mcp__claude-in-chrome__*` tools to verify features against real websites:
- After building retail parsers: verify against real product pages
- After audit changes: verify against real site robots.txt/llms.txt/schema.org
- Save real HTML snapshots to `tests/fixtures/` for reproducible regression tests

## Test Organization
- One test file per module: `test_<module>.py`
- Edge case files: `test_<topic>_edge_cases.py`
- Use pytest fixtures for shared setup
- Use `pytest.mark.asyncio` for async tests
- Real HTML snapshots go in `tests/fixtures/retail/` or `tests/fixtures/audit/`

## Never
- Skip tests to "speed things up"
- Mark tests as `xfail` without a tracked issue
- Reduce coverage threshold below 100%
- Move on to the next feature with failing tests
