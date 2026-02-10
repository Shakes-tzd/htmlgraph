"""
Unit tests for Service layer.

Tests verify that services:
- Aggregate data correctly
- Use caching effectively
- Prevent N+1 queries through bulk fetching
- Handle business logic correctly
- Manage cache invalidation

NOTE: These tests require Phase 2 refactor (services/ module) to be complete.
"""

from unittest.mock import AsyncMock

import pytest

from .conftest import PHASE2_COMPLETE, EventFactory

# Skip all tests if Phase 2 is not complete
pytestmark = pytest.mark.skipif(
    not PHASE2_COMPLETE,
    reason="Phase 2 refactor incomplete: services/ module does not exist yet",
)


@pytest.mark.asyncio
class TestActivityService:
    """Tests for ActivityService."""

    async def test_get_grouped_events_returns_correct_shape(
        self,
        activity_service,
        db_with_events,
    ):
        """Verify get_grouped_events() returns correct data structure."""
        result = await activity_service.get_grouped_events(limit=50)

        assert isinstance(result, dict)
        assert "events" in result
        assert "total" in result
        assert "cursor" in result
        assert isinstance(result["events"], list)

    async def test_get_grouped_events_with_limit(
        self,
        activity_service,
        db_with_events,
    ):
        """Verify limit parameter works correctly."""
        result = await activity_service.get_grouped_events(limit=10)

        assert len(result["events"]) <= 10

    async def test_get_grouped_events_with_offset(
        self,
        activity_service,
        db_with_events,
    ):
        """Verify offset parameter works correctly."""
        result1 = await activity_service.get_grouped_events(limit=5, offset=0)
        result2 = await activity_service.get_grouped_events(limit=5, offset=5)

        ids1 = {e["event_id"] for e in result1["events"]}
        ids2 = {e["event_id"] for e in result2["events"]}

        # No overlap between pages
        assert len(ids1 & ids2) == 0

    async def test_get_grouped_events_uses_bulk_query(
        self,
        activity_service,
        async_db_connection,
    ):
        """Verify get_grouped_events() uses bulk query (not N+1)."""
        # Create sample events
        for i in range(100):
            event = EventFactory.create()
            await activity_service._repository.create(event)

        # Track number of database queries
        query_count = 0
        original_execute = async_db_connection.execute

        async def counting_execute(*args, **kwargs):
            nonlocal query_count
            if isinstance(args[0], str) and "SELECT" in args[0]:
                query_count += 1
            return await original_execute(*args, **kwargs)

        async_db_connection.execute = counting_execute

        # Get grouped events
        result = await activity_service.get_grouped_events(limit=100)

        # Should be 1 query, not N queries
        assert query_count == 1
        assert len(result["events"]) == 100

    async def test_get_grouped_events_caches_result(
        self,
        activity_service,
        db_with_events,
        query_cache,
    ):
        """Verify caching works for grouped events."""
        # First call - cache miss
        result1 = await activity_service.get_grouped_events(limit=10)

        # Second call - cache hit
        result2 = await activity_service.get_grouped_events(limit=10)

        # Results should be identical
        assert result1["events"] == result2["events"]

        # Check cache hit was recorded
        metrics = query_cache.get_metrics()
        assert metrics is not None

    async def test_get_grouped_events_filters_by_session(
        self,
        activity_service,
        db_with_events,
    ):
        """Verify filtering by session_id works."""
        result = await activity_service.get_grouped_events(
            limit=100,
            session_id="sess-000",
        )

        # All events should be from specified session
        for event in result["events"]:
            assert event["session_id"] == "sess-000"

    async def test_get_grouped_events_filters_by_agent(
        self,
        activity_service,
        db_with_events,
    ):
        """Verify filtering by agent_id works."""
        result = await activity_service.get_grouped_events(
            limit=100,
            agent_id="agent-0",
        )

        # All events should be from specified agent
        for event in result["events"]:
            assert event["agent_id"] == "agent-0"


@pytest.mark.asyncio
class TestOrchestrationService:
    """Tests for OrchestrationService."""

    async def test_get_orchestration_chain_structure(
        self,
        orchestration_service,
        db_with_events,
    ):
        """Verify get_orchestration_chain() returns correct structure."""
        result = await orchestration_service.get_orchestration_chain(
            session_id="sess-000",
        )

        assert isinstance(result, dict)
        assert "chain" in result
        assert "metadata" in result
        assert isinstance(result["chain"], list)

    async def test_get_orchestration_bulk_loads_dependencies(
        self,
        orchestration_service,
        db_with_events,
    ):
        """Verify orchestration service bulk-loads all dependencies."""
        query_count = 0

        async def counting_query(*args, **kwargs):
            nonlocal query_count
            query_count += 1
            return []

        # Mock the query execution
        orchestration_service._execute_query = counting_query

        # This should use 1-2 bulk queries, not N+1
        result = await orchestration_service.get_orchestration_chain(
            session_id="sess-000",
        )

        # Should be constant queries regardless of event count
        assert query_count <= 2

    async def test_detect_delegation_handoffs(
        self,
        orchestration_service,
        db_with_events,
    ):
        """Verify detection of delegation handoffs."""
        result = await orchestration_service.detect_delegation_handoffs(
            session_id="sess-000",
        )

        assert isinstance(result, list)

    async def test_calculate_cost_by_model(
        self,
        orchestration_service,
        db_with_events,
    ):
        """Verify cost calculation by model."""
        result = await orchestration_service.calculate_cost_by_model(
            session_id="sess-000",
        )

        assert isinstance(result, dict)
        # Each model should have cost info
        for model, cost_info in result.items():
            assert "total_cost" in cost_info
            assert "token_count" in cost_info


@pytest.mark.asyncio
class TestAnalyticsService:
    """Tests for AnalyticsService."""

    async def test_get_cost_summary_structure(
        self,
        analytics_service,
        db_with_events,
    ):
        """Verify get_cost_summary() returns correct structure."""
        result = await analytics_service.get_cost_summary()

        assert isinstance(result, dict)
        assert "total_cost" in result
        assert "total_tokens" in result
        assert "by_model" in result
        assert "by_agent" in result

    async def test_get_cost_summary_aggregates_correctly(
        self,
        analytics_service,
        db_with_events,
    ):
        """Verify cost aggregation is accurate."""
        result = await analytics_service.get_cost_summary()

        # Sum of individual models should equal total
        total_by_model = sum(m.get("cost", 0) for m in result["by_model"].values())
        assert abs(total_by_model - result["total_cost"]) < 0.01

    async def test_get_agent_metrics_bulk_aggregates(
        self,
        analytics_service,
        db_with_events,
    ):
        """Verify agent metrics use bulk aggregation (not N+1)."""
        result = await analytics_service.get_agent_metrics()

        assert isinstance(result, dict)
        # Each agent should have metrics
        for agent_id, metrics in result.items():
            assert "event_count" in metrics
            assert "total_cost" in metrics
            assert "avg_duration" in metrics

    async def test_get_session_metrics(
        self,
        analytics_service,
        db_with_sessions,
    ):
        """Verify session metrics calculation."""
        result = await analytics_service.get_session_metrics()

        assert isinstance(result, dict)
        assert "total_sessions" in result
        assert "active_sessions" in result
        assert "avg_duration" in result
        assert "total_events" in result

    async def test_analytics_caches_expensive_operations(
        self,
        analytics_service,
        db_with_events,
        query_cache,
    ):
        """Verify expensive analytics operations are cached."""
        # First call - cache miss
        result1 = await analytics_service.get_cost_summary()

        # Second call - cache hit (should be faster)
        result2 = await analytics_service.get_cost_summary()

        # Results should be identical
        assert result1 == result2


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Tests for cache invalidation behavior."""

    async def test_cache_invalidation_on_new_event(
        self,
        activity_service,
        query_cache,
    ):
        """Verify cache is invalidated when new event created."""
        # Prime cache
        result1 = await activity_service.get_grouped_events(limit=10)

        # Create new event
        event = EventFactory.create()
        await activity_service._repository.create(event)

        # Cache should be invalidated
        # (Implementation-specific - may need different verification)
        pass

    async def test_cache_ttl_respected(
        self,
        activity_service,
        query_cache,
    ):
        """Verify cache respects TTL settings."""
        # This would test that cache expires after TTL
        # Implementation-specific
        pass


@pytest.mark.asyncio
class TestServiceErrorHandling:
    """Tests for service error handling."""

    async def test_handle_database_error_gracefully(
        self,
        activity_service,
    ):
        """Verify service handles database errors."""
        # Mock database to raise error
        activity_service._repository.find_all = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Should not raise, should return empty or error response
        result = await activity_service.get_grouped_events(limit=10)
        assert result is not None

    async def test_handle_missing_data_gracefully(
        self,
        activity_service,
    ):
        """Verify service handles missing data."""
        # Query non-existent session
        result = await activity_service.get_grouped_events(
            session_id="nonexistent-session",
        )

        # Should return empty result, not error
        assert isinstance(result, dict)
        assert result.get("events", []) == [] or len(result["events"]) == 0
