#!/usr/bin/env bash
# SessionStart hook: Load project context on session start/resume/compact

set -uo pipefail

cd "$CLAUDE_PROJECT_DIR"

VERSION=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
" 2>/dev/null || echo "unknown")

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo "=== AEO-CLI Session Context ==="
echo "Version: $VERSION"
echo "Branch: $BRANCH"
echo ""
echo "Recent commits:"
git log --oneline -5 2>/dev/null || echo "  (no commits)"
echo ""

# Show current phase status from CLAUDE.md
if grep -q "CURRENT PHASE" CLAUDE.md 2>/dev/null; then
    echo "Phase status:"
    grep -A 3 "CURRENT PHASE" CLAUDE.md 2>/dev/null || true
    echo ""
fi

# Show any uncommitted changes
CHANGES=$(git status --short 2>/dev/null)
if [[ -n "$CHANGES" ]]; then
    echo "Uncommitted changes:"
    echo "$CHANGES"
    echo ""
fi

echo "=== Ready to work ==="
exit 0
