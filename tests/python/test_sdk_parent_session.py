"""
Tests for SDK parent session support (Phase 1: Parent Session Tracking).

This module tests the ability of the SDK to accept and use parent session
context for activity tracking in nested Task() calls.
"""

import os
from pathlib import Path

import pytest
from htmlgraph import SDK
from htmlgraph.models import Session


@pytest.fixture
def temp_htmlgraph(tmp_path: Path) -> Path:
    """Create a temporary .htmlgraph directory."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir(exist_ok=True)

    # Create required subdirectories
    (htmlgraph_dir / "features").mkdir(exist_ok=True)
    (htmlgraph_dir / "sessions").mkdir(exist_ok=True)
    (htmlgraph_dir / "events").mkdir(exist_ok=True)
    (htmlgraph_dir / "bugs").mkdir(exist_ok=True)
    (htmlgraph_dir / "spikes").mkdir(exist_ok=True)

    return htmlgraph_dir


def test_sdk_with_parent_session_explicit(temp_htmlgraph: Path, isolated_db: Path):
    """Test SDK uses parent session for activity tracking (explicit parameter)."""
    # Create parent session
    parent_sdk = SDK(directory=temp_htmlgraph, agent="parent", db_path=str(isolated_db))
    _ = parent_sdk.start_session(session_id="sess-parent", title="Parent Session")

    # Create child SDK with parent session
    child_sdk = SDK(
        directory=temp_htmlgraph,
        agent="child",
        parent_session="sess-parent",
        db_path=str(isolated_db),
    )

    # Verify parent session is set
    assert child_sdk._parent_session == "sess-parent"

    # Track activity in child SDK - should go to parent session
    entry = child_sdk.track_activity(
        tool="TestTool", summary="Test activity from child", success=True
    )

    # Verify activity was tracked to parent session
    assert entry.payload is not None
    assert entry.payload.get("session_id") == "sess-parent"

    # Reload parent session and verify activity is there
    parent_sdk.reload()
    reloaded_parent = parent_sdk.session_manager.get_session("sess-parent")
    assert reloaded_parent is not None

    # Check events via event log
    events = reloaded_parent.get_events(events_dir=str(temp_htmlgraph / "events"))
    assert len(events) > 0
    assert any(e.get("tool") == "TestTool" for e in events)


def test_sdk_with_parent_from_env_var(temp_htmlgraph: Path, isolated_db: Path):
    """Test SDK reads parent session from environment variables."""
    # Set up environment variables
    os.environ["HTMLGRAPH_PARENT_SESSION"] = "sess-env-parent"
    os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = "evt-parent-task"

    try:
        # Create parent session
        parent_sdk = SDK(
            directory=temp_htmlgraph, agent="parent", db_path=str(isolated_db)
        )
        _ = parent_sdk.start_session(
            session_id="sess-env-parent", title="Env Parent Session"
        )

        # Create child SDK without explicit parent_session parameter
        child_sdk = SDK(
            directory=temp_htmlgraph, agent="child", db_path=str(isolated_db)
        )

        # Verify parent session was read from environment
        assert child_sdk._parent_session == "sess-env-parent"

        # Track activity
        entry = child_sdk.track_activity(
            tool="EnvTest", summary="Activity using env parent", success=True
        )

        # Verify parent activity ID was set from environment
        assert entry.parent_activity_id == "evt-parent-task"

        # Verify activity went to parent session
        assert entry.payload is not None
        assert entry.payload.get("session_id") == "sess-env-parent"

    finally:
        # Clean up environment
        os.environ.pop("HTMLGRAPH_PARENT_SESSION", None)
        os.environ.pop("HTMLGRAPH_PARENT_ACTIVITY", None)


def test_sdk_fallback_to_current_session(temp_htmlgraph: Path, isolated_db: Path):
    """Test SDK falls back to current session if no parent."""
    sdk = SDK(directory=temp_htmlgraph, agent="standalone", db_path=str(isolated_db))

    # Verify no parent session is set
    assert sdk._parent_session is None

    # Start a session for the SDK agent
    _ = sdk.start_session(session_id="sess-standalone", title="Standalone Session")

    # Track activity - should use current session
    entry = sdk.track_activity(
        tool="StandaloneTest", summary="Activity without parent", success=True
    )

    # Verify activity went to the current session
    assert entry.payload is not None
    assert entry.payload.get("session_id") == "sess-standalone"

    # Verify via session manager
    sdk.reload()
    current_session = sdk.session_manager.get_session("sess-standalone")
    assert current_session is not None

    events = current_session.get_events(events_dir=str(temp_htmlgraph / "events"))
    assert len(events) > 0
    assert any(e.get("tool") == "StandaloneTest" for e in events)


def test_session_model_parent_fields(temp_htmlgraph: Path):
    """Test Session model includes parent session metadata fields."""
    # Create a session with parent metadata
    session = Session(
        id="sess-child",
        agent="child-agent",
        parent_session="sess-parent",
        parent_activity="evt-123",
        nesting_depth=2,
    )

    # Verify fields are present
    assert session.parent_session == "sess-parent"
    assert session.parent_activity == "evt-123"
    assert session.nesting_depth == 2

    # Test serialization to HTML includes parent attributes
    html = session.to_html()
    assert 'data-parent-session="sess-parent"' in html
    assert 'data-parent-activity="evt-123"' in html
    assert 'data-nesting-depth="2"' in html


def test_parent_session_with_explicit_override(temp_htmlgraph: Path, isolated_db: Path):
    """Test explicit session_id parameter overrides parent session."""
    # Set up parent session
    parent_sdk = SDK(directory=temp_htmlgraph, agent="parent", db_path=str(isolated_db))
    _ = parent_sdk.start_session(session_id="sess-parent", title="Parent Session")

    # Create different target session
    other_sdk = SDK(directory=temp_htmlgraph, agent="other", db_path=str(isolated_db))
    _ = other_sdk.start_session(session_id="sess-other", title="Other Session")

    # Create child SDK with parent session
    child_sdk = SDK(
        directory=temp_htmlgraph,
        agent="child",
        parent_session="sess-parent",
        db_path=str(isolated_db),
    )

    # Track activity with explicit session_id override
    entry = child_sdk.track_activity(
        tool="OverrideTest",
        summary="Activity with explicit override",
        session_id="sess-other",  # Explicit override
        success=True,
    )

    # Verify activity went to explicitly specified session (not parent)
    assert entry.payload is not None
    assert entry.payload.get("session_id") == "sess-other"


def test_parent_activity_linking(temp_htmlgraph: Path, isolated_db: Path):
    """Test parent activity linking works correctly."""
    # Set environment for parent activity
    os.environ["HTMLGRAPH_PARENT_ACTIVITY"] = "evt-parent-123"

    try:
        # Create SDK with parent session
        sdk = SDK(
            directory=temp_htmlgraph,
            agent="child",
            parent_session="sess-parent",
            db_path=str(isolated_db),
        )

        # Start a parent session for tracking
        parent_sdk = SDK(
            directory=temp_htmlgraph, agent="parent", db_path=str(isolated_db)
        )
        _ = parent_sdk.start_session(session_id="sess-parent", title="Parent Session")

        # Track activity without explicit parent_activity_id
        entry = sdk.track_activity(
            tool="LinkTest", summary="Activity with parent link", success=True
        )

        # Verify parent activity ID was set from environment
        assert entry.parent_activity_id == "evt-parent-123"

    finally:
        os.environ.pop("HTMLGRAPH_PARENT_ACTIVITY", None)


def test_session_nesting_depth(temp_htmlgraph: Path):
    """Test session nesting depth tracking."""
    # Create nested sessions with different depths
    level0_session = Session(
        id="sess-level0",
        agent="agent",
        nesting_depth=0,  # Top-level
    )

    level1_session = Session(
        id="sess-level1",
        agent="agent",
        parent_session="sess-level0",
        nesting_depth=1,
    )

    level2_session = Session(
        id="sess-level2",
        agent="agent",
        parent_session="sess-level1",
        nesting_depth=2,
    )

    # Verify depth tracking
    assert level0_session.nesting_depth == 0
    assert level1_session.nesting_depth == 1
    assert level2_session.nesting_depth == 2

    # Verify HTML serialization
    html0 = level0_session.to_html()
    assert "data-nesting-depth" not in html0  # Depth 0 shouldn't be shown

    html1 = level1_session.to_html()
    assert 'data-nesting-depth="1"' in html1

    html2 = level2_session.to_html()
    assert 'data-nesting-depth="2"' in html2


def test_backward_compatibility_no_parent(temp_htmlgraph: Path, isolated_db: Path):
    """Test SDK is backward compatible when parent_session not provided."""
    # Create SDK without parent_session parameter (old behavior)
    sdk = SDK(directory=temp_htmlgraph, agent="agent", db_path=str(isolated_db))

    # Verify no parent session is set
    assert sdk._parent_session is None

    # Start a session
    _ = sdk.start_session(session_id="sess-test", title="Test Session")

    # Track activity should work as before
    entry = sdk.track_activity(
        tool="BackwardTest", summary="Backward compatible activity", success=True
    )

    # Verify activity tracked successfully
    assert entry.payload is not None
    assert entry.payload.get("session_id") == "sess-test"


def test_parent_session_priority_chain(temp_htmlgraph: Path, isolated_db: Path):
    """Test session resolution priority: explicit > parent > active."""
    # Set up environment with parent session
    os.environ["HTMLGRAPH_PARENT_SESSION"] = "sess-env-parent"

    try:
        # Create all three sessions
        parent_sdk = SDK(
            directory=temp_htmlgraph, agent="parent", db_path=str(isolated_db)
        )
        parent_sdk.start_session(session_id="sess-env-parent", title="Env Parent")

        explicit_sdk = SDK(
            directory=temp_htmlgraph, agent="explicit", db_path=str(isolated_db)
        )
        explicit_sdk.start_session(session_id="sess-explicit", title="Explicit Session")

        active_sdk = SDK(
            directory=temp_htmlgraph, agent="child", db_path=str(isolated_db)
        )
        _ = active_sdk.start_session(session_id="sess-active", title="Active Session")

        # Test 1: Explicit overrides everything
        sdk_explicit = SDK(
            directory=temp_htmlgraph,
            agent="child",
            parent_session="sess-env-parent",
            db_path=str(isolated_db),
        )
        entry = sdk_explicit.track_activity(
            tool="Test",
            summary="Explicit override",
            session_id="sess-explicit",  # Explicit
        )
        assert entry.payload.get("session_id") == "sess-explicit"

        # Test 2: Parent session used when no explicit
        sdk_parent = SDK(
            directory=temp_htmlgraph,
            agent="child",
            parent_session="sess-env-parent",
            db_path=str(isolated_db),
        )
        entry = sdk_parent.track_activity(tool="Test", summary="Using parent")
        assert entry.payload.get("session_id") == "sess-env-parent"

        # Test 3: Falls back to parent_session when explicitly provided
        os.environ.pop("HTMLGRAPH_PARENT_SESSION", None)
        sdk_with_explicit_parent = SDK(
            directory=temp_htmlgraph,
            agent="child",
            parent_session="sess-explicit",
            db_path=str(isolated_db),
        )
        entry = sdk_with_explicit_parent.track_activity(
            tool="Test", summary="Using explicit parent"
        )
        assert entry.payload.get("session_id") == "sess-explicit"

    finally:
        os.environ.pop("HTMLGRAPH_PARENT_SESSION", None)
