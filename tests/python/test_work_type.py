"""Tests for Phase 1: Work Type Classification."""

import pytest
from htmlgraph import WorkType, SpikeType, MaintenanceType, Spike, Chore
from htmlgraph.work_type_utils import infer_work_type_from_id
from htmlgraph.models import Session


class TestWorkTypeEnums:
    """Test work type enum definitions."""

    def test_work_type_values(self):
        """Test WorkType enum values."""
        assert WorkType.FEATURE.value == "feature-implementation"
        assert WorkType.SPIKE.value == "spike-investigation"
        assert WorkType.BUG_FIX.value == "bug-fix"
        assert WorkType.MAINTENANCE.value == "maintenance"
        assert WorkType.DOCUMENTATION.value == "documentation"
        assert WorkType.PLANNING.value == "planning"
        assert WorkType.REVIEW.value == "review"
        assert WorkType.ADMIN.value == "admin"

    def test_spike_type_values(self):
        """Test SpikeType enum values."""
        assert SpikeType.TECHNICAL.value == "technical"
        assert SpikeType.ARCHITECTURAL.value == "architectural"
        assert SpikeType.RISK.value == "risk"
        assert SpikeType.GENERAL.value == "general"

    def test_maintenance_type_values(self):
        """Test MaintenanceType enum values."""
        assert MaintenanceType.CORRECTIVE.value == "corrective"
        assert MaintenanceType.ADAPTIVE.value == "adaptive"
        assert MaintenanceType.PERFECTIVE.value == "perfective"
        assert MaintenanceType.PREVENTIVE.value == "preventive"


class TestSpikeModel:
    """Test Spike model."""

    def test_spike_defaults(self):
        """Test Spike model with defaults."""
        spike = Spike(
            id="spike-123",
            title="Investigate OAuth providers"
        )

        assert spike.type == "spike"
        assert spike.spike_type == SpikeType.GENERAL
        assert spike.timebox_hours is None
        assert spike.findings is None
        assert spike.decision is None

    def test_spike_with_all_fields(self):
        """Test Spike model with all fields."""
        spike = Spike(
            id="spike-456",
            title="Research API architecture",
            spike_type=SpikeType.ARCHITECTURAL,
            timebox_hours=8,
            findings="GraphQL provides better type safety than REST",
            decision="Use GraphQL for public API"
        )

        assert spike.type == "spike"
        assert spike.spike_type == SpikeType.ARCHITECTURAL
        assert spike.timebox_hours == 8
        assert spike.findings == "GraphQL provides better type safety than REST"
        assert spike.decision == "Use GraphQL for public API"

    def test_spike_enforces_type(self):
        """Test that Spike always has type='spike'."""
        # Even if we try to pass a different type, it should be overridden
        spike = Spike(
            id="spike-789",
            title="Test spike",
            type="wrong-type"  # This should be ignored
        )

        assert spike.type == "spike"


class TestChoreModel:
    """Test Chore model."""

    def test_chore_defaults(self):
        """Test Chore model with defaults."""
        chore = Chore(
            id="chore-123",
            title="Update dependencies"
        )

        assert chore.type == "chore"
        assert chore.maintenance_type is None
        assert chore.technical_debt_score is None

    def test_chore_with_all_fields(self):
        """Test Chore model with all fields."""
        chore = Chore(
            id="chore-456",
            title="Refactor authentication module",
            maintenance_type=MaintenanceType.PREVENTIVE,
            technical_debt_score=7
        )

        assert chore.type == "chore"
        assert chore.maintenance_type == MaintenanceType.PREVENTIVE
        assert chore.technical_debt_score == 7

    def test_chore_enforces_type(self):
        """Test that Chore always has type='chore'."""
        chore = Chore(
            id="chore-789",
            title="Test chore",
            type="wrong-type"  # This should be ignored
        )

        assert chore.type == "chore"


class TestWorkTypeInference:
    """Test work type inference utilities."""

    def test_infer_from_feature_id(self):
        """Test inference from feature ID."""
        assert infer_work_type_from_id("feat-123") == WorkType.FEATURE.value
        assert infer_work_type_from_id("feature-456") == WorkType.FEATURE.value

    def test_infer_from_spike_id(self):
        """Test inference from spike ID."""
        assert infer_work_type_from_id("spike-123") == WorkType.SPIKE.value

    def test_infer_from_bug_id(self):
        """Test inference from bug ID."""
        assert infer_work_type_from_id("bug-123") == WorkType.BUG_FIX.value

    def test_infer_from_chore_id(self):
        """Test inference from chore ID."""
        assert infer_work_type_from_id("chore-123") == WorkType.MAINTENANCE.value

    def test_infer_from_doc_id(self):
        """Test inference from documentation ID."""
        assert infer_work_type_from_id("doc-123") == WorkType.DOCUMENTATION.value

    def test_infer_from_plan_id(self):
        """Test inference from planning ID."""
        assert infer_work_type_from_id("plan-123") == WorkType.PLANNING.value

    def test_infer_returns_none_for_unknown(self):
        """Test that unknown IDs return None."""
        assert infer_work_type_from_id("unknown-123") is None
        assert infer_work_type_from_id(None) is None
        assert infer_work_type_from_id("") is None


class TestSessionWorkTypeCalculations:
    """Test Session work type calculation methods."""

    @pytest.fixture
    def mock_events(self, tmp_path):
        """Create mock events for testing."""
        import json
        from datetime import datetime

        events_dir = tmp_path / "events"
        events_dir.mkdir()

        session_id = "test-session-001"
        events = [
            {"event_id": "evt-001", "tool": "Bash", "work_type": "feature-implementation"},
            {"event_id": "evt-002", "tool": "Edit", "work_type": "feature-implementation"},
            {"event_id": "evt-003", "tool": "Read", "work_type": "spike-investigation"},
            {"event_id": "evt-004", "tool": "Bash", "work_type": "feature-implementation"},
            {"event_id": "evt-005", "tool": "Write", "work_type": "maintenance"},
        ]

        # Write events to JSONL file
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for evt in events:
                evt_record = {
                    **evt,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "summary": "Test event",
                    "success": True,
                    "feature_id": None,
                    "drift_score": None,
                    "start_commit": None,
                    "continued_from": None
                }
                f.write(json.dumps(evt_record) + "\n")

        return str(events_dir), session_id

    def test_calculate_work_breakdown(self, mock_events):
        """Test work breakdown calculation."""
        events_dir, session_id = mock_events

        session = Session(id=session_id, agent="test")
        breakdown = session.calculate_work_breakdown(events_dir=events_dir)

        assert breakdown["feature-implementation"] == 3
        assert breakdown["spike-investigation"] == 1
        assert breakdown["maintenance"] == 1

    def test_calculate_primary_work_type(self, mock_events):
        """Test primary work type calculation."""
        events_dir, session_id = mock_events

        session = Session(id=session_id, agent="test")
        primary = session.calculate_primary_work_type(events_dir=events_dir)

        assert primary == "feature-implementation"  # Most common type

    def test_empty_session_returns_none(self, tmp_path):
        """Test that empty session returns None for primary work type."""
        events_dir = tmp_path / "events"
        events_dir.mkdir()

        session = Session(id="empty-session", agent="test")
        primary = session.calculate_primary_work_type(events_dir=str(events_dir))

        assert primary is None
