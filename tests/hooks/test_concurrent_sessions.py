"""
Tests for concurrent session detection and formatting.

Tests the concurrent session awareness functionality including:
- Detection of active sessions within a time window
- Formatting of concurrent sessions for context injection
- Retrieval and formatting of recently completed sessions
- Time calculation and truncation of long queries
- Graceful handling of database errors
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.hooks.concurrent_sessions import (
    format_concurrent_sessions_markdown,
    format_recent_work_markdown,
    get_concurrent_sessions,
    get_recent_completed_sessions,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database instance."""
    db_path = tmp_path / "test.db"
    db = HtmlGraphDB(str(db_path))
    yield db
    db.disconnect()


class TestGetConcurrentSessions:
    """Test concurrent session detection."""

    def test_returns_empty_when_no_concurrent(self, test_db):
        """Should return empty list when no other sessions exist."""
        # Create only our own session
        test_db.insert_session("sess-current", "claude-code")

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)
        assert result == []

    def test_excludes_current_session(self, test_db):
        """Should not include the current session in results."""
        test_db.insert_session("sess-current", "claude-code")
        test_db.insert_session("sess-other", "claude-code")

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        session_ids = [s["id"] for s in result]
        assert "sess-current" not in session_ids

    def test_returns_active_sessions(self, test_db):
        """Should return other active sessions."""
        test_db.insert_session("sess-current", "claude-code")
        test_db.insert_session("sess-other1", "claude-code")
        test_db.insert_session("sess-other2", "codex")

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        assert len(result) == 2
        session_ids = {s["id"] for s in result}
        assert "sess-other1" in session_ids
        assert "sess-other2" in session_ids

    def test_excludes_completed_sessions(self, test_db):
        """Should not include completed sessions."""
        test_db.insert_session("sess-current", "claude-code")
        test_db.insert_session("sess-active", "claude-code")
        test_db.insert_session("sess-completed", "claude-code")

        # Mark one session as completed
        cursor = test_db.connection.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (now_iso, "sess-completed"),
        )
        test_db.connection.commit()

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        session_ids = {s["id"] for s in result}
        assert "sess-active" in session_ids
        assert "sess-completed" not in session_ids

    def test_respects_time_window(self, test_db):
        """Should only return sessions within the time window."""
        test_db.insert_session("sess-current", "claude-code")

        # Insert an old session (use same format as insert_session)
        cursor = test_db.connection.cursor()
        old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cursor.execute(
            "INSERT INTO sessions (session_id, agent_assigned, created_at, status) "
            "VALUES (?, ?, ?, ?)",
            ("sess-old", "claude-code", old_time, "active"),
        )

        # Insert a recent session
        test_db.insert_session("sess-recent", "claude-code")
        test_db.connection.commit()

        # Query with 30-minute window
        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        session_ids = {s["id"] for s in result}
        assert "sess-recent" in session_ids
        assert "sess-old" not in session_ids

    def test_includes_session_metadata(self, test_db):
        """Should include session id, agent_id, and query information."""
        test_db.insert_session("sess-current", "claude-code")
        test_db.insert_session("sess-other", "gemini")

        # Insert an event with query info
        event_id = "evt-12345"
        cursor = test_db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, session_id, input_summary, output_summary)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                "gemini",
                "tool_call",
                "sess-other",
                "Implementing authentication",
                "Started implementation",
            ),
        )
        test_db.connection.commit()

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        assert len(result) == 1
        session = result[0]
        assert session["id"] == "sess-other"
        assert session["agent_id"] == "gemini"
        assert session["last_user_query"] == "Implementing authentication"

    def test_gracefully_handles_db_errors(self, test_db):
        """Should return empty list when database errors occur."""
        test_db.insert_session("sess-current", "claude-code")

        # Create a mock DB object to simulate errors
        mock_db = mock.MagicMock()
        mock_db.connection = mock.MagicMock()
        mock_db.connection.cursor.side_effect = sqlite3.Error("DB Error")

        result = get_concurrent_sessions(mock_db, "sess-current", minutes=30)

        assert result == []

    def test_handles_none_connection(self, test_db):
        """Should handle case where connection is None by reconnecting."""
        test_db.insert_session("sess-current", "claude-code")
        test_db.insert_session("sess-other", "claude-code")

        # Temporarily disconnect
        test_db.disconnect()
        # Reconnect will happen in the function
        test_db.connection = None

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        assert len(result) == 1
        assert result[0]["id"] == "sess-other"

    def test_multiple_concurrent_sessions_sorted_by_creation(self, test_db):
        """Should return multiple sessions sorted by creation time."""
        test_db.insert_session("sess-current", "claude-code")

        # Insert sessions with slight delays to ensure order
        cursor = test_db.connection.cursor()
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        for i, agent in enumerate(["claude-code", "gemini", "codex"]):
            time_str = (base_time + timedelta(seconds=i)).isoformat()
            cursor.execute(
                "INSERT INTO sessions (session_id, agent_assigned, created_at, status) "
                "VALUES (?, ?, ?, ?)",
                (f"sess-{i}", agent, time_str, "active"),
            )
        test_db.connection.commit()

        result = get_concurrent_sessions(test_db, "sess-current", minutes=30)

        assert len(result) == 3
        # Should be in reverse order (newest first)
        assert result[0]["id"] == "sess-2"
        assert result[1]["id"] == "sess-1"
        assert result[2]["id"] == "sess-0"


class TestFormatConcurrentSessionsMarkdown:
    """Test markdown formatting of concurrent sessions."""

    def test_empty_sessions_returns_empty_string(self):
        """Should return empty string when no sessions."""
        result = format_concurrent_sessions_markdown([])
        assert result == ""

    def test_formats_single_session(self):
        """Should format a single concurrent session."""
        sessions = [
            {
                "id": "sess-abc123def456",
                "agent_id": "claude-code",
                "last_user_query": "Implementing authentication",
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "## Concurrent Sessions (Active Now)" in result
        assert "sess-abc123d" in result  # Truncated to 12 chars
        assert "claude-code" in result
        assert "Implementing authentication" in result
        assert "Coordinate with concurrent sessions" in result

    def test_truncates_session_id_to_12_chars(self):
        """Should truncate session IDs to 12 characters."""
        long_id = "sess-" + "a" * 100
        sessions = [
            {
                "id": long_id,
                "agent_id": "claude-code",
                "last_user_query": "Test",
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert long_id[:12] in result
        # Ensure we're not including more than 12 chars
        assert long_id[:12] in result
        # Check that beyond character 12 is NOT in the session ID section
        # The 'aaa' part at position 20+ should not be present
        assert "aaa aaa" not in result

    def test_truncates_queries_longer_than_50_chars(self):
        """Should truncate queries longer than 50 chars."""
        long_query = "A" * 100
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": long_query,
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "A" * 50 + "..." in result
        assert "A" * 51 not in result

    def test_handles_missing_query(self):
        """Should handle sessions with missing queries."""
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": None,
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "Unknown" in result
        assert "sess-123" in result

    def test_formats_time_ago_just_now(self):
        """Should show 'just now' for very recent activity."""
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": "Test query",
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "just now" in result

    def test_formats_time_ago_minutes(self):
        """Should show minutes for recent activity."""
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": "Test query",
                "last_user_query_at": past.isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "min ago" in result
        assert "5 min ago" in result

    def test_formats_time_ago_hours(self):
        """Should show hours for older activity."""
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": "Test query",
                "last_user_query_at": past.isoformat(),
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "hours ago" in result
        assert "2 hours ago" in result

    def test_handles_iso_format_with_z_suffix(self):
        """Should handle ISO format timestamps with Z suffix."""
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": "Test query",
                "last_user_query_at": now_str,
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "just now" in result
        assert "sess-123" in result

    def test_handles_invalid_timestamp(self):
        """Should handle invalid timestamps gracefully."""
        sessions = [
            {
                "id": "sess-123",
                "agent_id": "claude-code",
                "last_user_query": "Test query",
                "last_user_query_at": "invalid-timestamp",
            }
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "unknown" in result
        assert "sess-123" in result

    def test_formats_multiple_sessions(self):
        """Should format multiple sessions."""
        sessions = [
            {
                "id": "sess-111",
                "agent_id": "claude-code",
                "last_user_query": "Query 1",
                "last_user_query_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "sess-222",
                "agent_id": "gemini",
                "last_user_query": "Query 2",
                "last_user_query_at": (
                    datetime.now(timezone.utc) - timedelta(minutes=10)
                ).isoformat(),
            },
        ]

        result = format_concurrent_sessions_markdown(sessions)

        assert "sess-111" in result
        assert "sess-222" in result
        assert "claude-code" in result
        assert "gemini" in result
        assert "Query 1" in result
        assert "Query 2" in result


class TestGetRecentCompletedSessions:
    """Test recent completed session retrieval."""

    def test_returns_completed_sessions(self, test_db):
        """Should return recently completed sessions."""
        test_db.insert_session("sess-active", "claude-code")
        test_db.insert_session("sess-completed", "claude-code")

        # Mark as completed
        cursor = test_db.connection.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (now_iso, "sess-completed"),
        )
        test_db.connection.commit()

        result = get_recent_completed_sessions(test_db, hours=24, limit=5)

        session_ids = {s["id"] for s in result}
        assert "sess-completed" in session_ids
        assert "sess-active" not in session_ids

    def test_excludes_old_completed_sessions(self, test_db):
        """Should exclude sessions completed outside time window."""
        test_db.insert_session("sess-recent", "claude-code")
        test_db.insert_session("sess-old", "claude-code")

        cursor = test_db.connection.cursor()
        # Mark recent as completed
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (now_iso, "sess-recent"),
        )

        # Mark old as completed (>24 hours ago)
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (old_time, "sess-old"),
        )
        test_db.connection.commit()

        result = get_recent_completed_sessions(test_db, hours=24, limit=5)

        session_ids = {s["id"] for s in result}
        assert "sess-recent" in session_ids
        assert "sess-old" not in session_ids

    def test_respects_limit(self, test_db):
        """Should respect the limit parameter."""
        # Create multiple completed sessions
        for i in range(10):
            session_id = f"sess-{i}"
            test_db.insert_session(session_id, "claude-code")

            cursor = test_db.connection.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
                (now_iso, session_id),
            )
        test_db.connection.commit()

        result = get_recent_completed_sessions(test_db, hours=24, limit=3)

        assert len(result) == 3

    def test_returns_session_metadata(self, test_db):
        """Should return session metadata including query info."""
        test_db.insert_session("sess-completed", "claude-code")

        # Insert event with query
        cursor = test_db.connection.cursor()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, session_id, input_summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("evt-1", "claude-code", "tool_call", "sess-completed", "Completed task X"),
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (now_iso, "sess-completed"),
        )
        test_db.connection.commit()

        result = get_recent_completed_sessions(test_db, hours=24, limit=5)

        assert len(result) >= 1
        session = result[0]
        assert session["id"] == "sess-completed"
        assert session["agent_id"] == "claude-code"
        assert session["last_user_query"] == "Completed task X"

    def test_returns_empty_when_no_completed(self, test_db):
        """Should return empty list when no completed sessions."""
        test_db.insert_session("sess-active", "claude-code")

        result = get_recent_completed_sessions(test_db, hours=24, limit=5)

        assert result == []

    def test_gracefully_handles_db_errors(self, test_db):
        """Should return empty list when database errors occur."""
        test_db.insert_session("sess-completed", "claude-code")

        # Create a mock DB object to simulate errors
        mock_db = mock.MagicMock()
        mock_db.connection = mock.MagicMock()
        mock_db.connection.cursor.side_effect = sqlite3.Error("DB Error")

        result = get_recent_completed_sessions(mock_db, hours=24, limit=5)

        assert result == []

    def test_sorted_by_completion_time_descending(self, test_db):
        """Should return results sorted by completion time (newest first)."""
        test_db.insert_session("sess-1", "claude-code")
        test_db.insert_session("sess-2", "claude-code")
        test_db.insert_session("sess-3", "claude-code")

        cursor = test_db.connection.cursor()
        base_time = datetime.now(timezone.utc) - timedelta(hours=1)

        for i, session_id in enumerate(["sess-1", "sess-2", "sess-3"]):
            complete_time = (base_time + timedelta(minutes=i)).isoformat()
            cursor.execute(
                "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
                (complete_time, session_id),
            )
        test_db.connection.commit()

        result = get_recent_completed_sessions(test_db, hours=24, limit=5)

        # Should be in reverse order (newest first)
        assert result[0]["id"] == "sess-3"
        assert result[1]["id"] == "sess-2"
        assert result[2]["id"] == "sess-1"


class TestFormatRecentWorkMarkdown:
    """Test markdown formatting of recent work."""

    def test_empty_sessions_returns_empty_string(self):
        """Should return empty string when no sessions."""
        result = format_recent_work_markdown([])
        assert result == ""

    def test_formats_single_session(self):
        """Should format a single completed session."""
        sessions = [
            {
                "id": "sess-abc123",
                "last_user_query": "Implemented auth feature",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 15,
            }
        ]

        result = format_recent_work_markdown(sessions)

        assert "## Recent Work (Last 24 Hours)" in result
        assert "sess-abc123" in result
        assert "Implemented auth feature" in result
        assert "15 events" in result

    def test_truncates_session_id(self):
        """Should truncate session IDs to 12 characters."""
        long_id = "sess-" + "a" * 100
        sessions = [
            {
                "id": long_id,
                "last_user_query": "Test",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 5,
            }
        ]

        result = format_recent_work_markdown(sessions)

        assert long_id[:12] in result
        assert "`" in result  # Uses backticks for code formatting

    def test_truncates_queries_longer_than_60_chars(self):
        """Should truncate queries longer than 60 chars."""
        long_query = "B" * 100
        sessions = [
            {
                "id": "sess-123",
                "last_user_query": long_query,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 5,
            }
        ]

        result = format_recent_work_markdown(sessions)

        assert "B" * 60 + "..." in result
        assert "B" * 61 not in result

    def test_handles_missing_query(self):
        """Should handle sessions with missing queries."""
        sessions = [
            {
                "id": "sess-123",
                "last_user_query": None,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 5,
            }
        ]

        result = format_recent_work_markdown(sessions)

        assert "Unknown" in result
        assert "sess-123" in result

    def test_formats_multiple_sessions(self):
        """Should format multiple completed sessions."""
        sessions = [
            {
                "id": "sess-111",
                "last_user_query": "Implemented feature A",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 10,
            },
            {
                "id": "sess-222",
                "last_user_query": "Fixed bug B",
                "completed_at": (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                ).isoformat(),
                "total_events": 5,
            },
        ]

        result = format_recent_work_markdown(sessions)

        assert "sess-111" in result
        assert "sess-222" in result
        assert "Implemented feature A" in result
        assert "Fixed bug B" in result
        assert "10 events" in result
        assert "5 events" in result

    def test_handles_missing_total_events(self):
        """Should handle sessions with missing total_events."""
        sessions = [
            {
                "id": "sess-123",
                "last_user_query": "Test query",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": None,
            }
        ]

        result = format_recent_work_markdown(sessions)

        assert "0 events" in result
        assert "sess-123" in result

    def test_query_display_uses_short_format(self):
        """Should use short query format (60 chars vs 50 for concurrent)."""
        # Test that recent work format uses 60 char limit, not 50
        query_60 = "A" * 60
        query_61 = "A" * 61

        sessions = [
            {
                "id": "sess-123",
                "last_user_query": query_60,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 5,
            }
        ]

        result = format_recent_work_markdown(sessions)
        assert "A" * 60 in result

        sessions = [
            {
                "id": "sess-123",
                "last_user_query": query_61,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_events": 5,
            }
        ]

        result = format_recent_work_markdown(sessions)
        assert "A" * 60 + "..." in result
        assert "A" * 61 not in result


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_concurrent_and_recent_work_together(self, test_db):
        """Should handle concurrent sessions and recent work in same context."""
        # Create current session
        test_db.insert_session("sess-current", "claude-code")

        # Create concurrent session
        test_db.insert_session("sess-concurrent", "gemini")

        # Create completed session
        test_db.insert_session("sess-completed", "codex")

        cursor = test_db.connection.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Add events
        for session_id, query in [
            ("sess-concurrent", "Working on API design"),
            ("sess-completed", "Implemented database schema"),
        ]:
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, event_type, session_id, input_summary)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"evt-{session_id}",
                    "agent",
                    "tool_call",
                    session_id,
                    query,
                ),
            )

        # Complete one session
        cursor.execute(
            "UPDATE sessions SET status = 'completed', completed_at = ? WHERE session_id = ?",
            (now_iso, "sess-completed"),
        )
        test_db.connection.commit()

        # Get both concurrent and recent
        concurrent = get_concurrent_sessions(test_db, "sess-current", minutes=30)
        recent = get_recent_completed_sessions(test_db, hours=24, limit=5)

        assert len(concurrent) == 1
        assert concurrent[0]["id"] == "sess-concurrent"

        assert len(recent) == 1
        assert recent[0]["id"] == "sess-completed"

        # Format both
        concurrent_md = format_concurrent_sessions_markdown(concurrent)
        recent_md = format_recent_work_markdown(recent)

        # Session IDs are truncated to 12 chars
        assert "sess-concurr" in concurrent_md  # "sess-concurrent"[:12]
        assert "sess-complet" in recent_md  # "sess-completed"[:12]
        assert "Working on API design" in concurrent_md
        assert "Implemented database schema" in recent_md


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
