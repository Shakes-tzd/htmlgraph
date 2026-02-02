"""
Integration Tests for Cross-Session Broadcast Sync

Tests real-time broadcasting of feature/track/spike updates
across multiple active sessions.
"""

import time
from pathlib import Path

import pytest
from htmlgraph.api.broadcast import (
    BroadcastEvent,
    BroadcastEventType,
    CrossSessionBroadcaster,
)
from htmlgraph.api.websocket import WebSocketManager


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create temporary database for testing."""
    return str(tmp_path / "test.db")


@pytest.fixture
def websocket_manager(db_path: str) -> WebSocketManager:
    """Create WebSocketManager instance."""
    return WebSocketManager(db_path)


@pytest.fixture
def broadcaster(
    websocket_manager: WebSocketManager, db_path: str
) -> CrossSessionBroadcaster:
    """Create CrossSessionBroadcaster instance."""
    return CrossSessionBroadcaster(websocket_manager, db_path)


class TestBroadcastEvent:
    """Test BroadcastEvent data class."""

    def test_create_event(self):
        """Test creating broadcast event."""
        event = BroadcastEvent(
            event_type=BroadcastEventType.FEATURE_UPDATED,
            resource_id="feat-123",
            resource_type="feature",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"status": "in_progress"},
        )

        assert event.event_type == BroadcastEventType.FEATURE_UPDATED
        assert event.resource_id == "feat-123"
        assert event.resource_type == "feature"
        assert event.agent_id == "claude-1"
        assert event.session_id == "sess-1"
        assert event.payload["status"] == "in_progress"

    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = BroadcastEvent(
            event_type=BroadcastEventType.FEATURE_CREATED,
            resource_id="feat-456",
            resource_type="feature",
            agent_id="claude-2",
            session_id="sess-2",
            payload={"title": "New Feature"},
        )

        data = event.to_dict()

        assert data["type"] == "broadcast_event"
        assert data["event_type"] == "feature_created"
        assert data["resource_id"] == "feat-456"
        assert data["resource_type"] == "feature"
        assert data["agent_id"] == "claude-2"
        assert data["session_id"] == "sess-2"
        assert data["payload"]["title"] == "New Feature"
        assert "timestamp" in data


class TestCrossSessionBroadcaster:
    """Test CrossSessionBroadcaster functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_feature_update_no_clients(
        self, broadcaster: CrossSessionBroadcaster
    ):
        """Test broadcasting with no connected clients."""
        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"status": "in_progress"},
        )

        # No clients connected, should return 0
        assert clients_notified == 0

    @pytest.mark.asyncio
    async def test_broadcast_feature_created(
        self, broadcaster: CrossSessionBroadcaster
    ):
        """Test broadcasting feature creation."""
        clients_notified = await broadcaster.broadcast_feature_created(
            feature_id="feat-789",
            agent_id="claude-3",
            session_id="sess-3",
            payload={"title": "Test Feature", "status": "todo"},
        )

        assert clients_notified == 0  # No clients connected

    @pytest.mark.asyncio
    async def test_broadcast_status_change(self, broadcaster: CrossSessionBroadcaster):
        """Test broadcasting status change."""
        clients_notified = await broadcaster.broadcast_status_change(
            feature_id="feat-456",
            old_status="todo",
            new_status="in_progress",
            agent_id="claude-2",
            session_id="sess-2",
        )

        assert clients_notified == 0  # No clients connected

    @pytest.mark.asyncio
    async def test_broadcast_link_added(self, broadcaster: CrossSessionBroadcaster):
        """Test broadcasting link addition."""
        clients_notified = await broadcaster.broadcast_link_added(
            feature_id="feat-123",
            linked_feature_id="feat-456",
            link_type="depends_on",
            agent_id="claude-1",
            session_id="sess-1",
        )

        assert clients_notified == 0  # No clients connected

    @pytest.mark.asyncio
    async def test_broadcast_track_update(self, broadcaster: CrossSessionBroadcaster):
        """Test broadcasting track update."""
        clients_notified = await broadcaster.broadcast_track_update(
            track_id="trk-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"title": "Updated Track"},
        )

        assert clients_notified == 0  # No clients connected

    @pytest.mark.asyncio
    async def test_broadcast_spike_update(self, broadcaster: CrossSessionBroadcaster):
        """Test broadcasting spike update."""
        clients_notified = await broadcaster.broadcast_spike_update(
            spike_id="spk-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"title": "Research Spike"},
        )

        assert clients_notified == 0  # No clients connected


class TestBroadcastLatency:
    """Test broadcast latency requirements (<100ms)."""

    @pytest.mark.asyncio
    async def test_broadcast_latency(self, broadcaster: CrossSessionBroadcaster):
        """Verify broadcast completes in <100ms."""
        start = time.time()

        await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"status": "done"},
        )

        elapsed_ms = (time.time() - start) * 1000

        # Should complete in <100ms even with no clients
        assert elapsed_ms < 100, f"Broadcast took {elapsed_ms}ms, expected <100ms"

    @pytest.mark.asyncio
    async def test_multiple_broadcasts_latency(
        self, broadcaster: CrossSessionBroadcaster
    ):
        """Test latency with multiple rapid broadcasts."""
        start = time.time()

        # Send 10 broadcasts rapidly
        for i in range(10):
            await broadcaster.broadcast_feature_update(
                feature_id=f"feat-{i}",
                agent_id="claude-1",
                session_id="sess-1",
                payload={"status": "in_progress"},
            )

        elapsed_ms = (time.time() - start) * 1000

        # All 10 broadcasts should complete in <500ms
        assert elapsed_ms < 500, f"10 broadcasts took {elapsed_ms}ms, expected <500ms"


class TestBroadcastEventTypes:
    """Test all broadcast event types."""

    def test_all_event_types_defined(self):
        """Verify all expected event types are defined."""
        expected_types = [
            "FEATURE_UPDATED",
            "FEATURE_CREATED",
            "FEATURE_DELETED",
            "TRACK_UPDATED",
            "SPIKE_UPDATED",
            "STATUS_CHANGED",
            "LINK_ADDED",
            "COMMENT_ADDED",
        ]

        for event_type in expected_types:
            assert hasattr(BroadcastEventType, event_type)

    def test_event_type_values(self):
        """Verify event type string values."""
        assert BroadcastEventType.FEATURE_UPDATED.value == "feature_updated"
        assert BroadcastEventType.FEATURE_CREATED.value == "feature_created"
        assert BroadcastEventType.STATUS_CHANGED.value == "status_changed"
        assert BroadcastEventType.LINK_ADDED.value == "link_added"


class TestBroadcastPayloads:
    """Test broadcast payload structures."""

    @pytest.mark.asyncio
    async def test_feature_update_payload(self, broadcaster: CrossSessionBroadcaster):
        """Test feature update payload structure."""
        payload = {
            "title": "Updated Title",
            "status": "in_progress",
            "description": "Updated description",
            "tags": ["api", "backend"],
            "priority": "high",
        }

        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload=payload,
        )

        # Verify no errors with complex payload
        assert clients_notified == 0

    @pytest.mark.asyncio
    async def test_status_change_payload(self, broadcaster: CrossSessionBroadcaster):
        """Test status change payload structure."""
        clients_notified = await broadcaster.broadcast_status_change(
            feature_id="feat-123",
            old_status="todo",
            new_status="done",
            agent_id="claude-1",
            session_id="sess-1",
        )

        assert clients_notified == 0

    @pytest.mark.asyncio
    async def test_link_added_payload(self, broadcaster: CrossSessionBroadcaster):
        """Test link addition payload structure."""
        clients_notified = await broadcaster.broadcast_link_added(
            feature_id="feat-123",
            linked_feature_id="feat-456",
            link_type="blocks",
            agent_id="claude-1",
            session_id="sess-1",
        )

        assert clients_notified == 0


class TestBroadcastErrorHandling:
    """Test error handling in broadcast operations."""

    @pytest.mark.asyncio
    async def test_broadcast_with_invalid_data(
        self, broadcaster: CrossSessionBroadcaster
    ):
        """Test broadcasting with various data types."""
        # Should handle empty payload
        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={},
        )
        assert clients_notified == 0

        # Should handle complex nested payload
        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload={"nested": {"data": {"structure": "value"}}},
        )
        assert clients_notified == 0

    @pytest.mark.asyncio
    async def test_broadcast_with_none_values(
        self, broadcaster: CrossSessionBroadcaster
    ):
        """Test broadcasting with None values in payload."""
        payload = {
            "title": None,
            "status": "in_progress",
            "description": None,
        }

        clients_notified = await broadcaster.broadcast_feature_update(
            feature_id="feat-123",
            agent_id="claude-1",
            session_id="sess-1",
            payload=payload,
        )

        assert clients_notified == 0


# Note: Full WebSocket integration tests with actual connected clients
# would require a running FastAPI app and WebSocket connections.
# Those tests should be in end-to-end test suite.
