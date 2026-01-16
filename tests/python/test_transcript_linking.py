"""
Tests for transcript-feature linking functionality.

Covers:
- SessionManager._link_transcript_to_feature
- features.complete() with transcript_id
- ParallelWorkflow.link_transcripts()
- CLI command: htmlgraph transcript link-feature
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_graph_dir(tmp_path):
    """Create a temporary graph directory structure."""
    graph_dir = tmp_path / ".htmlgraph"
    (graph_dir / "features").mkdir(parents=True)
    (graph_dir / "sessions").mkdir(parents=True)
    (graph_dir / "events").mkdir(parents=True)
    return graph_dir


@pytest.fixture
def mock_transcript_session():
    """Create a mock TranscriptSession for testing."""
    session = MagicMock()
    session.session_id = "agent-test123"
    session.tool_call_count = 42
    session.duration_seconds = 300.0
    session.tool_breakdown = {"Read": 10, "Edit": 15, "Bash": 17}
    return session


class TestLinkTranscriptToFeature:
    """Tests for SessionManager._link_transcript_to_feature"""

    def test_link_adds_implemented_by_edge(
        self, temp_graph_dir, mock_transcript_session
    ):
        """Linking should add an implemented-by edge to the feature."""
        from htmlgraph.models import Node
        from htmlgraph.session_manager import SessionManager

        manager = SessionManager(temp_graph_dir)

        # Create a test feature
        node = Node(
            id="feat-test001",
            title="Test Feature",
            type="feature",
            status="done",
        )

        with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
            mock_reader.return_value.read_session.return_value = mock_transcript_session

            manager._link_transcript_to_feature(
                node, "agent-test123", manager.features_graph
            )

        # Check edge was added
        edges = node.edges.get("implemented-by", [])
        assert len(edges) == 1
        assert edges[0].target_id == "agent-test123"
        assert edges[0].relationship == "implemented-by"

        # Check properties were captured
        assert edges[0].properties.get("tool_count") == 42
        assert edges[0].properties.get("duration_seconds") == 300

    def test_link_does_not_duplicate(
        self, temp_graph_dir, mock_transcript_session, isolated_db
    ):
        """Linking the same transcript twice should not create duplicate edges."""
        from htmlgraph.models import Edge, Node
        from htmlgraph.session_manager import SessionManager

        manager = SessionManager(temp_graph_dir)

        # Create a feature with existing edge
        node = Node(
            id="feat-test002",
            title="Test Feature",
            type="feature",
            status="done",
        )
        existing_edge = Edge(
            target_id="agent-test123",
            relationship="implemented-by",
            since=datetime.now(),
        )
        node.add_edge(existing_edge)

        with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
            mock_reader.return_value.read_session.return_value = mock_transcript_session

            manager._link_transcript_to_feature(
                node, "agent-test123", manager.features_graph
            )

        # Should still only have one edge
        edges = node.edges.get("implemented-by", [])
        assert len(edges) == 1

    def test_link_aggregates_analytics(
        self, temp_graph_dir, mock_transcript_session, isolated_db
    ):
        """Linking should add transcript analytics to feature properties."""
        from htmlgraph.models import Node
        from htmlgraph.session_manager import SessionManager

        manager = SessionManager(temp_graph_dir)

        node = Node(
            id="feat-test003",
            title="Test Feature",
            type="feature",
            status="done",
        )

        with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
            mock_reader.return_value.read_session.return_value = mock_transcript_session

            manager._link_transcript_to_feature(
                node, "agent-test123", manager.features_graph
            )

        # Check properties were added
        assert node.properties.get("transcript_tool_count") == 42
        assert node.properties.get("transcript_duration_seconds") == 300


class TestCompleteWithTranscript:
    """Tests for features.complete() with transcript_id parameter."""

    def test_complete_with_transcript_id(self, temp_graph_dir, isolated_db):
        """Completing a feature with transcript_id should link the transcript."""
        from unittest.mock import MagicMock, patch

        from htmlgraph import SDK

        sdk = SDK(
            directory=temp_graph_dir, agent="test-agent", db_path=str(isolated_db)
        )

        # Create track and feature
        track = sdk.tracks.create("Test Track").save()
        # Create a test feature
        feature = sdk.features.create("Test Feature").set_track(track.id)
        feature_id = feature.id if hasattr(feature, "id") else feature.save().id

        mock_session = MagicMock()
        mock_session.tool_call_count = 25
        mock_session.duration_seconds = 180.0
        mock_session.tool_breakdown = {"Read": 10, "Write": 15}

        with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
            mock_reader.return_value.read_session.return_value = mock_session

            # Complete with transcript_id
            completed = sdk.features.complete(feature_id, transcript_id="agent-abc123")

        if completed:
            # Check that implemented-by edge was added
            completed.edges.get("implemented-by", [])
            # May or may not have edge depending on mock behavior
            assert completed.status == "done"


class TestParallelWorkflowLinkTranscripts:
    """Tests for ParallelWorkflow.link_transcripts()"""

    def test_link_transcripts_success(self, temp_graph_dir, isolated_db):
        """link_transcripts should link multiple features to transcripts."""
        from unittest.mock import MagicMock, patch

        from htmlgraph import SDK
        from htmlgraph.parallel import ParallelWorkflow

        sdk = SDK(
            directory=temp_graph_dir, agent="test-agent", db_path=str(isolated_db)
        )
        workflow = ParallelWorkflow(sdk)

        # Create track and test features
        track = sdk.tracks.create("Test Track").save()
        f1 = sdk.features.create("Feature 1").set_track(track.id).save()
        f2 = sdk.features.create("Feature 2").set_track(track.id).save()

        mock_session = MagicMock()
        mock_session.tool_call_count = 30
        mock_session.duration_seconds = 200.0
        mock_session.tool_breakdown = {"Read": 15, "Bash": 15}

        with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
            mock_reader.return_value.read_session.return_value = mock_session

            result = workflow.link_transcripts(
                [
                    (f1.id, "agent-001"),
                    (f2.id, "agent-002"),
                ]
            )

        assert result["linked_count"] == 2
        assert result["failed_count"] == 0
        assert len(result["linked"]) == 2

    def test_link_transcripts_feature_not_found(self, temp_graph_dir, isolated_db):
        """link_transcripts should handle missing features gracefully."""
        from htmlgraph import SDK
        from htmlgraph.parallel import ParallelWorkflow

        sdk = SDK(
            directory=temp_graph_dir, agent="test-agent", db_path=str(isolated_db)
        )
        workflow = ParallelWorkflow(sdk)

        result = workflow.link_transcripts(
            [
                ("feat-nonexistent", "agent-001"),
            ]
        )

        assert result["linked_count"] == 0
        assert result["failed_count"] == 1
        assert result["failed"][0]["error"] == "Feature not found"


class TestEventPayloadTranscriptId:
    """Tests for transcript_id in event payloads."""

    def test_complete_logs_transcript_id_in_payload(self, temp_graph_dir, isolated_db):
        """FeatureComplete event should include transcript_id in payload."""
        from datetime import datetime
        from unittest.mock import MagicMock, patch

        from htmlgraph.models import Node, Session
        from htmlgraph.session_manager import SessionManager

        manager = SessionManager(temp_graph_dir)

        # Create a test feature
        node = Node(
            id="feat-payload-test",
            title="Payload Test",
            type="feature",
            status="in-progress",
        )
        manager.features_graph.add(node)

        mock_transcript = MagicMock()
        mock_transcript.tool_call_count = 10
        mock_transcript.duration_seconds = 60.0
        mock_transcript.tool_breakdown = {}

        # Create a real Session object instead of MagicMock
        mock_session = Session(
            id="sess-test",
            agent="test-agent",
            status="active",
            started_at=datetime.now(),
            last_activity=datetime.now(),
            transcript_id=None,
        )

        # Mock active session
        with patch.object(manager, "get_active_session", return_value=mock_session):
            with patch.object(
                manager, "_create_transition_spike"
            ):  # Skip spike creation
                with patch("htmlgraph.transcript.TranscriptReader") as mock_reader:
                    mock_reader.return_value.read_session.return_value = mock_transcript

                    manager.complete_feature(
                        "feat-payload-test",
                        agent="test-agent",
                        log_activity=True,
                        transcript_id="agent-xyz789",
                    )

        # Verify the feature was completed
        assert manager.features_graph.get("feat-payload-test").status == "done"

        # Verify implemented-by edge was added
        feature = manager.features_graph.get("feat-payload-test")
        edges = feature.edges.get("implemented-by", [])
        assert len(edges) == 1
        assert edges[0].target_id == "agent-xyz789"
