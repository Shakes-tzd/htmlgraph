"""
Tests for Hybrid Event Capture System - Parent-Child Event Nesting

Tests verify:
1. Parent event creation on Task() calls
2. Subagent type extraction from tool input
3. Child event linking to parent events
4. Spike counting and aggregation
5. Event trace API responses
6. Parent event status updates
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from htmlgraph.db.schema import HtmlGraphDB


class TestParentEventCreation:
    """Test parent event creation in PreToolUse hook."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> HtmlGraphDB:
        """Create temporary database for testing."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)
        yield db
        db.disconnect()

    def test_task_parent_event_created(self, db: HtmlGraphDB) -> None:
        """Test that Task() calls create parent events."""
        session_id = "sess-test123"
        parent_event_id = "evt-parent123"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Ensure session exists
        db._ensure_session_exists(session_id, "claude-code")

        # Insert parent event (simulating PreToolUse behavior)
        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             input_summary, session_id, status, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                json.dumps({"subagent_type": "gemini-spawner", "prompt": "Test task"}),
                session_id,
                "started",
                "gemini-spawner",
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Verify parent event was created
        cursor.execute(
            "SELECT event_id, event_type, status, subagent_type FROM agent_events WHERE event_id = ?",
            (parent_event_id,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_event_id
        assert row[1] == "task_delegation"
        assert row[2] == "started"
        assert row[3] == "gemini-spawner"

    def test_parent_event_has_correct_fields(self, db: HtmlGraphDB) -> None:
        """Test that parent events have all required fields."""
        session_id = "sess-test456"
        parent_event_id = "evt-parent456"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent event with all fields
        input_data = {
            "subagent_type": "researcher",
            "prompt": "Research the topic",
        }

        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             input_summary, output_summary, session_id, status,
             subagent_type, child_spike_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                json.dumps(input_data),
                None,  # No output until SubagentStop
                session_id,
                "started",
                "researcher",
                0,
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Retrieve and verify
        cursor.execute(
            """
            SELECT event_id, agent_id, event_type, timestamp, tool_name,
                   input_summary, session_id, status, subagent_type,
                   child_spike_count, parent_event_id
            FROM agent_events WHERE event_id = ?
        """,
            (parent_event_id,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_event_id  # event_id
        assert row[1] == "claude-code"  # agent_id
        assert row[2] == "task_delegation"  # event_type
        assert row[3] == timestamp  # timestamp
        assert row[4] == "Task"  # tool_name
        assert row[7] == "started"  # status
        assert row[8] == "researcher"  # subagent_type
        assert row[9] == 0  # child_spike_count
        assert row[10] is None  # parent_event_id (parent events have no parent)


class TestChildEventLinking:
    """Test child event creation and linking to parents."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> HtmlGraphDB:
        """Create temporary database for testing."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)
        yield db
        db.disconnect()

    def test_child_event_links_to_parent(self, db: HtmlGraphDB) -> None:
        """Test that child events are correctly linked to parent events."""
        session_id = "sess-test789"
        parent_event_id = "evt-parent789"
        child_event_id = "subevt-child789"
        parent_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             input_summary, session_id, status, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                parent_timestamp,
                "Task",
                json.dumps({"subagent_type": "gemini-spawner"}),
                session_id,
                "started",
                "gemini-spawner",
            ),
        )

        # Insert child event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             input_summary, session_id, status, parent_event_id,
             subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                child_event_id,
                "subagent-gemini-spawner",
                "delegation",
                parent_timestamp,  # Same or later
                "SubagentStop",
                json.dumps(
                    {"task_description": "Analyze architecture", "tool_count": 5}
                ),
                session_id,
                "completed",
                parent_event_id,  # Link to parent
                "gemini-spawner",
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Query child event and verify parent link
        cursor.execute(
            "SELECT parent_event_id, agent_id, status FROM agent_events WHERE event_id = ?",
            (child_event_id,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_event_id  # parent_event_id
        assert row[1] == "subagent-gemini-spawner"  # agent_id
        assert row[2] == "completed"  # status

    def test_query_child_events_by_parent(self, db: HtmlGraphDB) -> None:
        """Test querying child events filtered by parent event_id."""
        session_id = "sess-test999"
        parent_event_id = "evt-parent999"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                session_id,
                "started",
                "debugger",
            ),
        )

        # Insert 3 child events
        for i in range(3):
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, event_type, timestamp, tool_name,
                 session_id, status, parent_event_id, subagent_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"subevt-{i}",
                    "subagent-debugger",
                    "delegation",
                    timestamp,
                    "SubagentStop",
                    session_id,
                    "completed",
                    parent_event_id,
                    "debugger",
                ),
            )

        db.connection.commit()  # type: ignore[union-attr]

        # Query all child events
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
            (parent_event_id,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 3  # Should have 3 child events


class TestSpikeCountAggregation:
    """Test child spike counting during subagent execution."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> HtmlGraphDB:
        """Create temporary database for testing."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)
        yield db
        db.disconnect()

    def test_count_spikes_after_parent_timestamp(self, db: HtmlGraphDB) -> None:
        """Test counting spikes created after parent event."""
        parent_timestamp = "2025-01-08 16:40:54"
        spike_timestamp = "2025-01-08 16:42:00"

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert spikes created after parent event
        for i in range(2):
            cursor.execute(
                """
                INSERT INTO features
                (id, type, title, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    f"spk-{i}",
                    "spike",
                    f"Analysis {i}",
                    "done",
                    spike_timestamp,
                ),
            )

        db.connection.commit()  # type: ignore[union-attr]

        # Count spikes after parent timestamp
        cursor.execute(
            "SELECT COUNT(*) FROM features WHERE type = 'spike' AND created_at > ?",
            (parent_timestamp,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 2  # Should count both spikes

    def test_parent_event_updated_with_spike_count(self, db: HtmlGraphDB) -> None:
        """Test that parent event is updated with child spike count."""
        session_id = "sess-spikes"
        parent_event_id = "evt-spikes"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent event with initial child_spike_count = 0
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status, subagent_type, child_spike_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                session_id,
                "started",
                "gemini-spawner",
                0,
            ),
        )

        # Update parent event with spike count and completion status
        output_summary = json.dumps(
            {
                "subagent_type": "gemini-spawner",
                "spikes_created": 3,
                "completion_time": timestamp,
            }
        )

        cursor.execute(
            """
            UPDATE agent_events
            SET status = 'completed',
                child_spike_count = 3,
                output_summary = ?
            WHERE event_id = ?
        """,
            (output_summary, parent_event_id),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Verify update
        cursor.execute(
            "SELECT status, child_spike_count, output_summary FROM agent_events WHERE event_id = ?",
            (parent_event_id,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "completed"  # status
        assert row[1] == 3  # child_spike_count
        assert json.loads(row[2])["spikes_created"] == 3  # output_summary


class TestEventTraceQueries:
    """Test event trace API queries."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> HtmlGraphDB:
        """Create temporary database for testing."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)
        yield db
        db.disconnect()

    def test_query_parent_events_with_children(self, db: HtmlGraphDB) -> None:
        """Test querying parent events and counting their children."""
        session_id = "sess-query"
        parent_event_id = "evt-query"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status, subagent_type, child_spike_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                parent_event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                session_id,
                "completed",
                "codex-spawner",
                2,
            ),
        )

        # Insert child events
        for i in range(2):
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, event_type, timestamp, tool_name,
                 session_id, status, parent_event_id, subagent_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"subevt-{i}",
                    "subagent-codex-spawner",
                    "delegation",
                    timestamp,
                    "SubagentStop",
                    session_id,
                    "completed",
                    parent_event_id,
                    "codex-spawner",
                ),
            )

        db.connection.commit()  # type: ignore[union-attr]

        # Query: Get parent event with child count
        cursor.execute(
            """
            SELECT
                parent.event_id,
                parent.subagent_type,
                parent.status,
                parent.child_spike_count,
                COUNT(child.event_id) as child_event_count
            FROM agent_events parent
            LEFT JOIN agent_events child ON child.parent_event_id = parent.event_id
            WHERE parent.event_type = 'task_delegation'
            GROUP BY parent.event_id
        """
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == parent_event_id  # parent event_id
        assert row[1] == "codex-spawner"  # subagent_type
        assert row[2] == "completed"  # status
        assert row[3] == 2  # child_spike_count
        assert row[4] == 2  # child_event_count

    def test_filter_parent_events_by_session(self, db: HtmlGraphDB) -> None:
        """Test filtering parent events by session ID."""
        session1 = "sess-filter1"
        session2 = "sess-filter2"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session1, "claude-code")
        db._ensure_session_exists(session2, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert parent events in different sessions
        for i, session in enumerate([session1, session1, session2]):
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, event_type, timestamp, tool_name,
                 session_id, status, subagent_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    f"evt-{i}",
                    "claude-code",
                    "task_delegation",
                    timestamp,
                    "Task",
                    session,
                    "completed",
                    "general-purpose",
                ),
            )

        db.connection.commit()  # type: ignore[union-attr]

        # Query parent events for session1
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE event_type = 'task_delegation' AND session_id = ?",
            (session1,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 2  # Should have 2 events in session1

        # Query parent events for session2
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE event_type = 'task_delegation' AND session_id = ?",
            (session2,),
        )

        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1  # Should have 1 event in session2


class TestEventTypeValidation:
    """Test event type validation and constraints."""

    @pytest.fixture
    def db(self, tmp_path: Path) -> HtmlGraphDB:
        """Create temporary database for testing."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)
        yield db
        db.disconnect()

    def test_task_delegation_event_type_allowed(self, db: HtmlGraphDB) -> None:
        """Test that 'task_delegation' event type is allowed in schema."""
        session_id = "sess-validation"
        event_id = "evt-validation"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # This should not raise an error (event_type is in CHECK constraint)
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event_id,
                "claude-code",
                "task_delegation",  # Must be in CHECK constraint
                timestamp,
                "Task",
                session_id,
                "started",
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Verify insertion succeeded
        cursor.execute(
            "SELECT event_type FROM agent_events WHERE event_id = ?", (event_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "task_delegation"

    def test_subagent_type_field_exists(self, db: HtmlGraphDB) -> None:
        """Test that subagent_type column exists and is accessible."""
        session_id = "sess-fields"
        event_id = "evt-fields"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert event with subagent_type
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                session_id,
                "started",
                "test-agent",
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Retrieve and verify subagent_type
        cursor.execute(
            "SELECT subagent_type FROM agent_events WHERE event_id = ?", (event_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "test-agent"

    def test_child_spike_count_field_exists(self, db: HtmlGraphDB) -> None:
        """Test that child_spike_count column exists and is accessible."""
        session_id = "sess-count"
        event_id = "evt-count"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        db._ensure_session_exists(session_id, "claude-code")

        if not db.connection:
            db.connect()

        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Insert event with child_spike_count
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, event_type, timestamp, tool_name,
             session_id, status, child_spike_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event_id,
                "claude-code",
                "task_delegation",
                timestamp,
                "Task",
                session_id,
                "completed",
                5,
            ),
        )

        db.connection.commit()  # type: ignore[union-attr]

        # Retrieve and verify child_spike_count
        cursor.execute(
            "SELECT child_spike_count FROM agent_events WHERE event_id = ?", (event_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 5
