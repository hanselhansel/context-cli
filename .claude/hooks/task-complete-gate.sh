#!/usr/bin/env bash
# TaskCompleted hook: Verify CI passes before marking tasks done
#
# Exit codes:
#   0 = allow task completion
#   2 = block task completion (CI not green)

set -uo pipefail

cd "$CLAUDE_PROJECT_DIR"

# 1. Lint check
if ! ruff check src/ tests/ >/dev/null 2>&1; then
    echo "BLOCKED: Lint errors. Cannot complete task." >&2
    exit 2
fi

# 2. Type check (use python3 -m to ensure correct Python version)
if ! python3 -m mypy src/ >/dev/null 2>&1; then
    echo "BLOCKED: Type errors. Cannot complete task." >&2
    exit 2
fi

# 3. Tests + 100% coverage
if ! python3 -m pytest tests/ -q --tb=short --cov=context_cli --cov-fail-under=100 >/dev/null 2>&1; then
    echo "BLOCKED: Tests failing or coverage < 100%. Cannot complete task." >&2
    exit 2
fi

exit 0
