"""
Test parent-child event linking for subagent events.

Verifies that:
1. Events logged with HTMLGRAPH_PARENT_ACTIVITY env var capture parent_event_id
2. API endpoints return parent_event_id in event data
3. Hierarchical grouping correctly groups events by parent
4. Activity feed displays parent-child relationships
"""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from htmlgraph import SDK
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    db_path = f"/tmp/test_parent_events_{uuid4().hex}.db"
    db = HtmlGraphDB(db_path)
    db.connect()
    db.create_tables()
    yield db
    # Cleanup
    db.disconnect()
    if Path(db_path).exists():
        Path(db_path).unlink()


@pytest.fixture
def temp_htmlgraph_dir(tmp_path):
    """Create temporary .htmlgraph directory."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir()
    (htmlgraph_dir / "features").mkdir()
    (htmlgraph_dir / "bugs").mkdir()
    (htmlgraph_dir / "spikes").mkdir()
    (htmlgraph_dir / "patterns").mkdir()
    (htmlgraph_dir / "insights").mkdir()
    (htmlgraph_dir / "metrics").mkdir()
    (htmlgraph_dir / "todos").mkdir()
    (htmlgraph_dir / "task-delegations").mkdir()
    return htmlgraph_dir


class TestParentChildEventLinking:
    """Test parent-child event linking functionality."""

    def test_event_captures_parent_activity_env_var(
        self, temp_db, temp_htmlgraph_dir, tmp_path
    ):
        """Test that _log_event captures HTMLGRAPH_PARENT_ACTIVITY env var."""
        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="test-agent", db_path=db_path)

        # Simulate parent event
        parent_event_id = f"evt-{uuid4().hex[:12]}"

        # Set parent activity in environment
        os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = parent_event_id

        try:
            # Log child event
            result = sdk._log_event(
                event_type="tool_call",
                tool_name="Edit",
                input_summary="Edit test file",
                output_summary="File edited successfully",
            )

            # Verify event was logged
            assert result is True

            # Verify parent_event_id was captured
            cursor = sdk._db.connection.cursor()
            cursor.execute(
                "SELECT parent_event_id FROM agent_events WHERE tool_name = 'Edit' LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == parent_event_id
        finally:
            # Cleanup
            if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
                del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]
            sdk._db.disconnect()

    def test_event_without_parent_activity(self, temp_db, temp_htmlgraph_dir, tmp_path):
        """Test that events log successfully without parent activity."""
        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="test-agent", db_path=db_path)

        # Ensure parent activity is not set
        if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
            del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]

        try:
            # Log event without parent
            result = sdk._log_event(
                event_type="tool_call",
                tool_name="Read",
                input_summary="Read test file",
                output_summary="File read successfully",
            )

            # Verify event was logged
            assert result is True

            # Verify parent_event_id is NULL
            cursor = sdk._db.connection.cursor()
            cursor.execute(
                "SELECT parent_event_id FROM agent_events WHERE tool_name = 'Read' LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] is None
        finally:
            sdk._db.disconnect()

    def test_hierarchical_event_structure(self, temp_htmlgraph_dir, tmp_path):
        """Test that hierarchical event structure is correctly formed."""
        # DEBUG: Check env var state at test start
        import sys

        parent_activity_before = os.environ.get("HTMLGRAPH_PARENT_ACTIVITY")
        print(
            f"\n>>> TEST START: HTMLGRAPH_PARENT_ACTIVITY={parent_activity_before}",
            file=sys.stderr,
        )

        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="parent-agent", db_path=db_path)

        try:
            # Create parent event
            sdk._log_event(
                event_type="delegation",
                tool_name="Task",
                input_summary="Delegate task",
                output_summary="Task delegated",
            )

            # Get the event we just created to use as parent
            cursor = sdk._db.connection.cursor()
            cursor.execute(
                "SELECT event_id FROM agent_events WHERE tool_name = 'Task' LIMIT 1"
            )
            row = cursor.fetchone()
            assert row is not None
            parent_id = row[0]

            # Set as parent for child events
            os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = parent_id

            # Create child event 1
            sdk._log_event(
                event_type="tool_call",
                tool_name="Edit",
                input_summary="Child edit 1",
                output_summary="Completed",
            )

            # Create child event 2
            sdk._log_event(
                event_type="tool_call",
                tool_name="Read",
                input_summary="Child read 1",
                output_summary="Completed",
            )

            # Verify hierarchy in database
            # Order by rowid ASC for reliable insertion order (timestamp may be identical)
            cursor.execute(
                "SELECT event_id, parent_event_id FROM agent_events ORDER BY rowid ASC"
            )
            rows = cursor.fetchall()

            # Should have 3 events: 1 parent, 2 children
            assert len(rows) == 3

            # Parent should have no parent
            assert rows[0][1] is None

            # Children should reference parent
            assert rows[1][1] == parent_id
            assert rows[2][1] == parent_id
        finally:
            if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
                del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]
            sdk._db.disconnect()

    def test_event_model_includes_parent_event_id(self, temp_htmlgraph_dir, tmp_path):
        """Test that EventModel includes parent_event_id field."""
        from htmlgraph.api.main import EventModel

        # Create test event data with parent_event_id
        parent_id = f"evt-{uuid4().hex[:12]}"
        event_model = EventModel(
            event_id="evt-123",
            agent_id="test-agent",
            event_type="tool_call",
            timestamp="2024-01-01T00:00:00",
            tool_name="Edit",
            input_summary="Test input",
            output_summary="Test output",
            session_id="sess-123",
            parent_event_id=parent_id,
            status="completed",
            model="claude-haiku-4-5-20251001",
        )

        # Verify parent_event_id is captured
        assert event_model.parent_event_id == parent_id
        # Verify model field is captured
        assert event_model.model == "claude-haiku-4-5-20251001"

    def test_api_events_query_includes_parent_event_id(
        self, temp_htmlgraph_dir, tmp_path
    ):
        """Test that /api/events endpoint returns parent_event_id."""
        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="test-agent", db_path=db_path)

        try:
            # Create parent event
            sdk._log_event(
                event_type="delegation",
                tool_name="Task",
                input_summary="Parent task",
                output_summary="Task created",
            )

            # Get parent event ID
            cursor = sdk._db.connection.cursor()
            cursor.execute(
                "SELECT event_id FROM agent_events WHERE tool_name = 'Task' LIMIT 1"
            )
            parent_id = cursor.fetchone()[0]

            # Create child event
            os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = parent_id
            sdk._log_event(
                event_type="tool_call",
                tool_name="Edit",
                input_summary="Child event",
                output_summary="Completed",
            )

            # Query events directly from database (simulating API query)
            # Order by rowid DESC for reliable insertion order (timestamp may be identical)
            cursor.execute(
                "SELECT event_id, parent_event_id FROM agent_events ORDER BY rowid DESC LIMIT 10"
            )
            rows = cursor.fetchall()

            # Verify we have parent and child events
            assert len(rows) == 2

            # Verify child has parent reference
            child_event = rows[0]  # Most recent (child)
            parent_event = rows[1]  # Older (parent)

            assert (
                child_event[1] == parent_event[0]
            )  # child.parent_event_id == parent.event_id
        finally:
            if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
                del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]
            sdk._db.disconnect()

    def test_deep_nesting_hierarchy(self, temp_htmlgraph_dir, tmp_path):
        """Test deep nesting: grandparent -> parent -> child."""
        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="test-agent", db_path=db_path)

        try:
            # Create grandparent event
            sdk._log_event(
                event_type="delegation",
                tool_name="Task",
                input_summary="Grandparent task",
            )

            cursor = sdk._db.connection.cursor()
            cursor.execute(
                "SELECT event_id FROM agent_events WHERE tool_name = 'Task' LIMIT 1"
            )
            grandparent_id = cursor.fetchone()[0]

            # Create parent event (child of grandparent)
            os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = grandparent_id
            sdk._log_event(
                event_type="delegation",
                tool_name="Task",
                input_summary="Parent task",
            )

            cursor.execute(
                "SELECT event_id FROM agent_events WHERE tool_name = 'Task' ORDER BY rowid DESC LIMIT 1"
            )
            parent_id = cursor.fetchone()[0]

            # Create child event (child of parent)
            os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = parent_id
            sdk._log_event(
                event_type="tool_call",
                tool_name="Edit",
                input_summary="Child event",
            )

            # Verify hierarchy
            # Order by rowid ASC for reliable insertion order (timestamp may be identical)
            cursor.execute(
                "SELECT event_id, parent_event_id FROM agent_events ORDER BY rowid ASC"
            )
            rows = cursor.fetchall()

            assert len(rows) == 3
            assert rows[0][1] is None  # grandparent has no parent
            assert rows[1][1] == rows[0][0]  # parent's parent is grandparent
            assert rows[2][1] == rows[1][0]  # child's parent is parent
        finally:
            if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
                del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]
            sdk._db.disconnect()

    def test_sibling_events_same_parent(self, temp_htmlgraph_dir, tmp_path):
        """Test that sibling events share same parent."""
        db_path = str(tmp_path / "test.db")
        sdk = SDK(directory=temp_htmlgraph_dir, agent="test-agent", db_path=db_path)

        try:
            # Create parent event
            sdk._log_event(
                event_type="delegation", tool_name="Task", input_summary="Parent"
            )

            cursor = sdk._db.connection.cursor()
            cursor.execute("SELECT event_id FROM agent_events WHERE tool_name = 'Task'")
            parent_id = cursor.fetchone()[0]

            # Create multiple child events
            os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = parent_id

            for i in range(3):
                sdk._log_event(
                    event_type="tool_call",
                    tool_name=f"Tool{i}",
                    input_summary=f"Sibling {i}",
                )

            # Verify all siblings share same parent
            cursor.execute(
                "SELECT parent_event_id FROM agent_events WHERE tool_name LIKE 'Tool%'"
            )
            rows = cursor.fetchall()

            assert len(rows) == 3
            assert all(row[0] == parent_id for row in rows)
        finally:
            if "HTMLGRAPH_PARENT_ACTIVITY" in os.environ:
                del os.environ["HTMLGRAPH_PARENT_ACTIVITY"]
            sdk._db.disconnect()
