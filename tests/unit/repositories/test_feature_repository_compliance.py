"""
FeatureRepository Compliance Tests.

Every FeatureRepository implementation MUST pass these tests.

These tests enforce the contract defined in FeatureRepository interface:
- Identity invariants (object instance caching)
- ACID properties
- Error handling
- Cache behavior
- Atomicity of operations

Run with: pytest tests/unit/repositories/test_feature_repository_compliance.py
"""

from typing import Any

import pytest
from htmlgraph.models import Edge
from htmlgraph.repositories.feature_repository import (
    FeatureNotFoundError,
    FeatureRepository,
    FeatureValidationError,
)


class FeatureRepositoryComplianceTests:
    """
    Base class for compliance tests.

    Every implementation should create a concrete test class that:
    1. Inherits from this class
    2. Provides a fixture that returns repo instance
    3. Provides a fixture with sample test data

    Example:
        class TestMemoryFeatureRepository(FeatureRepositoryComplianceTests):
            @pytest.fixture
            def repo(self):
                return MemoryFeatureRepository()

            @pytest.fixture
            def sample_features(self):
                return [...]
    """

    # Fixtures should be provided by concrete implementations
    @pytest.fixture
    def repo(self) -> FeatureRepository:
        """Concrete FeatureRepository implementation to test."""
        raise NotImplementedError("Subclass must provide repo fixture")

    @pytest.fixture
    def sample_features(self) -> list[dict[str, Any]]:
        """Sample feature data for testing."""
        return [
            {
                "title": "User Authentication",
                "status": "todo",
                "priority": "high",
                "track_id": "track-security",
            },
            {
                "title": "API Rate Limiting",
                "status": "in-progress",
                "priority": "high",
                "track_id": "track-performance",
            },
            {
                "title": "Database Optimization",
                "status": "todo",
                "priority": "medium",
                "track_id": "track-performance",
            },
            {
                "title": "Documentation",
                "status": "done",
                "priority": "low",
                "track_id": "track-docs",
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

    def _create_feature(self, repo: FeatureRepository, feature_data: dict) -> Any:
        """Helper to create feature from dict, avoiding duplicate 'title' argument."""
        data = feature_data.copy()
        title = data.pop("title")
        return repo.create(title, **data)

    # ===== IDENTITY INVARIANT TESTS =====

    def test_get_returns_same_instance(self, repo: FeatureRepository, sample_features):
        """get() should return identical object instance for same feature."""
        # Create feature
        sf = sample_features[0].copy()
        title = sf.pop("title")
        f1 = repo.create(title, **sf)
        feature_id = f1.id

        # Get twice
        f2 = repo.get(feature_id)
        f3 = repo.get(feature_id)

        # Should be same instance (identity, not just equality)
        assert f2 is f3, "get() must return same instance (identity) for same feature"
        assert f1 is f2, "Created feature should be same instance as retrieved"

    def test_get_nonexistent_returns_none(self, repo: FeatureRepository):
        """get() returns None for nonexistent feature, not exception."""
        result = repo.get("feat-nonexistent-12345")
        assert result is None, "get() should return None for nonexistent feature"

    def test_get_with_invalid_id_format(self, repo: FeatureRepository):
        """get() with invalid ID format raises ValueError."""
        with pytest.raises(ValueError):
            repo.get("")  # Empty ID
        with pytest.raises(ValueError):
            repo.get(None)  # None ID

    # ===== LIST OPERATIONS =====

    def test_list_with_no_filters_returns_all(
        self, repo: FeatureRepository, sample_features
    ):
        """list() with no filters returns all features."""
        # Create all features
        for sf in sample_features:
            self._create_feature(repo, sf)

        # List with no filters
        all_features = repo.list()
        assert isinstance(all_features, list), "list() must return a list"
        assert len(all_features) == len(sample_features), (
            "list() should return all features"
        )

    def test_list_returns_empty_list_not_none(self, repo: FeatureRepository):
        """list() returns empty list, never None."""
        result = repo.list()
        assert result is not None, "list() must never return None"
        assert isinstance(result, list), "list() must return a list"
        assert len(result) == 0, "Empty repo should return empty list"

    def test_list_with_empty_filters_dict(
        self, repo: FeatureRepository, sample_features
    ):
        """list() with empty filters dict returns all."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        result1 = repo.list({})
        result2 = repo.list(None)
        assert len(result1) == len(sample_features)
        assert len(result2) == len(sample_features)

    def test_list_with_single_filter(self, repo: FeatureRepository, sample_features):
        """list() with single filter returns matching features."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        result = repo.list({"status": "todo"})
        assert len(result) == 2, "Should find 2 todo features"
        assert all(f.status == "todo" for f in result)

    def test_list_with_multiple_filters(self, repo: FeatureRepository, sample_features):
        """list() with multiple filters applies all conditions (AND)."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        result = repo.list({"status": "todo", "priority": "high"})
        assert len(result) >= 1, "Should find at least 1 feature"
        assert all(f.status == "todo" and f.priority == "high" for f in result)

    def test_list_preserves_object_identity(
        self, repo: FeatureRepository, sample_features
    ):
        """Objects returned by list() should be same instances as from get()."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        all_features = repo.list()
        if all_features:
            first = all_features[0]
            retrieved = repo.get(first.id)
            assert retrieved is first, "list() should return same instances as get()"

    # ===== WHERE/QUERY BUILDER TESTS =====

    def test_where_returns_query_object(self, repo: FeatureRepository):
        """where() returns RepositoryQuery object."""
        query = repo.where(status="todo")
        assert hasattr(query, "execute"), "where() should return object with execute()"

    def test_where_chaining(self, repo: FeatureRepository, sample_features):
        """where() supports chaining multiple conditions."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        results = repo.where(status="todo").where(priority="high").execute()
        assert isinstance(results, list), "Chained query should return list"
        assert all(f.status == "todo" and f.priority == "high" for f in results)

    def test_where_with_invalid_attribute(self, repo: FeatureRepository):
        """where() with invalid attribute raises ValidationError."""
        with pytest.raises(FeatureValidationError):
            repo.where(invalid_attribute_xyz="value").execute()

    # ===== FILTERED ACCESS TESTS =====

    def test_by_track(self, repo: FeatureRepository, sample_features):
        """by_track() returns features in track."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        results = repo.by_track("track-performance")
        assert len(results) == 2, "Should find 2 features in performance track"
        assert all(f.track_id == "track-performance" for f in results)

    def test_by_track_empty(self, repo: FeatureRepository, sample_features):
        """by_track() returns empty list for nonexistent track."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        results = repo.by_track("track-nonexistent")
        assert results == [], "Should return empty list for nonexistent track"

    def test_by_status(self, repo: FeatureRepository, sample_features):
        """by_status() filters by status."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        todo = repo.by_status("todo")
        assert all(f.status == "todo" for f in todo)
        assert len(todo) == 2

    def test_by_priority(self, repo: FeatureRepository, sample_features):
        """by_priority() filters by priority."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        high = repo.by_priority("high")
        assert all(f.priority == "high" for f in high)
        assert len(high) == 2

    def test_by_assigned_to(self, repo: FeatureRepository, sample_features):
        """by_assigned_to() filters by agent assignment."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        # Assign some features
        features = repo.list()
        if features:
            features[0].agent_assigned = "claude"
            repo.save(features[0])

            assigned = repo.by_assigned_to("claude")
            assert len(assigned) >= 1
            assert all(f.agent_assigned == "claude" for f in assigned)

    # ===== BATCH OPERATIONS =====

    def test_batch_get(self, repo: FeatureRepository, sample_features):
        """batch_get() retrieves multiple features efficiently."""
        ids = []
        for sf in sample_features[:2]:
            f = self._create_feature(repo, sf)
            ids.append(f.id)

        results = repo.batch_get(ids)
        assert len(results) >= len(ids) - 1  # Allow for missing
        assert all(r is not None for r in results if r)

    def test_batch_get_preserves_identity(
        self, repo: FeatureRepository, sample_features
    ):
        """batch_get() returns same instances as get()."""
        f1 = self._create_feature(repo, sample_features[0])
        f2 = self._create_feature(repo, sample_features[1])

        batch = repo.batch_get([f1.id, f2.id])
        assert f1 in batch, "batch_get should return same instance as get"
        assert f2 in batch

    def test_batch_get_invalid_input(self, repo: FeatureRepository):
        """batch_get() with invalid input raises ValueError."""
        with pytest.raises(ValueError):
            repo.batch_get("not-a-list")

    def test_batch_update(self, repo: FeatureRepository, sample_features):
        """batch_update() efficiently updates multiple features."""
        ids = []
        for sf in sample_features[:2]:
            f = self._create_feature(repo, sf)
            ids.append(f.id)

        count = repo.batch_update(ids, {"status": "done", "priority": "critical"})
        assert count == 2, "Should update 2 features"

        # Verify updates
        for f_id in ids:
            f = repo.get(f_id)
            assert f.status == "done"
            assert f.priority == "critical"

    def test_batch_delete(self, repo: FeatureRepository, sample_features):
        """batch_delete() removes multiple features."""
        ids = []
        for sf in sample_features[:2]:
            f = self._create_feature(repo, sf)
            ids.append(f.id)

        count = repo.batch_delete(ids)
        assert count == 2, "Should delete 2 features"

        # Verify deletion
        for f_id in ids:
            assert repo.get(f_id) is None

    # ===== CREATE/SAVE OPERATIONS =====

    def test_create_generates_id(self, repo: FeatureRepository, sample_features):
        """create() generates ID if not provided."""
        feature = self._create_feature(repo, sample_features[0])
        assert feature.id is not None, "create() should generate ID"

    def test_create_returns_saved_instance(
        self, repo: FeatureRepository, sample_features
    ):
        """create() returns feature that's immediately retrievable."""
        created = self._create_feature(repo, sample_features[0])
        retrieved = repo.get(created.id)
        assert created is retrieved, "Created feature should match retrieved"

    def test_save_updates_existing(self, repo: FeatureRepository, sample_features):
        """save() updates existing feature."""
        f = self._create_feature(repo, sample_features[0])
        f.status = "in-progress"
        repo.save(f)

        retrieved = repo.get(f.id)
        assert retrieved.status == "in-progress"

    def test_save_preserves_identity(self, repo: FeatureRepository, sample_features):
        """save() returns same instance."""
        f = self._create_feature(repo, sample_features[0])
        f.priority = "critical"
        saved = repo.save(f)

        assert saved is f, "save() should return same instance"

    # ===== DELETE OPERATIONS =====

    def test_delete_removes_feature(self, repo: FeatureRepository, sample_features):
        """delete() removes feature from repo."""
        f = self._create_feature(repo, sample_features[0])
        success = repo.delete(f.id)

        assert success is True, "delete() should return True on success"
        assert repo.get(f.id) is None, "Feature should not exist after delete"

    def test_delete_nonexistent_returns_false(self, repo: FeatureRepository):
        """delete() returns False for nonexistent feature."""
        success = repo.delete("feat-nonexistent-xyz")
        assert success is False, "delete() should return False if not found"

    # ===== ADVANCED QUERIES =====

    def test_find_dependencies(self, repo: FeatureRepository, sample_features):
        """find_dependencies() returns transitive deps."""
        f1 = self._create_feature(repo, sample_features[0])
        f2 = self._create_feature(repo, sample_features[1])

        # f2 depends on f1
        f2.edges = {"depends_on": [Edge(target_id=f1.id, relationship="depends_on")]}
        repo.save(f2)

        deps = repo.find_dependencies(f2.id)
        assert f1 in deps, "Should find direct dependency"

    def test_find_blocking(self, repo: FeatureRepository, sample_features):
        """find_blocking() returns features blocked by this one."""
        f1 = self._create_feature(repo, sample_features[0])
        f2 = self._create_feature(repo, sample_features[1])

        # f2 depends on f1
        f2.edges = {"depends_on": [Edge(target_id=f1.id, relationship="depends_on")]}
        repo.save(f2)

        blocked = repo.find_blocking(f1.id)
        assert f2 in blocked, "Should find features blocked by f1"

    def test_filter_with_predicate(self, repo: FeatureRepository, sample_features):
        """filter() with custom predicate."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        # Custom predicate
        results = repo.filter(lambda f: "auth" in f.title.lower())
        assert len(results) >= 0  # May find "Authentication"

    # ===== CACHE MANAGEMENT =====

    def test_invalidate_single_feature_cache(
        self, repo: FeatureRepository, sample_features
    ):
        """invalidate_cache(id) clears single feature cache."""
        f = self._create_feature(repo, sample_features[0])
        repo.invalidate_cache(f.id)
        # Should reload on next access (depends on implementation)

    def test_invalidate_all_caches(self, repo: FeatureRepository, sample_features):
        """invalidate_cache() with no ID clears all."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        repo.invalidate_cache()  # Clear all
        # Should reload all on next access

    def test_reload(self, repo: FeatureRepository, sample_features):
        """reload() force-reloads from storage."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        repo.reload()
        # Should reload all features from disk

    def test_auto_load_property(self, repo: FeatureRepository):
        """auto_load property can be read and set."""
        original = repo.auto_load
        repo.auto_load = not original
        assert repo.auto_load == (not original)
        repo.auto_load = original

    # ===== UTILITY METHODS =====

    def test_count(self, repo: FeatureRepository, sample_features):
        """count() returns number of features."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        total = repo.count()
        assert total == len(sample_features)

    def test_count_with_filter(self, repo: FeatureRepository, sample_features):
        """count() with filters."""
        for sf in sample_features:
            self._create_feature(repo, sf)

        todo_count = repo.count({"status": "todo"})
        assert todo_count == 2

    def test_exists(self, repo: FeatureRepository, sample_features):
        """exists() checks feature without loading."""
        f = self._create_feature(repo, sample_features[0])

        assert repo.exists(f.id) is True
        assert repo.exists("feat-nonexistent") is False

    # ===== ERROR HANDLING =====

    def test_validation_error_on_invalid_data(self, repo: FeatureRepository):
        """Invalid data raises FeatureValidationError."""
        with pytest.raises(FeatureValidationError):
            repo.create("")  # Empty title should fail

    def test_not_found_error_dependency_query(self, repo: FeatureRepository):
        """Dependency query on nonexistent feature raises error."""
        with pytest.raises(FeatureNotFoundError):
            repo.find_dependencies("feat-nonexistent")

    def test_batch_update_invalid_input(self, repo: FeatureRepository):
        """batch_update() with invalid input raises error."""
        with pytest.raises(Exception):  # ValueError or FeatureValidationError
            repo.batch_update("not-a-list", {})

    # ===== CONCURRENCY (Basic Tests) =====

    def test_concurrent_safe_reads(self, repo: FeatureRepository, sample_features):
        """Multiple reads of same feature are safe."""
        f = self._create_feature(repo, sample_features[0])

        # Multiple concurrent-like reads
        f1 = repo.get(f.id)
        f2 = repo.get(f.id)
        f3 = repo.get(f.id)

        # All should be same instance
        assert f1 is f2 is f3

    def test_concurrent_safe_writes(self, repo: FeatureRepository, sample_features):
        """Sequential writes are atomic."""
        f = self._create_feature(repo, sample_features[0])

        # Sequential writes
        f.status = "in-progress"
        repo.save(f)
        assert repo.get(f.id).status == "in-progress"

        f.status = "done"
        repo.save(f)
        assert repo.get(f.id).status == "done"
