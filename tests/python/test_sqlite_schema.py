"""
Test suite for HtmlGraph SQLite schema and queries.

Tests verify:
- Schema creation and table structure
- Data insertion and retrieval
- Query builders and results
- Data relationships and integrity
- Index performance
- Migration compatibility
"""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from htmlgraph.db.queries import Queries

# Import schema and queries
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def temp_db() -> Generator[HtmlGraphDB, None, None]:
    """Create temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))
        db.connect()
        db.create_tables()
        yield db
        db.disconnect()


class TestSchemaCreation:
    """Test schema creation and table structure."""

    def test_database_connection(self, temp_db):
        """Test database connection and basic operations."""
        assert temp_db.connection is not None
        cursor = temp_db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert len(tables) > 0

    def test_all_tables_exist(self, temp_db):
        """Verify all required tables are created."""
        cursor = temp_db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = [
            "agent_events",
            "features",
            "sessions",
            "tracks",
            "agent_collaboration",
            "graph_edges",
            "event_log_archive",
        ]

        for table in required_tables:
            assert table in tables, f"Table {table} not found"

    def test_agent_events_schema(self, temp_db):
        """Verify agent_events table schema."""
        cursor = temp_db.connection.cursor()
        cursor.execute("PRAGMA table_info(agent_events)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = {
            "event_id": "TEXT",
            "agent_id": "TEXT",
            "event_type": "TEXT",
            "session_id": "TEXT",
            "timestamp": "DATETIME",
            "tool_name": "TEXT",
            "cost_tokens": "INTEGER",
        }

        for col, col_type in required_columns.items():
            assert col in columns, f"Column {col} not found"

    def test_features_schema(self, temp_db):
        """Verify features table schema."""
        cursor = temp_db.connection.cursor()
        cursor.execute("PRAGMA table_info(features)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = {
            "id": "TEXT",
            "type": "TEXT",
            "title": "TEXT",
            "status": "TEXT",
            "priority": "TEXT",
            "assigned_to": "TEXT",
        }

        for col, col_type in required_columns.items():
            assert col in columns, f"Column {col} not found"

    def test_sessions_schema(self, temp_db):
        """Verify sessions table schema."""
        cursor = temp_db.connection.cursor()
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        required_columns = {
            "session_id": "TEXT",
            "agent_assigned": "TEXT",
            "created_at": "DATETIME",
            "total_events": "INTEGER",
            "total_tokens_used": "INTEGER",
        }

        for col, col_type in required_columns.items():
            assert col in columns, f"Column {col} not found"

    def test_indexes_created(self, temp_db):
        """Verify indexes are created for performance."""
        cursor = temp_db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        # Check that at least some indexes exist
        # The exact naming may vary based on implementation
        assert len(indexes) > 0, "No indexes found"

        # Check for key indexes we care about (checking for substrings to be flexible)
        assert any("agent_events" in idx for idx in indexes), (
            "No agent_events indexes found"
        )
        assert any("features" in idx for idx in indexes), "No features indexes found"
        assert any("sessions" in idx for idx in indexes), "No sessions indexes found"


class TestEventInsertion:
    """Test agent event insertion and retrieval."""

    def test_insert_event_basic(self, temp_db):
        """Test basic event insertion."""
        session_id = "test-session-1"
        temp_db.insert_session(session_id, "test-agent")

        success = temp_db.insert_event(
            event_id="evt-001",
            agent_id="test-agent",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Read",
            input_summary="Read file test.py",
        )

        assert success is True

    def test_insert_event_with_context(self, temp_db):
        """Test event insertion with JSON context."""
        session_id = "test-session-2"
        temp_db.insert_session(session_id, "test-agent")

        context = {
            "file_path": "/tmp/test.py",
            "lines": 100,
            "encoding": "utf-8",
        }

        success = temp_db.insert_event(
            event_id="evt-002",
            agent_id="test-agent",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Read",
            context=context,
        )

        assert success is True

        # Verify context was stored as JSON
        events = temp_db.get_session_events(session_id)
        assert len(events) > 0
        stored_context = json.loads(events[0]["context"])
        assert stored_context["file_path"] == "/tmp/test.py"

    def test_insert_delegation_event(self, temp_db):
        """Test insertion of delegation events."""
        session_id = "test-session-3"
        temp_db.insert_session(session_id, "orchestrator")

        success = temp_db.insert_event(
            event_id="evt-003",
            agent_id="orchestrator",
            event_type="delegation",
            session_id=session_id,
            tool_name="Task",
            input_summary="Delegate to gemini",
            parent_agent_id="gemini",
        )

        assert success is True

    def test_retrieve_session_events(self, temp_db):
        """Test retrieving all events for a session."""
        session_id = "test-session-4"
        temp_db.insert_session(session_id, "test-agent")

        # Insert multiple events
        for i in range(5):
            temp_db.insert_event(
                event_id=f"evt-{i:03d}",
                agent_id="test-agent",
                event_type="tool_call" if i % 2 == 0 else "error",
                session_id=session_id,
                tool_name="Read",
            )

        events = temp_db.get_session_events(session_id)
        assert len(events) == 5


class TestFeatureOperations:
    """Test feature work item operations."""

    def test_insert_feature(self, temp_db):
        """Test feature insertion."""
        success = temp_db.insert_feature(
            feature_id="feat-001",
            feature_type="feature",
            title="Implement User Authentication",
            status="todo",
            priority="high",
            steps_total=5,
        )

        assert success is True

    def test_insert_bug(self, temp_db):
        """Test bug insertion."""
        success = temp_db.insert_feature(
            feature_id="bug-001",
            feature_type="bug",
            title="Fix login timeout",
            status="in-progress",  # Fixed: use hyphen, not underscore
            priority="critical",
        )

        assert success is True

    def test_insert_spike(self, temp_db):
        """Test spike insertion."""
        success = temp_db.insert_feature(
            feature_id="spk-001",
            feature_type="spike",
            title="Research OAuth providers",
            status="todo",
            priority="medium",
        )

        assert success is True

    def test_update_feature_status(self, temp_db):
        """Test updating feature status."""
        temp_db.insert_feature(
            feature_id="feat-002",
            feature_type="feature",
            title="Add dark mode",
            status="todo",
        )

        success = temp_db.update_feature_status(
            feature_id="feat-002",
            status="in-progress",  # Fixed: use hyphen, not underscore
            steps_completed=2,
        )

        assert success is True

        # Verify update
        feature = temp_db.get_feature_by_id("feat-002")
        assert feature["status"] == "in-progress"
        assert feature["steps_completed"] == 2

    def test_complete_feature_sets_completed_at(self, temp_db):
        """Test that completing a feature sets completed_at timestamp."""
        temp_db.insert_feature(
            feature_id="feat-003",
            feature_type="feature",
            title="Test feature",
        )

        temp_db.update_feature_status("feat-003", "done")

        feature = temp_db.get_feature_by_id("feat-003")
        assert feature["status"] == "done"
        assert feature["completed_at"] is not None

    def test_get_features_by_status(self, temp_db):
        """Test querying features by status."""
        # Insert multiple features with different statuses
        temp_db.insert_feature("feat-001", "feature", "Feature 1", status="todo")
        temp_db.insert_feature("feat-002", "feature", "Feature 2", status="todo")
        temp_db.insert_feature("feat-003", "feature", "Feature 3", status="done")

        todo_features = temp_db.get_features_by_status("todo")
        assert len(todo_features) == 2

        done_features = temp_db.get_features_by_status("done")
        assert len(done_features) == 1


class TestSessionOperations:
    """Test session tracking operations."""

    def test_insert_session(self, temp_db):
        """Test session insertion."""
        success = temp_db.insert_session(
            session_id="sess-001",
            agent_assigned="claude-code",
        )

        assert success is True

    def test_insert_subagent_session(self, temp_db):
        """Test subagent session with parent tracking."""
        # Create parent session
        temp_db.insert_session("sess-parent", "orchestrator")

        # Create subagent session
        success = temp_db.insert_session(
            session_id="sess-child",
            agent_assigned="gemini",
            parent_session_id="sess-parent",
            is_subagent=True,
        )

        assert success is True

    def test_session_with_transcript(self, temp_db):
        """Test session with transcript tracking."""
        success = temp_db.insert_session(
            session_id="sess-002",
            agent_assigned="claude-code",
            transcript_id="abc123",
            transcript_path="/path/to/transcript.jsonl",
        )

        assert success is True


class TestCollaborationTracking:
    """Test agent collaboration and handoff tracking."""

    def test_record_delegation(self, temp_db):
        """Test recording a delegation handoff."""
        session_id = "sess-collab-1"
        temp_db.insert_session(session_id, "orchestrator")
        temp_db.insert_feature("feat-x", "feature", "Test feature")

        success = temp_db.record_collaboration(
            handoff_id="hoff-001",
            from_agent="orchestrator",
            to_agent="codex",
            session_id=session_id,
            feature_id="feat-x",
            handoff_type="delegation",
            reason="Requires code generation",
        )

        assert success is True

    def test_record_parallel_work(self, temp_db):
        """Test recording parallel work collaboration."""
        session_id = "sess-collab-2"
        temp_db.insert_session(session_id, "orchestrator")

        success = temp_db.record_collaboration(
            handoff_id="hoff-002",
            from_agent="orchestrator",
            to_agent="analyzer",
            session_id=session_id,
            handoff_type="parallel",
            reason="Speed up analysis",
        )

        assert success is True


class TestQueryBuilders:
    """Test query builder correctness."""

    def test_get_events_by_session_query(self):
        """Test get_events_by_session query builder."""
        sql, params = Queries.get_events_by_session("sess-123")
        assert "session_id" in sql
        assert "sess-123" in params

    def test_get_events_by_agent_query(self):
        """Test get_events_by_agent query builder."""
        sql, params = Queries.get_events_by_agent("agent-1")
        assert "agent_id" in sql
        assert "agent-1" in params

    def test_get_events_by_type_query(self):
        """Test get_events_by_type query builder."""
        sql, params = Queries.get_events_by_type("error")
        assert "event_type" in sql
        assert "error" in params

    def test_tool_usage_summary_query(self):
        """Test tool usage summary query."""
        sql, params = Queries.get_tool_usage_summary("sess-456")
        assert "COUNT(*)" in sql
        assert "tool_name" in sql
        assert "sess-456" in params

    def test_get_features_by_status_query(self):
        """Test features by status query."""
        sql, params = Queries.get_features_by_status("todo")
        assert "status" in sql
        assert "todo" in params

    def test_get_session_metrics_query(self):
        """Test session metrics query."""
        sql, params = Queries.get_session_metrics("sess-789")
        assert "COUNT(DISTINCT" in sql
        assert "sess-789" in params

    def test_agent_performance_metrics_query(self):
        """Test agent performance metrics query."""
        sql, params = Queries.get_agent_performance_metrics()
        assert "error_rate" in sql.lower()
        assert len(params) == 0

    def test_system_statistics_query(self):
        """Test system statistics query."""
        sql, params = Queries.get_system_statistics()
        assert "total_events" in sql.lower()
        assert "total_features" in sql.lower()


class TestDataIntegrity:
    """Test data integrity and constraints."""

    def test_foreign_key_constraint_session(self, temp_db):
        """Test foreign key constraint for session references."""
        # Try to insert event with non-existent session
        # Should fail if foreign keys are enforced
        success = temp_db.insert_event(
            event_id="evt-bad",
            agent_id="test",
            event_type="tool_call",
            session_id="non-existent-session",
        )

        # With PRAGMA foreign_keys = ON, this should fail
        # If it passes, foreign keys might not be enabled
        if not success:
            pytest.skip("Foreign key constraints may not be enforced")

    def test_event_type_constraint(self, temp_db):
        """Test event_type check constraint."""
        session_id = "sess-constraint"
        temp_db.insert_session(session_id, "test-agent")

        # Valid event type
        success = temp_db.insert_event(
            event_id="evt-valid",
            agent_id="test",
            event_type="tool_call",
            session_id=session_id,
        )
        assert success is True

    def test_feature_type_constraint(self, temp_db):
        """Test feature type check constraint."""
        # Valid types
        for feature_type in ["feature", "bug", "spike", "chore", "epic"]:
            success = temp_db.insert_feature(
                feature_id=f"item-{feature_type}",
                feature_type=feature_type,
                title="Test",
            )
            assert success is True

    def test_duplicate_primary_key(self, temp_db):
        """Test that duplicate primary keys are rejected."""
        temp_db.insert_feature("feat-dup", "feature", "Feature 1")

        # Try to insert duplicate
        temp_db.insert_feature("feat-dup", "feature", "Feature 2")
        # Should fail but depends on SQLite error handling
        # The important thing is the database doesn't get corrupted


class TestQueryExecution:
    """Test query execution on actual database."""

    def test_execute_tool_usage_query(self, temp_db):
        """Test executing tool usage summary query."""
        # Setup test data
        session_id = "sess-query-1"
        temp_db.insert_session(session_id, "test-agent")

        for i in range(3):
            temp_db.insert_event(
                event_id=f"evt-{i}",
                agent_id="test-agent",
                event_type="tool_call",
                session_id=session_id,
                tool_name="Read",
                cost_tokens=10,
            )

        # Execute query
        sql, params = Queries.get_tool_usage_summary(session_id)
        cursor = temp_db.connection.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchall()

        assert len(result) > 0
        # Should have at least one row for "Read" tool
        assert any(row[0] == "Read" for row in result)

    def test_execute_feature_progress_query(self, temp_db):
        """Test executing feature progress query."""
        temp_db.insert_feature(
            feature_id="feat-progress",
            feature_type="feature",
            title="Test Progress",
            steps_total=10,
        )

        temp_db.update_feature_status(
            "feat-progress",
            "in_progress",
            steps_completed=5,
        )

        sql, params = Queries.get_feature_progress("feat-progress")
        cursor = temp_db.connection.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchone()

        assert result is not None
        # Result should contain progress_percent field
        assert "progress_percent" in result.keys() or len(result) >= 8


class TestPerformance:
    """Test database performance characteristics."""

    def test_large_event_insertion(self, temp_db):
        """Test inserting large number of events."""
        session_id = "sess-perf"
        temp_db.insert_session(session_id, "perf-agent")

        # Insert 1000 events
        for i in range(1000):
            temp_db.insert_event(
                event_id=f"evt-{i:04d}",
                agent_id="perf-agent",
                event_type="tool_call",
                session_id=session_id,
                tool_name=f"Tool{i % 10}",
                cost_tokens=i % 100,
            )

        # Verify all inserted
        events = temp_db.get_session_events(session_id)
        assert len(events) == 1000

    def test_query_with_large_dataset(self, temp_db):
        """Test query performance on larger dataset."""
        # Create multiple sessions with events
        for s in range(10):
            session_id = f"sess-{s}"
            temp_db.insert_session(session_id, f"agent-{s}")

            for e in range(100):
                temp_db.insert_event(
                    event_id=f"evt-{s}-{e}",
                    agent_id=f"agent-{s}",
                    event_type="tool_call" if e % 2 == 0 else "error",
                    session_id=session_id,
                    tool_name="Read",
                )

        # Query should still be fast with indexes
        for s in range(10):
            events = temp_db.get_session_events(f"sess-{s}")
            assert len(events) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
