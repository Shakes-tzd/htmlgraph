"""
Performance benchmarks for WebSocket real-time event streaming.

Validates:
- <100ms latency for event delivery
- Handling 1000+ events/sec
- 10+ concurrent clients
- Memory efficiency
"""

import time
from unittest.mock import AsyncMock

import pytest
from htmlgraph.api.websocket import (
    EventBatcher,
    EventSubscriptionFilter,
    WebSocketManager,
)


class TestWebSocketLatency:
    """Latency performance benchmarks."""

    @pytest.mark.asyncio
    async def test_batch_send_latency_multiple_runs(self):
        """Measure batch send latency over multiple runs."""
        manager = WebSocketManager(db_path=":memory:")
        mock_ws = AsyncMock()

        from htmlgraph.api.websocket import WebSocketClient

        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )

        latencies = []

        for batch_size in [10, 25, 50, 100]:
            batch = [
                {"event_id": str(i), "cost_tokens": i * 10} for i in range(batch_size)
            ]

            start_time = time.time()
            await manager._send_batch(client, batch)
            elapsed_ms = (time.time() - start_time) * 1000

            latencies.append((batch_size, elapsed_ms))
            assert elapsed_ms < 100, (
                f"Batch size {batch_size}: {elapsed_ms:.2f}ms > 100ms"
            )

        # Log results
        for batch_size, latency_ms in latencies:
            print(f"Batch size {batch_size:3d}: {latency_ms:6.2f}ms")

    def test_event_filtering_performance_1000_events(self):
        """Measure filtering performance with 1000 events."""
        filter = EventSubscriptionFilter(
            event_types=["tool_call", "error"],
            cost_threshold_tokens=50,
        )

        events = [
            {
                "event_type": "tool_call" if i % 2 == 0 else "error",
                "session_id": "session-123",
                "cost_tokens": i * 10,
            }
            for i in range(1000)
        ]

        start_time = time.time()
        matches = [e for e in events if filter.matches_event(e)]
        elapsed_ms = (time.time() - start_time) * 1000

        assert elapsed_ms < 50, f"Filtering took {elapsed_ms:.2f}ms (must be <50ms)"
        print(f"Filtered 1000 events in {elapsed_ms:.2f}ms ({len(matches)} matches)")

    def test_event_batching_performance(self):
        """Measure event batching overhead."""
        batcher = EventBatcher(batch_size=50, batch_window_ms=50.0)

        events = [{"event_id": str(i), "cost_tokens": i} for i in range(1000)]

        start_time = time.time()
        batch_count = 0

        for event in events:
            result = batcher.add_event(event)
            if result is not None:
                batch_count += 1

        elapsed_ms = (time.time() - start_time) * 1000
        print(f"Batched 1000 events into ~{batch_count} batches in {elapsed_ms:.2f}ms")

        assert elapsed_ms < 100, f"Batching took {elapsed_ms:.2f}ms (must be <100ms)"


class TestThroughput:
    """Throughput performance tests."""

    @pytest.mark.asyncio
    async def test_concurrent_client_throughput(self):
        """Test throughput with 10 concurrent clients."""
        manager = WebSocketManager(
            db_path=":memory:",
            max_clients_per_session=15,
        )

        # Connect 10 clients
        mocks = [AsyncMock() for _ in range(10)]
        session_id = "perf-test-session"

        for i, mock_ws in enumerate(mocks):
            await manager.connect(mock_ws, session_id, f"client-{i}")

        # Send 1000 events and measure throughput
        start_time = time.time()
        events_sent = 0

        for i in range(1000):
            event = {
                "event_type": "tool_call",
                "session_id": session_id,
                "cost_tokens": i % 500,
            }
            count = await manager.broadcast_event(session_id, event)
            events_sent += count

        elapsed_seconds = time.time() - start_time
        throughput = events_sent / elapsed_seconds

        print(
            f"Throughput: {throughput:.0f} events/sec ({events_sent} events in {elapsed_seconds:.2f}s)"
        )
        assert throughput > 1000, f"Throughput {throughput:.0f}/sec < 1000/sec"

    @pytest.mark.asyncio
    async def test_high_volume_event_stream(self):
        """Test with high volume event stream."""
        manager = WebSocketManager(
            db_path=":memory:",
            event_batch_size=100,
            event_batch_window_ms=50.0,
        )

        mock_ws = AsyncMock()
        await manager.connect(mock_ws, "session-1", "client-1")

        # Stream 5000 events
        start_time = time.time()

        for i in range(5000):
            await manager.broadcast_event(
                "session-1",
                {
                    "event_type": "tool_call",
                    "session_id": "session-1",
                    "cost_tokens": i,
                },
            )

        elapsed_seconds = time.time() - start_time
        throughput = 5000 / elapsed_seconds

        print(f"High-volume stream: {throughput:.0f} events/sec")
        assert throughput > 5000, f"Throughput {throughput:.0f}/sec < 5000/sec"


class TestMemoryEfficiency:
    """Memory efficiency tests."""

    def test_connection_memory_overhead(self):
        """Measure memory overhead per connection."""
        import sys

        from htmlgraph.api.websocket import WebSocketClient

        mock_ws = AsyncMock()

        # Create multiple clients and measure memory
        clients = []
        for i in range(100):
            client = WebSocketClient(
                websocket=mock_ws,
                client_id=f"client-{i}",
                subscription_filter=EventSubscriptionFilter(),
            )
            clients.append(client)

        # Get approximate size
        client_size = sys.getsizeof(clients[0])
        total_size = client_size * len(clients)

        print(f"Per-client overhead: ~{client_size} bytes")
        print(f"100 clients: ~{total_size / 1024:.1f} KB")

        # Should be reasonable (< 1MB for 100 clients)
        assert total_size < 1024 * 1024, "Excessive memory per client"

    @pytest.mark.asyncio
    async def test_event_batcher_memory(self):
        """Measure event batcher memory overhead."""
        batcher = EventBatcher(batch_size=100)

        # Add 10000 events
        for i in range(10000):
            batcher.add_event({"event_id": str(i), "data": "x" * 100})

        # Flush remaining
        batch = batcher.flush()
        if batch:
            print(f"Final batch size: {len(batch)} events")


class TestLatencyDistribution:
    """Latency distribution and percentiles."""

    @pytest.mark.asyncio
    async def test_latency_percentiles(self):
        """Measure latency percentiles for batch sends."""

        manager = WebSocketManager(db_path=":memory:")
        mock_ws = AsyncMock()

        from htmlgraph.api.websocket import WebSocketClient

        client = WebSocketClient(
            websocket=mock_ws,
            client_id="client-1",
            subscription_filter=EventSubscriptionFilter(),
        )

        latencies_ms = []

        # Take 100 measurements
        for i in range(100):
            batch = [{"event_id": str(j), "cost_tokens": j} for j in range(50)]

            start_time = time.time()
            await manager._send_batch(client, batch)
            elapsed_ms = (time.time() - start_time) * 1000

            latencies_ms.append(elapsed_ms)

        # Calculate percentiles
        latencies_ms.sort()
        p50 = latencies_ms[50]
        p95 = latencies_ms[95]
        p99 = latencies_ms[99]
        max_latency = latencies_ms[99]

        print("Latency distribution (ms):")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        # Verify SLO: P95 < 50ms, P99 < 100ms
        assert p95 < 50, f"P95 latency {p95:.2f}ms exceeds 50ms"
        assert p99 < 100, f"P99 latency {p99:.2f}ms exceeds 100ms"


class TestScalability:
    """Scalability tests."""

    @pytest.mark.asyncio
    async def test_scaling_with_client_count(self):
        """Measure performance scaling with client count."""
        manager = WebSocketManager(db_path=":memory:", max_clients_per_session=50)

        client_counts = [1, 5, 10, 25, 50]
        results = []

        for client_count in client_counts:
            # Connect clients
            mocks = [AsyncMock() for _ in range(client_count)]
            session_id = f"scale-test-{client_count}"

            for i, mock_ws in enumerate(mocks):
                await manager.connect(mock_ws, session_id, f"client-{i}")

            # Send 100 events
            start_time = time.time()
            events_sent = 0

            for i in range(100):
                event = {"event_type": "tool_call", "session_id": session_id}
                count = await manager.broadcast_event(session_id, event)
                events_sent += count

            elapsed_ms = (time.time() - start_time) * 1000
            avg_latency = elapsed_ms / 100

            results.append((client_count, avg_latency))
            print(f"Clients: {client_count:2d}, Avg latency: {avg_latency:.2f}ms")

        # Should scale approximately linearly or better
        latency_1_client = results[0][1]
        latency_50_clients = results[-1][1]

        # Allow up to 10x degradation for 50x more clients
        assert latency_50_clients < latency_1_client * 10

    @pytest.mark.asyncio
    async def test_concurrent_sessions_performance(self):
        """Measure performance with multiple concurrent sessions."""
        manager = WebSocketManager(db_path=":memory:")

        # Create 10 sessions with 5 clients each
        start_time = time.time()

        for session_idx in range(10):
            session_id = f"session-{session_idx}"
            for client_idx in range(5):
                mock_ws = AsyncMock()
                await manager.connect(mock_ws, session_id, f"client-{client_idx}")

        connection_time_ms = (time.time() - start_time) * 1000

        print(f"Connected 50 clients (10 sessions) in {connection_time_ms:.2f}ms")

        # Should complete quickly
        assert connection_time_ms < 1000, (
            f"Connection setup took {connection_time_ms:.2f}ms"
        )

        # Verify all connected
        total_clients = sum(len(clients) for clients in manager.connections.values())
        assert total_clients == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
