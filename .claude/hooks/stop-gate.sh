#!/usr/bin/env bash
# Stop hook: Full CI verification gate before allowing Claude to stop
#
# Exit codes:
#   0 = allow stop (all checks pass or safety valve triggered)
#   2 = block stop (force Claude to continue fixing issues)
#
# Safety valve: if stop_hook_active is true (Claude already continued from
# a previous stop-gate failure), allow stop to prevent infinite loops.

set -uo pipefail

cd "$CLAUDE_PROJECT_DIR"

INPUT=$(cat)

# Safety valve: prevent infinite loops
STOP_HOOK_ACTIVE=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(str(data.get('stop_hook_active', False)).lower())
" 2>/dev/null || echo "false")

if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
    exit 0
fi

# 1. Lint check
echo "--- Stop gate: checking lint ---"
if ! ruff check src/ tests/ 2>&1; then
    echo "BLOCKED: Lint errors found. Fix before stopping." >&2
    exit 2
fi

# 2. Type check
echo "--- Stop gate: checking types ---"
if ! mypy src/ 2>&1; then
    echo "BLOCKED: Type errors found. Fix before stopping." >&2
    exit 2
fi

# 3. Tests + 100% coverage
echo "--- Stop gate: running tests ---"
if ! pytest tests/ -q --tb=short --cov=aeo_cli --cov-fail-under=100 2>&1; then
    echo "BLOCKED: Tests failing or coverage below 100%. Fix before stopping." >&2
    exit 2
fi

# 4. Uncommitted Python changes
if [[ -n $(git status --short -- '*.py' 2>/dev/null) ]]; then
    echo "BLOCKED: Uncommitted Python changes. Commit and push before stopping." >&2
    exit 2
fi

# 5. Unpushed commits
if [[ -n $(git log origin/main..HEAD --oneline 2>/dev/null) ]]; then
    echo "BLOCKED: Unpushed commits. Push before stopping." >&2
    exit 2
fi

echo "--- Stop gate: all checks passed ---"
exit 0
