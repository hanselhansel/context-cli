# Versioning Rules

## Scheme
Semantic versioning: MAJOR.MINOR.PATCH

## Phase to Version Mapping
| Phase | Version | Description |
|-------|---------|-------------|
| A1 | 0.3.0 | Strengthen core |
| A2 | 0.4.0 | Intelligence layer |
| A3 | 0.5.0 | Ecosystem |
| A4 | 0.6.0 | Polish |
| B0 | 0.7.0 | Shared LLM infra |
| B1 | 0.8.0 | CI/CD integration |
| B2 | 0.9.0 | Batch generate |
| B3 | 0.10.0 | Citation radar |
| B4 | 0.11.0 | Benchmark |
| B5 | 0.12.0 | Retail |
| Final | 1.0.0 | All features complete |
| Rebrand | 2.0.0 | Pivot from AEO-CLI to Context CLI |

## When to Bump
- **Patch** (0.3.1, 0.3.2): After completing each meaningful feature within a phase
- **Minor** (0.3.0 → 0.4.0): At phase completion, all features done + CI green

## Version Bump Workflow
1. Update `version` in `pyproject.toml`
2. Update `CHANGELOG.md` with new features since last version
3. Commit: `chore: release v{version}`
4. Tag: `git tag v{version}`
5. Push: `git push origin main --tags`
6. GitHub Actions auto-publishes to PyPI

## Files to Update on Version Bump
- `pyproject.toml` → `version = "X.Y.Z"`
- `CHANGELOG.md` → new section with features
- `README.md` → update Features, CLI Usage, and AI Bots sections if changed

## CHANGELOG Format
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature description

### Changed
- Change description

### Fixed
- Fix description
```
