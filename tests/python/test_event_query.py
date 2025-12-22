"""Tests for SDK event inspection API."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from htmlgraph.event_log import JsonlEventLog, EventRecord
from htmlgraph.models import Session


@pytest.fixture
def temp_events_dir():
    """Create a temporary events directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_session(temp_events_dir):
    """Create a sample session with events."""
    session = Session(
        id="test-session-001",
        agent="test-agent",
        status="active"
    )

    # Create event log and add some events
    event_log = JsonlEventLog(temp_events_dir)

    # Add various events
    events = [
        {"event_id": "evt-001", "tool": "Bash", "feature_id": "feat-123", "summary": "Test 1"},
        {"event_id": "evt-002", "tool": "Edit", "feature_id": "feat-123", "summary": "Test 2"},
        {"event_id": "evt-003", "tool": "Bash", "feature_id": None, "summary": "Test 3"},
        {"event_id": "evt-004", "tool": "Read", "feature_id": "feat-456", "summary": "Test 4"},
        {"event_id": "evt-005", "tool": "Bash", "feature_id": "feat-123", "summary": "Test 5"},
    ]

    for i, evt_data in enumerate(events):
        record = EventRecord(
            event_id=evt_data["event_id"],
            timestamp=datetime.now() - timedelta(minutes=5-i),
            session_id=session.id,
            agent="test-agent",
            tool=evt_data["tool"],
            summary=evt_data["summary"],
            success=True,
            feature_id=evt_data["feature_id"],
            drift_score=None,
            start_commit=None,
            continued_from=None
        )
        event_log.append(record)

    return session, str(temp_events_dir)


def test_session_get_events_all(sample_session):
    """Test getting all events for a session."""
    session, events_dir = sample_session
    events = session.get_events(limit=None, events_dir=events_dir)

    assert len(events) == 5
    assert events[0]["event_id"] == "evt-001"
    assert events[-1]["event_id"] == "evt-005"


def test_session_get_events_limit(sample_session):
    """Test getting events with limit."""
    session, events_dir = sample_session
    events = session.get_events(limit=3, events_dir=events_dir)

    assert len(events) == 3
    assert events[0]["event_id"] == "evt-001"
    assert events[-1]["event_id"] == "evt-003"


def test_session_get_events_offset(sample_session):
    """Test getting events with offset."""
    session, events_dir = sample_session
    events = session.get_events(limit=2, offset=2, events_dir=events_dir)

    assert len(events) == 2
    assert events[0]["event_id"] == "evt-003"
    assert events[1]["event_id"] == "evt-004"


def test_session_query_events_by_tool(sample_session):
    """Test querying events by tool."""
    session, events_dir = sample_session
    bash_events = session.query_events(tool="Bash", events_dir=events_dir)

    assert len(bash_events) == 3
    assert all(evt["tool"] == "Bash" for evt in bash_events)
    # Newest first
    assert bash_events[0]["event_id"] == "evt-005"


def test_session_query_events_by_feature(sample_session):
    """Test querying events by feature."""
    session, events_dir = sample_session
    feature_events = session.query_events(feature_id="feat-123", events_dir=events_dir)

    assert len(feature_events) == 3
    assert all(evt["feature_id"] == "feat-123" for evt in feature_events)


def test_session_query_events_by_tool_and_feature(sample_session):
    """Test querying events by both tool and feature."""
    session, events_dir = sample_session
    filtered = session.query_events(
        tool="Bash",
        feature_id="feat-123",
        events_dir=events_dir
    )

    assert len(filtered) == 2
    assert all(evt["tool"] == "Bash" and evt["feature_id"] == "feat-123" for evt in filtered)


def test_session_query_events_with_limit(sample_session):
    """Test querying events with limit."""
    session, events_dir = sample_session
    limited = session.query_events(tool="Bash", limit=2, events_dir=events_dir)

    assert len(limited) == 2
    # Newest first
    assert limited[0]["event_id"] == "evt-005"
    assert limited[1]["event_id"] == "evt-003"


def test_session_event_stats(sample_session):
    """Test event statistics calculation."""
    session, events_dir = sample_session
    stats = session.event_stats(events_dir=events_dir)

    assert stats["total_events"] == 5
    assert stats["tools_used"] == 3
    assert stats["features_worked"] == 2

    # Check tool counts
    assert stats["by_tool"]["Bash"] == 3
    assert stats["by_tool"]["Edit"] == 1
    assert stats["by_tool"]["Read"] == 1

    # Check feature counts
    assert stats["by_feature"]["feat-123"] == 3
    assert stats["by_feature"]["feat-456"] == 1


def test_event_log_get_session_events(temp_events_dir):
    """Test JsonlEventLog.get_session_events() method."""
    event_log = JsonlEventLog(temp_events_dir)

    # Create test events
    for i in range(10):
        record = EventRecord(
            event_id=f"evt-{i:03d}",
            timestamp=datetime.now(),
            session_id="test-session",
            agent="test",
            tool="Test",
            summary=f"Event {i}",
            success=True,
            feature_id=None,
            drift_score=None,
            start_commit=None,
            continued_from=None
        )
        event_log.append(record)

    # Test getting all events
    events = event_log.get_session_events("test-session", limit=None)
    assert len(events) == 10

    # Test with limit
    events = event_log.get_session_events("test-session", limit=5)
    assert len(events) == 5

    # Test with offset
    events = event_log.get_session_events("test-session", limit=3, offset=5)
    assert len(events) == 3
    assert events[0]["event_id"] == "evt-005"


def test_event_log_query_events_all_sessions(temp_events_dir):
    """Test querying events across all sessions."""
    event_log = JsonlEventLog(temp_events_dir)

    # Create events for multiple sessions
    for session_num in range(2):
        for i in range(3):
            record = EventRecord(
                event_id=f"evt-s{session_num}-{i}",
                timestamp=datetime.now(),
                session_id=f"session-{session_num}",
                agent="test",
                tool="Bash" if i % 2 == 0 else "Edit",
                summary=f"Event {i}",
                success=True,
                feature_id=None,
                drift_score=None,
                start_commit=None,
                continued_from=None
            )
            event_log.append(record)

    # Query all Bash events across all sessions
    bash_events = event_log.query_events(session_id=None, tool="Bash")
    assert len(bash_events) == 4  # 2 sessions × 2 Bash events each


def test_event_log_query_events_since(temp_events_dir):
    """Test querying events since a timestamp."""
    event_log = JsonlEventLog(temp_events_dir)

    base_time = datetime.now()

    # Create events at different times
    for i in range(5):
        record = EventRecord(
            event_id=f"evt-{i}",
            timestamp=base_time - timedelta(minutes=5-i),
            session_id="test-session",
            agent="test",
            tool="Test",
            summary=f"Event {i}",
            success=True,
            feature_id=None,
            drift_score=None,
            start_commit=None,
            continued_from=None
        )
        event_log.append(record)

    # Query events from last 2 minutes
    recent_time = base_time - timedelta(minutes=2)
    recent_events = event_log.query_events(
        session_id="test-session",
        since=recent_time
    )

    # Should get events 3 and 4 (most recent 2)
    assert len(recent_events) >= 2


def test_session_get_events_empty_session(temp_events_dir):
    """Test getting events for a session with no events."""
    session = Session(id="empty-session", agent="test", status="active")
    events = session.get_events(events_dir=str(temp_events_dir))

    assert events == []


def test_session_query_events_no_matches(sample_session):
    """Test querying events with no matches."""
    session, events_dir = sample_session
    no_matches = session.query_events(tool="NonExistent", events_dir=events_dir)

    assert no_matches == []
