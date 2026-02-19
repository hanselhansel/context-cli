# Agent Team Rules

## File Ownership (CRITICAL)
- Before spawning agents, map EVERY task to the specific files it will modify
- Assign file ownership so NO file is edited by more than one agent
- If two tasks need the same file, either:
  a. Assign both tasks to the same agent, OR
  b. Make one task block the other (sequential, not parallel)
- The leader MUST declare file ownership in each agent's spawn prompt

## Task Description Format
Every task MUST include:
```
OWNED FILES (only these may be edited):
- src/aeo_cli/core/checks/robots.py
- tests/test_robots.py
DO NOT EDIT: auditor.py, main.py, models.py (owned by lead)
```

## Task Decomposition Strategy
- Decompose by MODULE/FILE, not by feature
- Example (WRONG): Agent A = "add bots", Agent B = "add batch mode" (both touch main.py)
- Example (RIGHT): Agent A = "all changes to robots.py + test_robots.py", Agent B = "all changes to batch.py + test_batch.py"
- Shared files (models.py, auditor.py, main.py) should be assigned to ONE agent or the leader

## Shared File Protocol
- Files edited by multiple features (models.py, main.py, auditor.py) are "shared files"
- Shared files MUST be edited by the leader AFTER all agents complete, OR assigned to exactly one agent
- Agents must NEVER edit files outside their assigned ownership set

## mypy Cache Safety
- Only ONE agent (or the leader) should run mypy at a time
- Agents should run `ruff check` and `pytest` but skip mypy in their verification
- The leader runs the full CI gate (`make ci` including mypy) after merging all agent work
- The stop-gate clears `.mypy_cache` before running mypy to prevent corruption

## Commit Coordination
- Each agent commits and pushes its own files immediately after green tests
- `git add` specific files by name (never `git add .` or `git add -A`)
- Before editing, agents should `git pull --rebase` to get latest changes
- If a rebase conflict occurs, the agent should stop and notify the leader

## When NOT to Use Agent Teams
- Tasks that all touch the same 2-3 files -> use sequential subagents or do it solo
- Tasks with heavy cross-file dependencies -> solo is faster
- Fewer than 3 independent file domains -> overhead exceeds benefit

## When to Use Teams vs Subagents vs Solo
- **Teams (3+ agents)**: Work is on DIFFERENT files with no overlap
- **Subagents**: Quick research, verification, or read-only exploration
- **Solo**: Tasks that touch shared files (main.py, models.py, auditor.py)
