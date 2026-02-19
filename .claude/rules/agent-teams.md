# Agent Team Rules

## Isolation Strategy: Git Worktrees (PRIMARY)
Each agent gets its own git worktree = own branch + own working directory.
No two agents ever touch the same filesystem. Merge happens under leader control.

### Worktree Setup (Leader does this BEFORE spawning agents)
1. Create a worktree per agent:
   `git worktree add ../aeo-cli-{agent-name} -b {agent-name}/{feature} main`
2. Install deps in each worktree:
   `cd ../aeo-cli-{agent-name} && pip install -e ".[dev]"`
3. Verify each worktree: `cd ../aeo-cli-{agent-name} && make ci`

### Agent Spawn Protocol
- Each agent is a separate Claude Code session launched in its worktree dir
- Agent's CWD is the worktree root (NOT the main repo)
- Agent commits + pushes to its own branch
- Agent runs ruff + pytest locally; leader runs mypy after merge

### Merge Protocol (Leader does this AFTER all agents complete)
1. Return to main repo: `cd /path/to/aeo-cli`
2. For each agent branch:
   `git merge {agent-name}/{feature} --no-ff`
3. If conflicts: resolve manually or let Claude resolve
4. Run full CI: `make ci`
5. Cleanup worktrees:
   `git worktree remove ../aeo-cli-{agent-name}`
   `git worktree prune`

### Worktree Cleanup
- ALWAYS clean up after merging: `git worktree remove` + `git worktree prune`
- List active worktrees: `git worktree list`
- Remove stale entries: `git worktree prune`

## File Ownership (SECONDARY defense — minimizes merge conflicts)
Even with worktree isolation, assign file ownership to minimize merge pain:
- Map every task to specific files BEFORE spawning
- Assign ownership so minimal file overlap between agents
- Shared files (models.py, main.py, auditor.py) → leader or one agent
- This doesn't prevent conflicts (worktrees do that) but makes merges cleaner

## Task Description Format
Every agent task MUST include:
```
WORKTREE: ../aeo-cli-{agent-name}
BRANCH: {agent-name}/{feature}
OWNED FILES (primary responsibility):
- src/aeo_cli/core/checks/robots.py
- tests/test_robots.py
SHARED FILES (may also touch — merge handled by leader):
- src/aeo_cli/core/models.py
```

## Task Decomposition Strategy
- Decompose by MODULE/FILE, not by feature
- Example (WRONG): Agent A = "add bots", Agent B = "add batch" (both touch main.py)
- Example (RIGHT): Agent A = "robots.py + test_robots.py", Agent B = "batch.py + test_batch.py"

## mypy Cache Safety
- Each worktree has its own .mypy_cache (isolated by default)
- Agents should still skip mypy (faster iteration)
- Leader runs mypy after merge on main

## Commit Coordination
- Each agent commits ONLY to its own worktree branch
- `git add` specific files by name (never `git add .` or `git add -A`)
- Push to remote: `git push origin {agent-name}/{feature}`
- Leader merges to main after all agents complete

## When NOT to Use Agent Teams
- Tasks that all touch the same 2-3 files → solo
- Tasks with heavy cross-file dependencies → solo
- Fewer than 3 independent file domains → overhead exceeds benefit

## When to Use Teams vs Subagents vs Solo
- **Teams (3+ agents, worktrees)**: Work on DIFFERENT files, true isolation needed
- **Subagents**: Quick research, verification, read-only exploration
- **Solo**: Tasks touching shared files (main.py, models.py, auditor.py)
