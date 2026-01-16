"""Tests for Phase 2: Analytics API."""

import json
from datetime import datetime

import pytest
from htmlgraph import SDK, Analytics, WorkType
from htmlgraph.models import Session


class TestAnalyticsIntegration:
    """Test Analytics integration with SDK."""

    def test_sdk_has_analytics_property(self, isolated_graph_dir, isolated_db):
        """Test that SDK has analytics property."""
        sdk = SDK(directory=isolated_graph_dir, agent="test", db_path=str(isolated_db))

        assert hasattr(sdk, "analytics")
        assert isinstance(sdk.analytics, Analytics)

    def test_analytics_has_sdk_reference(self, isolated_graph_dir, isolated_db):
        """Test that Analytics has reference to SDK."""
        sdk = SDK(directory=isolated_graph_dir, agent="test", db_path=str(isolated_db))

        assert sdk.analytics.sdk is sdk


class TestWorkTypeDistribution:
    """Test work_type_distribution() method."""

    @pytest.fixture
    def sdk_with_events(self, isolated_graph_dir_full, isolated_db):
        """Create SDK with mock events."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        # Create session
        session_id = "test-session-001"
        events = [
            {"work_type": WorkType.FEATURE.value},  # 3 feature events
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.SPIKE.value},  # 2 spike events
            {"work_type": WorkType.SPIKE.value},
            {"work_type": WorkType.MAINTENANCE.value},  # 1 maintenance event
        ]

        # Write events to JSONL
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    "feature_id": None,
                    "drift_score": None,
                    "start_commit": None,
                    "continued_from": None,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML file
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        return sdk, session_id

    def test_distribution_for_session(self, sdk_with_events):
        """Test work type distribution for a single session."""
        sdk, session_id = sdk_with_events

        dist = sdk.analytics.work_type_distribution(session_id=session_id)

        # 3 feature, 2 spike, 1 maintenance = 6 total
        # Expected: feature=50%, spike=33.33%, maintenance=16.67%
        assert dist[WorkType.FEATURE.value] == pytest.approx(50.0, rel=0.1)
        assert dist[WorkType.SPIKE.value] == pytest.approx(33.33, rel=0.1)
        assert dist[WorkType.MAINTENANCE.value] == pytest.approx(16.67, rel=0.1)

    def test_distribution_empty_session(self, isolated_graph_dir_full, isolated_db):
        """Test distribution for session with no events."""
        sdk = SDK(
            directory=isolated_graph_dir_full, agent="test", db_path=str(isolated_db)
        )
        dist = sdk.analytics.work_type_distribution(session_id="nonexistent")

        assert dist == {}

    def test_distribution_ignores_events_without_work_type(
        self, isolated_graph_dir_full, isolated_db
    ):
        """Test that events without work_type are ignored."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-002"
        events = [
            {"work_type": WorkType.FEATURE.value},
            {"work_type": None},  # No work type
            {"work_type": WorkType.SPIKE.value},
            {},  # No work type field
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        dist = sdk.analytics.work_type_distribution(session_id=session_id)

        # Only 2 events have work_type, so they're 50% each
        assert dist[WorkType.FEATURE.value] == pytest.approx(50.0, rel=0.1)
        assert dist[WorkType.SPIKE.value] == pytest.approx(50.0, rel=0.1)


class TestSpikeToFeatureRatio:
    """Test spike_to_feature_ratio() method."""

    @pytest.fixture
    def sdk_with_mixed_work(self, isolated_graph_dir_full, isolated_db):
        """Create SDK with mixed spike and feature events."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-003"
        events = [
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.SPIKE.value},
            {"work_type": WorkType.SPIKE.value},
            {"work_type": WorkType.SPIKE.value},
            {"work_type": WorkType.MAINTENANCE.value},  # Should be ignored
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        return sdk, session_id

    def test_spike_to_feature_ratio(self, sdk_with_mixed_work):
        """Test spike-to-feature ratio calculation."""
        sdk, session_id = sdk_with_mixed_work

        ratio = sdk.analytics.spike_to_feature_ratio(session_id=session_id)

        # 3 spike, 2 feature = 3/2 = 1.5
        assert ratio == pytest.approx(1.5, rel=0.01)

    def test_ratio_with_no_features(self, isolated_graph_dir_full, isolated_db):
        """Test ratio when there are no feature events."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-004"
        events = [
            {"work_type": WorkType.SPIKE.value},
            {"work_type": WorkType.SPIKE.value},
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        ratio = sdk.analytics.spike_to_feature_ratio(session_id=session_id)

        # No features = return 0.0
        assert ratio == 0.0

    def test_ratio_empty_session(self, isolated_graph_dir_full, isolated_db):
        """Test ratio for empty session."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        ratio = sdk.analytics.spike_to_feature_ratio(session_id="nonexistent")

        assert ratio == 0.0


class TestMaintenanceBurden:
    """Test maintenance_burden() method."""

    @pytest.fixture
    def sdk_with_maintenance(self, isolated_graph_dir_full, isolated_db):
        """Create SDK with maintenance events."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-005"
        events = [
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.BUG_FIX.value},  # Maintenance
            {"work_type": WorkType.MAINTENANCE.value},  # Maintenance
            {"work_type": WorkType.SPIKE.value},  # Not maintenance
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        return sdk, session_id

    def test_maintenance_burden_calculation(self, sdk_with_maintenance):
        """Test maintenance burden calculation."""
        sdk, session_id = sdk_with_maintenance

        burden = sdk.analytics.maintenance_burden(session_id=session_id)

        # 2 maintenance out of 6 total = 33.33%
        assert burden == pytest.approx(33.33, rel=0.1)

    def test_burden_with_no_maintenance(self, isolated_graph_dir_full, isolated_db):
        """Test burden when there's no maintenance work."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-006"
        events = [
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.SPIKE.value},
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        burden = sdk.analytics.maintenance_burden(session_id=session_id)

        assert burden == 0.0

    def test_burden_empty_session(self, isolated_graph_dir_full, isolated_db):
        """Test burden for empty session."""
        graph_dir = isolated_graph_dir_full

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        burden = sdk.analytics.maintenance_burden(session_id="nonexistent")

        assert burden == 0.0


class TestSessionFiltering:
    """Test get_sessions_by_work_type() method."""

    @pytest.fixture
    def sdk_with_sessions(self, isolated_graph_dir_full, isolated_db):
        """Create SDK with multiple sessions."""
        graph_dir = isolated_graph_dir_full
        sessions_dir = graph_dir / "sessions"

        # Create sessions with different primary work types
        from htmlgraph.converter import session_to_html

        sessions = [
            Session(
                id="session-spike-001",
                agent="test",
                primary_work_type=WorkType.SPIKE.value,
            ),
            Session(
                id="session-feature-001",
                agent="test",
                primary_work_type=WorkType.FEATURE.value,
            ),
            Session(
                id="session-spike-002",
                agent="test",
                primary_work_type=WorkType.SPIKE.value,
            ),
            Session(
                id="session-maintenance-001",
                agent="test",
                primary_work_type=WorkType.MAINTENANCE.value,
            ),
        ]

        for session in sessions:
            session_to_html(session, sessions_dir / f"{session.id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        return sdk

    def test_filter_by_spike_work_type(self, sdk_with_sessions):
        """Test filtering sessions by spike work type."""
        sdk = sdk_with_sessions

        spike_sessions = sdk.analytics.get_sessions_by_work_type(WorkType.SPIKE.value)

        assert len(spike_sessions) == 2
        assert "session-spike-001" in spike_sessions
        assert "session-spike-002" in spike_sessions

    def test_filter_by_feature_work_type(self, sdk_with_sessions):
        """Test filtering sessions by feature work type."""
        sdk = sdk_with_sessions

        feature_sessions = sdk.analytics.get_sessions_by_work_type(
            WorkType.FEATURE.value
        )

        assert len(feature_sessions) == 1
        assert "session-feature-001" in feature_sessions

    def test_filter_returns_empty_for_no_matches(self, sdk_with_sessions):
        """Test filtering returns empty list when no matches."""
        sdk = sdk_with_sessions

        doc_sessions = sdk.analytics.get_sessions_by_work_type(
            WorkType.DOCUMENTATION.value
        )

        assert len(doc_sessions) == 0


class TestSessionWorkBreakdownMethods:
    """Test session work breakdown convenience methods."""

    @pytest.fixture
    def sdk_with_session(self, isolated_graph_dir_full, isolated_db):
        """Create SDK with a session that has events."""
        graph_dir = isolated_graph_dir_full
        events_dir = graph_dir / "events"

        session_id = "test-session-007"
        events = [
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.FEATURE.value},
            {"work_type": WorkType.SPIKE.value},
        ]

        # Write events
        event_file = events_dir / f"{session_id}.jsonl"
        with event_file.open("w") as f:
            for i, evt in enumerate(events):
                evt_record = {
                    "event_id": f"evt-{i:03d}",
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    "agent": "test",
                    "tool": "Bash",
                    "summary": f"Event {i}",
                    "success": True,
                    **evt,
                }
                f.write(json.dumps(evt_record) + "\n")

        # Create session HTML
        from htmlgraph.converter import session_to_html

        session = Session(id=session_id, agent="test", event_count=len(events))
        session_to_html(session, graph_dir / "sessions" / f"{session_id}.html")

        sdk = SDK(directory=graph_dir, agent="test", db_path=str(isolated_db))
        return sdk, session_id

    def test_calculate_session_work_breakdown(self, sdk_with_session):
        """Test calculate_session_work_breakdown convenience method."""
        sdk, session_id = sdk_with_session

        breakdown = sdk.analytics.calculate_session_work_breakdown(session_id)

        assert breakdown[WorkType.FEATURE.value] == 2
        assert breakdown[WorkType.SPIKE.value] == 1

    def test_calculate_session_primary_work_type(self, sdk_with_session):
        """Test calculate_session_primary_work_type convenience method."""
        sdk, session_id = sdk_with_session

        primary = sdk.analytics.calculate_session_primary_work_type(session_id)

        assert primary == WorkType.FEATURE.value  # Most common
