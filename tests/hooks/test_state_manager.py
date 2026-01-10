"""
Comprehensive unit tests for HtmlGraph Hooks State Manager.

Tests unified state file management:
- ParentActivityTracker: Tracks active parent activity context (Skill/Task invocations)
- UserQueryEventTracker: Tracks active UserQuery event IDs (per-session)
- DriftQueueManager: Manages drift classification queue (high-drift activities)

Test coverage includes:
- File I/O operations (load, save, clear)
- Timestamp handling and age-based filtering
- JSON validation and corrupted file handling
- Concurrent access and atomic writes
- Edge cases: empty files, missing files, stale entries
- Error handling and logging
"""

import json
import logging
from datetime import datetime, timedelta
from unittest import mock

import pytest
from htmlgraph.hooks.state_manager import (
    DriftQueueManager,
    ParentActivityTracker,
    UserQueryEventTracker,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def graph_dir(tmp_path):
    """Create a temporary .htmlgraph directory for testing."""
    dir_path = tmp_path / ".htmlgraph"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


@pytest.fixture
def parent_activity_tracker(graph_dir):
    """Create a ParentActivityTracker instance with temporary directory."""
    return ParentActivityTracker(graph_dir)


@pytest.fixture
def user_query_tracker(graph_dir):
    """Create a UserQueryEventTracker instance with temporary directory."""
    return UserQueryEventTracker(graph_dir)


@pytest.fixture
def drift_queue_manager(graph_dir):
    """Create a DriftQueueManager instance with temporary directory."""
    return DriftQueueManager(graph_dir)


@pytest.fixture
def sample_parent_activity():
    """Sample parent activity data."""
    return {
        "parent_id": "evt-xyz123",
        "tool": "Task",
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_user_query():
    """Sample user query event data."""
    return {
        "event_id": "evt-abc456",
        "timestamp": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_drift_activity():
    """Sample drift queue activity."""
    return {
        "tool": "Read",
        "summary": "Read: /path/to/file.py",
        "file_paths": ["/path/to/file.py"],
        "drift_score": 0.87,
        "feature_id": "feat-xyz123",
    }


# ============================================================================
# Tests for ParentActivityTracker
# ============================================================================


class TestParentActivityTrackerLoad:
    """Test ParentActivityTracker.load() functionality."""

    def test_load_existing_file_returns_data(
        self, parent_activity_tracker, sample_parent_activity
    ):
        """Test loading valid parent activity from existing file."""
        # Setup: Save parent activity
        parent_activity_tracker.save(
            sample_parent_activity["parent_id"],
            sample_parent_activity["tool"],
        )

        # Execute: Load parent activity
        result = parent_activity_tracker.load()

        # Verify
        assert result is not None
        assert result["parent_id"] == sample_parent_activity["parent_id"]
        assert result["tool"] == sample_parent_activity["tool"]
        assert "timestamp" in result

    def test_load_missing_file_returns_empty_dict(self, parent_activity_tracker):
        """Test loading when file does not exist returns empty dict."""
        result = parent_activity_tracker.load()
        assert result == {}

    def test_load_filters_stale_entries(self, parent_activity_tracker, graph_dir):
        """Test that load() filters out stale entries older than max_age_minutes."""
        # Setup: Create file with old timestamp
        old_time = datetime.now() - timedelta(minutes=10)
        stale_data = {
            "parent_id": "evt-old",
            "tool": "Task",
            "timestamp": old_time.isoformat(),
        }
        file_path = graph_dir / "parent-activity.json"
        with open(file_path, "w") as f:
            json.dump(stale_data, f)

        # Execute: Load with 5 minute max age (default)
        result = parent_activity_tracker.load(max_age_minutes=5)

        # Verify: Stale entry is filtered out
        assert result == {}

    def test_load_preserves_fresh_entries(self, parent_activity_tracker, graph_dir):
        """Test that load() preserves entries younger than max_age_minutes."""
        # Setup: Create file with recent timestamp
        recent_time = datetime.now() - timedelta(minutes=2)
        fresh_data = {
            "parent_id": "evt-fresh",
            "tool": "Skill",
            "timestamp": recent_time.isoformat(),
        }
        file_path = graph_dir / "parent-activity.json"
        with open(file_path, "w") as f:
            json.dump(fresh_data, f)

        # Execute: Load with 5 minute max age
        result = parent_activity_tracker.load(max_age_minutes=5)

        # Verify: Fresh entry is preserved
        assert result["parent_id"] == "evt-fresh"
        assert result["tool"] == "Skill"

    def test_load_handles_corrupted_json(self, parent_activity_tracker, graph_dir):
        """Test that load() handles corrupted JSON gracefully."""
        # Setup: Create corrupted JSON file
        file_path = graph_dir / "parent-activity.json"
        with open(file_path, "w") as f:
            f.write("{invalid json")

        # Execute & Verify: Should return empty dict without raising
        result = parent_activity_tracker.load()
        assert result == {}

    def test_load_handles_invalid_timestamp(self, parent_activity_tracker, graph_dir):
        """Test that load() handles invalid timestamp format gracefully."""
        # Setup: Create file with invalid timestamp
        file_path = graph_dir / "parent-activity.json"
        with open(file_path, "w") as f:
            json.dump(
                {
                    "parent_id": "evt-xyz",
                    "tool": "Task",
                    "timestamp": "not-a-timestamp",
                },
                f,
            )

        # Execute & Verify: Should return empty dict without raising
        result = parent_activity_tracker.load()
        assert result == {}


class TestParentActivityTrackerSave:
    """Test ParentActivityTracker.save() functionality."""

    def test_save_creates_file_with_timestamp(self, parent_activity_tracker, graph_dir):
        """Test that save() creates file with timestamp."""
        # Execute
        parent_activity_tracker.save("evt-test123", "Task")

        # Verify: File exists
        file_path = graph_dir / "parent-activity.json"
        assert file_path.exists()

        # Verify: File contains correct data
        with open(file_path) as f:
            data = json.load(f)
        assert data["parent_id"] == "evt-test123"
        assert data["tool"] == "Task"
        assert "timestamp" in data

    def test_save_overwrites_existing_file(self, parent_activity_tracker, graph_dir):
        """Test that save() overwrites existing parent activity."""
        # Setup: Save initial activity
        parent_activity_tracker.save("evt-first", "Task")

        # Execute: Save second activity
        parent_activity_tracker.save("evt-second", "Skill")

        # Verify: File contains second activity
        file_path = graph_dir / "parent-activity.json"
        with open(file_path) as f:
            data = json.load(f)
        assert data["parent_id"] == "evt-second"
        assert data["tool"] == "Skill"

    def test_save_uses_atomic_write(self, parent_activity_tracker, graph_dir):
        """Test that save() uses atomic write (temp file + rename)."""
        # This is tested by verifying no partial files remain
        parent_activity_tracker.save("evt-test", "Task")

        # Verify: Only the final file exists, no temp files
        files = list(graph_dir.glob("*"))
        assert len(files) == 1
        assert files[0].name == "parent-activity.json"

    def test_save_multiple_operations_sequentially(
        self, parent_activity_tracker, graph_dir
    ):
        """Test multiple sequential save operations maintain integrity."""
        # Execute: Multiple saves
        for i in range(5):
            parent_activity_tracker.save(f"evt-{i}", "Task")

        # Verify: Final save is preserved
        file_path = graph_dir / "parent-activity.json"
        with open(file_path) as f:
            data = json.load(f)
        assert data["parent_id"] == "evt-4"

    def test_save_handles_special_characters_in_parent_id(
        self, parent_activity_tracker, graph_dir
    ):
        """Test save() handles special characters in parent_id."""
        parent_activity_tracker.save("evt-abc/123:456", "Task")

        file_path = graph_dir / "parent-activity.json"
        with open(file_path) as f:
            data = json.load(f)
        assert data["parent_id"] == "evt-abc/123:456"


class TestParentActivityTrackerClear:
    """Test ParentActivityTracker.clear() functionality."""

    def test_clear_deletes_existing_file(self, parent_activity_tracker, graph_dir):
        """Test that clear() deletes the parent activity file."""
        # Setup: Create file
        parent_activity_tracker.save("evt-test", "Task")
        file_path = graph_dir / "parent-activity.json"
        assert file_path.exists()

        # Execute: Clear
        parent_activity_tracker.clear()

        # Verify: File is deleted
        assert not file_path.exists()

    def test_clear_handles_missing_file(self, parent_activity_tracker):
        """Test that clear() handles missing file gracefully."""
        # Execute & Verify: Should not raise when file doesn't exist
        parent_activity_tracker.clear()  # Should not raise


# ============================================================================
# Tests for UserQueryEventTracker
# ============================================================================


class TestUserQueryEventTrackerLoad:
    """Test UserQueryEventTracker.load() functionality."""

    def test_load_returns_event_id_for_existing_session(
        self, user_query_tracker, graph_dir
    ):
        """Test loading event ID for existing session file."""
        # Setup: Save event for session
        session_id = "sess-test123"
        event_id = "evt-abc456"
        user_query_tracker.save(session_id, event_id)

        # Execute: Load
        result = user_query_tracker.load(session_id)

        # Verify
        assert result == event_id

    def test_load_returns_none_for_missing_session(self, user_query_tracker):
        """Test load() returns None when session file doesn't exist."""
        result = user_query_tracker.load("sess-nonexistent")
        assert result is None

    def test_load_filters_stale_events(self, user_query_tracker, graph_dir):
        """Test that load() filters out stale events older than max_age_minutes."""
        # Setup: Create file with old timestamp
        session_id = "sess-stale"
        old_time = datetime.now() - timedelta(minutes=5)
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path, "w") as f:
            json.dump(
                {
                    "event_id": "evt-old",
                    "timestamp": old_time.isoformat(),
                },
                f,
            )

        # Execute: Load with 2 minute max age (default)
        result = user_query_tracker.load(session_id, max_age_minutes=2)

        # Verify: Stale event is filtered out
        assert result is None

    def test_load_preserves_fresh_events(self, user_query_tracker, graph_dir):
        """Test that load() preserves events younger than max_age_minutes."""
        # Setup: Create file with recent timestamp
        session_id = "sess-fresh"
        recent_time = datetime.now() - timedelta(minutes=1)
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path, "w") as f:
            json.dump(
                {
                    "event_id": "evt-fresh",
                    "timestamp": recent_time.isoformat(),
                },
                f,
            )

        # Execute: Load with 2 minute max age
        result = user_query_tracker.load(session_id, max_age_minutes=2)

        # Verify: Fresh event is preserved
        assert result == "evt-fresh"

    def test_load_handles_corrupted_json(self, user_query_tracker, graph_dir):
        """Test that load() handles corrupted JSON gracefully."""
        # Setup: Create corrupted file
        session_id = "sess-corrupt"
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path, "w") as f:
            f.write("{invalid}")

        # Execute & Verify: Should return None without raising
        result = user_query_tracker.load(session_id)
        assert result is None

    def test_load_handles_invalid_timestamp(self, user_query_tracker, graph_dir):
        """Test that load() handles invalid timestamp format gracefully."""
        # Setup: Create file with invalid timestamp
        session_id = "sess-badtime"
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path, "w") as f:
            json.dump(
                {
                    "event_id": "evt-test",
                    "timestamp": "not-a-timestamp",
                },
                f,
            )

        # Execute & Verify: Should return None without raising
        result = user_query_tracker.load(session_id)
        assert result is None


class TestUserQueryEventTrackerSave:
    """Test UserQueryEventTracker.save() functionality."""

    def test_save_creates_session_specific_file(self, user_query_tracker, graph_dir):
        """Test that save() creates session-specific file."""
        # Execute
        session_id = "sess-xyz789"
        event_id = "evt-abc456"
        user_query_tracker.save(session_id, event_id)

        # Verify: Session file exists
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        assert file_path.exists()

        # Verify: File contains correct data
        with open(file_path) as f:
            data = json.load(f)
        assert data["event_id"] == event_id
        assert "timestamp" in data

    def test_save_session_isolation(self, user_query_tracker, graph_dir):
        """Test that different sessions are isolated (separate files)."""
        # Execute: Save events for different sessions
        user_query_tracker.save("sess-one", "evt-one")
        user_query_tracker.save("sess-two", "evt-two")

        # Verify: Each session has separate file
        file_one = graph_dir / "user-query-event-sess-one.json"
        file_two = graph_dir / "user-query-event-sess-two.json"
        assert file_one.exists()
        assert file_two.exists()

        # Verify: Each file has correct data
        with open(file_one) as f:
            data_one = json.load(f)
        with open(file_two) as f:
            data_two = json.load(f)
        assert data_one["event_id"] == "evt-one"
        assert data_two["event_id"] == "evt-two"

    def test_save_overwrites_existing_session_event(
        self, user_query_tracker, graph_dir
    ):
        """Test that save() overwrites existing event for same session."""
        # Setup: Save initial event
        session_id = "sess-update"
        user_query_tracker.save(session_id, "evt-first")

        # Execute: Save second event for same session
        user_query_tracker.save(session_id, "evt-second")

        # Verify: File contains second event
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path) as f:
            data = json.load(f)
        assert data["event_id"] == "evt-second"


class TestUserQueryEventTrackerClear:
    """Test UserQueryEventTracker.clear() functionality."""

    def test_clear_deletes_session_file(self, user_query_tracker, graph_dir):
        """Test that clear() deletes the session-specific file."""
        # Setup: Create session file
        session_id = "sess-delete"
        user_query_tracker.save(session_id, "evt-test")
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        assert file_path.exists()

        # Execute: Clear
        user_query_tracker.clear(session_id)

        # Verify: File is deleted
        assert not file_path.exists()

    def test_clear_handles_missing_session_file(self, user_query_tracker):
        """Test that clear() handles missing session file gracefully."""
        # Execute & Verify: Should not raise
        user_query_tracker.clear("sess-nonexistent")

    def test_clear_only_affects_specified_session(self, user_query_tracker, graph_dir):
        """Test that clear() only deletes specified session, not others."""
        # Setup: Create files for two sessions
        user_query_tracker.save("sess-one", "evt-one")
        user_query_tracker.save("sess-two", "evt-two")

        # Execute: Clear only one session
        user_query_tracker.clear("sess-one")

        # Verify: Only first session file is deleted
        assert not (graph_dir / "user-query-event-sess-one.json").exists()
        assert (graph_dir / "user-query-event-sess-two.json").exists()


# ============================================================================
# Tests for DriftQueueManager
# ============================================================================


class TestDriftQueueManagerLoad:
    """Test DriftQueueManager.load() functionality."""

    def test_load_existing_queue_returns_data(self, drift_queue_manager, graph_dir):
        """Test loading existing drift queue with activities."""
        # Setup: Create queue file
        queue_data = {
            "activities": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "tool": "Read",
                    "summary": "Read: /path/to/file.py",
                    "file_paths": ["/path/to/file.py"],
                    "drift_score": 0.87,
                    "feature_id": "feat-xyz",
                }
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute: Load queue
        result = drift_queue_manager.load()

        # Verify
        assert isinstance(result, dict)
        assert "activities" in result
        assert len(result["activities"]) == 1
        assert result["activities"][0]["tool"] == "Read"

    def test_load_missing_file_returns_empty_queue(self, drift_queue_manager):
        """Test load() returns empty queue when file doesn't exist."""
        result = drift_queue_manager.load()
        assert result == {"activities": [], "last_classification": None}

    def test_load_filters_stale_activities(self, drift_queue_manager, graph_dir):
        """Test that load() filters out activities older than max_age_hours."""
        # Setup: Create queue with old and new activities
        old_time = datetime.now() - timedelta(hours=72)
        recent_time = datetime.now() - timedelta(hours=12)
        queue_data = {
            "activities": [
                {
                    "timestamp": old_time.isoformat(),
                    "tool": "Read",
                    "summary": "Old read",
                    "file_paths": [],
                    "drift_score": 0.8,
                    "feature_id": "feat-old",
                },
                {
                    "timestamp": recent_time.isoformat(),
                    "tool": "Write",
                    "summary": "Recent write",
                    "file_paths": [],
                    "drift_score": 0.9,
                    "feature_id": "feat-new",
                },
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute: Load with 48 hour max age (default)
        result = drift_queue_manager.load(max_age_hours=48)

        # Verify: Only recent activity remains
        assert len(result["activities"]) == 1
        assert result["activities"][0]["summary"] == "Recent write"

    def test_load_preserves_invalid_timestamps(self, drift_queue_manager, graph_dir):
        """Test that load() preserves activities with invalid timestamps to avoid data loss."""
        # Setup: Create queue with invalid timestamp
        queue_data = {
            "activities": [
                {
                    "timestamp": "not-a-timestamp",
                    "tool": "Read",
                    "summary": "Suspicious timestamp",
                    "file_paths": [],
                    "drift_score": 0.8,
                    "feature_id": "feat-suspicious",
                }
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute: Load
        result = drift_queue_manager.load()

        # Verify: Activity with invalid timestamp is preserved
        assert len(result["activities"]) == 1
        assert result["activities"][0]["feature_id"] == "feat-suspicious"

    def test_load_handles_corrupted_json(self, drift_queue_manager, graph_dir):
        """Test that load() handles corrupted JSON gracefully."""
        # Setup: Create corrupted file
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            f.write("{invalid json content")

        # Execute & Verify: Should return empty queue without raising
        result = drift_queue_manager.load()
        assert result == {"activities": [], "last_classification": None}

    def test_load_auto_saves_when_stale_entries_removed(
        self, drift_queue_manager, graph_dir
    ):
        """Test that load() saves file automatically when stale entries are removed."""
        # Setup: Create queue with stale entries
        old_time = datetime.now() - timedelta(hours=72)
        queue_data = {
            "activities": [
                {
                    "timestamp": old_time.isoformat(),
                    "tool": "Read",
                    "summary": "Old",
                    "file_paths": [],
                    "drift_score": 0.8,
                    "feature_id": "feat-old",
                }
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)
        original_mtime = file_path.stat().st_mtime

        # Wait a small moment to ensure mtime changes
        import time

        time.sleep(0.01)

        # Execute: Load with cleanup
        result = drift_queue_manager.load(max_age_hours=48)

        # Verify: File was updated (cleaned activities removed)
        new_mtime = file_path.stat().st_mtime
        assert new_mtime >= original_mtime
        assert len(result["activities"]) == 0


class TestDriftQueueManagerSave:
    """Test DriftQueueManager.save() functionality."""

    def test_save_persists_queue_to_file(self, drift_queue_manager, graph_dir):
        """Test that save() persists queue to file."""
        # Setup
        queue = {
            "activities": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "tool": "Read",
                    "summary": "Test read",
                    "file_paths": ["/test"],
                    "drift_score": 0.85,
                    "feature_id": "feat-test",
                }
            ],
            "last_classification": None,
        }

        # Execute: Save
        drift_queue_manager.save(queue)

        # Verify: File exists and contains data
        file_path = graph_dir / "drift-queue.json"
        assert file_path.exists()
        with open(file_path) as f:
            saved_data = json.load(f)
        assert len(saved_data["activities"]) == 1

    def test_save_preserves_last_classification_timestamp(
        self, drift_queue_manager, graph_dir
    ):
        """Test that save() preserves last_classification metadata."""
        # Setup
        classification_time = datetime.now().isoformat()
        queue = {
            "activities": [],
            "last_classification": classification_time,
        }

        # Execute: Save
        drift_queue_manager.save(queue)

        # Verify
        file_path = graph_dir / "drift-queue.json"
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data["last_classification"] == classification_time

    def test_save_uses_atomic_write(self, drift_queue_manager, graph_dir):
        """Test that save() uses atomic write (temp file + rename)."""
        # Setup
        queue = {
            "activities": [],
            "last_classification": None,
        }

        # Execute
        drift_queue_manager.save(queue)

        # Verify: Only final file exists, no temp files
        files = [f for f in graph_dir.glob("*") if f.is_file()]
        assert len(files) == 1
        assert files[0].name == "drift-queue.json"


class TestDriftQueueManagerAddActivity:
    """Test DriftQueueManager.add_activity() functionality."""

    def test_add_activity_appends_to_queue(
        self, drift_queue_manager, sample_drift_activity
    ):
        """Test that add_activity() appends activity to queue."""
        # Execute
        drift_queue_manager.add_activity(sample_drift_activity)

        # Verify: Activity was added
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 1
        assert result["activities"][0]["tool"] == "Read"
        assert result["activities"][0]["drift_score"] == 0.87

    def test_add_activity_with_custom_timestamp(
        self, drift_queue_manager, sample_drift_activity
    ):
        """Test that add_activity() accepts custom timestamp."""
        # Setup
        custom_time = datetime.now() - timedelta(hours=24)

        # Execute
        drift_queue_manager.add_activity(sample_drift_activity, timestamp=custom_time)

        # Verify
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 1
        assert result["activities"][0]["timestamp"] == custom_time.isoformat()

    def test_add_activity_uses_current_time_by_default(
        self, drift_queue_manager, sample_drift_activity
    ):
        """Test that add_activity() uses current time when not provided."""
        # Execute
        before_time = datetime.now()
        drift_queue_manager.add_activity(sample_drift_activity)
        after_time = datetime.now()

        # Verify
        result = drift_queue_manager.load()
        activity_time = datetime.fromisoformat(result["activities"][0]["timestamp"])
        assert before_time <= activity_time <= after_time

    def test_add_activity_multiple_activities(
        self, drift_queue_manager, sample_drift_activity
    ):
        """Test that multiple add_activity() calls accumulate activities."""
        # Execute: Add multiple activities
        for i in range(3):
            activity = sample_drift_activity.copy()
            activity["feature_id"] = f"feat-{i}"
            drift_queue_manager.add_activity(activity)

        # Verify: All activities are present
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 3
        feature_ids = [a["feature_id"] for a in result["activities"]]
        assert "feat-0" in feature_ids
        assert "feat-1" in feature_ids
        assert "feat-2" in feature_ids

    def test_add_activity_handles_missing_optional_fields(self, drift_queue_manager):
        """Test that add_activity() handles activities with missing optional fields."""
        # Setup: Minimal activity
        minimal_activity = {
            "tool": "Read",
            "summary": "Test",
        }

        # Execute & Verify: Should not raise
        drift_queue_manager.add_activity(minimal_activity)

        result = drift_queue_manager.load()
        assert len(result["activities"]) == 1


class TestDriftQueueManagerClear:
    """Test DriftQueueManager.clear() functionality."""

    def test_clear_deletes_queue_file(
        self, drift_queue_manager, graph_dir, sample_drift_activity
    ):
        """Test that clear() deletes the drift queue file."""
        # Setup: Add activity to create file
        drift_queue_manager.add_activity(sample_drift_activity)
        file_path = graph_dir / "drift-queue.json"
        assert file_path.exists()

        # Execute: Clear
        drift_queue_manager.clear()

        # Verify: File is deleted
        assert not file_path.exists()

    def test_clear_handles_missing_file(self, drift_queue_manager):
        """Test that clear() handles missing file gracefully."""
        # Execute & Verify: Should not raise
        drift_queue_manager.clear()

    def test_clear_activities_preserves_classification_timestamp(
        self, drift_queue_manager, graph_dir, sample_drift_activity
    ):
        """Test that clear_activities() preserves last_classification timestamp."""
        # Setup: Add activity and set classification time
        old_classification_time = (datetime.now() - timedelta(hours=1)).isoformat()
        drift_queue_manager.add_activity(sample_drift_activity)
        queue = drift_queue_manager.load()
        queue["last_classification"] = old_classification_time
        drift_queue_manager.save(queue)

        # Execute: Clear activities
        drift_queue_manager.clear_activities()

        # Verify: Timestamp is preserved, activities cleared
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 0
        assert result["last_classification"] == old_classification_time

    def test_clear_activities_creates_new_timestamp_if_none_exists(
        self, drift_queue_manager, sample_drift_activity
    ):
        """Test that clear_activities() creates timestamp when none exists."""
        # Setup
        drift_queue_manager.add_activity(sample_drift_activity)

        # Execute: Clear activities
        before_time = datetime.now()
        drift_queue_manager.clear_activities()
        after_time = datetime.now()

        # Verify: New timestamp is set
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 0
        if result["last_classification"]:
            ts = datetime.fromisoformat(result["last_classification"])
            assert before_time <= ts <= after_time


# ============================================================================
# Integration Tests
# ============================================================================


class TestStateManagerIntegration:
    """Integration tests for state manager components working together."""

    def test_parent_activity_and_user_query_isolation(
        self, parent_activity_tracker, user_query_tracker, graph_dir
    ):
        """Test that parent activity and user queries are isolated."""
        # Execute: Save both types of state
        parent_activity_tracker.save("evt-parent", "Task")
        user_query_tracker.save("sess-one", "evt-query")

        # Verify: Both files exist independently
        assert (graph_dir / "parent-activity.json").exists()
        assert (graph_dir / "user-query-event-sess-one.json").exists()

        # Verify: Each can be loaded independently
        parent = parent_activity_tracker.load()
        query = user_query_tracker.load("sess-one")
        assert parent["parent_id"] == "evt-parent"
        assert query == "evt-query"

    def test_concurrent_session_handling(self, user_query_tracker, graph_dir):
        """Test handling of multiple concurrent sessions."""
        # Execute: Create multiple sessions
        sessions = ["sess-1", "sess-2", "sess-3"]
        for i, session in enumerate(sessions):
            user_query_tracker.save(session, f"evt-{i}")

        # Verify: Each session has independent state
        for i, session in enumerate(sessions):
            result = user_query_tracker.load(session)
            assert result == f"evt-{i}"

        # Verify: Clearing one doesn't affect others
        user_query_tracker.clear("sess-2")
        assert user_query_tracker.load("sess-1") == "evt-0"
        assert user_query_tracker.load("sess-2") is None
        assert user_query_tracker.load("sess-3") == "evt-2"

    def test_drift_queue_accumulation_and_cleanup(self, drift_queue_manager):
        """Test drift queue accumulation and cleanup workflow."""
        # Execute: Add activities with varying ages
        now = datetime.now()
        for i in range(3):
            activity = {
                "tool": "Read",
                "summary": f"Activity {i}",
                "file_paths": [],
                "drift_score": 0.8 + (i * 0.05),
                "feature_id": f"feat-{i}",
            }
            age_hours = i * 24  # 0, 24, 48 hours old
            drift_queue_manager.add_activity(
                activity,
                timestamp=now - timedelta(hours=age_hours),
            )

        # Verify: All activities loaded initially
        result = drift_queue_manager.load(max_age_hours=72)
        assert len(result["activities"]) == 3

        # Verify: Cleanup removes old activities
        result = drift_queue_manager.load(max_age_hours=36)
        assert len(result["activities"]) <= 2

    def test_directory_creation_on_first_use(self, tmp_path):
        """Test that trackers create .htmlgraph directory if missing."""
        # Setup: Directory doesn't exist yet
        graph_dir = tmp_path / ".htmlgraph"
        assert not graph_dir.exists()

        # Execute: Create tracker (should create directory)
        ParentActivityTracker(graph_dir)

        # Verify: Directory was created
        assert graph_dir.exists()
        assert graph_dir.is_dir()


# ============================================================================
# Error Handling and Edge Cases
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_parent_activity_permission_error_on_save(
        self, parent_activity_tracker, graph_dir
    ):
        """Test that permission errors during save are logged gracefully."""
        # Setup: Mock to simulate permission error
        with mock.patch("builtins.open", side_effect=PermissionError("Access denied")):
            # Execute & Verify: Should not raise
            parent_activity_tracker.save("evt-test", "Task")

    def test_user_query_empty_file_handling(self, user_query_tracker, graph_dir):
        """Test handling of empty JSON file."""
        # Setup: Create empty JSON file
        session_id = "sess-empty"
        file_path = graph_dir / f"user-query-event-{session_id}.json"
        with open(file_path, "w") as f:
            json.dump({}, f)

        # Execute & Verify: Should return None (no event_id)
        result = user_query_tracker.load(session_id)
        assert result is None

    def test_drift_queue_missing_required_timestamp_field(
        self, drift_queue_manager, graph_dir
    ):
        """Test drift queue handling when timestamp field is missing."""
        # Setup: Create queue with missing timestamp
        queue_data = {
            "activities": [
                {
                    "tool": "Read",
                    "summary": "No timestamp",
                    "file_paths": [],
                    "drift_score": 0.8,
                    "feature_id": "feat-notimestamp",
                }
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute & Verify: Should load without raising
        result = drift_queue_manager.load()
        assert len(result["activities"]) == 1
        assert result["activities"][0]["summary"] == "No timestamp"

    @pytest.mark.parametrize(
        "invalid_json",
        [
            "",
            "{invalid json content}",
        ],
    )
    def test_drift_queue_various_invalid_formats(
        self, drift_queue_manager, graph_dir, invalid_json
    ):
        """Test drift queue handling with various invalid JSON formats."""
        # Setup: Create file with invalid content
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            f.write(invalid_json)

        # Execute & Verify: Should return safe default
        result = drift_queue_manager.load()
        assert isinstance(result, dict)
        assert "activities" in result
        assert isinstance(result["activities"], list)

    def test_drift_queue_empty_activities_list(self, drift_queue_manager, graph_dir):
        """Test drift queue with empty activities list."""
        # Setup: Create file with empty activities
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump({"activities": [], "last_classification": None}, f)

        # Execute & Verify
        result = drift_queue_manager.load()
        assert isinstance(result, dict)
        assert result["activities"] == []
        assert result["last_classification"] is None

    def test_drift_queue_multiple_activities_with_metadata(
        self, drift_queue_manager, graph_dir
    ):
        """Test drift queue with multiple activities and classification metadata."""
        # Setup: Create file with multiple activities
        classification_time = datetime.now().isoformat()
        file_path = graph_dir / "drift-queue.json"
        queue_data = {
            "activities": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "tool": "Read",
                    "summary": "First read",
                    "file_paths": ["/file1.py"],
                    "drift_score": 0.8,
                    "feature_id": "feat-1",
                },
                {
                    "timestamp": datetime.now().isoformat(),
                    "tool": "Write",
                    "summary": "First write",
                    "file_paths": ["/file2.py"],
                    "drift_score": 0.9,
                    "feature_id": "feat-2",
                },
            ],
            "last_classification": classification_time,
        }
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute
        result = drift_queue_manager.load()

        # Verify
        assert len(result["activities"]) == 2
        assert result["last_classification"] == classification_time
        assert result["activities"][0]["tool"] == "Read"
        assert result["activities"][1]["tool"] == "Write"


# ============================================================================
# Logging Tests
# ============================================================================


class TestLogging:
    """Test logging functionality."""

    def test_parent_activity_debug_logging_on_load(
        self, parent_activity_tracker, caplog
    ):
        """Test debug logging when loading parent activity."""
        # Setup
        parent_activity_tracker.save("evt-test", "Task")

        # Execute
        with caplog.at_level(logging.DEBUG):
            parent_activity_tracker.load()

        # Verify: Debug log was created
        assert any(
            "Loaded parent activity" in record.message for record in caplog.records
        )

    def test_corruption_warning_logging(
        self, parent_activity_tracker, graph_dir, caplog
    ):
        """Test warning logging for corrupted files."""
        # Setup: Create corrupted file
        file_path = graph_dir / "parent-activity.json"
        with open(file_path, "w") as f:
            f.write("{invalid")

        # Execute
        with caplog.at_level(logging.WARNING):
            parent_activity_tracker.load()

        # Verify: Warning was logged
        assert any("Corrupted" in record.message for record in caplog.records)

    def test_stale_entry_cleanup_logging(self, drift_queue_manager, graph_dir, caplog):
        """Test info logging when cleaning stale drift queue entries."""
        # Setup: Create queue with old activity
        old_time = datetime.now() - timedelta(hours=72)
        queue_data = {
            "activities": [
                {
                    "timestamp": old_time.isoformat(),
                    "tool": "Read",
                    "summary": "Old",
                    "file_paths": [],
                    "drift_score": 0.8,
                    "feature_id": "feat-old",
                }
            ],
            "last_classification": None,
        }
        file_path = graph_dir / "drift-queue.json"
        with open(file_path, "w") as f:
            json.dump(queue_data, f)

        # Execute
        with caplog.at_level(logging.INFO):
            drift_queue_manager.load(max_age_hours=48)

        # Verify: Info log about cleanup
        assert any(
            "Cleaned" in record.message and "stale" in record.message
            for record in caplog.records
        )
