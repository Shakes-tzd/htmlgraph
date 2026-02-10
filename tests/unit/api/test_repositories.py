"""
Unit tests for Repository layer.

Tests verify that repositories:
- Execute correct SQL queries
- Handle pagination correctly
- Support filtering
- Manage transactions
- Handle errors gracefully

NOTE: These tests require Phase 2 refactor (repositories/ module) to be complete.
"""

import pytest

from .conftest import PHASE2_COMPLETE, EventFactory, FeatureFactory, SessionFactory

# Skip all tests if Phase 2 is not complete
pytestmark = pytest.mark.skipif(
    not PHASE2_COMPLETE,
    reason="Phase 2 refactor incomplete: repositories/ module does not exist yet",
)


@pytest.mark.asyncio
class TestEventsRepository:
    """Tests for EventsRepository."""

    async def test_create_event(self, events_repository, async_db_connection):
        """Verify create() inserts event correctly."""
        event = EventFactory.create()

        result = await events_repository.create(event)

        assert result is not None
        assert result["event_id"] == event["event_id"]
        assert result["agent_id"] == event["agent_id"]

    async def test_find_event_by_id(self, events_repository, db_with_events):
        """Verify find_by_id() retrieves correct event."""
        # Create a known event
        event = EventFactory.create(event_id="evt-test-001")
        await events_repository.create(event)

        result = await events_repository.find_by_id("evt-test-001")

        assert result is not None
        assert result["event_id"] == "evt-test-001"
        assert result["agent_id"] == event["agent_id"]

    async def test_find_all_events_with_pagination(
        self, events_repository, db_with_events
    ):
        """Verify find_all() respects limit and offset."""
        # Get first 10 events
        result = await events_repository.find_all(limit=10, offset=0)
        assert len(result) == 10

        # Get next 10 events
        result2 = await events_repository.find_all(limit=10, offset=10)
        assert len(result2) == 10

        # Verify no overlap
        ids1 = {r["event_id"] for r in result}
        ids2 = {r["event_id"] for r in result2}
        assert len(ids1 & ids2) == 0

    async def test_find_events_by_session(self, events_repository, db_with_events):
        """Verify find_by_session_id() filters correctly."""
        result = await events_repository.find_by_session_id("sess-000")

        # Should have multiple events from same session
        assert len(result) > 0
        for event in result:
            assert event["session_id"] == "sess-000"

    async def test_find_events_by_agent(self, events_repository, db_with_events):
        """Verify find_by_agent_id() filters correctly."""
        result = await events_repository.find_by_agent_id("agent-0")

        assert len(result) > 0
        for event in result:
            assert event["agent_id"] == "agent-0"

    async def test_find_nonexistent_event(self, events_repository):
        """Verify find_by_id() returns None for missing event."""
        result = await events_repository.find_by_id("nonexistent")
        assert result is None

    async def test_delete_event(self, events_repository):
        """Verify delete() removes event."""
        event = EventFactory.create()
        await events_repository.create(event)

        # Verify event exists
        result = await events_repository.find_by_id(event["event_id"])
        assert result is not None

        # Delete it
        await events_repository.delete(event["event_id"])

        # Verify it's gone
        result = await events_repository.find_by_id(event["event_id"])
        assert result is None


@pytest.mark.asyncio
class TestFeaturesRepository:
    """Tests for FeaturesRepository."""

    async def test_create_feature(self, features_repository):
        """Verify create() inserts feature correctly."""
        feature = FeatureFactory.create()

        result = await features_repository.create(feature)

        assert result is not None
        assert result["id"] == feature["id"]
        assert result["title"] == feature["title"]

    async def test_find_feature_by_id(self, features_repository):
        """Verify find_by_id() retrieves correct feature."""
        feature = FeatureFactory.create(title="Unique Feature")
        await features_repository.create(feature)

        result = await features_repository.find_by_id(feature["id"])

        assert result is not None
        assert result["title"] == "Unique Feature"

    async def test_find_all_features(self, features_repository, db_with_features):
        """Verify find_all() returns all features."""
        result = await features_repository.find_all()

        assert len(result) > 0

    async def test_find_features_by_status(self, features_repository, db_with_features):
        """Verify find_by_status() filters correctly."""
        result = await features_repository.find_by_status("todo")

        assert len(result) > 0
        for feature in result:
            assert feature["status"] == "todo"

    async def test_update_feature_status(self, features_repository):
        """Verify update() changes feature status."""
        feature = FeatureFactory.create(status="todo")
        await features_repository.create(feature)

        # Update status
        updated = await features_repository.update(
            feature["id"], {"status": "in_progress"}
        )

        assert updated["status"] == "in_progress"

    async def test_feature_pagination(self, features_repository, db_with_features):
        """Verify pagination works correctly."""
        result1 = await features_repository.find_all(limit=5, offset=0)
        result2 = await features_repository.find_all(limit=5, offset=5)

        assert len(result1) == 5
        assert len(result2) == 5

        # Verify no overlap
        ids1 = {f["id"] for f in result1}
        ids2 = {f["id"] for f in result2}
        assert len(ids1 & ids2) == 0


@pytest.mark.asyncio
class TestSessionsRepository:
    """Tests for SessionsRepository."""

    async def test_create_session(self, sessions_repository):
        """Verify create() inserts session correctly."""
        session = SessionFactory.create()

        result = await sessions_repository.create(session)

        assert result is not None
        assert result["session_id"] == session["session_id"]

    async def test_find_session_by_id(self, sessions_repository):
        """Verify find_by_id() retrieves correct session."""
        session = SessionFactory.create()
        await sessions_repository.create(session)

        result = await sessions_repository.find_by_id(session["session_id"])

        assert result is not None
        assert result["session_id"] == session["session_id"]

    async def test_find_all_sessions(self, sessions_repository, db_with_sessions):
        """Verify find_all() returns all sessions."""
        result = await sessions_repository.find_all()

        assert len(result) > 0

    async def test_find_active_sessions(self, sessions_repository, db_with_sessions):
        """Verify find_by_status() filters correctly."""
        result = await sessions_repository.find_by_status("active")

        assert len(result) > 0
        for session in result:
            assert session["status"] == "active"

    async def test_update_session_status(self, sessions_repository):
        """Verify update() changes session status."""
        session = SessionFactory.create(status="active")
        await sessions_repository.create(session)

        # Mark as completed
        updated = await sessions_repository.update(
            session["session_id"], {"status": "completed"}
        )

        assert updated["status"] == "completed"

    async def test_find_sessions_by_agent(self, sessions_repository, db_with_sessions):
        """Verify find_by_agent() filters correctly."""
        result = await sessions_repository.find_by_agent("agent-0")

        assert len(result) > 0
        for session in result:
            assert session["agent"] == "agent-0"


@pytest.mark.asyncio
class TestRepositoryErrorHandling:
    """Tests for repository error handling."""

    async def test_invalid_event_id_type(self, events_repository):
        """Verify graceful handling of invalid ID types."""
        # Should not raise, just return None
        result = await events_repository.find_by_id(None)
        assert result is None

    async def test_database_connection_error(self, events_repository):
        """Verify handling of connection errors."""
        # This would test actual connection failures
        # Typically done with mocked database
        pass

    async def test_transaction_rollback(self, events_repository):
        """Verify transaction rollback on error."""
        # Create event
        event = EventFactory.create()
        await events_repository.create(event)

        # Try to create duplicate (should fail)
        with pytest.raises(Exception):  # Database error
            await events_repository.create(event)

        # Original event should still exist (no partial state)
        result = await events_repository.find_by_id(event["event_id"])
        assert result is not None
