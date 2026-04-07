"""
Integration tests for offline-first merge with conflict resolution.

Tests:
- Offline event logging
- Last-write-wins merge strategy
- Priority-based conflict resolution
- Conflict tracking and reporting
- Reconnection and synchronization
- Performance (<1s for 100 events)
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from htmlgraph.api.offline import (
    ConflictInfo,
    ConflictTracker,
    EventMerger,
    MergeStrategy,
    OfflineEvent,
    OfflineEventLog,
    OfflineEventStatus,
    ReconnectionManager,
)
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Initialize database with schema
    db = HtmlGraphDB(db_path)
    db.connect()
    db.create_tables()
    db.disconnect()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def offline_log(test_db):
    """Create offline event log."""
    return OfflineEventLog(test_db)


@pytest.fixture
def event_merger(test_db):
    """Create event merger."""
    return EventMerger(test_db, MergeStrategy.LAST_WRITE_WINS)


@pytest.fixture
def conflict_tracker(test_db):
    """Create conflict tracker."""
    return ConflictTracker(test_db)


@pytest.mark.asyncio
async def test_offline_event_logging(offline_log):
    """Test logging offline events."""
    event = OfflineEvent(
        event_id="evt-1",
        agent_id="claude-1",
        resource_id="feat-123",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    # Log event
    success = await offline_log.log_event(event)
    assert success

    # Retrieve unsynced events
    unsynced = await offline_log.get_unsynced_events()
    assert len(unsynced) == 1
    assert unsynced[0].event_id == "evt-1"
    assert unsynced[0].resource_id == "feat-123"
    assert unsynced[0].status == OfflineEventStatus.LOCAL_ONLY


@pytest.mark.asyncio
async def test_mark_synced(offline_log):
    """Test marking events as synced."""
    event = OfflineEvent(
        event_id="evt-2",
        agent_id="claude-1",
        resource_id="feat-456",
        resource_type="feature",
        operation="create",
        timestamp=datetime.now(),
        payload={"title": "New Feature"},
    )

    await offline_log.log_event(event)

    # Mark as synced
    success = await offline_log.mark_synced("evt-2")
    assert success

    # Should not appear in unsynced
    unsynced = await offline_log.get_unsynced_events()
    assert len(unsynced) == 0


@pytest.mark.asyncio
async def test_last_write_wins_merge_local_wins(event_merger):
    """Test last-write-wins conflict resolution (local wins)."""
    local_time = datetime.now()
    remote_time = local_time - timedelta(seconds=10)

    local_event = OfflineEvent(
        event_id="local-1",
        agent_id="claude-1",
        resource_id="feat-123",
        resource_type="feature",
        operation="update",
        timestamp=local_time,
        payload={"status": "in_progress"},
    )

    remote_event = {
        "event_id": "remote-1",
        "resource_id": "feat-123",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": remote_time.isoformat(),
        "payload": {"status": "todo"},
    }

    result = await event_merger.merge_events([local_event], [remote_event])

    assert result["conflict_count"] == 1
    assert result["resolution_strategy"] == "last_write_wins"
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0].winner == "local"


@pytest.mark.asyncio
async def test_last_write_wins_merge_remote_wins(event_merger):
    """Test last-write-wins conflict resolution (remote wins)."""
    local_time = datetime.now()
    remote_time = local_time + timedelta(seconds=10)

    local_event = OfflineEvent(
        event_id="local-2",
        agent_id="claude-1",
        resource_id="feat-456",
        resource_type="feature",
        operation="update",
        timestamp=local_time,
        payload={"status": "todo"},
    )

    remote_event = {
        "event_id": "remote-2",
        "resource_id": "feat-456",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": remote_time.isoformat(),
        "payload": {"status": "in_progress"},
    }

    result = await event_merger.merge_events([local_event], [remote_event])

    assert result["conflict_count"] == 1
    assert result["conflicts"][0].winner == "remote"


@pytest.mark.asyncio
async def test_no_conflict_different_resources(event_merger):
    """Test merge with no conflicts (different resources)."""
    local_event = OfflineEvent(
        event_id="local-3",
        agent_id="claude-1",
        resource_id="feat-111",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    remote_event = {
        "event_id": "remote-3",
        "resource_id": "feat-222",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": datetime.now().isoformat(),
        "payload": {"status": "done"},
    }

    result = await event_merger.merge_events([local_event], [remote_event])

    # No conflicts: both events merged
    assert result["conflict_count"] == 0
    assert len(result["merged_events"]) == 2


@pytest.mark.asyncio
async def test_priority_based_merge(test_db):
    """Test priority-based conflict resolution."""
    # Create database with features
    db = HtmlGraphDB(test_db)

    # Insert high priority feature
    db.insert_feature(
        feature_id="feat-high",
        feature_type="feature",
        title="High Priority Feature",
        priority="high",
    )

    # Insert low priority feature
    db.insert_feature(
        feature_id="feat-low",
        feature_type="feature",
        title="Low Priority Feature",
        priority="low",
    )

    db.disconnect()

    # Create merger with priority strategy
    merger = EventMerger(test_db, MergeStrategy.PRIORITY_BASED)

    # Local: high priority feature update
    local_event = OfflineEvent(
        event_id="local-4",
        agent_id="claude-1",
        resource_id="feat-high",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    # Remote: low priority (should lose)
    remote_event = {
        "event_id": "remote-4",
        "resource_id": "feat-high",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": datetime.now().isoformat(),
        "payload": {"status": "todo"},
    }

    result = await merger.merge_events([local_event], [remote_event])

    # High priority local should win
    assert result["conflict_count"] == 1
    assert result["conflicts"][0].winner == "local"


@pytest.mark.asyncio
async def test_conflict_tracking(conflict_tracker):
    """Test tracking and reporting conflicts."""
    local_event = OfflineEvent(
        event_id="local-5",
        agent_id="claude-1",
        resource_id="feat-789",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    remote_event = {
        "event_id": "remote-5",
        "resource_id": "feat-789",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": datetime.now().isoformat(),
        "payload": {"status": "done"},
    }

    conflict = ConflictInfo(
        local_event=local_event,
        remote_event=remote_event,
        conflict_type="concurrent_modification",
        local_timestamp=local_event.timestamp,
        remote_timestamp=datetime.fromisoformat(remote_event["timestamp"]),
        resolution_strategy=MergeStrategy.LAST_WRITE_WINS,
    )

    # Log conflict
    success = await conflict_tracker.log_conflict(conflict)
    assert success

    # Get conflict report
    report = await conflict_tracker.get_conflict_report()
    assert report["total_conflicts"] == 1
    assert report["pending"] == 1
    assert len(report["conflicts"]) == 1


@pytest.mark.asyncio
async def test_resolve_conflict(conflict_tracker):
    """Test manual conflict resolution."""
    local_event = OfflineEvent(
        event_id="local-6",
        agent_id="claude-1",
        resource_id="feat-999",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    remote_event = {
        "event_id": "remote-6",
        "resource_id": "feat-999",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": datetime.now().isoformat(),
        "payload": {"status": "blocked"},
    }

    conflict = ConflictInfo(
        local_event=local_event,
        remote_event=remote_event,
        conflict_type="concurrent_modification",
        local_timestamp=local_event.timestamp,
        remote_timestamp=datetime.fromisoformat(remote_event["timestamp"]),
        resolution_strategy=MergeStrategy.USER_CHOICE,
    )

    await conflict_tracker.log_conflict(conflict)

    # User resolves conflict
    success = await conflict_tracker.resolve_conflict("local-6", "remote")
    assert success

    # Get updated report
    report = await conflict_tracker.get_conflict_report()
    assert report["pending"] == 0
    assert report["resolved"] == 1


@pytest.mark.asyncio
async def test_reconnection_sync(offline_log, event_merger, conflict_tracker):
    """Test full reconnection and sync workflow."""
    # Create offline events
    event1 = OfflineEvent(
        event_id="evt-sync-1",
        agent_id="claude-1",
        resource_id="feat-sync-1",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    event2 = OfflineEvent(
        event_id="evt-sync-2",
        agent_id="claude-1",
        resource_id="feat-sync-2",
        resource_type="feature",
        operation="create",
        timestamp=datetime.now(),
        payload={"title": "New Feature", "status": "todo"},
    )

    await offline_log.log_event(event1)
    await offline_log.log_event(event2)

    # Create reconnection manager
    manager = ReconnectionManager(offline_log, event_merger, conflict_tracker)

    # Simulate reconnection
    result = await manager.on_reconnect()

    assert result["status"] in ["success", "no_changes"]
    assert result["synced_events"] >= 0


@pytest.mark.asyncio
async def test_merge_performance(event_merger):
    """Test merge performance (<1s for 100 events)."""
    import time

    # Create 100 local events
    local_events = []
    for i in range(100):
        event = OfflineEvent(
            event_id=f"perf-local-{i}",
            agent_id="claude-1",
            resource_id=f"feat-perf-{i}",
            resource_type="feature",
            operation="update",
            timestamp=datetime.now(),
            payload={"status": "in_progress"},
        )
        local_events.append(event)

    # Create 50 remote events (no conflicts)
    remote_events = []
    for i in range(50):
        remote_event = {
            "event_id": f"perf-remote-{i}",
            "resource_id": f"feat-remote-{i}",
            "resource_type": "feature",
            "operation": "update",
            "timestamp": datetime.now().isoformat(),
            "payload": {"status": "done"},
        }
        remote_events.append(remote_event)

    # Measure merge time
    start_time = time.time()
    result = await event_merger.merge_events(local_events, remote_events)
    elapsed_time = time.time() - start_time

    # Should complete in < 1 second
    assert elapsed_time < 1.0
    assert len(result["merged_events"]) == 150
    assert result["conflict_count"] == 0


@pytest.mark.asyncio
async def test_multiple_conflicts(event_merger, conflict_tracker):
    """Test handling multiple conflicts in single merge."""
    # Create 10 local events
    local_events = []
    for i in range(10):
        event = OfflineEvent(
            event_id=f"multi-local-{i}",
            agent_id="claude-1",
            resource_id=f"feat-multi-{i}",
            resource_type="feature",
            operation="update",
            timestamp=datetime.now(),
            payload={"status": "in_progress"},
        )
        local_events.append(event)

    # Create 10 conflicting remote events (same resources, earlier timestamp)
    remote_events = []
    earlier_time = datetime.now() - timedelta(seconds=5)
    for i in range(10):
        remote_event = {
            "event_id": f"multi-remote-{i}",
            "resource_id": f"feat-multi-{i}",
            "resource_type": "feature",
            "operation": "update",
            "timestamp": earlier_time.isoformat(),
            "payload": {"status": "todo"},
        }
        remote_events.append(remote_event)

    # Merge
    result = await event_merger.merge_events(local_events, remote_events)

    # Should detect all 10 conflicts
    assert result["conflict_count"] == 10
    # All should resolve to local (later timestamp)
    assert all(c.winner == "local" for c in result["conflicts"])

    # Log conflicts
    for conflict in result["conflicts"]:
        await conflict_tracker.log_conflict(conflict)

    # Verify tracking
    report = await conflict_tracker.get_conflict_report()
    assert report["total_conflicts"] == 10
    assert report["resolved"] == 10  # All auto-resolved by last-write-wins


@pytest.mark.asyncio
async def test_conflict_serialization(conflict_tracker):
    """Test conflict serialization for audit trail."""
    local_event = OfflineEvent(
        event_id="serial-1",
        agent_id="claude-1",
        resource_id="feat-serial",
        resource_type="feature",
        operation="update",
        timestamp=datetime.now(),
        payload={"status": "in_progress"},
    )

    remote_event = {
        "event_id": "serial-remote-1",
        "resource_id": "feat-serial",
        "resource_type": "feature",
        "operation": "update",
        "timestamp": datetime.now().isoformat(),
        "payload": {"status": "done"},
    }

    conflict = ConflictInfo(
        local_event=local_event,
        remote_event=remote_event,
        conflict_type="concurrent_modification",
        local_timestamp=local_event.timestamp,
        remote_timestamp=datetime.fromisoformat(remote_event["timestamp"]),
        resolution_strategy=MergeStrategy.LAST_WRITE_WINS,
        winner="local",
    )

    # Serialize
    conflict_dict = conflict.to_dict()

    assert conflict_dict["local_event_id"] == "serial-1"
    assert conflict_dict["remote_event_id"] == "serial-remote-1"
    assert conflict_dict["resource_id"] == "feat-serial"
    assert conflict_dict["conflict_type"] == "concurrent_modification"
    assert conflict_dict["winner"] == "local"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
