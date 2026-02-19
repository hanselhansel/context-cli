"""AEO-CLI — Agentic Engine Optimization auditor CLI."""

from __future__ import annotations

import typer

app = typer.Typer(
    help="AEO-CLI: Audit URLs for AI crawler readiness and get a 0-100 AEO score."
)

# Register commands from cli/ subpackage
from context_cli.cli import audit as _audit_mod  # noqa: E402
from context_cli.cli import benchmark as _bench_mod  # noqa: E402
from context_cli.cli import compare as _compare_mod  # noqa: E402
from context_cli.cli import generate as _generate_mod  # noqa: E402
from context_cli.cli import history as _history_mod  # noqa: E402
from context_cli.cli import mcp_cmd as _mcp_mod  # noqa: E402
from context_cli.cli import radar as _radar_mod  # noqa: E402
from context_cli.cli import retail as _retail_mod  # noqa: E402
from context_cli.cli import watch as _watch_mod  # noqa: E402

_audit_mod.register(app)
_bench_mod.register(app)
_compare_mod.register(app)
_generate_mod.register(app)
_history_mod.register(app)
_mcp_mod.register(app)
_radar_mod.register(app)
_retail_mod.register(app)
_watch_mod.register(app)
