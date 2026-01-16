"""
Unit tests for WebSocketManager - Real-time Event Streaming.

Tests cover:
- Connection management
- Event subscription filtering
- Event batching
- Metrics collection
- Error handling
- Performance (<100ms latency)
"""

from unittest.mock import AsyncMock

import pytest
from htmlgraph.api.websocket import (
    EventBatcher,
    EventSubscriptionFilter,
    WebSocketClient,
    WebSocketManager,
)


class TestEventSubscriptionFilter:
    """Tests for event filtering logic."""

    def test_matches_all_events_by_default(self):
        """Default filter matches all events."""
        filter = EventSubscriptionFilter()
        event = {
            "event_type": "tool_call",
            "session_id": "session-123",
            "tool_name": "Edit",
            "cost_tokens": 100,
            "status": "completed",
        }
        assert filter.matches_event(event)

    def test_filters_by_event_type(self):
        """Filter by event type."""
        filter = EventSubscriptionFilter(event_types=["error"])
        assert not filter.matches_event({"event_type": "tool_call"})
        assert filter.matches_event({"event_type": "error"})

    def test_filters_by_session_id(self):
        """Filter by session ID."""
        filter = EventSubscriptionFilter(session_id="session-123")
        assert not filter.matches_event(
            {"session_id": "other-session", "event_type": "tool_call"}
        )
        assert filter.matches_event(
            {"session_id": "session-123", "event_type": "tool_call"}
        )

    def test_filters_by_tool_names(self):
        """Filter by tool names."""
        filter = EventSubscriptionFilter(tool_names=["Edit", "Read"])
        assert not filter.matches_event(
            {"tool_name": "Bash", "event_type": "tool_call"}
        )
        assert filter.matches_event({"tool_name": "Edit", "event_type": "tool_call"})

    def test_filters_by_cost_threshold(self):
        """Filter by cost threshold."""
        filter = EventSubscriptionFilter(cost_threshold_tokens=100)
        assert not filter.matches_event({"cost_tokens": 50, "event_type": "tool_call"})
        assert filter.matches_event({"cost_tokens": 100, "event_type": "tool_call"})
        assert filter.matches_event({"cost_tokens": 200, "event_type": "tool_call"})

    def test_filters_by_status(self):
        """Filter by status."""
        filter = EventSubscriptionFilter(statuses=["error", "timeout"])
        assert not filter.matches_event(
            {"status": "completed", "event_type": "tool_call"}
        )
        assert filter.matches_event({"status": "error", "event_type": "tool_call"})

    def test_filters_by_feature_id(self):
        """Filter by feature IDs."""
        filter = EventSubscriptionFilter(feature_ids=["feat-123", "feat-456"])
        assert not filter.matches_event(
            {"feature_id": "feat-789", "event_type": "tool_call"}
        )
        assert filter.matches_event(
            {"feature_id": "feat-123", "event_type": "tool_call"}
        )


class TestEventBatcher:
    """Tests for event batching."""

    def test_batch_size_trigger(self):
        """Batch is ready when size threshold reached."""
        batcher = EventBatcher(batch_size=2)

        # First event doesn't trigger batch
        result = batcher.add_event({"id": 1})
        assert result is None

        # Second event triggers batch
        result = batcher.add_event({"id": 2})
        assert result is not None
        assert len(result) == 2

    def test_batch_window_trigger(self):
        """Batch is ready when time window expires."""
        batcher = EventBatcher(batch_size=100, batch_window_ms=50.0)

        batcher.add_event({"id": 1})
        # Wait for window to expire
        import time

        time.sleep(0.06)

        result = batcher.add_event({"id": 2})
        # Should flush first batch when adding new event after window
        assert result is not None

    def test_batch_flush(self):
        """Flush remaining events."""
        batcher = EventBatcher()
        batcher.add_event({"id": 1})
        batcher.add_event({"id": 2})

        result = batcher.flush()
        assert result is not None
        assert len(result) == 2

        # Empty flush returns None
        result = batcher.flush()
        assert result is None

    def test_batch_reset(self):
        """Batcher resets after returning batch."""
        batcher = EventBatcher(batch_size=2)
        batcher.add_event({"id": 1})
        batch1 = batcher.add_event({"id": 2})

        # When batch_size=2, adding 2nd event returns batch with both
        assert batch1 == [{"id": 1}, {"id": 2}]
        assert batcher.events == []

        # Add third event should start new batch
        batcher.add_event({"id": 3})
        assert batcher.events == [{"id": 3}]


class TestWebSocketManager:
    """Tests for WebSocket connection management."""

    @pytest.fixture
    def manager(self):
        """Create WebSocket manager instance."""
        return WebSocketManager(db_path=":memory:")

    @pytest.mark.asyncio
    async def test_connect_new_client(self, manager):
        """Connect new WebSocket client."""
        mock_websocket = AsyncMock()
        session_id = "session-123"
        client_id = "client-001"

        result = await manager.connect(mock_websocket, session_id, client_id)

        assert result is True
        assert session_id in manager.connections
        assert client_id in manager.connections[session_id]
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_client(self, manager):
        """Disconnect WebSocket client."""
        mock_websocket = AsyncMock()
        session_id = "session-123"
        client_id = "client-001"

        await manager.connect(mock_websocket, session_id, client_id)
        assert len(manager.connections) == 1

        await manager.disconnect(session_id, client_id)
        assert len(manager.connections) == 0

    @pytest.mark.asyncio
    async def test_max_clients_per_session(self, manager):
        """Enforce max clients per session."""
        manager.max_clients_per_session = 2

        # Connect first two clients
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        assert await manager.connect(mock_ws1, "session-123", "client-1")
        assert await manager.connect(mock_ws2, "session-123", "client-2")

        # Third client should be rejected
        mock_ws3 = AsyncMock()
        result = await manager.connect(mock_ws3, "session-123", "client-3")
        assert result is False
        mock_ws3.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_event(self, manager):
        """Broadcast event to all connected clients."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await manager.connect(mock_ws1, "session-123", "client-1")
        await manager.connect(mock_ws2, "session-123", "client-2")

        event = {
            "event_type": "tool_call",
            "session_id": "session-123",
            "cost_tokens": 100,
        }

        count = await manager.broadcast_event("session-123", event)

        assert count == 2
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    def test_get_session_metrics(self, manager):
        """Get metrics for a session."""
        mock_ws = AsyncMock()

        # Before connecting
        metrics = manager.get_session_metrics("nonexistent-session")
        assert metrics == {}

        # After connecting (mock the connection directly for this test)
        session_id = "session-123"
        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )
        client.events_sent = 10
        client.bytes_sent = 5000

        manager.connections[session_id] = {"client-1": client}
        metrics = manager.get_session_metrics(session_id)

        assert metrics["session_id"] == session_id
        assert metrics["connected_clients"] == 1
        assert metrics["total_events_sent"] == 10
        assert metrics["total_bytes_sent"] == 5000

    def test_get_global_metrics(self, manager):
        """Get global WebSocket metrics."""
        mock_ws = AsyncMock()

        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )

        # Manually add to connections to test metrics
        manager.connections["session-123"] = {"client-1": client}
        # Update metric manually since we're not going through connect()
        manager.metrics["total_connections"] = 1

        metrics = manager.get_global_metrics()

        assert metrics["total_connections"] >= 1
        assert metrics["active_sessions"] == 1
        assert metrics["total_connected_clients"] == 1

    @pytest.mark.asyncio
    async def test_send_batch_updates_metrics(self, manager):
        """Verify send_batch updates metrics."""
        mock_ws = AsyncMock()
        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )

        batch = [
            {"event_id": "1", "cost_tokens": 50},
            {"event_id": "2", "cost_tokens": 75},
        ]

        await manager._send_batch(client, batch)

        assert client.events_sent == 2
        assert client.bytes_sent > 0
        assert manager.metrics["total_events_broadcast"] == 2
        assert manager.metrics["total_bytes_sent"] > 0

    @pytest.mark.asyncio
    async def test_broadcast_with_filter(self, manager):
        """Broadcast only to clients whose filters match."""
        mock_ws1 = AsyncMock()  # All events
        mock_ws2 = AsyncMock()  # Only errors

        filter1 = EventSubscriptionFilter()
        filter2 = EventSubscriptionFilter(event_types=["error"])

        client1 = WebSocketClient(mock_ws1, "c1", filter1)
        client2 = WebSocketClient(mock_ws2, "c2", filter2)

        manager.connections["session-123"] = {"c1": client1, "c2": client2}

        # Broadcast tool_call event
        event = {"event_type": "tool_call", "session_id": "session-123"}
        count = await manager.broadcast_event("session-123", event)

        # Only client1 should receive it
        assert count == 1
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_new_events(self, manager):
        """Fetch new events from mock database."""
        # Create a mock row as a tuple (simulating SQLite Row)
        mock_row = (
            "evt-1",
            "agent-1",
            "tool_call",
            "2024-01-01T12:00:01Z",
            "Edit",
            "input",
            "output",
            "session-123",
            "completed",
            "claude-opus",
            None,
            0.5,
            100,
            None,
        )

        class MockCursor:
            async def fetchall(self):
                return [mock_row]

        class MockDB:
            async def execute(self, *args, **kwargs):
                return MockCursor()

        mock_db = MockDB()

        events = await manager._fetch_new_events(
            mock_db, "session-123", "2024-01-01T12:00:00Z"
        )

        assert len(events) == 1
        assert events[0]["event_id"] == "evt-1"
        assert events[0]["cost_tokens"] == 100


class TestLatencyPerformance:
    """Tests for latency requirements."""

    @pytest.mark.asyncio
    async def test_batch_send_latency(self):
        """Verify batch sending completes in <100ms."""
        import time

        manager = WebSocketManager(db_path=":memory:")
        mock_ws = AsyncMock()

        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )

        # Create batch with 50 events
        batch = [{"event_id": str(i), "cost_tokens": i * 10} for i in range(50)]

        start_time = time.time()
        await manager._send_batch(client, batch)
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 100, f"Batch send took {elapsed_ms:.2f}ms (must be <100ms)"

    def test_event_filtering_performance(self):
        """Verify event filtering is fast."""
        import time

        filter = EventSubscriptionFilter(
            event_types=["tool_call", "error"],
            cost_threshold_tokens=50,
        )

        events = [
            {
                "event_type": "tool_call",
                "session_id": "session-123",
                "cost_tokens": i * 10,
            }
            for i in range(1000)
        ]

        start_time = time.time()
        matches = [e for e in events if filter.matches_event(e)]
        elapsed_ms = (time.time() - start_time) * 1000

        assert len(matches) > 0
        assert elapsed_ms < 50, f"Filtering took {elapsed_ms:.2f}ms (must be <50ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
