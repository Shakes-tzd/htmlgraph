"""
Tests for multi-agent dashboard attribution.

Verifies that:
1. Agent badges are rendered on feature cards
2. Work timeline shows all agents who touched a feature
3. Agent analytics tab displays workload distribution
4. SDK can query agents who worked on a feature
5. Event-to-feature linking works correctly
6. Cost tracking by agent is accurate
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from htmlgraph import SDK
from htmlgraph.event_log import EventRecord, JsonlEventLog


@pytest.fixture
def tmp_htmlgraph(isolated_graph_dir_full: Path, isolated_db: Path):
    """Create a temporary .htmlgraph directory structure."""
    return isolated_graph_dir_full


@pytest.fixture
def event_log(tmp_htmlgraph: Path, isolated_db: Path):
    """Create event log instance."""
    events_dir = tmp_htmlgraph / "events"
    return JsonlEventLog(events_dir)


class TestAgentBadgeRendering:
    """Test that agent badges are rendered on feature cards."""

    def test_feature_card_shows_agent_assigned(self, tmp_htmlgraph: Path, isolated_db):
        """Feature card should display agent_assigned badge."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )

        # Create track first
        track = sdk.tracks.create("Test Track").save()

        # Create feature with track
        feature = sdk.features.create("Test Feature").set_track(track.id).save()

        # Verify agent is assigned
        assert feature.agent_assigned == "orchestrator"

        # In HTML rendering, agent badge should appear
        # This would be verified in dashboard rendering tests
        assert hasattr(feature, "agent_assigned")

    def test_multiple_features_show_different_agents(
        self, tmp_htmlgraph: Path, isolated_db
    ):
        """Features created by different agents should show different badges."""
        sdk1 = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        sdk2 = SDK(directory=tmp_htmlgraph, agent="codex", db_path=str(isolated_db))

        # Create track
        track = sdk1.tracks.create("Multi Agent Track").save()

        feat1 = sdk1.features.create("Orchestrator Feature").set_track(track.id).save()
        feat2 = sdk2.features.create("Codex Feature").set_track(track.id).save()

        assert feat1.agent_assigned == "orchestrator"
        assert feat2.agent_assigned == "codex"


class TestAgentWorkTimeline:
    """Test work timeline showing all agents who touched a feature."""

    def test_feature_tracks_multiple_agents(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Feature should track all agents who worked on it via events."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )

        # Create track and feature
        track = sdk.tracks.create("Multi-Agent Track").save()
        feature = sdk.features.create("Multi-Agent Feature").set_track(track.id).save()
        feature_id = feature.id

        # Simulate multiple agents working on it via events
        session_id = "test-session-001"
        agents = ["orchestrator", "codex", "gemini"]

        for i, agent in enumerate(agents):
            event = EventRecord(
                event_id=f"evt-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} updated feature",
                success=True,
                feature_id=feature_id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                work_type="feature-implementation",
                tokens_actual=1000 * (i + 1),
                cost_usd=0.01 * (i + 1),
            )
            event_log.append(event)

        # Query events for this feature (exclude creation events)
        all_events = event_log.query_events(feature_id=feature_id)
        events = [e for e in all_events if e.get("tool") != "FeatureCreate"]

        assert len(events) == 3
        agents_in_events = {e["agent"] for e in events}
        assert agents_in_events == {"orchestrator", "codex", "gemini"}

    def test_timeline_shows_timestamp_of_each_agent_work(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Timeline should show when each agent worked on feature."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("Timestamp Track").save()
        feature = sdk.features.create("Timestamped Feature").set_track(track.id).save()
        feature_id = feature.id

        # Create events with different timestamps
        session_id = "test-session-002"
        now = datetime.now(timezone.utc)

        agents = [
            ("orchestrator", now, 1000),
            ("codex", now, 2000),
            ("gemini", now, 3000),
        ]

        for i, (agent, ts, tokens) in enumerate(agents):
            event = EventRecord(
                event_id=f"evt-ts-{i}",
                timestamp=ts,
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} worked on feature",
                success=True,
                feature_id=feature_id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                tokens_actual=tokens,
                cost_usd=0.01 * (i + 1),
            )
            event_log.append(event)

        all_events = event_log.query_events(feature_id=feature_id)
        events = [e for e in all_events if e.get("tool") != "FeatureCreate"]

        # Verify timestamps are preserved
        assert len(events) == 3
        for event in events:
            assert "timestamp" in event
            assert event["timestamp"] is not None


class TestAgentAnalyticsView:
    """Test agent analytics tab with workload distribution."""

    def test_agent_workload_distribution(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Analytics should show features per agent."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )

        # Create track first
        track = sdk.tracks.create("Analytics Track").save()

        # Create multiple features
        features = []
        for i in range(3):
            f = sdk.features.create(f"Feature {i}").set_track(track.id).save()
            features.append(f)

        # Create events for different agents
        agents = ["orchestrator", "codex", "gemini"]
        session_id = "test-session-003"

        for i, agent in enumerate(agents):
            for j, feature in enumerate(features):
                if i <= j:  # Distribute work
                    event = EventRecord(
                        event_id=f"evt-dist-{i}-{j}",
                        timestamp=datetime.now(timezone.utc),
                        session_id=session_id,
                        agent=agent,
                        tool="Edit",
                        summary=f"{agent} worked on {feature.id}",
                        success=True,
                        feature_id=feature.id,
                        drift_score=None,
                        start_commit=None,
                        continued_from=None,
                        tokens_actual=1000,
                        cost_usd=0.01,
                    )
                    event_log.append(event)

        # Verify we can query events by agent
        orch_events = event_log.query_events(session_id=session_id)
        orch_agents = {e["agent"] for e in orch_events}

        assert "orchestrator" in orch_agents
        assert "codex" in orch_agents
        assert "gemini" in orch_agents

    def test_agent_cost_calculation(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Analytics should calculate total cost per agent."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("Cost Track").save()
        feature = sdk.features.create("Cost Feature").set_track(track.id).save()

        # Create events with costs
        session_id = "test-session-004"
        costs = {"orchestrator": 0.05, "codex": 0.10, "gemini": 0.15}

        for i, (agent, cost) in enumerate(costs.items()):
            event = EventRecord(
                event_id=f"evt-cost-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} worked",
                success=True,
                feature_id=feature.id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                tokens_actual=1000,
                cost_usd=cost,
            )
            event_log.append(event)

        # Query and verify costs
        events = event_log.query_events(feature_id=feature.id)
        total_cost = sum(e.get("cost_usd") or 0 for e in events)

        assert total_cost == pytest.approx(0.30, rel=1e-2)

    def test_agent_token_tracking(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db
    ):
        """Analytics should track tokens by agent."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("Token Track").save()
        feature = sdk.features.create("Token Feature").set_track(track.id).save()

        session_id = "test-session-005"
        tokens_by_agent = {"orchestrator": 5000, "codex": 10000, "gemini": 15000}

        for i, (agent, tokens) in enumerate(tokens_by_agent.items()):
            event = EventRecord(
                event_id=f"evt-tok-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} used {tokens} tokens",
                success=True,
                feature_id=feature.id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                tokens_actual=tokens,
                cost_usd=0.01,
            )
            event_log.append(event)

        events = event_log.query_events(feature_id=feature.id)
        total_tokens = sum(e.get("tokens_actual", 0) or 0 for e in events)

        assert total_tokens == 30000


class TestSDKAgentQuerying:
    """Test SDK methods to query agent work."""

    def test_feature_has_agent_assigned(self, tmp_htmlgraph: Path, isolated_db):
        """Feature should have agent_assigned field."""
        sdk = SDK(directory=tmp_htmlgraph, agent="claude", db_path=str(isolated_db))
        track = sdk.tracks.create("SDK Track").save()
        feature = sdk.features.create("SDK Test Feature").set_track(track.id).save()

        # Retrieve and verify
        retrieved = sdk.features.get(feature.id)
        assert retrieved is not None
        assert retrieved.agent_assigned == "claude"

    def test_query_features_by_agent(self, tmp_htmlgraph: Path, isolated_db):
        """Should be able to query features created by specific agent."""
        sdk1 = SDK(directory=tmp_htmlgraph, agent="agent1", db_path=str(isolated_db))
        sdk2 = SDK(directory=tmp_htmlgraph, agent="agent2", db_path=str(isolated_db))

        # Create track
        track = sdk1.tracks.create("Query Track").save()

        # Create features by different agents
        sdk1.features.create("Agent1 Feature").set_track(track.id).save()
        sdk2.features.create("Agent2 Feature").set_track(track.id).save()
        sdk1.features.create("Agent1 Feature 2").set_track(track.id).save()

        # Query by agent
        agent1_features = sdk1.features.where(agent_assigned="agent1")

        assert len(agent1_features) >= 2
        assert all(f.agent_assigned == "agent1" for f in agent1_features)

    def test_feature_enrichment_with_work_history(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Feature should be enrichable with work history from events."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("History Track").save()
        feature = sdk.features.create("History Feature").set_track(track.id).save()

        session_id = "test-session-006"

        # Add events from multiple agents
        for i, agent in enumerate(["orchestrator", "codex", "gemini"]):
            event = EventRecord(
                event_id=f"evt-hist-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} worked on feature",
                success=True,
                feature_id=feature.id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                tokens_actual=1000 * (i + 1),
                cost_usd=0.01 * (i + 1),
            )
            event_log.append(event)

        # Verify events exist
        events = event_log.query_events(feature_id=feature.id)
        agents_who_worked = {e["agent"] for e in events}

        assert "orchestrator" in agents_who_worked
        assert "codex" in agents_who_worked
        assert "gemini" in agents_who_worked


class TestEventToFeatureLinking:
    """Test linking events to features."""

    def test_event_includes_feature_id(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog
    ):
        """Event should include feature_id for attribution."""
        feature_id = "feat-test-001"
        session_id = "sess-test-001"

        event = EventRecord(
            event_id="evt-link-001",
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            agent="test-agent",
            tool="Edit",
            summary="Test event",
            success=True,
            feature_id=feature_id,
            drift_score=None,
            start_commit=None,
            continued_from=None,
        )
        event_log.append(event)

        # Retrieve and verify
        events = event_log.query_events(feature_id=feature_id)
        assert len(events) == 1
        assert events[0]["feature_id"] == feature_id

    def test_query_events_by_feature(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog
    ):
        """Should query all events for a specific feature."""
        feature_id = "feat-test-002"
        session_id = "sess-test-002"

        # Create events
        for i in range(5):
            event = EventRecord(
                event_id=f"evt-query-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=f"agent-{i}",
                tool="Edit",
                summary=f"Event {i}",
                success=True,
                feature_id=feature_id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
            )
            event_log.append(event)

        # Query by feature
        events = event_log.query_events(feature_id=feature_id)

        assert len(events) == 5
        assert all(e["feature_id"] == feature_id for e in events)

    def test_recent_agent_work_query(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog
    ):
        """Should query recent work by agents on a feature."""
        feature_id = "feat-test-003"
        session_id = "sess-test-003"

        # Create events
        for i in range(3):
            event = EventRecord(
                event_id=f"evt-recent-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=f"agent-{i}",
                tool="Edit",
                summary=f"Recent work {i}",
                success=True,
                feature_id=feature_id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
            )
            event_log.append(event)

        # Query most recent events
        recent_events = event_log.query_events(feature_id=feature_id, limit=1)

        assert len(recent_events) == 1


class TestDashboardPerformance:
    """Test dashboard performance with many features."""

    def test_dashboard_load_with_100_features(self, tmp_htmlgraph: Path, isolated_db):
        """Dashboard should load efficiently with 100+ features."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )

        # Create track first
        track = sdk.tracks.create("Performance Track").save()

        # Create 100 features
        for i in range(100):
            sdk.features.create(f"Feature {i}").set_track(track.id).save()

        # Retrieve all features
        all_features = sdk.features.all()

        assert len(all_features) >= 100

    def test_event_query_performance(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog
    ):
        """Event queries should be efficient with many events."""
        feature_id = "feat-perf-test"
        session_id = "sess-perf-test"

        # Create 1000 events
        for i in range(1000):
            event = EventRecord(
                event_id=f"evt-perf-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=f"agent-{i % 5}",  # 5 different agents
                tool="Edit",
                summary=f"Event {i}",
                success=True,
                feature_id=feature_id if i % 2 == 0 else f"other-feat-{i}",
                drift_score=None,
                start_commit=None,
                continued_from=None,
            )
            event_log.append(event)

        # Query should still be fast
        events = event_log.query_events(feature_id=feature_id, limit=100)

        assert len(events) <= 100
        assert all(e["feature_id"] == feature_id for e in events)


class TestMultiAgentCollaboration:
    """Test indicators of multi-agent collaboration."""

    def test_feature_worked_by_multiple_agents(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Feature should show when multiple agents have worked on it."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("Collaboration Track").save()
        feature = (
            sdk.features.create("Collaboration Feature").set_track(track.id).save()
        )
        feature_id = feature.id

        # Multiple agents work on it
        agents = ["orchestrator", "codex", "gemini"]
        session_id = "test-session-collab"

        for i, agent in enumerate(agents):
            event = EventRecord(
                event_id=f"evt-collab-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} contributed",
                success=True,
                feature_id=feature_id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                tokens_actual=1000,
                cost_usd=0.01,
            )
            event_log.append(event)

        # Verify collaboration
        events = event_log.query_events(feature_id=feature_id)
        unique_agents = {e["agent"] for e in events}

        assert len(unique_agents) == 3
        assert unique_agents == {"orchestrator", "codex", "gemini"}

    def test_collaboration_effort_hours(
        self, tmp_htmlgraph: Path, event_log: JsonlEventLog, isolated_db: Path
    ):
        """Should track total effort hours across agents."""
        sdk = SDK(
            directory=tmp_htmlgraph, agent="orchestrator", db_path=str(isolated_db)
        )
        track = sdk.tracks.create("Effort Track").save()
        feature = (
            sdk.features.create("Effort Tracking Feature").set_track(track.id).save()
        )

        session_id = "test-session-effort"
        # Simulate effort duration
        effort_by_agent = {
            "orchestrator": 1800,  # 30 minutes in seconds
            "codex": 3600,  # 1 hour
            "gemini": 5400,  # 1.5 hours
        }

        for i, (agent, duration) in enumerate(effort_by_agent.items()):
            event = EventRecord(
                event_id=f"evt-effort-{i}",
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                agent=agent,
                tool="Edit",
                summary=f"{agent} worked for {duration} seconds",
                success=True,
                feature_id=feature.id,
                drift_score=None,
                start_commit=None,
                continued_from=None,
                execution_duration_seconds=duration,
                tokens_actual=1000,
                cost_usd=0.01,
            )
            event_log.append(event)

        # Verify effort tracking
        events = event_log.query_events(feature_id=feature.id)
        total_seconds = sum(e.get("execution_duration_seconds") or 0 for e in events)

        # 30min + 1h + 1.5h = 3h = 10800 seconds
        assert total_seconds == pytest.approx(10800, rel=1e-2)
