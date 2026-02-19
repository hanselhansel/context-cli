#!/usr/bin/env bash
# PostToolUse hook: after Bash commands that include "git commit"
# Checks if there are unpushed commits and reminds to push

cd "$CLAUDE_PROJECT_DIR"
INPUT=$(cat)

# Only trigger on Bash tool
TOOL=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)
if [[ "$TOOL" != "Bash" ]]; then
    exit 0
fi

# Check for unpushed commits
UNPUSHED=$(git log origin/main..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
if [[ "$UNPUSHED" -gt 0 ]]; then
    echo "REMINDER: $UNPUSHED unpushed commit(s). Run: git push origin main"
fi
exit 0
