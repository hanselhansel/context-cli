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

# 2. Type check (with cache cleanup to prevent corruption)
echo "--- Stop gate: checking types ---"
python3 -c "import shutil; shutil.rmtree('.mypy_cache', True)" 2>/dev/null
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

# 6. README freshness advisory (non-blocking but visible)
CHANGED_FEATURES=$(git log --oneline HEAD~10..HEAD 2>/dev/null | grep -c "^.*feat:" || true)
if [[ "$CHANGED_FEATURES" -gt 3 ]]; then
    README_UPDATED=$(git log --oneline HEAD~10..HEAD -- README.md 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$README_UPDATED" -eq 0 ]]; then
        echo "WARNING: $CHANGED_FEATURES features committed but README.md not updated."
        echo "  Consider updating README to reflect new features."
    fi
fi

# 7. File size advisory (non-blocking)
LARGE_FILES=$(find src/ -name "*.py" -exec wc -l {} + 2>/dev/null | \
    awk '$1 > 400 && !/total$/ {print "  " $1 " lines: " $2}' | sort -rn)
if [[ -n "$LARGE_FILES" ]]; then
    echo "WARNING: Source files over 400 lines (consider splitting):"
    echo "$LARGE_FILES"
fi

echo "--- Stop gate: all checks passed ---"
exit 0
