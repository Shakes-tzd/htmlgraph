"""Tests for the Cursor AI session ingester."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from htmlgraph.ingest.cursor import (
    CursorConversation,
    IngestResult,
    find_cursor_db,
    load_cursor_conversations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_cursor_db(path: Path, rows: list[dict] | None = None) -> Path:
    """Create a minimal Cursor tracking database at the given path."""
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("""
            CREATE TABLE conversation_summaries (
                conversationId TEXT PRIMARY KEY,
                title TEXT,
                tldr TEXT,
                overview TEXT,
                summaryBullets TEXT,
                model TEXT,
                mode TEXT,
                updatedAt INTEGER NOT NULL
            )
        """)
        if rows:
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO conversation_summaries
                        (conversationId, title, tldr, overview, summaryBullets,
                         model, mode, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("conversationId", ""),
                        row.get("title"),
                        row.get("tldr"),
                        row.get("overview"),
                        row.get("summaryBullets", "[]"),
                        row.get("model"),
                        row.get("mode"),
                        row.get("updatedAt", 1767380654720),
                    ),
                )
        conn.commit()
    finally:
        conn.close()
    return path


def _sample_row(
    conversation_id: str = "conv-abc123",
    title: str = "Fix the authentication bug",
    tldr: str = "Debugged JWT validation logic",
    model: str = "claude-3-5-sonnet",
    mode: str = "agent",
    updated_at_ms: int = 1767380654720,
    bullets: list[str] | None = None,
) -> dict:
    if bullets is None:
        bullets = ["Found the issue", "Fixed the token validation"]
    return {
        "conversationId": conversation_id,
        "title": title,
        "tldr": tldr,
        "overview": "A longer description of what happened",
        "summaryBullets": json.dumps(bullets),
        "model": model,
        "mode": mode,
        "updatedAt": updated_at_ms,
    }


@pytest.fixture
def tmp_cursor_db(tmp_path: Path) -> Path:
    """Create a temporary Cursor tracking DB with one conversation."""
    db_path = tmp_path / "ai-code-tracking.db"
    _create_cursor_db(db_path, rows=[_sample_row()])
    return db_path


@pytest.fixture
def tmp_cursor_db_multi(tmp_path: Path) -> Path:
    """Create a temporary Cursor tracking DB with multiple conversations."""
    db_path = tmp_path / "ai-code-tracking.db"
    rows = [
        _sample_row(
            conversation_id=f"conv-{i:04d}",
            title=f"Conversation {i}",
            updated_at_ms=1767380654720 + i * 10000,
        )
        for i in range(5)
    ]
    _create_cursor_db(db_path, rows=rows)
    return db_path


@pytest.fixture
def tmp_empty_cursor_db(tmp_path: Path) -> Path:
    """Create an empty Cursor tracking DB (no rows)."""
    db_path = tmp_path / "ai-code-tracking.db"
    _create_cursor_db(db_path, rows=[])
    return db_path


# ---------------------------------------------------------------------------
# CursorConversation tests
# ---------------------------------------------------------------------------


class TestCursorConversation:
    def test_parse_full_row(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = (
            "conv-abc123",
            "Fix the bug",
            "Fixed JWT validation",
            "Long overview",
            '["Point 1", "Point 2"]',
            "claude-3-5-sonnet",
            "agent",
            1767380654720,
        )
        conv = CursorConversation.from_row(row, columns)
        assert conv.conversation_id == "conv-abc123"
        assert conv.title == "Fix the bug"
        assert conv.tldr == "Fixed JWT validation"
        assert conv.model == "claude-3-5-sonnet"
        assert conv.mode == "agent"
        assert conv.summary_bullets == ["Point 1", "Point 2"]
        assert conv.updated_at.tzinfo is not None

    def test_timestamp_parsed_from_ms(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", None, None, None, "[]", None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert conv.updated_at.year >= 2025

    def test_invalid_updated_at_falls_back(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        # 0 ms → epoch (1970); verify graceful parse, not a crash
        row = ("c1", None, None, None, "[]", None, None, 0)
        conv = CursorConversation.from_row(row, columns)
        assert conv.updated_at.year == 1970

    def test_invalid_bullets_json_becomes_empty(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", None, None, None, "not json", None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert conv.summary_bullets == []

    def test_none_fields_normalised(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", "", "", "", "[]", "", "", 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert conv.title is None
        assert conv.tldr is None
        assert conv.model is None
        assert conv.mode is None

    def test_description_uses_title(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", "My title", "My tldr", None, "[]", None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert conv.description == "My title"

    def test_description_falls_back_to_tldr(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", None, "My tldr", None, "[]", None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert conv.description == "My tldr"

    def test_description_falls_back_to_first_bullet(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("c1", None, None, None, '["First bullet"]', None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert "First bullet" in conv.description

    def test_description_fallback_uses_id(self) -> None:
        columns = [
            "conversationId", "title", "tldr", "overview",
            "summaryBullets", "model", "mode", "updatedAt"
        ]
        row = ("conv-xyz999", None, None, None, "[]", None, None, 1767380654720)
        conv = CursorConversation.from_row(row, columns)
        assert "conv-xyz999" in conv.description


# ---------------------------------------------------------------------------
# find_cursor_db tests
# ---------------------------------------------------------------------------


class TestFindCursorDb:
    def test_finds_existing_db(self, tmp_cursor_db: Path) -> None:
        result = find_cursor_db(db_path=tmp_cursor_db)
        assert result == tmp_cursor_db

    def test_returns_none_for_missing_path(self, tmp_path: Path) -> None:
        result = find_cursor_db(db_path=tmp_path / "nonexistent.db")
        assert result is None

    def test_returns_none_when_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When default path doesn't exist and no explicit path given, returns None."""
        import htmlgraph.ingest.cursor as cursor_mod

        monkeypatch.setattr(
            cursor_mod, "_CURSOR_DEFAULT_DB_PATH", Path("/nonexistent/path.db")
        )
        result = find_cursor_db(db_path=None)
        assert result is None


# ---------------------------------------------------------------------------
# load_cursor_conversations tests
# ---------------------------------------------------------------------------


class TestLoadCursorConversations:
    def test_loads_single_conversation(self, tmp_cursor_db: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_cursor_db)
        assert len(convs) == 1
        assert convs[0].conversation_id == "conv-abc123"
        assert convs[0].title == "Fix the authentication bug"

    def test_loads_multiple_conversations(self, tmp_cursor_db_multi: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_cursor_db_multi)
        assert len(convs) == 5

    def test_empty_db_returns_empty(self, tmp_empty_cursor_db: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_empty_cursor_db)
        assert convs == []

    def test_missing_db_returns_empty(self, tmp_path: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_path / "missing.db")
        assert convs == []

    def test_respects_limit(self, tmp_cursor_db_multi: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_cursor_db_multi, limit=2)
        assert len(convs) == 2

    def test_sorted_newest_first(self, tmp_cursor_db_multi: Path) -> None:
        convs = load_cursor_conversations(db_path=tmp_cursor_db_multi)
        timestamps = [c.updated_at for c in convs]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_db_without_table_returns_empty(self, tmp_path: Path) -> None:
        """DB that exists but lacks the expected table returns empty list."""
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE other_table (id TEXT)")
        conn.commit()
        conn.close()
        convs = load_cursor_conversations(db_path=db_path)
        assert convs == []


# ---------------------------------------------------------------------------
# IngestResult tests
# ---------------------------------------------------------------------------


class TestCursorIngestResult:
    def test_default_values(self) -> None:
        result = IngestResult()
        assert result.ingested == 0
        assert result.skipped == 0
        assert result.errors == 0
        assert result.session_ids == []
        assert result.error_files == []
