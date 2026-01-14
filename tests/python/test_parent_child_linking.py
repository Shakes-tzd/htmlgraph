"""
Test parent-child event linking for nested tracing.

Verifies that:
1. Child events have parent_event_id set correctly
2. Environment variable mechanism works for cross-process linking
3. Database schema supports parent-child relationships
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.hooks.event_tracker import track_event


@pytest.fixture(autouse=True)
def clean_env_vars():
    """Clean up environment variables before and after each test."""
    # Clean before test
    for var in [
        "HTMLGRAPH_PARENT_EVENT",
        "HTMLGRAPH_PARENT_ACTIVITY",
        "HTMLGRAPH_PARENT_SESSION",
        "HTMLGRAPH_PARENT_SESSION_ID",
        "HTMLGRAPH_PROJECT_ROOT",
    ]:
        os.environ.pop(var, None)
    yield
    # Clean after test
    for var in [
        "HTMLGRAPH_PARENT_EVENT",
        "HTMLGRAPH_PARENT_ACTIVITY",
        "HTMLGRAPH_PARENT_SESSION",
        "HTMLGRAPH_PARENT_SESSION_ID",
        "HTMLGRAPH_PROJECT_ROOT",
    ]:
        os.environ.pop(var, None)


@pytest.fixture
def temp_graph_dir():
    """Create temporary .htmlgraph directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir(parents=True)
        yield graph_dir


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager to avoid file I/O."""
    with patch("htmlgraph.hooks.event_tracker.SessionManager") as mock:
        instance = MagicMock()

        # Create a proper mock session with all required attributes as real values
        # NOT MagicMock objects (to avoid SQLite binding errors)
        mock_session = MagicMock(
            spec=["id", "agent", "is_subagent", "transcript_id", "transcript_path"]
        )
        # Use spec to prevent MagicMock from auto-creating attributes
        mock_session.id = "sess-test-123"
        mock_session.agent = "claude-code"
        mock_session.is_subagent = False
        mock_session.transcript_id = None
        mock_session.transcript_path = None

        # Mock the session converter for loading sessions
        instance.session_converter = MagicMock()
        instance.session_converter.load.return_value = mock_session

        instance.get_active_session.return_value = mock_session
        instance.track_activity.return_value = MagicMock(
            id="evt-child-001", drift_score=None, feature_id=None
        )
        mock.return_value = instance
        yield instance


def test_parent_event_id_column_exists(temp_graph_dir):
    """Test that parent_event_id column exists in database schema."""
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

    # Create session
    db.insert_session("sess-test-schema", "claude-code")

    # Insert event with parent_event_id
    db.insert_event(
        event_id="evt-child-001",
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-test-schema",
        tool_name="Read",
        input_summary="Test read",
        parent_event_id="evt-parent-001",  # This column should exist
    )

    # Verify it was stored correctly
    events = db.get_session_events("sess-test-schema")
    assert len(events) == 1
    assert events[0]["parent_event_id"] == "evt-parent-001"


def test_parent_event_from_environment(temp_graph_dir, mock_session_manager):
    """Test parent event ID from HTMLGRAPH_PARENT_EVENT environment variable."""
    # Create parent event in database first
    parent_event_id = "evt-parent-002"

    # Use htmlgraph.db instead of index.sqlite (unified database)
    db_path = str(temp_graph_dir / "htmlgraph.db")
    db = HtmlGraphDB(db_path)

    # Create parent session
    db.insert_session("sess-test-123", "claude-code")

    # Create parent Task event
    db.insert_event(
        event_id=parent_event_id,
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-test-123",
        tool_name="Task",
        input_summary="Parent task",
    )

    # Set up environment with parent event ID
    os.environ["HTMLGRAPH_PARENT_EVENT"] = parent_event_id
    # CRITICAL: Set project root so get_database_path() finds our test database
    os.environ["HTMLGRAPH_PROJECT_ROOT"] = str(temp_graph_dir.parent)

    try:
        # Create mock hook input for child Read event
        hook_input = {
            "cwd": str(temp_graph_dir.parent),
            "session_id": "sess-test-123",  # Provide session_id in hook_input
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": {"content": "file contents"},
        }

        # Track event (this should link to parent via environment variable)
        # Patch both resolve_project_path AND get_database_path to use test database
        # Note: get_database_path is imported inside track_event from htmlgraph.config
        with (
            patch("htmlgraph.hooks.event_tracker.resolve_project_path") as mock_path,
            patch("htmlgraph.config.get_database_path") as mock_db_path,
        ):
            mock_path.return_value = str(temp_graph_dir.parent)
            mock_db_path.return_value = db_path
            track_event("PostToolUse", hook_input)

        # Verify database has event with parent_event_id
        events = db.get_session_events("sess-test-123")

        # Find the Read event
        read_events = [e for e in events if e["tool_name"] == "Read"]
        assert len(read_events) > 0, "Read event should be recorded"

        # Verify parent linking
        read_event = read_events[0]
        assert read_event["parent_event_id"] == parent_event_id, (
            "Child event should have parent_event_id set from environment"
        )

    finally:
        # Clean up environment
        os.environ.pop("HTMLGRAPH_PARENT_EVENT", None)
        os.environ.pop("HTMLGRAPH_PROJECT_ROOT", None)


def test_parent_child_query_by_parent_id(temp_graph_dir):
    """Test querying child events by parent_event_id."""
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

    # Create session
    db.insert_session("sess-query-test", "claude-code")

    # Create parent event
    parent_id = "evt-parent-query"
    db.insert_event(
        event_id=parent_id,
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-query-test",
        tool_name="Task",
        input_summary="Parent task",
        parent_event_id=None,  # Root level
    )

    # Create multiple child events
    for i in range(3):
        db.insert_event(
            event_id=f"evt-child-{i}",
            agent_id="claude-code",
            event_type="tool_call",
            session_id="sess-query-test",
            tool_name="Read",
            input_summary=f"Child read {i}",
            parent_event_id=parent_id,  # Link to parent
        )

    # Query children by parent
    cursor = db.connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
        (parent_id,),
    )
    child_count = cursor.fetchone()[0]
    assert child_count == 3, "Parent should have 3 child events"


def test_null_parent_event_id_for_root_events(temp_graph_dir):
    """Test that root-level events have NULL parent_event_id."""
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

    # Create session
    db.insert_session("sess-root-test", "claude-code")

    # Create root-level event (no parent)
    db.insert_event(
        event_id="evt-root-001",
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-root-test",
        tool_name="Task",
        input_summary="Root task",
        parent_event_id=None,  # Explicitly NULL
    )

    # Verify it was stored with NULL parent
    events = db.get_session_events("sess-root-test")
    assert len(events) == 1
    assert events[0]["parent_event_id"] is None


def test_nested_event_hierarchy(temp_graph_dir):
    """Test complete nested event hierarchy: Task -> Read -> Edit."""
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

    # Create session
    session_id = "sess-nested-001"
    db.insert_session(session_id, "claude-code")

    # 1. Parent Task event
    parent_task_id = "evt-task-parent"
    db.insert_event(
        event_id=parent_task_id,
        agent_id="claude-code",
        event_type="tool_call",
        session_id=session_id,
        tool_name="Task",
        input_summary="Task: Delegate to subagent",
        output_summary="Task started",
        parent_event_id=None,  # Root level
    )

    # 2. Child Read event
    child_read_id = "evt-read-child"
    db.insert_event(
        event_id=child_read_id,
        agent_id="general-purpose",
        event_type="tool_call",
        session_id=session_id,
        tool_name="Read",
        input_summary="Read: /test/file.py",
        output_summary="File contents",
        parent_event_id=parent_task_id,  # Links to Task
    )

    # 3. Child Edit event
    child_edit_id = "evt-edit-child"
    db.insert_event(
        event_id=child_edit_id,
        agent_id="general-purpose",
        event_type="tool_call",
        session_id=session_id,
        tool_name="Edit",
        input_summary="Edit: /test/file.py",
        output_summary="File edited",
        parent_event_id=parent_task_id,  # Also links to Task
    )

    # Query and verify hierarchy
    events = db.get_session_events(session_id)
    assert len(events) == 3

    # Verify parent has no parent
    task_event = next(e for e in events if e["event_id"] == parent_task_id)
    assert task_event["parent_event_id"] is None

    # Verify children have correct parent
    read_event = next(e for e in events if e["event_id"] == child_read_id)
    assert read_event["parent_event_id"] == parent_task_id

    edit_event = next(e for e in events if e["event_id"] == child_edit_id)
    assert edit_event["parent_event_id"] == parent_task_id

    # Query children by parent
    cursor = db.connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
        (parent_task_id,),
    )
    child_count = cursor.fetchone()[0]
    assert child_count == 2, "Task should have 2 child events"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
