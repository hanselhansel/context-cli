#!/usr/bin/env bash
# TeammateIdle hook: Quality gate for agent team members
# Prevents teammates from going idle with broken CI
#
# Exit codes:
#   0 = allow idle (all checks pass)
#   2 = block idle (force teammate to fix issues)

set -uo pipefail

cd "$CLAUDE_PROJECT_DIR"

# 1. Lint check
if ! ruff check src/ tests/ >/dev/null 2>&1; then
    echo "BLOCKED: Lint errors. Fix before going idle." >&2
    exit 2
fi

# 2. Tests + 100% coverage
if ! python3 -m pytest tests/ -q --tb=short --cov=context_cli --cov-fail-under=100 >/dev/null 2>&1; then
    echo "BLOCKED: Tests failing or coverage < 100%. Fix before going idle." >&2
    exit 2
fi

exit 0
