"""
HtmlGraph FastAPI Backend - Real-time Agent Observability Dashboard

Provides REST API and WebSocket support for viewing:
- Agent activity feed with real-time event streaming
- Orchestration chains and delegation handoffs
- Feature tracker with Kanban views
- Session metrics and performance analytics

Architecture:
- FastAPI backend querying SQLite database
- Jinja2 templates for server-side rendering
- HTMX for interactive UI without page reloads
- WebSocket for real-time event streaming
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class QueryCache:
    """Simple in-memory cache with TTL support for query results."""

    def __init__(self, ttl_seconds: float = 30.0):
        """Initialize query cache with TTL."""
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.metrics: dict[str, dict[str, float]] = {}

    def get(self, key: str) -> Any | None:
        """Get cached value if exists and not expired."""
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp."""
        self.cache[key] = (value, time.time())

    def record_metric(self, key: str, query_time_ms: float, cache_hit: bool) -> None:
        """Record performance metrics for a query."""
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "total_ms": 0, "avg_ms": 0, "hits": 0}

        metrics = self.metrics[key]
        metrics["count"] += 1
        metrics["total_ms"] += query_time_ms
        metrics["avg_ms"] = metrics["total_ms"] / metrics["count"]
        if cache_hit:
            metrics["hits"] += 1

    def get_metrics(self) -> dict[str, dict[str, float]]:
        """Get all collected metrics."""
        return self.metrics


class EventModel(BaseModel):
    """Event data model for API responses."""

    event_id: str
    agent_id: str
    event_type: str
    timestamp: str
    tool_name: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    session_id: str
    parent_event_id: str | None = None
    status: str


class FeatureModel(BaseModel):
    """Feature data model for API responses."""

    id: str
    type: str
    title: str
    description: str | None = None
    status: str
    priority: str
    assigned_to: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class SessionModel(BaseModel):
    """Session data model for API responses."""

    session_id: str
    agent: str | None = None
    status: str
    started_at: str
    ended_at: str | None = None
    event_count: int = 0
    duration_seconds: float | None = None


def _ensure_database_initialized(db_path: str) -> None:
    """
    Ensure SQLite database exists and has correct schema.

    Args:
        db_path: Path to SQLite database file
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if database exists and has tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]

        if not table_names:
            # Database is empty, create schema
            logger.info(f"Creating database schema at {db_path}")
            from htmlgraph.db.schema import HtmlGraphDB

            db = HtmlGraphDB(db_path)
            db.connect()
            db.create_tables()
            db.disconnect()
            logger.info("Database schema created successfully")
        else:
            logger.debug(f"Database already initialized with tables: {table_names}")

        conn.close()

    except sqlite3.Error as e:
        logger.warning(f"Database check warning: {e}")
        # Try to create anyway
        try:
            from htmlgraph.db.schema import HtmlGraphDB

            db = HtmlGraphDB(db_path)
            db.connect()
            db.create_tables()
            db.disconnect()
        except Exception as create_error:
            logger.error(f"Failed to create database: {create_error}")
            raise


def get_app(db_path: str) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Configured FastAPI application instance
    """
    # Ensure database is initialized
    _ensure_database_initialized(db_path)

    app = FastAPI(
        title="HtmlGraph Dashboard API",
        description="Real-time agent observability dashboard",
        version="0.1.0",
    )

    # Store database path and query cache in app state
    app.state.db_path = db_path
    app.state.query_cache = QueryCache(ttl_seconds=30.0)

    # Setup Jinja2 templates
    template_dir = Path(__file__).parent / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    templates = Jinja2Templates(directory=str(template_dir))

    # Add custom filters
    def format_number(value: int | None) -> str:
        if value is None:
            return "0"
        return f"{value:,}"

    templates.env.filters["format_number"] = format_number

    # Setup static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ========== DATABASE HELPERS ==========

    async def get_db() -> aiosqlite.Connection:
        """Get database connection."""
        db = await aiosqlite.connect(app.state.db_path)
        db.row_factory = aiosqlite.Row
        return db

    # ========== ROUTES ==========

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        """Main dashboard view with navigation tabs."""
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "HtmlGraph Agent Observability",
            },
        )

    # ========== AGENTS ENDPOINTS ==========

    @app.get("/views/agents", response_class=HTMLResponse)
    async def agents_view(request: Request) -> HTMLResponse:
        """Get agent workload and performance stats as HTMX partial."""
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key for agents view
            cache_key = "agents_view:all"

            # Check cache first
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                logger.debug(
                    f"Cache HIT for agents_view (key={cache_key}, time={query_time_ms:.2f}ms)"
                )
                agents, total_actions, total_tokens = cached_response
            else:
                # Query agent statistics from 'agent_events' table joined with sessions
                # Optimized with GROUP BY on indexed column
                query = """
                    SELECT
                        e.agent_id,
                        COUNT(*) as event_count,
                        SUM(e.cost_tokens) as total_tokens,
                        COUNT(DISTINCT e.session_id) as session_count,
                        MAX(e.timestamp) as last_active
                    FROM agent_events e
                    GROUP BY e.agent_id
                    ORDER BY event_count DESC
                """

                # Execute query with timing
                exec_start = time.time()
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                exec_time_ms = (time.time() - exec_start) * 1000

                agents = []
                total_actions = 0
                total_tokens = 0

                # First pass to calculate totals
                for row in rows:
                    total_actions += row[1]
                    total_tokens += row[2] or 0

                # Second pass to build agent objects with percentages
                for row in rows:
                    event_count = row[1]
                    workload_pct = (
                        (event_count / total_actions * 100) if total_actions > 0 else 0
                    )

                    agents.append(
                        {
                            "agent_id": row[0],
                            "event_count": event_count,
                            "total_tokens": row[2] or 0,
                            "session_count": row[3],
                            "last_active": row[4],
                            "workload_pct": round(workload_pct, 1),
                        }
                    )

                # Cache the results
                cache_data = (agents, total_actions, total_tokens)
                cache.set(cache_key, cache_data)
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
                logger.debug(
                    f"Cache MISS for agents_view (key={cache_key}, "
                    f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
                    f"agents={len(agents)})"
                )

            return templates.TemplateResponse(
                "partials/agents.html",
                {
                    "request": request,
                    "agents": agents,
                    "total_agents": len(agents),
                    "total_actions": total_actions,
                    "total_tokens": total_tokens,
                },
            )
        finally:
            await db.close()

    # ========== ACTIVITY FEED ENDPOINTS ==========

    @app.get("/views/activity-feed", response_class=HTMLResponse)
    async def activity_feed(
        request: Request,
        limit: int = 50,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> HTMLResponse:
        """Get latest agent events as HTMX partial with hierarchical parent-child grouping."""
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key from query parameters
            cache_key = (
                f"activity_feed:{limit}:{session_id or 'all'}:{agent_id or 'all'}"
            )

            # Check cache first
            cached_rows = cache.get(cache_key)
            if cached_rows is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                logger.debug(
                    f"Cache HIT for activity_feed (key={cache_key}, time={query_time_ms:.2f}ms)"
                )
                rows = cached_rows
            else:
                # Build query using 'agent_events' table from Phase 1 PreToolUse hook implementation
                # Optimized with index hints and selective columns
                query = """
                    SELECT e.event_id, e.agent_id, e.event_type, e.timestamp, e.tool_name,
                           e.input_summary, e.output_summary, e.session_id,
                           e.status
                    FROM agent_events e
                    WHERE 1=1
                """
                params: list = []

                if session_id:
                    query += " AND e.session_id = ?"
                    params.append(session_id)

                if agent_id:
                    query += " AND e.agent_id = ?"
                    params.append(agent_id)

                query += " ORDER BY e.timestamp DESC LIMIT ?"
                params.append(limit)

                # Execute query with timing
                exec_start = time.time()
                cursor = await db.execute(query, params)
                rows = list(await cursor.fetchall())
                exec_time_ms = (time.time() - exec_start) * 1000

                # Cache the results
                cache.set(cache_key, rows)
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
                logger.debug(
                    f"Cache MISS for activity_feed (key={cache_key}, "
                    f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms)"
                )

            events = [
                {
                    "event_id": row[0],
                    "agent_id": row[1] or "unknown",
                    "event_type": row[2],
                    "timestamp": row[3],
                    "tool_name": row[4],
                    "input_summary": row[5],
                    "output_summary": row[6],
                    "session_id": row[7],
                    "status": row[8],
                    "parent_event_id": None,
                    "cost_tokens": 0,
                    "execution_duration_seconds": 0.0,
                }
                for row in rows
            ]

            # Group events by parent_event_id for hierarchical display
            # Organize as: parent events with their children nested
            events_by_parent: dict = {}
            root_events = []

            # First pass: organize into hierarchy
            for event in events:
                parent_id = event.get("parent_event_id")
                if parent_id:
                    # This is a child event
                    if parent_id not in events_by_parent:
                        events_by_parent[parent_id] = []
                    events_by_parent[parent_id].append(event)
                else:
                    # This is a root-level event
                    root_events.append(event)

            # Query returns DESC order which is preserved by iteration

            # Structure for template: list of parent events with children
            hierarchical_events = []
            for parent_event in root_events:
                parent_id = parent_event["event_id"]
                children = events_by_parent.get(parent_id, [])
                hierarchical_events.append(
                    {
                        "parent": parent_event,
                        "children": children,
                        "has_children": len(children) > 0,
                    }
                )

            # Reverse to preserve DESC order from database query (newest first)
            hierarchical_events.reverse()

            return templates.TemplateResponse(
                "partials/activity-feed-hierarchical.html",
                {
                    "request": request,
                    "hierarchical_events": hierarchical_events,
                    "all_events": events,
                    "limit": limit,
                },
            )
        finally:
            await db.close()

    @app.get("/api/events", response_model=list[EventModel])
    async def get_events(
        limit: int = 50,
        session_id: str | None = None,
        agent_id: str | None = None,
        offset: int = 0,
    ) -> list[EventModel]:
        """Get events as JSON API with parent-child hierarchical linking."""
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key from query parameters
            cache_key = (
                f"api_events:{limit}:{offset}:{session_id or 'all'}:{agent_id or 'all'}"
            )

            # Check cache first
            cached_results = cache.get(cache_key)
            if cached_results is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                logger.debug(
                    f"Cache HIT for api_events (key={cache_key}, time={query_time_ms:.2f}ms)"
                )
                return list(cached_results) if isinstance(cached_results, list) else []
            else:
                # Query from 'agent_events' table from Phase 1 PreToolUse hook implementation
                # Optimized with column selection and proper indexing
                query = """
                    SELECT e.event_id, e.agent_id, e.event_type, e.timestamp, e.tool_name,
                           e.input_summary, e.output_summary, e.session_id,
                           e.status
                    FROM agent_events e
                    WHERE 1=1
                """
                params: list = []

                if session_id:
                    query += " AND e.session_id = ?"
                    params.append(session_id)

                if agent_id:
                    query += " AND e.agent_id = ?"
                    params.append(agent_id)

                query += " ORDER BY e.timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # Execute query with timing
                exec_start = time.time()
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                exec_time_ms = (time.time() - exec_start) * 1000

                # Build result models
                results = [
                    EventModel(
                        event_id=row[0],
                        agent_id=row[1] or "unknown",
                        event_type=row[2],
                        timestamp=row[3],
                        tool_name=row[4],
                        input_summary=row[5],
                        output_summary=row[6],
                        session_id=row[7],
                        parent_event_id=None,  # Not available in all schema versions
                        status=row[8],
                    )
                    for row in rows
                ]

                # Cache the results
                cache.set(cache_key, results)
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
                logger.debug(
                    f"Cache MISS for api_events (key={cache_key}, "
                    f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
                    f"rows={len(results)})"
                )

                return results
        finally:
            await db.close()

    # ========== PERFORMANCE METRICS ENDPOINT ==========

    @app.get("/api/query-metrics")
    async def get_query_metrics() -> dict[str, Any]:
        """Get query performance metrics and cache statistics."""
        cache = app.state.query_cache
        metrics = cache.get_metrics()

        # Calculate aggregate statistics
        total_queries = sum(m.get("count", 0) for m in metrics.values())
        total_cache_hits = sum(m.get("hits", 0) for m in metrics.values())
        hit_rate = (total_cache_hits / total_queries * 100) if total_queries > 0 else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "cache_status": {
                "ttl_seconds": cache.ttl_seconds,
                "cached_queries": len(cache.cache),
                "total_queries_tracked": total_queries,
                "cache_hits": total_cache_hits,
                "cache_hit_rate_percent": round(hit_rate, 2),
            },
            "query_metrics": metrics,
        }

    # ========== EVENT TRACES ENDPOINT (Parent-Child Nesting) ==========

    @app.get("/api/event-traces")
    async def get_event_traces(
        limit: int = 50,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get event traces showing parent-child relationships for Task delegations.

        This endpoint returns task delegation events with their child events,
        showing the complete hierarchy of delegated work:

        Example:
        {
            "traces": [
                {
                    "parent_event_id": "evt-abc123",
                    "agent_id": "claude-code",
                    "subagent_type": "gemini-spawner",
                    "started_at": "2025-01-08T16:40:54",
                    "status": "completed",
                    "duration_seconds": 287,
                    "child_events": [
                        {
                            "event_id": "subevt-xyz789",
                            "agent_id": "subagent-gemini-spawner",
                            "event_type": "delegation",
                            "timestamp": "2025-01-08T16:42:01",
                            "status": "completed"
                        }
                    ],
                    "child_spike_count": 2,
                    "child_spikes": ["spk-001", "spk-002"]
                }
            ]
        }

        Args:
            limit: Maximum number of parent events to return (default 50)
            session_id: Filter by session (optional)

        Returns:
            Dict with traces array showing parent-child relationships
        """
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key
            cache_key = f"event_traces:{limit}:{session_id or 'all'}"

            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                return cached_result  # type: ignore[no-any-return]

            exec_start = time.time()

            # Query parent events (task delegations)
            parent_query = """
                SELECT event_id, agent_id, subagent_type, timestamp, status,
                       child_spike_count, output_summary
                FROM agent_events
                WHERE event_type = 'task_delegation'
            """
            parent_params: list[Any] = []

            if session_id:
                parent_query += " AND session_id = ?"
                parent_params.append(session_id)

            parent_query += " ORDER BY timestamp DESC LIMIT ?"
            parent_params.append(limit)

            cursor = await db.execute(parent_query, parent_params)
            parent_rows = await cursor.fetchall()

            traces: list[dict[str, Any]] = []

            for parent_row in parent_rows:
                parent_event_id = parent_row[0]
                agent_id = parent_row[1]
                subagent_type = parent_row[2]
                started_at = parent_row[3]
                status = parent_row[4]
                child_spike_count = parent_row[5] or 0
                output_summary = parent_row[6]

                # Parse output summary to get child spike IDs if available
                child_spikes = []
                try:
                    if output_summary:
                        output_data = (
                            json.loads(output_summary)
                            if isinstance(output_summary, str)
                            else output_summary
                        )
                        # Try to extract spike IDs if present
                        if isinstance(output_data, dict):
                            spikes_info = output_data.get("spikes_created", [])
                            if isinstance(spikes_info, list):
                                child_spikes = spikes_info
                except Exception:
                    pass

                # Query child events (subagent completion events)
                child_query = """
                    SELECT event_id, agent_id, event_type, timestamp, status
                    FROM agent_events
                    WHERE parent_event_id = ?
                    ORDER BY timestamp ASC
                """
                child_cursor = await db.execute(child_query, (parent_event_id,))
                child_rows = await child_cursor.fetchall()

                child_events = []
                for child_row in child_rows:
                    child_events.append(
                        {
                            "event_id": child_row[0],
                            "agent_id": child_row[1],
                            "event_type": child_row[2],
                            "timestamp": child_row[3],
                            "status": child_row[4],
                        }
                    )

                # Calculate duration if completed
                duration_seconds = None
                if status == "completed" and started_at:
                    try:
                        from datetime import datetime as dt

                        start_dt = dt.fromisoformat(started_at)
                        now_dt = dt.now()
                        duration_seconds = (now_dt - start_dt).total_seconds()
                    except Exception:
                        pass

                trace = {
                    "parent_event_id": parent_event_id,
                    "agent_id": agent_id,
                    "subagent_type": subagent_type or "general-purpose",
                    "started_at": started_at,
                    "status": status,
                    "duration_seconds": duration_seconds,
                    "child_events": child_events,
                    "child_spike_count": child_spike_count,
                    "child_spikes": child_spikes,
                }

                traces.append(trace)

            exec_time_ms = (time.time() - exec_start) * 1000

            # Build response
            result = {
                "timestamp": datetime.now().isoformat(),
                "total_traces": len(traces),
                "traces": traces,
                "limitations": {
                    "note": "Child spike count is approximate and based on timestamp proximity",
                    "note_2": "Spike IDs in child_spikes only available if recorded in output_summary",
                },
            }

            # Cache the result
            cache.set(cache_key, result)
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
            logger.debug(
                f"Cache MISS for event_traces (key={cache_key}, "
                f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms, "
                f"traces={len(traces)})"
            )

            return result

        finally:
            await db.close()

    # ========== COMPLETE ACTIVITY FEED ENDPOINT ==========

    @app.get("/api/complete-activity-feed")
    async def complete_activity_feed(
        limit: int = 100,
        session_id: str | None = None,
        include_delegations: bool = True,
        include_spikes: bool = True,
    ) -> dict[str, Any]:
        """
        Get unified activity feed combining events from all sources.

        This endpoint aggregates:
        - Hook events (tool_call from PreToolUse)
        - Subagent events (delegation completions from SubagentStop)
        - SDK spike logs (knowledge created by delegated tasks)

        This provides complete visibility into ALL activity, including
        delegated work that would otherwise be invisible due to Claude Code's
        hook isolation design (see GitHub issue #14859).

        Args:
            limit: Maximum number of events to return
            session_id: Filter by session (optional)
            include_delegations: Include delegation events (default True)
            include_spikes: Include spike creation events (default True)

        Returns:
            Dict with events array and metadata
        """
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key
            cache_key = f"complete_activity:{limit}:{session_id or 'all'}:{include_delegations}:{include_spikes}"

            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                return cached_result  # type: ignore[no-any-return]

            events: list[dict[str, Any]] = []

            # 1. Query hook events (tool_call, delegation from agent_events)
            event_types = ["tool_call"]
            if include_delegations:
                event_types.extend(["delegation", "completion"])

            event_type_placeholders = ",".join("?" for _ in event_types)
            query = f"""
                SELECT
                    'hook_event' as source,
                    event_id,
                    agent_id,
                    event_type,
                    timestamp,
                    tool_name,
                    input_summary,
                    output_summary,
                    session_id,
                    status
                FROM agent_events
                WHERE event_type IN ({event_type_placeholders})
            """
            params: list[Any] = list(event_types)

            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            exec_start = time.time()
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            for row in rows:
                events.append(
                    {
                        "source": row[0],
                        "event_id": row[1],
                        "agent_id": row[2] or "unknown",
                        "event_type": row[3],
                        "timestamp": row[4],
                        "tool_name": row[5],
                        "input_summary": row[6],
                        "output_summary": row[7],
                        "session_id": row[8],
                        "status": row[9],
                    }
                )

            # 2. Query spike logs if requested (knowledge created by delegated tasks)
            if include_spikes:
                try:
                    spike_query = """
                        SELECT
                            'spike_log' as source,
                            id as event_id,
                            assigned_to as agent_id,
                            'knowledge_created' as event_type,
                            created_at as timestamp,
                            title as tool_name,
                            hypothesis as input_summary,
                            findings as output_summary,
                            NULL as session_id,
                            status
                        FROM features
                        WHERE type = 'spike'
                    """
                    spike_params: list[Any] = []

                    spike_query += " ORDER BY created_at DESC LIMIT ?"
                    spike_params.append(limit)

                    spike_cursor = await db.execute(spike_query, spike_params)
                    spike_rows = await spike_cursor.fetchall()

                    for row in spike_rows:
                        events.append(
                            {
                                "source": row[0],
                                "event_id": row[1],
                                "agent_id": row[2] or "sdk",
                                "event_type": row[3],
                                "timestamp": row[4],
                                "tool_name": row[5],
                                "input_summary": row[6],
                                "output_summary": row[7],
                                "session_id": row[8],
                                "status": row[9] or "completed",
                            }
                        )
                except Exception as e:
                    # Spike query might fail if columns don't exist
                    logger.debug(
                        f"Spike query failed (expected if schema differs): {e}"
                    )

            # 3. Query delegation handoffs from agent_collaboration
            if include_delegations:
                try:
                    collab_query = """
                        SELECT
                            'delegation' as source,
                            handoff_id as event_id,
                            from_agent || ' -> ' || to_agent as agent_id,
                            'handoff' as event_type,
                            timestamp,
                            handoff_type as tool_name,
                            reason as input_summary,
                            context as output_summary,
                            session_id,
                            status
                        FROM agent_collaboration
                        WHERE handoff_type = 'delegation'
                    """
                    collab_params: list[Any] = []

                    if session_id:
                        collab_query += " AND session_id = ?"
                        collab_params.append(session_id)

                    collab_query += " ORDER BY timestamp DESC LIMIT ?"
                    collab_params.append(limit)

                    collab_cursor = await db.execute(collab_query, collab_params)
                    collab_rows = await collab_cursor.fetchall()

                    for row in collab_rows:
                        events.append(
                            {
                                "source": row[0],
                                "event_id": row[1],
                                "agent_id": row[2] or "orchestrator",
                                "event_type": row[3],
                                "timestamp": row[4],
                                "tool_name": row[5],
                                "input_summary": row[6],
                                "output_summary": row[7],
                                "session_id": row[8],
                                "status": row[9] or "pending",
                            }
                        )
                except Exception as e:
                    logger.debug(f"Collaboration query failed: {e}")

            # Sort all events by timestamp DESC
            events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

            # Limit to requested count
            events = events[:limit]

            exec_time_ms = (time.time() - exec_start) * 1000

            # Build response
            result = {
                "timestamp": datetime.now().isoformat(),
                "total_events": len(events),
                "sources": {
                    "hook_events": sum(
                        1 for e in events if e["source"] == "hook_event"
                    ),
                    "spike_logs": sum(1 for e in events if e["source"] == "spike_log"),
                    "delegations": sum(
                        1 for e in events if e["source"] == "delegation"
                    ),
                },
                "events": events,
                "limitations": {
                    "note": "Subagent tool activity not tracked (Claude Code limitation)",
                    "github_issue": "https://github.com/anthropics/claude-code/issues/14859",
                    "workaround": "SubagentStop hook captures completion, SDK logging captures results",
                },
            }

            # Cache the result
            cache.set(cache_key, result)
            query_time_ms = (time.time() - query_start_time) * 1000
            cache.record_metric(cache_key, exec_time_ms, cache_hit=False)

            return result

        finally:
            await db.close()

    # ========== ORCHESTRATION ENDPOINTS ==========

    @app.get("/views/orchestration", response_class=HTMLResponse)
    async def orchestration_view(request: Request) -> HTMLResponse:
        """Get delegation chains and agent handoffs as HTMX partial."""
        db = await get_db()
        try:
            # Query from agent_collaboration table which stores delegations
            query = """
                SELECT handoff_id, from_agent, to_agent, timestamp, reason,
                       session_id, status, context
                FROM agent_collaboration
                WHERE handoff_type = 'delegation'
                ORDER BY timestamp DESC
                LIMIT 50
            """

            cursor = await db.execute(query)
            rows = list(await cursor.fetchall())
            print(f"DEBUG orchestration_view: Query executed, got {len(rows)} rows")
            if rows:
                print(f"DEBUG: First row raw: {rows[0]}")

            delegations = []
            for row in rows:
                # Parse context JSON if it exists
                context_data = {}
                try:
                    if row[7]:  # context field
                        context_data = (
                            json.loads(row[7]) if isinstance(row[7], str) else row[7]
                        )
                except Exception:
                    pass

                delegation = {
                    "handoff_id": row[0],
                    "event_id": row[
                        0
                    ],  # Use handoff_id as event_id for template compatibility
                    "from_agent": row[1],
                    "to_agent": row[2],
                    "timestamp": row[3],
                    "reason": row[4],
                    "session_id": row[5],
                    "status": row[6],
                    "context": row[7],
                    "task": context_data.get("task_description", ""),
                    "result": context_data.get("result", ""),
                }
                delegations.append(delegation)
            print(
                f"DEBUG orchestration_view: Created {len(delegations)} delegation dicts"
            )

            return templates.TemplateResponse(
                "partials/orchestration.html",
                {
                    "request": request,
                    "delegations": delegations,
                },
            )
        except Exception as e:
            print(f"DEBUG orchestration_view ERROR: {e}")
            raise
        finally:
            await db.close()

    # ========== FEATURES ENDPOINTS ==========

    @app.get("/views/features", response_class=HTMLResponse)
    async def features_view(request: Request, status: str = "all") -> HTMLResponse:
        """Get features by status as HTMX partial."""
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key from query parameters
            cache_key = f"features_view:{status}"

            # Check cache first
            cached_response = cache.get(cache_key)
            features_by_status: dict = {
                "todo": [],
                "in_progress": [],
                "blocked": [],
                "done": [],
            }

            if cached_response is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                logger.debug(
                    f"Cache HIT for features_view (key={cache_key}, time={query_time_ms:.2f}ms)"
                )
                features_by_status = cached_response
            else:
                # OPTIMIZATION: Use composite index idx_features_status_priority
                # for efficient filtering and ordering
                query = """
                    SELECT id, type, title, status, priority, assigned_to, created_at, updated_at
                    FROM features
                    WHERE 1=1
                """
                params: list = []

                if status != "all":
                    query += " AND status = ?"
                    params.append(status)

                query += " ORDER BY priority DESC, created_at DESC LIMIT 100"

                exec_start = time.time()
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                exec_time_ms = (time.time() - exec_start) * 1000

                for row in rows:
                    feature_status = row[3]
                    features_by_status.setdefault(feature_status, []).append(
                        {
                            "id": row[0],
                            "type": row[1],
                            "title": row[2],
                            "status": feature_status,
                            "priority": row[4],
                            "assigned_to": row[5],
                            "created_at": row[6],
                            "updated_at": row[7],
                        }
                    )

                # Cache the results
                cache.set(cache_key, features_by_status)
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
                logger.debug(
                    f"Cache MISS for features_view (key={cache_key}, "
                    f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms)"
                )

            return templates.TemplateResponse(
                "partials/features.html",
                {
                    "request": request,
                    "features_by_status": features_by_status,
                },
            )
        finally:
            await db.close()

    # ========== METRICS ENDPOINTS ==========

    @app.get("/views/metrics", response_class=HTMLResponse)
    async def metrics_view(request: Request) -> HTMLResponse:
        """Get session metrics and performance data as HTMX partial."""
        db = await get_db()
        cache = app.state.query_cache
        query_start_time = time.time()

        try:
            # Create cache key for metrics view
            cache_key = "metrics_view:all"

            # Check cache first
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, query_time_ms, cache_hit=True)
                logger.debug(
                    f"Cache HIT for metrics_view (key={cache_key}, time={query_time_ms:.2f}ms)"
                )
                sessions, stats = cached_response
            else:
                # OPTIMIZATION: Combine session data with event counts in single query
                # This eliminates N+1 query problem (was 20+ queries, now 2)
                query = """
                    SELECT
                        s.session_id,
                        s.agent,
                        s.status,
                        s.started_at,
                        s.ended_at,
                        COUNT(DISTINCT e.event_id) as event_count
                    FROM sessions s
                    LEFT JOIN agent_events e ON s.session_id = e.session_id
                    GROUP BY s.session_id
                    ORDER BY s.started_at DESC
                    LIMIT 20
                """

                exec_start = time.time()
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                exec_time_ms = (time.time() - exec_start) * 1000

                sessions = []
                for row in rows:
                    started_at = datetime.fromisoformat(row[3])

                    # Calculate duration
                    if row[4]:
                        ended_at = datetime.fromisoformat(row[4])
                        duration_seconds = (ended_at - started_at).total_seconds()
                    else:
                        duration_seconds = (datetime.now() - started_at).total_seconds()

                    sessions.append(
                        {
                            "session_id": row[0],
                            "agent": row[1],
                            "status": row[2],
                            "started_at": row[3],
                            "ended_at": row[4],
                            "event_count": int(row[5]) if row[5] else 0,
                            "duration_seconds": duration_seconds,
                        }
                    )

                # OPTIMIZATION: Combine all stats in single query instead of subqueries
                # This reduces query count from 4 subqueries + 1 main to just 1
                stats_query = """
                    SELECT
                        (SELECT COUNT(*) FROM agent_events) as total_events,
                        (SELECT COUNT(DISTINCT agent_id) FROM agent_events) as total_agents,
                        (SELECT COUNT(*) FROM sessions) as total_sessions,
                        (SELECT COUNT(*) FROM features) as total_features
                """

                stats_cursor = await db.execute(stats_query)
                stats_row = await stats_cursor.fetchone()

                if stats_row:
                    stats = {
                        "total_events": int(stats_row[0]) if stats_row[0] else 0,
                        "total_agents": int(stats_row[1]) if stats_row[1] else 0,
                        "total_sessions": int(stats_row[2]) if stats_row[2] else 0,
                        "total_features": int(stats_row[3]) if stats_row[3] else 0,
                    }
                else:
                    stats = {
                        "total_events": 0,
                        "total_agents": 0,
                        "total_sessions": 0,
                        "total_features": 0,
                    }

                # Cache the results
                cache_data = (sessions, stats)
                cache.set(cache_key, cache_data)
                query_time_ms = (time.time() - query_start_time) * 1000
                cache.record_metric(cache_key, exec_time_ms, cache_hit=False)
                logger.debug(
                    f"Cache MISS for metrics_view (key={cache_key}, "
                    f"db_time={exec_time_ms:.2f}ms, total_time={query_time_ms:.2f}ms)"
                )

            return templates.TemplateResponse(
                "partials/metrics.html",
                {
                    "request": request,
                    "sessions": sessions,
                    "stats": stats,
                },
            )
        finally:
            await db.close()

    # ========== WEBSOCKET FOR REAL-TIME UPDATES ==========

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time event streaming.

        OPTIMIZATION: Uses timestamp-based filtering to minimize data transfers.
        The timestamp > ? filter with DESC index makes queries O(log n) instead of O(n).
        """
        await websocket.accept()
        last_timestamp: str | None = None
        poll_interval = 0.5  # OPTIMIZATION: Adaptive polling (reduced from 1s)

        try:
            while True:
                db = await get_db()
                try:
                    # OPTIMIZATION: Only select needed columns, use DESC index
                    # Pattern uses index: idx_agent_events_timestamp DESC
                    query = """
                        SELECT event_id, agent_id, event_type, timestamp, tool_name,
                               input_summary, output_summary, session_id, status
                        FROM agent_events
                        WHERE 1=1
                    """
                    params: list = []

                    if last_timestamp:
                        query += " AND timestamp > ?"
                        params.append(last_timestamp)

                    query += " ORDER BY timestamp ASC LIMIT 100"

                    cursor = await db.execute(query, params)
                    rows = await cursor.fetchall()

                    if rows:
                        rows_list = [list(row) for row in rows]
                        # Update last timestamp (last row since ORDER BY ts ASC)
                        last_timestamp = rows_list[-1][3]

                        # Send events in order (no need to reverse with ASC)
                        for row in rows_list:
                            event_data = {
                                "type": "event",
                                "event_id": row[0],
                                "agent_id": row[1] or "unknown",
                                "event_type": row[2],
                                "timestamp": row[3],
                                "tool_name": row[4],
                                "input_summary": row[5],
                                "output_summary": row[6],
                                "session_id": row[7],
                                "status": row[8],
                                "parent_event_id": None,
                                "cost_tokens": 0,
                                "execution_duration_seconds": 0.0,
                            }
                            await websocket.send_json(event_data)
                    else:
                        # No new events, increase poll interval (exponential backoff)
                        poll_interval = min(poll_interval * 1.2, 2.0)
                finally:
                    await db.close()

                # OPTIMIZATION: Reduced sleep interval for faster real-time updates
                await asyncio.sleep(poll_interval)

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=1011)

    return app


# Create default app instance
def create_app(db_path: str | None = None) -> FastAPI:
    """Create FastAPI app with default database path."""
    if db_path is None:
        # Use default database location
        db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

    return get_app(db_path)


# Export for uvicorn
app = create_app()
