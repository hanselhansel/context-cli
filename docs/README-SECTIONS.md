# README Section Mapping

| README Section | Source of Truth | When to Update |
|---|---|---|
| Features list | CHANGELOG.md + new capabilities | Every minor version bump |
| AI Bots Checked | `core/checks/robots.py` AI_BOTS list | When bots added/removed |
| CLI Usage | `cli/audit.py` Typer options | When CLI flags change |
| Score Breakdown | `core/scoring.py` weights | When scoring changes |
| MCP Integration | `server.py` tools | When MCP tools change |
