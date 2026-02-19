#!/usr/bin/env bash
# PostToolUse hook: Auto-lint Python files after Edit/Write
# Non-blocking — reports issues but always exits 0

set -uo pipefail

INPUT=$(cat)

# Extract file path from tool input JSON
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

# Only lint Python files
if [[ "$FILE_PATH" == *.py ]]; then
    cd "$CLAUDE_PROJECT_DIR"
    OUTPUT=$(ruff check --fix "$FILE_PATH" 2>&1) || true
    if [[ -n "$OUTPUT" ]]; then
        echo "$OUTPUT"
    fi
fi

exit 0
