"""
Test parent-child event linking for nested tracing.

Verifies that:
1. Child events have parent_event_id set correctly
2. Environment variable mechanism works for cross-process linking
3. Parent activity state file mechanism works for same-process linking
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.hooks.event_tracker import (
    load_parent_activity,
    save_parent_activity,
    track_event,
)


@pytest.fixture(autouse=True)
def clean_env_vars():
    """Clean up environment variables before and after each test."""
    # Clean before test
    for var in [
        "HTMLGRAPH_PARENT_EVENT",
        "HTMLGRAPH_PARENT_ACTIVITY",
        "HTMLGRAPH_PARENT_SESSION",
        "HTMLGRAPH_PARENT_SESSION_ID",
    ]:
        os.environ.pop(var, None)
    yield
    # Clean after test
    for var in [
        "HTMLGRAPH_PARENT_EVENT",
        "HTMLGRAPH_PARENT_ACTIVITY",
        "HTMLGRAPH_PARENT_SESSION",
        "HTMLGRAPH_PARENT_SESSION_ID",
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
        # Create a proper mock session with all required attributes explicitly set
        mock_session = MagicMock()
        mock_session.id = "sess-test-123"
        mock_session.agent = "claude-code"
        mock_session.is_subagent = False
        mock_session.transcript_id = None
        mock_session.transcript_path = None
        instance.get_active_session.return_value = mock_session
        instance.track_activity.return_value = MagicMock(
            id="evt-child-001", drift_score=None
        )
        mock.return_value = instance
        yield instance


def test_parent_activity_file_mechanism(temp_graph_dir):
    """Test parent activity state persistence via file."""
    # Save parent activity
    parent_id = "evt-parent-001"
    save_parent_activity(temp_graph_dir, parent_id, "Task")

    # Load parent activity
    state = load_parent_activity(temp_graph_dir)
    assert state["parent_id"] == parent_id
    assert state["tool"] == "Task"

    # Clear parent activity
    save_parent_activity(temp_graph_dir, None)
    state = load_parent_activity(temp_graph_dir)
    assert state == {}


def test_parent_event_from_environment(temp_graph_dir, mock_session_manager):
    """Test parent event ID from HTMLGRAPH_PARENT_EVENT environment variable."""
    # Create parent event in database first
    parent_event_id = "evt-parent-002"
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

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

    try:
        # Create mock hook input for child Read event
        hook_input = {
            "cwd": str(temp_graph_dir.parent),
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": {"content": "file contents"},
        }

        # Track event (this should link to parent via environment variable)
        with patch("htmlgraph.hooks.event_tracker.resolve_project_path") as mock_path:
            mock_path.return_value = str(temp_graph_dir.parent)
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


def test_parent_event_from_activity_state(temp_graph_dir, mock_session_manager):
    """Test parent event ID from parent-activity.json state file."""
    # Create parent event in database first
    parent_event_id = "evt-parent-003"
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

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

    # Save parent activity state (this will be read by track_event)
    save_parent_activity(temp_graph_dir, parent_event_id, "Task")

    # Create mock hook input
    hook_input = {
        "cwd": str(temp_graph_dir.parent),
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/test/file.py",
            "old_string": "old",
            "new_string": "new",
        },
        "tool_response": {"success": True},
    }

    # Track event (this should link to parent via state file)
    with patch("htmlgraph.hooks.event_tracker.resolve_project_path") as mock_path:
        mock_path.return_value = str(temp_graph_dir.parent)
        track_event("PostToolUse", hook_input)

    # Verify database has event with parent_event_id
    events = db.get_session_events("sess-test-123")

    # Find the Edit event
    edit_events = [e for e in events if e["tool_name"] == "Edit"]
    assert len(edit_events) > 0, "Edit event should be recorded"

    # Verify parent linking
    edit_event = edit_events[0]
    assert edit_event["parent_event_id"] == parent_event_id, (
        "Child event should have parent_event_id set from activity state"
    )


def test_task_event_creates_parent_context(temp_graph_dir, mock_session_manager):
    """Test that Task tool invocation creates parent context for subsequent events."""
    # Mock track_activity to return event with ID
    task_event_id = "evt-task-001"
    mock_session_manager.track_activity.return_value = MagicMock(
        id=task_event_id, drift_score=None
    )

    # Create mock Task hook input
    hook_input = {
        "cwd": str(temp_graph_dir.parent),
        "tool_name": "Task",
        "tool_input": {
            "description": "Test task delegation",
            "subagent_type": "general-purpose",
        },
        "tool_response": {"success": True},
    }

    # Track Task event
    with patch("htmlgraph.hooks.event_tracker.resolve_project_path") as mock_path:
        mock_path.return_value = str(temp_graph_dir.parent)
        track_event("PostToolUse", hook_input)

    # Verify parent activity state was saved
    state = load_parent_activity(temp_graph_dir)
    assert state["parent_id"] == task_event_id
    assert state["tool"] == "Task"


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


def test_environment_variable_takes_precedence(temp_graph_dir, mock_session_manager):
    """Test that environment variable takes precedence when both mechanisms exist."""
    # Create both parent events in database first
    env_parent_id = "evt-env-parent"
    file_parent_id = "evt-file-parent"
    db = HtmlGraphDB(str(temp_graph_dir / "index.sqlite"))

    # Create parent session
    db.insert_session("sess-test-123", "claude-code")

    # Create environment variable parent event
    db.insert_event(
        event_id=env_parent_id,
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-test-123",
        tool_name="Task",
        input_summary="Env parent task",
    )

    # Create file-based parent event
    db.insert_event(
        event_id=file_parent_id,
        agent_id="claude-code",
        event_type="tool_call",
        session_id="sess-test-123",
        tool_name="Task",
        input_summary="File parent task",
    )

    # Set up both mechanisms with different parent IDs
    os.environ["HTMLGRAPH_PARENT_EVENT"] = env_parent_id
    save_parent_activity(temp_graph_dir, file_parent_id, "Task")

    try:
        # Create mock hook input
        hook_input = {
            "cwd": str(temp_graph_dir.parent),
            "tool_name": "Bash",
            "tool_input": {"command": "echo test"},
            "tool_response": {"output": "test"},
        }

        # Track event
        with patch("htmlgraph.hooks.event_tracker.resolve_project_path") as mock_path:
            mock_path.return_value = str(temp_graph_dir.parent)
            track_event("PostToolUse", hook_input)

        # Verify environment variable was used
        events = db.get_session_events("sess-test-123")

        bash_events = [e for e in events if e["tool_name"] == "Bash"]
        assert len(bash_events) > 0

        # Environment variable should take precedence
        bash_event = bash_events[0]
        assert bash_event["parent_event_id"] == env_parent_id

    finally:
        os.environ.pop("HTMLGRAPH_PARENT_EVENT", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
