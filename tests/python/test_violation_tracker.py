"""
Unit tests for ViolationTracker and CIGS models.

Tests cover:
- ViolationRecord creation and serialization
- ViolationTracker recording and retrieval
- SessionViolationSummary aggregation
- Thread-safety and concurrent access
- JSONL file persistence
"""

import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import pytest
from htmlgraph.cigs.models import (
    AutonomyLevel,
    CostMetrics,
    OperationClassification,
    SessionViolationSummary,
    TokenCost,
    ViolationRecord,
    ViolationType,
)
from htmlgraph.cigs.tracker import ViolationTracker


class TestViolationRecord:
    """Tests for ViolationRecord dataclass."""

    def test_create_violation_record(self):
        """Test creating a violation record."""
        record = ViolationRecord(
            id="viol-001",
            session_id="sess-001",
            timestamp=datetime.utcnow(),
            tool="Read",
            tool_params={"file_path": "/test/file.py"},
            violation_type=ViolationType.DIRECT_EXPLORATION,
            context_before="Exploring codebase",
            should_have_delegated_to="spawn_gemini()",
            actual_cost_tokens=5000,
            optimal_cost_tokens=500,
            waste_tokens=4500,
            warning_level=1,
            was_warned=False,
            warning_ignored=False,
            agent="claude-code",
            feature_id="feat-123",
        )

        assert record.id == "viol-001"
        assert record.tool == "Read"
        assert record.waste_tokens == 4500
        assert record.violation_type == ViolationType.DIRECT_EXPLORATION

    def test_violation_record_to_dict(self):
        """Test serialization to dictionary."""
        record = ViolationRecord(
            id="viol-001",
            session_id="sess-001",
            timestamp=datetime(2026, 1, 4, 10, 0, 0),
            tool="Grep",
            tool_params={"pattern": "test"},
            violation_type=ViolationType.DIRECT_EXPLORATION,
            actual_cost_tokens=3000,
            optimal_cost_tokens=500,
            waste_tokens=2500,
        )

        data = record.to_dict()

        assert data["id"] == "viol-001"
        assert data["tool"] == "Grep"
        assert data["violation_type"] == "direct_exploration"
        assert data["actual_cost_tokens"] == 3000
        assert isinstance(data["timestamp"], str)

    def test_violation_record_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "viol-001",
            "session_id": "sess-001",
            "timestamp": "2026-01-04T10:00:00",
            "tool": "Edit",
            "tool_params": {},
            "violation_type": "direct_implementation",
            "context_before": None,
            "should_have_delegated_to": "spawn_codex()",
            "actual_cost_tokens": 4000,
            "optimal_cost_tokens": 500,
            "waste_tokens": 3500,
            "warning_level": 1,
            "was_warned": False,
            "warning_ignored": False,
            "agent": "claude-code",
            "feature_id": None,
        }

        record = ViolationRecord.from_dict(data)

        assert record.id == "viol-001"
        assert record.tool == "Edit"
        assert record.violation_type == ViolationType.DIRECT_IMPLEMENTATION
        assert isinstance(record.timestamp, datetime)


class TestViolationTracker:
    """Tests for ViolationTracker class."""

    @pytest.fixture
    def temp_graph_dir(self):
        """Create temporary graph directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_graph_dir):
        """Test tracker initialization."""
        tracker = ViolationTracker(temp_graph_dir)

        assert tracker.graph_dir == temp_graph_dir
        assert tracker.cigs_dir == temp_graph_dir / "cigs"
        assert tracker.violations_file == temp_graph_dir / "cigs" / "violations.jsonl"
        # Directory should be created
        assert tracker.cigs_dir.exists()

    def test_record_violation(self, temp_graph_dir):
        """Test recording a violation."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-test-001")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Single file exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini(prompt='Search codebase')",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        violation_id = tracker.record_violation(
            tool="Read",
            params={"file_path": "/test/file.py"},
            classification=classification,
            predicted_waste=4500,
        )

        assert violation_id.startswith("viol-")
        assert tracker.violations_file.exists()

    def test_record_multiple_violations(self, temp_graph_dir):
        """Test recording multiple violations."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-test-001")

        classification = OperationClassification(
            tool="Grep",
            category="exploration",
            should_delegate=True,
            reason="Code search",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=3000,
            optimal_cost=500,
            waste_percentage=83.3,
        )

        ids = []
        for i in range(3):
            violation_id = tracker.record_violation(
                tool="Grep",
                params={"pattern": f"pattern-{i}"},
                classification=classification,
                predicted_waste=2500,
            )
            ids.append(violation_id)

        assert len(ids) == 3
        assert len(set(ids)) == 3  # All unique
        assert tracker.violations_file.exists()

    def test_get_session_violations(self, temp_graph_dir):
        """Test retrieving session violations."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-test-001")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        # Record 2 violations
        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )
        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )

        summary = tracker.get_session_violations()

        assert summary.session_id == "sess-test-001"
        assert summary.total_violations == 2
        assert summary.total_waste_tokens == 9000
        assert len(summary.violations) == 2
        assert not summary.circuit_breaker_triggered

    def test_circuit_breaker_trigger(self, temp_graph_dir):
        """Test circuit breaker triggering at 3 violations."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-test-cb")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        # Record 3 violations
        for _ in range(3):
            tracker.record_violation(
                tool="Read",
                params={},
                classification=classification,
                predicted_waste=4500,
            )

        summary = tracker.get_session_violations()

        assert summary.total_violations == 3
        assert summary.circuit_breaker_triggered

    def test_violations_by_type(self, temp_graph_dir):
        """Test aggregation of violations by type."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-test-types")

        # Record exploration violations
        exploration_class = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        # Record implementation violations
        impl_class = OperationClassification(
            tool="Edit",
            category="implementation",
            should_delegate=True,
            reason="Implementation",
            is_exploration_sequence=False,
            suggested_delegation="spawn_codex()",
            predicted_cost=4000,
            optimal_cost=500,
            waste_percentage=87.5,
        )

        tracker.record_violation(
            tool="Read",
            params={},
            classification=exploration_class,
            predicted_waste=4500,
        )
        tracker.record_violation(
            tool="Edit",
            params={},
            classification=impl_class,
            predicted_waste=3500,
        )
        tracker.record_violation(
            tool="Read",
            params={},
            classification=exploration_class,
            predicted_waste=4500,
        )

        summary = tracker.get_session_violations()

        assert summary.total_violations == 3
        assert ViolationType.DIRECT_EXPLORATION in summary.violations_by_type
        assert ViolationType.DIRECT_IMPLEMENTATION in summary.violations_by_type
        assert summary.violations_by_type[ViolationType.DIRECT_EXPLORATION] == 2
        assert summary.violations_by_type[ViolationType.DIRECT_IMPLEMENTATION] == 1

    def test_get_recent_violations(self, temp_graph_dir):
        """Test retrieving violations from recent sessions."""
        tracker = ViolationTracker(temp_graph_dir)

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        # Record violations for multiple sessions
        for session_num in range(7):
            tracker.set_session_id(f"sess-{session_num:03d}")
            for _ in range(2):
                tracker.record_violation(
                    tool="Read",
                    params={},
                    classification=classification,
                    predicted_waste=4500,
                )

        # Get last 3 sessions
        recent = tracker.get_recent_violations(sessions=3)

        session_ids = set(v.session_id for v in recent)
        assert len(session_ids) == 3
        # Should be last 3: sess-004, sess-005, sess-006
        assert "sess-004" in session_ids
        assert "sess-005" in session_ids
        assert "sess-006" in session_ids

    def test_get_session_waste(self, temp_graph_dir):
        """Test getting total session waste."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-waste")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )
        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=3500,
        )

        waste = tracker.get_session_waste()

        assert waste == 8000

    def test_thread_safety(self, temp_graph_dir):
        """Test thread-safe concurrent violation recording."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-thread-test")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        recorded_ids = []
        lock = threading.Lock()

        def record_violations():
            for i in range(10):
                violation_id = tracker.record_violation(
                    tool="Read",
                    params={"index": i},
                    classification=classification,
                    predicted_waste=4500,
                )
                with lock:
                    recorded_ids.append(violation_id)

        # Create multiple threads
        threads = [threading.Thread(target=record_violations) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Should have recorded 50 violations (5 threads * 10 violations)
        assert len(recorded_ids) == 50
        assert len(set(recorded_ids)) == 50  # All unique

        summary = tracker.get_session_violations()
        assert summary.total_violations == 50

    def test_persistence_across_instances(self, temp_graph_dir):
        """Test that violations persist across tracker instances."""
        # First instance records violations
        tracker1 = ViolationTracker(temp_graph_dir)
        tracker1.set_session_id("sess-persist")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        tracker1.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )

        # Second instance reads violations
        tracker2 = ViolationTracker(temp_graph_dir)
        summary = tracker2.get_session_violations("sess-persist")

        assert summary.total_violations == 1
        assert summary.total_waste_tokens == 4500

    def test_jsonl_format(self, temp_graph_dir):
        """Test that violations are stored in valid JSONL format."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-jsonl")

        classification = OperationClassification(
            tool="Grep",
            category="exploration",
            should_delegate=True,
            reason="Code search",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=3000,
            optimal_cost=500,
            waste_percentage=83.3,
        )

        tracker.record_violation(
            tool="Grep",
            params={"pattern": "test"},
            classification=classification,
            predicted_waste=2500,
        )

        # Read and validate JSONL format
        with open(tracker.violations_file) as f:
            lines = f.readlines()

        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["tool"] == "Grep"
        assert data["violation_type"] == "direct_exploration"
        assert data["actual_cost_tokens"] == 3000

    def test_compliance_rate_calculation(self, temp_graph_dir):
        """Test compliance rate calculation."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-compliance")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        # No violations = 100% compliance
        summary = tracker.get_session_violations()
        assert summary.compliance_rate == 1.0

        # 1 violation = 80% compliance (1.0 - 1/5)
        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )
        summary = tracker.get_session_violations()
        assert summary.compliance_rate == 0.8

        # 5 violations = 0% compliance (saturated at 1.0 - 5/5)
        for _ in range(4):
            tracker.record_violation(
                tool="Read",
                params={},
                classification=classification,
                predicted_waste=4500,
            )
        summary = tracker.get_session_violations()
        assert summary.compliance_rate == 0.0

    def test_empty_violations(self, temp_graph_dir):
        """Test behavior with no violations."""
        tracker = ViolationTracker(temp_graph_dir)

        summary = tracker.get_session_violations()

        assert summary.total_violations == 0
        assert summary.total_waste_tokens == 0
        assert summary.compliance_rate == 1.0
        assert not summary.circuit_breaker_triggered
        assert len(summary.violations) == 0

    def test_clear_session_file(self, temp_graph_dir):
        """Test clearing the violations file."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-clear")

        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="Exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        tracker.record_violation(
            tool="Read",
            params={},
            classification=classification,
            predicted_waste=4500,
        )

        assert tracker.violations_file.exists()

        tracker.clear_session_file()

        assert not tracker.violations_file.exists()

        summary = tracker.get_session_violations()
        assert summary.total_violations == 0

    def test_exploration_sequence_classification(self, temp_graph_dir):
        """Test classification of exploration sequence violations."""
        tracker = ViolationTracker(temp_graph_dir)
        tracker.set_session_id("sess-explore-seq")

        # Record with exploration sequence flag
        classification = OperationClassification(
            tool="Glob",
            category="exploration",
            should_delegate=True,
            reason="Part of exploration sequence",
            is_exploration_sequence=True,
            suggested_delegation="spawn_gemini()",
            predicted_cost=2000,
            optimal_cost=500,
            waste_percentage=75.0,
        )

        tracker.record_violation(
            tool="Glob",
            params={},
            classification=classification,
            predicted_waste=1500,
        )

        summary = tracker.get_session_violations()

        assert ViolationType.EXPLORATION_SEQUENCE in summary.violations_by_type


class TestSessionViolationSummary:
    """Tests for SessionViolationSummary."""

    def test_summary_string_representation(self):
        """Test human-readable summary string."""
        summary = SessionViolationSummary(
            session_id="sess-001",
            total_violations=3,
            violations_by_type={
                ViolationType.DIRECT_EXPLORATION: 2,
                ViolationType.DIRECT_IMPLEMENTATION: 1,
            },
            total_waste_tokens=12000,
            circuit_breaker_triggered=False,
            compliance_rate=0.4,
        )

        summary_str = summary.summary()

        assert "sess-001" in summary_str
        assert "3" in summary_str
        assert "40.0%" in summary_str
        assert "12000" in summary_str

    def test_count_property(self):
        """Test count property."""
        summary = SessionViolationSummary(
            session_id="sess-001",
            total_violations=5,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=0.5,
        )

        assert summary.count == 5


class TestDataModels:
    """Tests for other CIGS data models."""

    def test_token_cost_creation(self):
        """Test TokenCost creation."""
        cost = TokenCost(
            total_tokens=10000,
            orchestrator_tokens=1000,
            subagent_tokens=9000,
            estimated_savings=4500,
        )

        assert cost.total_tokens == 10000
        assert cost.estimated_savings == 4500

    def test_operation_classification_creation(self):
        """Test OperationClassification creation."""
        classification = OperationClassification(
            tool="Read",
            category="exploration",
            should_delegate=True,
            reason="File exploration",
            is_exploration_sequence=False,
            suggested_delegation="spawn_gemini()",
            predicted_cost=5000,
            optimal_cost=500,
            waste_percentage=90.0,
        )

        assert classification.tool == "Read"
        assert classification.should_delegate
        assert classification.waste_percentage == 90.0

    def test_autonomy_level_creation(self):
        """Test AutonomyLevel creation."""
        autonomy = AutonomyLevel(
            level="collaborator",
            messaging_intensity="high",
            enforcement_mode="strict",
            reason="High violation rate detected",
            based_on_violations=5,
            based_on_patterns=["exploration_sequence"],
        )

        assert autonomy.level == "collaborator"
        assert autonomy.messaging_intensity == "high"
        assert len(autonomy.based_on_patterns) == 1

    def test_cost_metrics_creation(self):
        """Test CostMetrics creation."""
        metrics = CostMetrics(
            total_tokens=50000,
            orchestrator_tokens=5000,
            subagent_tokens=45000,
            waste_tokens=10000,
            optimal_tokens=40000,
            efficiency_score=80.0,
            waste_percentage=20.0,
        )

        assert metrics.total_tokens == 50000
        assert metrics.efficiency_score == 80.0
