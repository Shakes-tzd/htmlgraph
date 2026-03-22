"""
Tests for session-scoped active work item DB methods.

Verifies the database layer for Phase 1 of the Session-Scoped Active Work Item
track (feat-c0e9782b). Each session tracks its own active work item via the
`active_feature_id` column on the sessions table.

Test coverage:
- set_active_work_item sets the value correctly
- get_active_work_item_for_session returns the set value
- get_active_work_item_for_session returns None when no active item
- clear_active_work_item resets the value to None
- Two parallel sessions can hold different active items independently
- Schema migration adds active_feature_id to pre-existing sessions tables
"""

from pathlib import Path
from uuid import uuid4

import pytest
from htmlgraph.db.schema import HtmlGraphDB

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db(tmp_path):
    """Create a fresh temporary HtmlGraphDB for each test."""
    db_path = str(tmp_path / f"test_{uuid4().hex}.db")
    db = HtmlGraphDB(db_path)
    yield db
    db.disconnect()
    if Path(db_path).exists():
        Path(db_path).unlink()


def _insert_session(db: HtmlGraphDB, session_id: str) -> None:
    """Helper: insert a minimal session row."""
    db.insert_session(session_id=session_id, agent_assigned="test-agent")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSetActiveWorkItem:
    """Tests for set_active_work_item."""

    def test_set_active_work_item_stores_value(self, temp_db):
        """set_active_work_item should persist the feature ID in the DB."""
        session_id = "sess-test-set-01"
        feature_id = "feat-abc123"

        _insert_session(temp_db, session_id)
        temp_db.set_active_work_item(session_id, feature_id)

        cursor = temp_db.connection.cursor()
        row = cursor.execute(
            "SELECT active_feature_id FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        assert row is not None
        assert row[0] == feature_id

    def test_set_active_work_item_overwrites_previous_value(self, temp_db):
        """set_active_work_item should replace an existing active item."""
        session_id = "sess-test-overwrite"
        _insert_session(temp_db, session_id)

        temp_db.set_active_work_item(session_id, "feat-first")
        temp_db.set_active_work_item(session_id, "feat-second")

        result = temp_db.get_active_work_item_for_session(session_id)
        assert result == "feat-second"


class TestGetActiveWorkItemForSession:
    """Tests for get_active_work_item_for_session."""

    def test_returns_feature_id_after_set(self, temp_db):
        """Should return the feature ID that was set."""
        session_id = "sess-test-get-01"
        feature_id = "feat-get-test"

        _insert_session(temp_db, session_id)
        temp_db.set_active_work_item(session_id, feature_id)

        result = temp_db.get_active_work_item_for_session(session_id)
        assert result == feature_id

    def test_returns_none_when_no_active_item(self, temp_db):
        """Should return None for a session with no active work item set."""
        session_id = "sess-test-none-01"
        _insert_session(temp_db, session_id)

        result = temp_db.get_active_work_item_for_session(session_id)
        assert result is None

    def test_returns_none_for_unknown_session(self, temp_db):
        """Should return None when the session_id does not exist."""
        result = temp_db.get_active_work_item_for_session("sess-nonexistent-xyz")
        assert result is None


class TestClearActiveWorkItem:
    """Tests for clear_active_work_item."""

    def test_clear_resets_to_none(self, temp_db):
        """clear_active_work_item should set active_feature_id back to NULL."""
        session_id = "sess-test-clear-01"
        _insert_session(temp_db, session_id)

        temp_db.set_active_work_item(session_id, "feat-to-clear")
        assert temp_db.get_active_work_item_for_session(session_id) == "feat-to-clear"

        temp_db.clear_active_work_item(session_id)
        assert temp_db.get_active_work_item_for_session(session_id) is None

    def test_clear_on_session_with_no_item_is_safe(self, temp_db):
        """Clearing when no item is set should not raise."""
        session_id = "sess-test-clear-noop"
        _insert_session(temp_db, session_id)

        # Should not raise
        temp_db.clear_active_work_item(session_id)
        assert temp_db.get_active_work_item_for_session(session_id) is None


class TestParallelSessions:
    """Tests proving two sessions maintain independent active items."""

    def test_two_sessions_hold_different_active_items(self, temp_db):
        """Parallel sessions should not share or overwrite each other's active item."""
        session_a = "sess-parallel-A"
        session_b = "sess-parallel-B"
        feature_a = "feat-parallel-A"
        feature_b = "feat-parallel-B"

        _insert_session(temp_db, session_a)
        _insert_session(temp_db, session_b)

        temp_db.set_active_work_item(session_a, feature_a)
        temp_db.set_active_work_item(session_b, feature_b)

        assert temp_db.get_active_work_item_for_session(session_a) == feature_a
        assert temp_db.get_active_work_item_for_session(session_b) == feature_b

    def test_clearing_one_session_does_not_affect_other(self, temp_db):
        """Clearing active item in one session must not affect the other."""
        session_a = "sess-clear-A"
        session_b = "sess-clear-B"

        _insert_session(temp_db, session_a)
        _insert_session(temp_db, session_b)

        temp_db.set_active_work_item(session_a, "feat-A")
        temp_db.set_active_work_item(session_b, "feat-B")

        temp_db.clear_active_work_item(session_a)

        assert temp_db.get_active_work_item_for_session(session_a) is None
        assert temp_db.get_active_work_item_for_session(session_b) == "feat-B"


class TestSchemaMigration:
    """Tests for schema migration adding active_feature_id to existing tables."""

    def test_migration_adds_column_to_existing_table(self, tmp_path):
        """
        Simulate a pre-existing sessions table without active_feature_id.

        The migrate_sessions() call inside create_tables() should add the column
        automatically so that subsequent operations succeed.
        """
        import sqlite3

        db_path = str(tmp_path / "legacy.db")

        # Bootstrap a minimal sessions table WITHOUT active_feature_id
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                agent_assigned TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
        """)
        conn.execute(
            "INSERT INTO sessions (session_id, agent_assigned) VALUES ('sess-legacy', 'agent')"
        )
        conn.commit()
        conn.close()

        # Open with HtmlGraphDB — migration should add active_feature_id
        db = HtmlGraphDB(db_path)

        cursor = db.connection.cursor()
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "active_feature_id" in columns, (
            "active_feature_id column should be added by migration"
        )

        # Functional check: existing row should have NULL active_feature_id
        result = db.get_active_work_item_for_session("sess-legacy")
        assert result is None

        db.disconnect()
        Path(db_path).unlink()
