"""Tests for SQLite audit history persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from context_cli.core.history import DEFAULT_DB_PATH, HistoryDB, HistoryEntry
from context_cli.core.models import (
    AuditReport,
    ContentReport,
    LlmsTxtReport,
    RobotsReport,
    SchemaReport,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

_URL = "https://example.com"
_URL_B = "https://other.com"


def _make_report(url: str = _URL, score: float = 65.0) -> AuditReport:
    return AuditReport(
        url=url,
        overall_score=score,
        robots=RobotsReport(found=True, score=20.0, detail="ok"),
        llms_txt=LlmsTxtReport(found=True, score=10.0, detail="ok"),
        schema_org=SchemaReport(score=15.0, detail="ok"),
        content=ContentReport(score=20.0, detail="ok"),
    )


@pytest.fixture
def db(tmp_path: Path) -> HistoryDB:
    """Create a temporary HistoryDB for testing."""
    db = HistoryDB(tmp_path / "test_history.db")
    yield db
    db.close()


# ── HistoryDB init ──────────────────────────────────────────────────────────


def test_db_creates_file(tmp_path: Path) -> None:
    """HistoryDB should create the database file and parent directories."""
    db_path = tmp_path / "sub" / "dir" / "history.db"
    db = HistoryDB(db_path)
    assert db_path.exists()
    db.close()


def test_default_db_path() -> None:
    """DEFAULT_DB_PATH should point to ~/.context-cli/history.db."""
    assert DEFAULT_DB_PATH == Path.home() / ".context-cli" / "history.db"


# ── save ────────────────────────────────────────────────────────────────────


def test_save_returns_row_id(db: HistoryDB) -> None:
    report = _make_report()
    row_id = db.save(report)
    assert row_id >= 1


def test_save_increments_id(db: HistoryDB) -> None:
    id1 = db.save(_make_report())
    id2 = db.save(_make_report())
    assert id2 > id1


def test_save_stores_url(db: HistoryDB) -> None:
    db.save(_make_report())
    entries = db.list_entries(_URL)
    assert len(entries) == 1
    assert entries[0].url == _URL


def test_save_stores_scores(db: HistoryDB) -> None:
    db.save(_make_report(score=72.5))
    entries = db.list_entries(_URL)
    assert entries[0].overall_score == 72.5
    assert entries[0].robots_score == 20.0
    assert entries[0].llms_txt_score == 10.0
    assert entries[0].schema_org_score == 15.0
    assert entries[0].content_score == 20.0


def test_save_stores_timestamp(db: HistoryDB) -> None:
    db.save(_make_report())
    entries = db.list_entries(_URL)
    assert entries[0].timestamp  # Non-empty ISO timestamp


# ── list_entries ────────────────────────────────────────────────────────────


def test_list_entries_empty(db: HistoryDB) -> None:
    entries = db.list_entries(_URL)
    assert entries == []


def test_list_entries_filtered_by_url(db: HistoryDB) -> None:
    db.save(_make_report(_URL))
    db.save(_make_report(_URL_B))
    entries = db.list_entries(_URL)
    assert len(entries) == 1
    assert entries[0].url == _URL


def test_list_entries_newest_first(db: HistoryDB) -> None:
    db.save(_make_report(score=50.0))
    db.save(_make_report(score=60.0))
    db.save(_make_report(score=70.0))
    entries = db.list_entries(_URL)
    assert entries[0].overall_score == 70.0
    assert entries[-1].overall_score == 50.0


def test_list_entries_respects_limit(db: HistoryDB) -> None:
    for i in range(5):
        db.save(_make_report(score=float(i * 10)))
    entries = db.list_entries(_URL, limit=3)
    assert len(entries) == 3


# ── get_report ──────────────────────────────────────────────────────────────


def test_get_report_returns_full_report(db: HistoryDB) -> None:
    report = _make_report(score=88.0)
    row_id = db.save(report)
    loaded = db.get_report(row_id)
    assert loaded is not None
    assert loaded.overall_score == 88.0
    assert loaded.url == _URL
    assert loaded.robots.score == 20.0


def test_get_report_missing_id(db: HistoryDB) -> None:
    result = db.get_report(9999)
    assert result is None


# ── get_latest ──────────────────────────────────────────────────────────────


def test_get_latest_returns_newest(db: HistoryDB) -> None:
    db.save(_make_report(score=50.0))
    db.save(_make_report(score=80.0))
    latest = db.get_latest(_URL)
    assert latest is not None
    assert latest.overall_score == 80.0


def test_get_latest_returns_none_when_empty(db: HistoryDB) -> None:
    result = db.get_latest(_URL)
    assert result is None


# ── get_latest_report ───────────────────────────────────────────────────────


def test_get_latest_report_returns_full(db: HistoryDB) -> None:
    db.save(_make_report(score=75.0))
    report = db.get_latest_report(_URL)
    assert report is not None
    assert report.overall_score == 75.0


def test_get_latest_report_returns_none_when_empty(db: HistoryDB) -> None:
    result = db.get_latest_report(_URL)
    assert result is None


# ── delete_url ──────────────────────────────────────────────────────────────


def test_delete_url_removes_entries(db: HistoryDB) -> None:
    db.save(_make_report())
    db.save(_make_report())
    count = db.delete_url(_URL)
    assert count == 2
    assert db.list_entries(_URL) == []


def test_delete_url_doesnt_affect_other_urls(db: HistoryDB) -> None:
    db.save(_make_report(_URL))
    db.save(_make_report(_URL_B))
    db.delete_url(_URL)
    entries = db.list_entries(_URL_B)
    assert len(entries) == 1


def test_delete_url_returns_zero_when_empty(db: HistoryDB) -> None:
    count = db.delete_url("https://nonexistent.com")
    assert count == 0


# ── HistoryEntry model ──────────────────────────────────────────────────────


def test_history_entry_fields() -> None:
    entry = HistoryEntry(
        id=1,
        url=_URL,
        timestamp="2025-01-01T00:00:00+00:00",
        overall_score=65.0,
        robots_score=20.0,
        llms_txt_score=10.0,
        schema_org_score=15.0,
        content_score=20.0,
    )
    assert entry.id == 1
    assert entry.url == _URL


# ── close ───────────────────────────────────────────────────────────────────


def test_close_is_idempotent(tmp_path: Path) -> None:
    """Closing twice should not raise."""
    db = HistoryDB(tmp_path / "test.db")
    db.close()
    # Second close on already-closed connection — should not crash
    db.close()
