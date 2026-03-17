# Changelog Conventions

Context CLI follows the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format for documenting notable changes.

## Format

Each release entry follows this structure:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that were removed

### Fixed
- Bug fixes

### Security
- Vulnerability fixes
```

## Categories

Use these categories in the order listed:

| Category | When to use |
|---|---|
| **Added** | New features, new CLI commands, new checks, new output formats |
| **Changed** | Changes to existing behavior, scoring weight adjustments, API changes |
| **Deprecated** | Features marked for future removal |
| **Removed** | Features that have been removed |
| **Fixed** | Bug fixes, corrected scoring, fixed edge cases |
| **Security** | Vulnerability patches, dependency updates for security |

## Guidelines

- Write entries from the user's perspective, not the developer's
- Start each entry with a verb (Add, Fix, Change, Remove, etc.)
- Reference issue numbers where applicable
- Group related changes into a single entry when they form a logical unit
- Keep entries concise but descriptive enough to understand without reading the code
- Unreleased changes go under an `## [Unreleased]` section at the top

## Version Links

At the bottom of `CHANGELOG.md`, include comparison links:

```markdown
[Unreleased]: https://github.com/hanselhansel/context-cli/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/hanselhansel/context-cli/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/hanselhansel/context-cli/releases/tag/v2.0.0
```

## Versioning

Context CLI follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **Major** (X.0.0) -- breaking changes to CLI interface, scoring model changes, API changes
- **Minor** (0.Y.0) -- new features, new commands, new checks
- **Patch** (0.0.Z) -- bug fixes, documentation updates, dependency updates
