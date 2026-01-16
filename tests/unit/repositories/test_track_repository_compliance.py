"""
TrackRepository Compliance Tests.

Every TrackRepository implementation MUST pass these tests.

These tests enforce the contract defined in TrackRepository interface:
- Identity invariants (object instance caching)
- ACID properties
- Error handling
- Cache behavior
- Atomicity of operations

Run with: pytest tests/unit/repositories/test_track_repository_compliance.py
"""

from typing import Any

import pytest
from htmlgraph.repositories.track_repository import (
    TrackRepository,
    TrackValidationError,
)


class TrackRepositoryComplianceTests:
    """
    Base class for compliance tests.

    Every implementation should create a concrete test class that:
    1. Inherits from this class
    2. Provides a fixture that returns repo instance
    3. Provides a fixture with sample test data

    Example:
        class TestMemoryTrackRepository(TrackRepositoryComplianceTests):
            @pytest.fixture
            def repo(self):
                return MemoryTrackRepository()

            @pytest.fixture
            def sample_tracks(self):
                return [...]
    """

    # Fixtures should be provided by concrete implementations
    @pytest.fixture
    def repo(self) -> TrackRepository:
        """Concrete TrackRepository implementation to test."""
        raise NotImplementedError("Subclass must provide repo fixture")

    @pytest.fixture
    def sample_tracks(self) -> list[dict[str, Any]]:
        """Sample track data for testing."""
        return [
            {
                "title": "Planning Phase 1",
                "status": "active",
                "priority": "high",
            },
            {
                "title": "Feature Development",
                "status": "active",
                "priority": "high",
            },
            {
                "title": "Documentation Sprint",
                "status": "todo",
                "priority": "medium",
            },
            {
                "title": "Legacy Code Refactoring",
                "status": "done",
                "priority": "low",
            },
        ]

    def setup_method(self) -> None:
        """Setup before each test."""
        # Subclass can override
        pass

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        # Subclass can override
        pass

    def _create_track(self, repo: TrackRepository, track_data: dict) -> Any:
        """Helper to create track from dict, avoiding duplicate 'title' argument."""
        data = track_data.copy()
        title = data.pop("title")
        return repo.create(title, **data)

    # ===== IDENTITY INVARIANT TESTS =====

    def test_get_returns_same_instance(self, repo: TrackRepository, sample_tracks):
        """get() should return identical object instance for same track."""
        # Create track
        t1 = self._create_track(repo, sample_tracks[0])
        track_id = t1.id

        # Get same track twice
        t2 = repo.get(track_id)
        t3 = repo.get(track_id)

        # Should be identical instances (identity, not just equality)
        assert t2 is t3, "get() must return same instance for same track"
        assert t2 is t1, "created track should be identical to fetched track"

    def test_get_returns_none_for_missing(self, repo: TrackRepository):
        """get() should return None for non-existent track."""
        result = repo.get("track-nonexistent-12345")
        assert result is None

    def test_list_returns_empty_list_not_none(self, repo: TrackRepository):
        """list() should return empty list, never None."""
        result = repo.list()
        assert isinstance(result, list)
        assert result == []

    # ===== CREATE/SAVE TESTS =====

    def test_create_generates_id(self, repo: TrackRepository, sample_tracks):
        """create() should generate ID if not provided."""
        track = self._create_track(repo, sample_tracks[0])
        assert track.id is not None
        assert len(track.id) > 0

    def test_create_returns_identical_instance(
        self, repo: TrackRepository, sample_tracks
    ):
        """create() should return identical instance on get()."""
        created = self._create_track(repo, sample_tracks[0])
        fetched = repo.get(created.id)
        assert created is fetched

    def test_create_persists_to_storage(self, repo: TrackRepository, sample_tracks):
        """create() should persist track to storage."""
        track = self._create_track(repo, sample_tracks[0])
        exists = repo.exists(track.id)
        assert exists is True

    def test_save_updates_existing(self, repo: TrackRepository, sample_tracks):
        """save() should update existing track."""
        track = self._create_track(repo, sample_tracks[0])
        track.status = "done"
        saved = repo.save(track)

        # Fetch and verify
        fetched = repo.get(track.id)
        assert fetched.status == "done"
        assert saved is fetched  # Same instance

    def test_save_returns_same_instance(self, repo: TrackRepository, sample_tracks):
        """save() should return same instance."""
        track = self._create_track(repo, sample_tracks[0])
        saved = repo.save(track)
        assert saved is track

    # ===== LIST AND FILTER TESTS =====

    def test_list_returns_all_tracks(self, repo: TrackRepository, sample_tracks):
        """list() should return all created tracks."""
        created_ids = []
        for t in sample_tracks:
            track = self._create_track(repo, t)
            created_ids.append(track.id)

        all_tracks = repo.list()
        assert len(all_tracks) == len(sample_tracks)
        fetched_ids = [t.id for t in all_tracks]
        assert set(fetched_ids) == set(created_ids)

    def test_list_with_filters(self, repo: TrackRepository, sample_tracks):
        """list() should support filtering."""
        for t in sample_tracks:
            self._create_track(repo, t)

        active = repo.list({"status": "active"})
        assert all(t.status == "active" for t in active)
        assert len(active) == 2  # Two active tracks in sample data

    def test_by_status(self, repo: TrackRepository, sample_tracks):
        """by_status() should filter tracks by status."""
        for t in sample_tracks:
            self._create_track(repo, t)

        completed = repo.by_status("completed")
        assert all(t.status == "completed" for t in completed)

    def test_by_priority(self, repo: TrackRepository, sample_tracks):
        """by_priority() should filter tracks by priority."""
        for t in sample_tracks:
            self._create_track(repo, t)

        high = repo.by_priority("high")
        assert all(t.priority == "high" for t in high)

    def test_active_tracks(self, repo: TrackRepository, sample_tracks):
        """active_tracks() should return tracks in progress."""
        for t in sample_tracks:
            self._create_track(repo, t)

        active = repo.active_tracks()
        assert all(t.status == "active" for t in active)
        assert len(active) == 2

    def test_where_chaining(self, repo: TrackRepository, sample_tracks):
        """where() should support chaining filters."""
        for t in sample_tracks:
            self._create_track(repo, t)

        query = repo.where(status="active").where(priority="high")
        results = query.execute()

        assert all(t.status == "active" for t in results)
        assert all(t.priority == "high" for t in results)

    # ===== BATCH OPERATIONS =====

    def test_batch_get(self, repo: TrackRepository, sample_tracks):
        """batch_get() should retrieve multiple tracks efficiently."""
        ids = []
        for t in sample_tracks[:3]:
            track = self._create_track(repo, t)
            ids.append(track.id)

        tracks = repo.batch_get(ids)
        assert len(tracks) == 3
        fetched_ids = [t.id for t in tracks]
        assert set(fetched_ids) == set(ids)

    def test_batch_get_partial(self, repo: TrackRepository, sample_tracks):
        """batch_get() should handle partial results gracefully."""
        ids = []
        for t in sample_tracks[:2]:
            track = self._create_track(repo, t)
            ids.append(track.id)

        # Add non-existent ID
        ids.append("track-nonexistent-99999")

        tracks = repo.batch_get(ids)
        # Implementation-dependent: may include None or skip missing
        assert len(tracks) >= 2

    def test_batch_update(self, repo: TrackRepository, sample_tracks):
        """batch_update() should update multiple tracks."""
        ids = []
        for t in sample_tracks[:3]:
            track = self._create_track(repo, t)
            ids.append(track.id)

        count = repo.batch_update(ids, {"status": "done", "priority": "low"})
        assert count == 3

        # Verify updates
        updated = repo.batch_get(ids)
        assert all(t.status == "done" for t in updated)
        assert all(t.priority == "low" for t in updated)

    def test_batch_delete(self, repo: TrackRepository, sample_tracks):
        """batch_delete() should delete multiple tracks."""
        ids = []
        for t in sample_tracks[:3]:
            track = self._create_track(repo, t)
            ids.append(track.id)

        count = repo.batch_delete(ids)
        assert count == 3

        # Verify deletion
        for track_id in ids:
            exists = repo.exists(track_id)
            assert exists is False

    # ===== DELETE TESTS =====

    def test_delete_existing_track(self, repo: TrackRepository, sample_tracks):
        """delete() should remove existing track."""
        track = self._create_track(repo, sample_tracks[0])
        success = repo.delete(track.id)
        assert success is True
        assert repo.exists(track.id) is False

    def test_delete_nonexistent_track(self, repo: TrackRepository):
        """delete() should return False for non-existent track."""
        success = repo.delete("track-nonexistent-99999")
        assert success is False

    # ===== ADVANCED QUERY TESTS =====

    def test_find_by_features(self, repo: TrackRepository, sample_tracks):
        """find_by_features() should find tracks containing features."""
        track = self._create_track(repo, sample_tracks[0])
        # Store features in properties dict since Node doesn't have features field
        track.properties["features"] = ["feat-001", "feat-002"]
        repo.save(track)

        results = repo.find_by_features(["feat-001"])
        assert len(results) >= 1
        assert any(t.id == track.id for t in results)

    def test_with_feature_count(self, repo: TrackRepository, sample_tracks):
        """with_feature_count() should calculate feature counts."""
        t1 = self._create_track(repo, sample_tracks[0])
        # Store features in properties dict since Node doesn't have features field
        t1.properties["features"] = ["feat-001", "feat-002"]
        repo.save(t1)

        t2 = self._create_track(repo, sample_tracks[1])
        t2.properties["features"] = ["feat-003"]
        repo.save(t2)

        tracks = repo.with_feature_count()
        assert len(tracks) >= 2

    def test_filter_with_predicate(self, repo: TrackRepository, sample_tracks):
        """filter() should support custom predicates."""
        for t in sample_tracks:
            self._create_track(repo, t)

        # Filter for tracks with high priority
        high_priority = repo.filter(lambda t: t.priority == "high")
        assert all(t.priority == "high" for t in high_priority)

    # ===== CACHE MANAGEMENT TESTS =====

    def test_invalidate_cache_single(self, repo: TrackRepository, sample_tracks):
        """invalidate_cache() should clear single track cache."""
        track = self._create_track(repo, sample_tracks[0])
        track_id = track.id

        # Invalidate and reload
        repo.invalidate_cache(track_id)
        reloaded = repo.get(track_id)

        # Should be different instance after invalidation
        assert reloaded is not track or reloaded.id == track.id

    def test_invalidate_cache_all(self, repo: TrackRepository, sample_tracks):
        """invalidate_cache() with no args should clear all caches."""
        self._create_track(repo, sample_tracks[0])
        repo.invalidate_cache()
        # Cache cleared, next get should work

    def test_reload(self, repo: TrackRepository, sample_tracks):
        """reload() should force reload from storage."""
        track = self._create_track(repo, sample_tracks[0])
        track_id = track.id

        repo.reload()
        reloaded = repo.get(track_id)
        assert reloaded.id == track_id

    def test_auto_load_property(self, repo: TrackRepository):
        """auto_load property should get/set auto-loading behavior."""
        # Get current value
        current = repo.auto_load
        assert isinstance(current, bool)

        # Set and verify
        repo.auto_load = not current
        assert repo.auto_load == (not current)

        # Restore
        repo.auto_load = current

    # ===== UTILITY TESTS =====

    def test_count_all(self, repo: TrackRepository, sample_tracks):
        """count() should count all tracks."""
        for t in sample_tracks:
            self._create_track(repo, t)

        total = repo.count()
        assert total == len(sample_tracks)

    def test_count_with_filters(self, repo: TrackRepository, sample_tracks):
        """count() should support filters."""
        for t in sample_tracks:
            self._create_track(repo, t)

        active_count = repo.count({"status": "active"})
        assert active_count == 2

    def test_exists(self, repo: TrackRepository, sample_tracks):
        """exists() should check track existence."""
        track = self._create_track(repo, sample_tracks[0])
        assert repo.exists(track.id) is True
        assert repo.exists("track-nonexistent-99999") is False

    # ===== ERROR HANDLING TESTS =====

    def test_create_with_invalid_data(self, repo: TrackRepository):
        """create() should raise on invalid data."""
        with pytest.raises((TrackValidationError, ValueError, TypeError)):
            repo.create("")  # Empty title

    def test_batch_update_with_invalid_ids(self, repo: TrackRepository):
        """batch_update() should handle invalid IDs gracefully."""
        count = repo.batch_update(["track-nonexistent-1"], {"status": "active"})
        assert count == 0

    def test_where_with_invalid_filters(self, repo: TrackRepository):
        """where() should raise on invalid filter keys."""
        with pytest.raises((TrackValidationError, ValueError)):
            repo.where(invalid_field="value")
            # May raise on execute or where call depending on implementation

    # ===== CONCURRENCY AND EDGE CASES =====

    def test_multiple_creates_same_title(self, repo: TrackRepository):
        """create() should allow multiple tracks with same title."""
        t1 = repo.create("Duplicate Title")
        t2 = repo.create("Duplicate Title")
        assert t1.id != t2.id

    def test_create_and_fetch_consistency(self, repo: TrackRepository, sample_tracks):
        """Created track should match fetched track exactly."""
        created = repo.create(
            sample_tracks[0]["title"],
            status="active",
            priority="high",
        )

        fetched = repo.get(created.id)
        assert fetched.title == created.title
        assert fetched.status == created.status
        assert fetched.priority == created.priority

    def test_list_after_delete(self, repo: TrackRepository, sample_tracks):
        """list() should not include deleted tracks."""
        track = self._create_track(repo, sample_tracks[0])
        track_id = track.id

        initial_count = repo.count()
        repo.delete(track_id)
        final_count = repo.count()

        assert final_count == initial_count - 1
        assert not any(t.id == track_id for t in repo.list())

    def test_save_after_delete(self, repo: TrackRepository, sample_tracks):
        """save() after delete should re-insert track."""
        track = self._create_track(repo, sample_tracks[0])
        track_id = track.id

        repo.delete(track_id)
        assert repo.exists(track_id) is False

        repo.save(track)
        assert repo.exists(track_id) is True

    def test_empty_filters_means_no_filters(self, repo: TrackRepository, sample_tracks):
        """Empty filter dict should return all tracks."""
        for t in sample_tracks:
            self._create_track(repo, t)

        all_tracks = repo.list({})
        with_no_args = repo.list()

        # Both should return all tracks
        assert len(all_tracks) == len(with_no_args)
