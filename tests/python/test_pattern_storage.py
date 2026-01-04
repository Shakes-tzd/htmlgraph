"""
Comprehensive tests for PatternStorage (CIGS pattern persistence).

Tests cover:
- Basic CRUD operations (add, get, remove)
- Pattern queries and filtering
- Thread-safe concurrent access
- Atomic file operations
- JSON persistence validation
- Edge cases and error handling
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from threading import Thread

import pytest
from htmlgraph.cigs.models import PatternRecord
from htmlgraph.cigs.pattern_storage import PatternStorage


class TestPatternStorageBasic:
    """Basic CRUD operations for pattern storage."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    @pytest.fixture
    def storage(self, temp_graph_dir):
        """Create PatternStorage instance."""
        return PatternStorage(temp_graph_dir)

    def test_initialization_creates_file(self, temp_graph_dir):
        """PatternStorage initialization should create patterns.json."""
        storage = PatternStorage(temp_graph_dir)

        assert storage.patterns_file.exists()
        assert storage.patterns_file.name == "patterns.json"

    def test_initialization_with_existing_file(self, temp_graph_dir):
        """PatternStorage should work with existing patterns file."""
        # Create initial storage
        storage1 = PatternStorage(temp_graph_dir)

        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Test Pattern",
            description="A test pattern",
            trigger_conditions=["condition1"],
            example_sequence=["action1"],
        )
        storage1.add_pattern(pattern)

        # Create second storage instance
        storage2 = PatternStorage(temp_graph_dir)
        retrieved = storage2.get_pattern("test-1")

        assert retrieved is not None
        assert retrieved.name == "Test Pattern"

    def test_add_pattern_generates_id(self, storage):
        """Adding pattern without ID should generate one."""
        pattern = PatternRecord(
            id="",
            pattern_type="anti-pattern",
            name="Test Pattern",
            description="A test pattern",
            trigger_conditions=["condition1"],
            example_sequence=["action1"],
        )

        pattern_id = storage.add_pattern(pattern)

        assert pattern_id
        assert pattern_id.startswith("pattern-")
        retrieved = storage.get_pattern(pattern_id)
        assert retrieved is not None

    def test_add_pattern_with_explicit_id(self, storage):
        """Adding pattern with explicit ID should use it."""
        pattern = PatternRecord(
            id="custom-id",
            pattern_type="anti-pattern",
            name="Test Pattern",
            description="A test pattern",
            trigger_conditions=["condition1"],
            example_sequence=["action1"],
        )

        pattern_id = storage.add_pattern(pattern)

        assert pattern_id == "custom-id"
        retrieved = storage.get_pattern("custom-id")
        assert retrieved is not None

    def test_get_pattern_found(self, storage):
        """Should retrieve added pattern."""
        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Exploration Sequence",
            description="Multiple reads in sequence",
            trigger_conditions=["3+ reads in 5 calls"],
            example_sequence=["Read", "Grep", "Read"],
        )
        storage.add_pattern(pattern)

        retrieved = storage.get_pattern("test-1")

        assert retrieved is not None
        assert retrieved.name == "Exploration Sequence"
        assert retrieved.pattern_type == "anti-pattern"

    def test_get_pattern_not_found(self, storage):
        """Should return None for non-existent pattern."""
        retrieved = storage.get_pattern("non-existent")
        assert retrieved is None

    def test_get_all_patterns_empty(self, storage):
        """Should return empty list when no patterns exist."""
        patterns = storage.get_all_patterns()
        assert patterns == []

    def test_get_all_patterns_mixed(self, storage):
        """Should return all patterns regardless of type."""
        anti = PatternRecord(
            id="anti-1",
            pattern_type="anti-pattern",
            name="Bad Pattern",
            description="A bad pattern",
            trigger_conditions=[],
            example_sequence=[],
        )
        good = PatternRecord(
            id="good-1",
            pattern_type="good-pattern",
            name="Good Pattern",
            description="A good pattern",
            trigger_conditions=[],
            example_sequence=[],
        )

        storage.add_pattern(anti)
        storage.add_pattern(good)

        patterns = storage.get_all_patterns()

        assert len(patterns) == 2
        assert any(p.id == "anti-1" for p in patterns)
        assert any(p.id == "good-1" for p in patterns)

    def test_get_anti_patterns(self, storage):
        """Should return only anti-patterns."""
        anti1 = PatternRecord(
            id="anti-1",
            pattern_type="anti-pattern",
            name="Bad 1",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        anti2 = PatternRecord(
            id="anti-2",
            pattern_type="anti-pattern",
            name="Bad 2",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        good = PatternRecord(
            id="good-1",
            pattern_type="good-pattern",
            name="Good",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )

        storage.add_pattern(anti1)
        storage.add_pattern(anti2)
        storage.add_pattern(good)

        anti_patterns = storage.get_anti_patterns()

        assert len(anti_patterns) == 2
        assert all(p.pattern_type == "anti-pattern" for p in anti_patterns)

    def test_get_good_patterns(self, storage):
        """Should return only good patterns."""
        anti = PatternRecord(
            id="anti-1",
            pattern_type="anti-pattern",
            name="Bad",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        good1 = PatternRecord(
            id="good-1",
            pattern_type="good-pattern",
            name="Good 1",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        good2 = PatternRecord(
            id="good-2",
            pattern_type="good-pattern",
            name="Good 2",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )

        storage.add_pattern(anti)
        storage.add_pattern(good1)
        storage.add_pattern(good2)

        good_patterns = storage.get_good_patterns()

        assert len(good_patterns) == 2
        assert all(p.pattern_type == "good-pattern" for p in good_patterns)

    def test_remove_pattern_found(self, storage):
        """Should remove pattern if found."""
        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Pattern",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        storage.add_pattern(pattern)

        removed = storage.remove_pattern("test-1")

        assert removed is True
        assert storage.get_pattern("test-1") is None

    def test_remove_pattern_not_found(self, storage):
        """Should return False if pattern not found."""
        removed = storage.remove_pattern("non-existent")
        assert removed is False

    def test_update_pattern_occurrence(self, storage):
        """Should increment occurrence count and track sessions."""
        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Pattern",
            description="",
            trigger_conditions=[],
            example_sequence=[],
            occurrence_count=0,
            sessions_affected=[],
        )
        storage.add_pattern(pattern)

        # First occurrence
        result = storage.update_pattern_occurrence("test-1", "sess-1")
        assert result is True
        retrieved = storage.get_pattern("test-1")
        assert retrieved.occurrence_count == 1
        assert "sess-1" in retrieved.sessions_affected

        # Second occurrence in same session
        result = storage.update_pattern_occurrence("test-1", "sess-1")
        assert result is True
        retrieved = storage.get_pattern("test-1")
        assert retrieved.occurrence_count == 2
        assert retrieved.sessions_affected.count("sess-1") == 1  # Only added once

        # Third occurrence in different session
        result = storage.update_pattern_occurrence("test-1", "sess-2")
        assert result is True
        retrieved = storage.get_pattern("test-1")
        assert retrieved.occurrence_count == 3
        assert len(retrieved.sessions_affected) == 2

    def test_update_pattern_occurrence_not_found(self, storage):
        """Should return False if pattern not found."""
        result = storage.update_pattern_occurrence("non-existent", "sess-1")
        assert result is False


class TestPatternStorageQueries:
    """Pattern querying and filtering."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    @pytest.fixture
    def storage_with_patterns(self, temp_graph_dir):
        """Create storage with various patterns."""
        storage = PatternStorage(temp_graph_dir)

        # Add anti-patterns with different occurrence counts
        for i in range(3):
            pattern = PatternRecord(
                id=f"anti-{i}",
                pattern_type="anti-pattern",
                name=f"Anti Pattern {i}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=i + 1,
                sessions_affected=[f"sess-{j}" for j in range(i + 1)],
            )
            storage.add_pattern(pattern)

        # Add good patterns
        for i in range(2):
            pattern = PatternRecord(
                id=f"good-{i}",
                pattern_type="good-pattern",
                name=f"Good Pattern {i}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=(i + 1) * 2,
                sessions_affected=[f"sess-{j}" for j in range((i + 1) * 2)],
            )
            storage.add_pattern(pattern)

        return storage

    def test_query_patterns_by_type(self, storage_with_patterns):
        """Should filter patterns by type."""
        anti = storage_with_patterns.query_patterns(pattern_type="anti-pattern")
        assert len(anti) == 3
        assert all(p.pattern_type == "anti-pattern" for p in anti)

        good = storage_with_patterns.query_patterns(pattern_type="good-pattern")
        assert len(good) == 2
        assert all(p.pattern_type == "good-pattern" for p in good)

    def test_query_patterns_by_occurrence(self, storage_with_patterns):
        """Should filter patterns by minimum occurrence count."""
        # All patterns have at least 1 occurrence
        all_patterns = storage_with_patterns.query_patterns(min_occurrences=1)
        assert len(all_patterns) == 5

        # Only patterns with 2+ occurrences
        frequent = storage_with_patterns.query_patterns(min_occurrences=2)
        assert len(frequent) == 4
        assert all(p.occurrence_count >= 2 for p in frequent)

    def test_query_patterns_combined_filters(self, storage_with_patterns):
        """Should support both type and occurrence filters."""
        anti_frequent = storage_with_patterns.query_patterns(
            pattern_type="anti-pattern",
            min_occurrences=2,
        )
        assert len(anti_frequent) == 2
        assert all(p.pattern_type == "anti-pattern" for p in anti_frequent)
        assert all(p.occurrence_count >= 2 for p in anti_frequent)

    def test_get_patterns_by_session(self, storage_with_patterns):
        """Should return patterns detected in specific session."""
        # sess-0 appears in multiple patterns
        patterns = storage_with_patterns.get_patterns_by_session("sess-0")
        assert len(patterns) == 5  # All patterns have sess-0

        # sess-2 only in some patterns
        patterns = storage_with_patterns.get_patterns_by_session("sess-2")
        assert len(patterns) == 2  # anti-2 and good-1


class TestPatternStorageThreadSafety:
    """Thread safety and concurrent access."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    def test_concurrent_writes(self, temp_graph_dir):
        """Multiple threads should safely write patterns."""
        storage = PatternStorage(temp_graph_dir)
        errors = []

        def add_patterns(thread_id):
            try:
                for i in range(10):
                    pattern = PatternRecord(
                        id=f"thread-{thread_id}-pattern-{i}",
                        pattern_type="anti-pattern",
                        name=f"Pattern {thread_id}-{i}",
                        description="",
                        trigger_conditions=[],
                        example_sequence=[],
                    )
                    storage.add_pattern(pattern)
            except Exception as e:
                errors.append(e)

        # Run 5 threads concurrently
        threads = [Thread(target=add_patterns, args=(i,)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Errors during concurrent writes: {errors}"

        # Verify all patterns were added
        all_patterns = storage.get_all_patterns()
        assert len(all_patterns) == 50  # 5 threads * 10 patterns each

    def test_concurrent_reads_and_writes(self, temp_graph_dir):
        """Concurrent reads and writes should not corrupt data."""
        storage = PatternStorage(temp_graph_dir)
        errors = []
        read_counts = []

        # Pre-populate some patterns
        for i in range(10):
            pattern = PatternRecord(
                id=f"initial-{i}",
                pattern_type="anti-pattern",
                name=f"Initial {i}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=0,
            )
            storage.add_pattern(pattern)

        def reader_thread():
            try:
                for _ in range(20):
                    patterns = storage.get_all_patterns()
                    read_counts.append(len(patterns))
            except Exception as e:
                errors.append(e)

        def writer_thread():
            try:
                for i in range(20):
                    pattern = PatternRecord(
                        id=f"written-{i}",
                        pattern_type="anti-pattern",
                        name=f"Written {i}",
                        description="",
                        trigger_conditions=[],
                        example_sequence=[],
                    )
                    storage.add_pattern(pattern)
                    storage.update_pattern_occurrence("initial-0", f"sess-{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            Thread(target=reader_thread),
            Thread(target=writer_thread),
            Thread(target=reader_thread),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert not errors, f"Errors during concurrent operations: {errors}"

        # Verify consistency
        final_patterns = storage.get_all_patterns()
        assert len(final_patterns) == 30  # 10 initial + 20 written

        initial_pattern = storage.get_pattern("initial-0")
        assert initial_pattern.occurrence_count == 20


class TestPatternStorageJSON:
    """JSON persistence and file operations."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    def test_json_format_correctness(self, temp_graph_dir):
        """JSON file should match expected format."""
        storage = PatternStorage(temp_graph_dir)

        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Read-Grep-Read Sequence",
            description="Multiple exploration tools used in sequence",
            trigger_conditions=["3+ exploration tools in last 5 calls"],
            example_sequence=["Read", "Grep", "Read"],
            occurrence_count=0,
            sessions_affected=[],
            correct_approach="Use spawn_gemini() for exploration",
            delegation_suggestion="spawn_gemini(prompt='...')",
        )
        storage.add_pattern(pattern)

        # Read raw JSON
        with open(storage.patterns_file) as f:
            data = json.load(f)

        # Verify structure
        assert "patterns" in data
        assert "good_patterns" in data
        assert len(data["patterns"]) == 1

        # Verify pattern fields
        stored_pattern = data["patterns"][0]
        assert stored_pattern["id"] == "test-1"
        assert stored_pattern["pattern_type"] == "anti-pattern"
        assert stored_pattern["name"] == "Read-Grep-Read Sequence"
        assert stored_pattern["occurrence_count"] == 0
        assert (
            stored_pattern["correct_approach"] == "Use spawn_gemini() for exploration"
        )

    def test_json_pretty_printed(self, temp_graph_dir):
        """JSON file should be human-readable."""
        storage = PatternStorage(temp_graph_dir)

        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Test",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        storage.add_pattern(pattern)

        content = storage.patterns_file.read_text()

        # Should have indentation (pretty printed)
        assert "\n" in content
        assert "  " in content  # 2-space indentation

    def test_atomic_write_safety(self, temp_graph_dir):
        """Atomic writes should not leave corrupted files."""
        storage = PatternStorage(temp_graph_dir)

        # Add patterns
        for i in range(5):
            pattern = PatternRecord(
                id=f"test-{i}",
                pattern_type="anti-pattern",
                name=f"Pattern {i}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
            )
            storage.add_pattern(pattern)

        # File should always be valid JSON
        with open(storage.patterns_file) as f:
            data = json.load(f)

        assert data is not None
        assert "patterns" in data
        assert len(data["patterns"]) == 5

    def test_corrupt_file_recovery(self, temp_graph_dir):
        """Should handle corrupt JSON gracefully."""
        storage = PatternStorage(temp_graph_dir)

        # Corrupt the file
        storage.patterns_file.write_text("{invalid json")

        # Reading should return empty patterns
        patterns = storage.get_all_patterns()
        assert patterns == []

        # Writing should recover
        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Pattern",
            description="",
            trigger_conditions=[],
            example_sequence=[],
        )
        storage.add_pattern(pattern)

        # File should be valid again
        retrieved = storage.get_pattern("test-1")
        assert retrieved is not None


class TestPatternStorageAnalytics:
    """Analytics export functionality."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    def test_export_analytics_empty(self, temp_graph_dir):
        """Should export empty analytics."""
        storage = PatternStorage(temp_graph_dir)

        analytics = storage.export_analytics()

        assert "timestamp" in analytics
        assert "summary" in analytics
        assert analytics["summary"]["total_anti_patterns"] == 0
        assert analytics["summary"]["total_good_patterns"] == 0
        assert analytics["summary"]["total_detections"] == 0

    def test_export_analytics_with_patterns(self, temp_graph_dir):
        """Should export analytics with pattern statistics."""
        storage = PatternStorage(temp_graph_dir)

        # Add patterns with various occurrence counts
        patterns_data = [
            ("anti-1", "anti-pattern", 5),
            ("anti-2", "anti-pattern", 3),
            ("good-1", "good-pattern", 10),
        ]

        for pattern_id, pattern_type, occurrence_count in patterns_data:
            pattern = PatternRecord(
                id=pattern_id,
                pattern_type=pattern_type,
                name=f"Pattern {pattern_id}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
                occurrence_count=occurrence_count,
                sessions_affected=[f"sess-{i}" for i in range(occurrence_count)],
            )
            storage.add_pattern(pattern)

        analytics = storage.export_analytics()

        # Verify summary
        # total_detections counts only anti-patterns (occurrences of violations)
        assert analytics["summary"]["total_anti_patterns"] == 2
        assert analytics["summary"]["total_good_patterns"] == 1
        assert analytics["summary"]["total_detections"] == 8  # 5 + 3 anti-patterns only

        # Verify anti-patterns sorted by occurrence
        anti_patterns = analytics["anti_patterns"]
        assert len(anti_patterns) == 2
        assert anti_patterns[0]["id"] == "anti-1"  # Higher occurrence first
        assert anti_patterns[0]["occurrences"] == 5
        assert anti_patterns[1]["occurrences"] == 3

        # Verify good patterns
        good_patterns = analytics["good_patterns"]
        assert len(good_patterns) == 1
        assert good_patterns[0]["id"] == "good-1"

    def test_export_analytics_timestamp(self, temp_graph_dir):
        """Should include current timestamp in export."""
        storage = PatternStorage(temp_graph_dir)

        before = datetime.utcnow().isoformat()
        analytics = storage.export_analytics()
        after = datetime.utcnow().isoformat()

        timestamp = analytics["timestamp"]

        # Timestamp should be between before and after
        assert before <= timestamp <= after


class TestPatternStorageEdgeCases:
    """Edge cases and error handling."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    def test_update_non_existent_pattern_occurrence(self, temp_graph_dir):
        """Should handle updating non-existent pattern gracefully."""
        storage = PatternStorage(temp_graph_dir)

        result = storage.update_pattern_occurrence("non-existent", "sess-1")
        assert result is False

    def test_special_characters_in_pattern_name(self, temp_graph_dir):
        """Should handle special characters in pattern data."""
        storage = PatternStorage(temp_graph_dir)

        pattern = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Pattern with émojis 🚨 and 特殊文字",
            description="Description with quotes 'single' and \"double\"",
            trigger_conditions=["condition with unicode: π, €, ¥"],
            example_sequence=["Read", "Grep"],
        )
        storage.add_pattern(pattern)

        retrieved = storage.get_pattern("test-1")

        assert retrieved.name == "Pattern with émojis 🚨 and 特殊文字"
        assert "π" in retrieved.trigger_conditions[0]

    def test_large_number_of_patterns(self, temp_graph_dir):
        """Should handle large number of patterns."""
        storage = PatternStorage(temp_graph_dir)

        # Add 100 patterns
        for i in range(100):
            pattern = PatternRecord(
                id=f"pattern-{i:03d}",
                pattern_type="anti-pattern" if i % 2 == 0 else "good-pattern",
                name=f"Pattern {i}",
                description=f"Description {i}",
                trigger_conditions=[f"condition-{i}"],
                example_sequence=[f"action-{i}"],
            )
            storage.add_pattern(pattern)

        # Verify all were stored
        all_patterns = storage.get_all_patterns()
        assert len(all_patterns) == 100

        # Verify random access
        pattern_50 = storage.get_pattern("pattern-050")
        assert pattern_50 is not None
        assert pattern_50.name == "Pattern 50"

    def test_clear_all_patterns(self, temp_graph_dir):
        """Should clear all patterns."""
        storage = PatternStorage(temp_graph_dir)

        # Add patterns
        for i in range(5):
            pattern = PatternRecord(
                id=f"test-{i}",
                pattern_type="anti-pattern",
                name=f"Pattern {i}",
                description="",
                trigger_conditions=[],
                example_sequence=[],
            )
            storage.add_pattern(pattern)

        assert len(storage.get_all_patterns()) == 5

        # Clear all
        storage.clear_all()

        assert len(storage.get_all_patterns()) == 0
        assert storage.patterns_file.exists()  # File still exists


class TestPatternStorageUpdateExisting:
    """Tests for updating existing patterns."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary .htmlgraph directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_dir = Path(tmpdir) / ".htmlgraph"
            graph_dir.mkdir(parents=True)
            yield graph_dir

    def test_update_pattern_by_id(self, temp_graph_dir):
        """Should update existing pattern when adding with same ID."""
        storage = PatternStorage(temp_graph_dir)

        # Add initial pattern
        pattern1 = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Initial Name",
            description="Initial description",
            trigger_conditions=["cond1"],
            example_sequence=["seq1"],
            occurrence_count=5,
        )
        storage.add_pattern(pattern1)

        # Update with new data
        pattern2 = PatternRecord(
            id="test-1",
            pattern_type="anti-pattern",
            name="Updated Name",
            description="Updated description",
            trigger_conditions=["cond1", "cond2"],
            example_sequence=["seq1", "seq2"],
            occurrence_count=10,
        )
        storage.add_pattern(pattern2)

        # Should have only one pattern
        all_patterns = storage.get_all_patterns()
        assert len(all_patterns) == 1

        # Should have updated data
        retrieved = storage.get_pattern("test-1")
        assert retrieved.name == "Updated Name"
        assert retrieved.occurrence_count == 10
        assert len(retrieved.trigger_conditions) == 2
