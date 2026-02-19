"""SQLite persistence for Context Lint history."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from context_cli.core.models import AuditReport

# Default DB location
DEFAULT_DB_PATH = Path.home() / ".context-cli" / "history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    overall_score REAL NOT NULL,
    robots_score REAL NOT NULL,
    llms_txt_score REAL NOT NULL,
    schema_org_score REAL NOT NULL,
    content_score REAL NOT NULL,
    report_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audits_url ON audits (url);
CREATE INDEX IF NOT EXISTS idx_audits_timestamp ON audits (timestamp);
"""


class HistoryEntry(BaseModel):
    """A single audit history entry."""

    id: int = Field(description="Database row ID")
    url: str = Field(description="Audited URL")
    timestamp: str = Field(description="ISO 8601 timestamp of the audit")
    overall_score: float = Field(description="Overall Readiness Score")
    robots_score: float = Field(description="Robots pillar score")
    llms_txt_score: float = Field(description="llms.txt pillar score")
    schema_org_score: float = Field(description="Schema.org pillar score")
    content_score: float = Field(description="Content pillar score")


class HistoryDB:
    """SQLite-backed audit history store."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def save(self, report: AuditReport) -> int:
        """Save an audit report and return the row ID."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """INSERT INTO audits
               (url, timestamp, overall_score, robots_score, llms_txt_score,
                schema_org_score, content_score, report_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                report.url,
                now,
                report.overall_score,
                report.robots.score,
                report.llms_txt.score,
                report.schema_org.score,
                report.content.score,
                report.model_dump_json(),
            ),
        )
        self._conn.commit()
        return cursor.lastrowid or 0

    def list_entries(self, url: str, limit: int = 20) -> list[HistoryEntry]:
        """List recent audit entries for a URL, newest first."""
        rows = self._conn.execute(
            """SELECT id, url, timestamp, overall_score, robots_score,
                      llms_txt_score, schema_org_score, content_score
               FROM audits WHERE url = ? ORDER BY timestamp DESC LIMIT ?""",
            (url, limit),
        ).fetchall()
        return [HistoryEntry(**dict(r)) for r in rows]

    def get_report(self, entry_id: int) -> AuditReport | None:
        """Retrieve the full audit report for a given entry ID."""
        row = self._conn.execute(
            "SELECT report_json FROM audits WHERE id = ?", (entry_id,)
        ).fetchone()
        if row is None:
            return None
        return AuditReport.model_validate_json(row["report_json"])

    def get_latest(self, url: str) -> HistoryEntry | None:
        """Get the most recent entry for a URL."""
        entries = self.list_entries(url, limit=1)
        return entries[0] if entries else None

    def get_latest_report(self, url: str) -> AuditReport | None:
        """Get the most recent full report for a URL."""
        latest = self.get_latest(url)
        if latest is None:
            return None
        return self.get_report(latest.id)

    def delete_url(self, url: str) -> int:
        """Delete all entries for a URL. Returns the number of rows deleted."""
        cursor = self._conn.execute("DELETE FROM audits WHERE url = ?", (url,))
        self._conn.commit()
        return cursor.rowcount
