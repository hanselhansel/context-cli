#!/usr/bin/env bash
# PreCompact hook: Re-inject critical context before compaction
# Outputs the most important project state so it survives context compression

set -uo pipefail

cd "$CLAUDE_PROJECT_DIR"

echo "=== CRITICAL CONTEXT (preserve across compaction) ==="
echo ""

# Re-inject the anti-compaction header from CLAUDE.md (first 40 lines)
head -40 CLAUDE.md 2>/dev/null || true
echo ""

echo "=== CURRENT PROJECT STATE ==="
VERSION=$(python3 -c "
import tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
" 2>/dev/null || echo "unknown")
echo "Version: $VERSION"
echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
echo "Last commit: $(git log --oneline -1 2>/dev/null || echo 'none')"
echo ""

# Show phase status
if grep -q "CURRENT PHASE" CLAUDE.md 2>/dev/null; then
    grep -A 5 "CURRENT PHASE" CLAUDE.md 2>/dev/null || true
fi

echo "=== END CRITICAL CONTEXT ==="
exit 0
