# Agent Team Rules

## MANDATORY: Agent Teams for ALL Phases
Agent teams are REQUIRED for every phase of the roadmap. No exceptions.
Even phases that seem "too small" (e.g., B0, A4) MUST use 2+ agents.
If the work seems too small for a team, split it into finer-grained file domains.
The consistency of always using teams outweighs any per-phase coordination overhead.

## Isolation Strategy: Git Worktrees (PRIMARY)
Each agent gets its own git worktree = own branch + own working directory.
No two agents ever touch the same filesystem. Merge happens under leader control.

### Worktree Setup (Leader does this BEFORE spawning agents)
1. Create a worktree per agent:
   `git worktree add ../context-cli-{agent-name} -b {agent-name}/{feature} main`
2. Install deps in each worktree:
   `cd ../context-cli-{agent-name} && pip install -e ".[dev]"`
3. Verify each worktree: `cd ../context-cli-{agent-name} && make ci`

### Agent Spawn Protocol
- Each agent is a separate Claude Code session launched in its worktree dir
- Agent's CWD is the worktree root (NOT the main repo)
- Agent commits + pushes to its own branch
- Agent runs ruff + pytest locally; leader runs mypy after merge

### Merge Protocol (Leader does this AFTER all agents complete)
1. Return to main repo: `cd /path/to/context-cli`
2. For each agent branch:
   `git merge {agent-name}/{feature} --no-ff`
3. If conflicts: resolve manually or let Claude resolve
4. Run full CI: `make ci`
5. Cleanup worktrees:
   `git worktree remove ../context-cli-{agent-name}`
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
WORKTREE: ../context-cli-{agent-name}
BRANCH: {agent-name}/{feature}
OWNED FILES (primary responsibility):
- src/context_cli/core/checks/robots.py
- tests/test_robots.py
SHARED FILES (may also touch — merge handled by leader):
- src/context_cli/core/models.py
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

## Recovery Protocol (Session Interruption)
If a session is interrupted while agents are running in worktrees:
1. Check worktrees: `git worktree list`
2. For each worktree, check if agent committed: `git log {branch} --not main --oneline`
3. If committed: merge to main (`git merge {branch} --no-ff`), clean up worktree
4. If not committed: check for uncommitted changes in worktree (`git -C ../context-cli-{name} status`), complete manually
5. Run `make ci` after all merges
6. Clean up: `git worktree remove ../context-cli-{name}` + `git worktree prune`

**Key insight**: Agents in worktrees are independent — their work persists even if the leader session dies. The stop hook skips CI when worktrees are active (main hasn't changed).

## When to Use Teams vs Subagents
- **Teams (2+ agents, worktrees)**: ALWAYS for phase implementation. Decompose to 2+ independent file domains.
- **Subagents**: Quick research, verification, read-only exploration within a session.
- **Solo**: NEVER for phase implementation. Only for single-file hotfixes or urgent patches.
