"""
Pytest fixtures for API unit and integration tests.

Provides:
- Database fixtures with sample data
- Repository fixtures
- Service fixtures
- Cache fixtures
- Request/response fixtures

NOTE: These tests are for Phase 3 (post-refactor validation).
Phase 2 (refactoring to repositories/services) must be complete first.
"""

import asyncio
import sqlite3
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import aiosqlite
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from htmlgraph.api.cache import QueryCache
from htmlgraph.api.main import get_app
from htmlgraph.db.schema import HtmlGraphDB

# Check if Phase 2 refactor is complete
try:
    from htmlgraph.api.repositories import (
        EventsRepository,
        FeaturesRepository,
        SessionsRepository,
    )
    from htmlgraph.api.services import (
        ActivityService,
        AnalyticsService,
        OrchestrationService,
    )
    PHASE2_COMPLETE = True
except ImportError:
    PHASE2_COMPLETE = False
    # Create placeholder classes for fixtures
    EventsRepository = None
    FeaturesRepository = None
    SessionsRepository = None
    ActivityService = None
    AnalyticsService = None
    OrchestrationService = None

# Export PHASE2_COMPLETE for use in test modules
__all__ = ["PHASE2_COMPLETE"]


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create temporary SQLite database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield str(db_path)


@pytest.fixture
def sync_db_connection(temp_db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Create synchronous database connection for setup."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    # Initialize schema
    db = HtmlGraphDB(temp_db_path)
    db.connect()
    db.create_tables()
    db.disconnect()

    yield conn
    conn.close()


@pytest_asyncio.fixture
async def async_db_connection(temp_db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Create asynchronous database connection for testing."""
    if not PHASE2_COMPLETE:
        yield None
        return

    db = await aiosqlite.connect(temp_db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA busy_timeout = 5000")

    yield db

    await db.close()


@pytest_asyncio.fixture
async def events_repository(async_db_connection: aiosqlite.Connection):
    """Create EventsRepository for testing."""
    if not PHASE2_COMPLETE or EventsRepository is None:
        return None
    return EventsRepository(db=async_db_connection)


@pytest_asyncio.fixture
async def features_repository(async_db_connection: aiosqlite.Connection):
    """Create FeaturesRepository for testing."""
    if not PHASE2_COMPLETE or FeaturesRepository is None:
        return None
    return FeaturesRepository(db=async_db_connection)


@pytest_asyncio.fixture
async def sessions_repository(async_db_connection: aiosqlite.Connection):
    """Create SessionsRepository for testing."""
    if not PHASE2_COMPLETE or SessionsRepository is None:
        return None
    return SessionsRepository(db=async_db_connection)


@pytest.fixture
def query_cache() -> QueryCache:
    """Create QueryCache instance for testing."""
    return QueryCache(ttl_seconds=1.0)


@pytest_asyncio.fixture
async def activity_service(
    async_db_connection: aiosqlite.Connection,
    query_cache: QueryCache,
):
    """Create ActivityService for testing."""
    if not PHASE2_COMPLETE or ActivityService is None:
        return None
    return ActivityService(
        db=async_db_connection,
        cache=query_cache,
        logger=MagicMock(),
    )


@pytest_asyncio.fixture
async def orchestration_service(
    async_db_connection: aiosqlite.Connection,
    query_cache: QueryCache,
):
    """Create OrchestrationService for testing."""
    if not PHASE2_COMPLETE or OrchestrationService is None:
        return None
    return OrchestrationService(
        db=async_db_connection,
        cache=query_cache,
        logger=MagicMock(),
    )


@pytest_asyncio.fixture
async def analytics_service(
    async_db_connection: aiosqlite.Connection,
    query_cache: QueryCache,
):
    """Create AnalyticsService for testing."""
    if not PHASE2_COMPLETE or AnalyticsService is None:
        return None
    return AnalyticsService(
        db=async_db_connection,
        cache=query_cache,
        logger=MagicMock(),
    )


@pytest.fixture
def test_client(temp_db_path: str) -> TestClient:
    """Create FastAPI TestClient for integration tests."""
    app = get_app(temp_db_path)
    return TestClient(app)


# Sample data factories

class EventFactory:
    """Factory for creating sample events."""

    counter = 0

    @classmethod
    def create(
        cls,
        session_id: str = "test-session",
        agent_id: str = "test-agent",
        event_type: str = "UserQuery",
        status: str = "completed",
        tool_name: str | None = None,
        cost_tokens: int = 100,
    ) -> dict:
        """Create a sample event."""
        cls.counter += 1
        return {
            "event_id": f"evt-{cls.counter:06d}",
            "session_id": session_id,
            "agent_id": agent_id,
            "event_type": event_type,
            "tool_name": tool_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "cost_tokens": cost_tokens,
            "input_summary": "Test input",
            "output_summary": "Test output",
            "model": "claude-opus-4-5",
            "parent_event_id": None,
        }


class FeatureFactory:
    """Factory for creating sample features."""

    counter = 0

    @classmethod
    def create(
        cls,
        title: str = "Test Feature",
        feature_type: str = "feature",
        status: str = "todo",
        priority: str = "medium",
    ) -> dict:
        """Create a sample feature."""
        cls.counter += 1
        return {
            "id": f"feat-{cls.counter:08x}",
            "type": feature_type,
            "title": title,
            "description": "Test feature description",
            "status": status,
            "priority": priority,
            "assigned_to": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }


class SessionFactory:
    """Factory for creating sample sessions."""

    counter = 0

    @classmethod
    def create(
        cls,
        agent: str = "test-agent",
        status: str = "active",
        event_count: int = 10,
    ) -> dict:
        """Create a sample session."""
        cls.counter += 1
        started_at = datetime.utcnow()
        ended_at = started_at + timedelta(minutes=5) if status == "completed" else None

        return {
            "session_id": f"sess-{cls.counter:08x}",
            "agent": agent,
            "status": status,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat() if ended_at else None,
            "event_count": event_count,
            "duration_seconds": 300.0 if ended_at else None,
        }


@pytest_asyncio.fixture
async def db_with_events(
    async_db_connection: aiosqlite.Connection,
    events_repository,
):
    """Create database with sample events."""
    if not PHASE2_COMPLETE or events_repository is None:
        return async_db_connection

    # Create 100 sample events
    for i in range(100):
        event = EventFactory.create(
            session_id=f"sess-{i % 5:03d}",
            agent_id=f"agent-{i % 3}",
        )
        await events_repository.create(event)

    return async_db_connection


@pytest_asyncio.fixture
async def db_with_features(
    async_db_connection: aiosqlite.Connection,
    features_repository,
):
    """Create database with sample features."""
    if not PHASE2_COMPLETE or features_repository is None:
        return async_db_connection

    statuses = ["todo", "in_progress", "done"]

    for i in range(20):
        feature = FeatureFactory.create(
            title=f"Feature {i}",
            status=statuses[i % 3],
        )
        await features_repository.create(feature)

    return async_db_connection


@pytest_asyncio.fixture
async def db_with_sessions(
    async_db_connection: aiosqlite.Connection,
    sessions_repository,
):
    """Create database with sample sessions."""
    if not PHASE2_COMPLETE or sessions_repository is None:
        return async_db_connection

    statuses = ["active", "completed"]

    for i in range(10):
        session = SessionFactory.create(
            agent=f"agent-{i % 3}",
            status=statuses[i % 2],
        )
        await sessions_repository.create(session)

    return async_db_connection
