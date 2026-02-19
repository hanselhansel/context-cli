# Refactoring Rules

## The TDD Refactoring Step
After tests pass (Green), ALWAYS refactor before committing:
- Extract functions/classes that do too much
- Split files approaching the size threshold
- Remove duplication
- Improve naming

## File Size Guidelines (Source Files Only)
- **Target**: Keep source files under 300 lines
- **Warning**: Files over 300 lines should be evaluated for splitting
- **Hard limit**: Files over 400 lines MUST be split before committing
- **Exceptions**: Only with explicit justification (e.g., models.py during transitional growth)
- **Test files**: No line limit. Test files are naturally larger.

## When to Split a Module
Split when ANY of these are true:
- File exceeds 400 lines
- File has 3+ unrelated responsibilities
- You're adding a new feature area to an existing file
- Two developers (or agents) would likely conflict editing the same file

## How to Split
1. Create a new module in the appropriate package
2. Move the extracted code
3. Update imports in all consumers
4. Re-export from `__init__.py` if needed for backward compatibility
5. Verify: `ruff check src/ tests/ && mypy src/ && pytest tests/ -q --cov=context_cli --cov-fail-under=100`

## Module Structure Standards
- One clear responsibility per module
- Public API at the top of the file
- Private helpers prefixed with `_`
- Imports sorted: stdlib → third-party → local (enforced by ruff)

## What NOT to Refactor
- Working code that isn't being touched by the current feature
- Test files (they're naturally verbose — that's OK)
- Generated code or configuration files
