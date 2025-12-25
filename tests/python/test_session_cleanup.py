"""
Tests for session stale reference cleanup.

Tests the cleanup_missing_references() method and automatic cleanup
during session loading.
"""

import pytest
from datetime import datetime
from pathlib import Path
from htmlgraph.models import Session
from htmlgraph.converter import SessionConverter


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create temporary .htmlgraph directory structure."""
    graph_dir = tmp_path / ".htmlgraph"

    # Create collection directories
    for collection in ["features", "bugs", "spikes", "chores", "epics", "sessions"]:
        (graph_dir / collection).mkdir(parents=True)

    # Create some real work items
    real_items = [
        ("features", "feat-001"),
        ("features", "feat-002"),
        ("bugs", "bug-001"),
        ("spikes", "spk-001"),
    ]

    for collection, item_id in real_items:
        item_path = graph_dir / collection / f"{item_id}.html"
        item_path.write_text(f"<article id='{item_id}'><h1>Test Item</h1></article>")

    return graph_dir


def test_cleanup_removes_missing_references(temp_graph_dir):
    """Test that cleanup removes references to deleted/missing work items."""
    # Create session with mixed valid and invalid references
    session = Session(
        id="sess-test-001",
        agent="test-agent",
        status="active",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        event_count=10,
        worked_on=[
            "feat-001",       # Valid - exists
            "feat-002",       # Valid - exists
            "feat-999",       # Invalid - missing
            "bug-001",        # Valid - exists
            "bug-888",        # Invalid - missing
            "spk-001",        # Valid - exists
            "spk-777",        # Invalid - missing
        ]
    )

    # Run cleanup
    result = session.cleanup_missing_references(temp_graph_dir)

    # Verify results
    assert result["removed_count"] == 3
    assert set(result["removed"]) == {"feat-999", "bug-888", "spk-777"}
    assert result["kept_count"] == 4
    assert set(result["kept"]) == {"feat-001", "feat-002", "bug-001", "spk-001"}

    # Verify session.worked_on was updated
    assert len(session.worked_on) == 4
    assert "feat-999" not in session.worked_on
    assert "bug-888" not in session.worked_on
    assert "spk-777" not in session.worked_on


def test_cleanup_keeps_all_valid_references(temp_graph_dir):
    """Test that cleanup keeps all valid references."""
    session = Session(
        id="sess-test-002",
        agent="test-agent",
        status="active",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        event_count=5,
        worked_on=["feat-001", "bug-001", "spk-001"]
    )

    # Run cleanup
    result = session.cleanup_missing_references(temp_graph_dir)

    # Verify nothing was removed
    assert result["removed_count"] == 0
    assert result["kept_count"] == 3
    assert len(session.worked_on) == 3


def test_automatic_cleanup_on_load(temp_graph_dir):
    """Test that cleanup happens automatically when loading sessions."""
    # Create a session with stale references
    session = Session(
        id="sess-test-003",
        agent="test-agent",
        status="active",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        event_count=10,
        worked_on=[
            "feat-001",   # Valid
            "feat-999",   # Invalid - missing
            "bug-001",    # Valid
            "bug-888",    # Invalid - missing
        ]
    )

    # Save session
    sessions_dir = temp_graph_dir / "sessions"
    converter = SessionConverter(sessions_dir)
    converter.save(session)

    # Load session back (should trigger automatic cleanup)
    loaded_session = converter.load("sess-test-003")

    # Verify cleanup happened automatically
    assert loaded_session is not None
    assert len(loaded_session.worked_on) == 2
    assert "feat-001" in loaded_session.worked_on
    assert "bug-001" in loaded_session.worked_on
    assert "feat-999" not in loaded_session.worked_on
    assert "bug-888" not in loaded_session.worked_on


def test_cleanup_with_empty_worked_on(temp_graph_dir):
    """Test cleanup with empty worked_on list."""
    session = Session(
        id="sess-test-004",
        agent="test-agent",
        status="active",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        event_count=1,
        worked_on=[]
    )

    # Run cleanup
    result = session.cleanup_missing_references(temp_graph_dir)

    # Verify nothing breaks
    assert result["removed_count"] == 0
    assert result["kept_count"] == 0
    assert len(session.worked_on) == 0


def test_cleanup_with_unknown_prefix(temp_graph_dir):
    """Test cleanup keeps items with unknown prefixes."""
    session = Session(
        id="sess-test-005",
        agent="test-agent",
        status="active",
        created_at=datetime.now(),
        last_activity=datetime.now(),
        event_count=5,
        worked_on=[
            "feat-001",          # Valid - exists
            "unknown-type-123",  # Unknown prefix - kept
        ]
    )

    # Run cleanup
    result = session.cleanup_missing_references(temp_graph_dir)

    # Unknown types should be kept (don't assume they're missing)
    assert result["removed_count"] == 0
    assert result["kept_count"] == 2
    assert "unknown-type-123" in session.worked_on
