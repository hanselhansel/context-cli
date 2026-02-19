# Commit Rules

## Micro-Commit Cadence
- Commit + push after EVERY green feature (tests pass + lint clean)
- Never batch multiple features into one commit
- Never leave uncommitted changes when moving to next feature

## Message Format
```
<type>: <short description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Types
- `feat`: New feature or capability
- `fix`: Bug fix
- `refactor`: Code restructuring (no behavior change)
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Release, config, or tooling changes
- `ci`: CI/CD pipeline changes

## Examples
```
feat: add DeepSeek and Grok to AI bot checklist
test: add edge cases for llms-full.txt detection
fix: handle timeout in schema.org extraction
chore: release v0.3.1
refactor: extract retry logic into core/retry.py
```

## Auto-Push
- After every commit: `git push origin main`
- After version bumps: `git push origin main --tags`

## What Gets Committed
- Source code changes (`src/`)
- Test changes (`tests/`)
- Configuration (pyproject.toml, CLAUDE.md)
- Documentation (docs/, CHANGELOG.md)

## Never Commit
- `.env` files or secrets
- `__pycache__/` or `.pyc` files
- `.coverage` or `htmlcov/`
- `node_modules/` or `venv/`

## Refactoring in Commits
- Refactoring is part of the feature, not a separate commit
- If refactoring is substantial (splitting a 500-line file), it MAY be a separate commit BEFORE the feature commit
- Format: `refactor: split auditor.py into per-pillar check modules`
- Never commit unrefactored code that violates the 300-line guideline

## Agent Team Commits
- Each agent commits ONLY files in its ownership set
- `git add` specific files by name (never `git add .` or `git add -A`)
- Always `git pull --rebase` before committing to avoid conflicts
- If rebase conflicts, STOP and notify the leader — do not force-push
