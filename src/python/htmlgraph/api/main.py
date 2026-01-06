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
from datetime import datetime
from pathlib import Path

import aiosqlite
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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

    # Store database path in app state
    app.state.db_path = db_path

    # Setup Jinja2 templates
    template_dir = Path(__file__).parent / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    templates = Jinja2Templates(directory=str(template_dir))

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
        try:
            # Build query - include parent_event_id for hierarchical grouping
            query = """
                SELECT event_id, agent_id, event_type, timestamp, tool_name,
                       input_summary, output_summary, session_id, status, parent_event_id
                FROM agent_events WHERE 1=1
            """
            params: list = []

            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            # Execute query
            cursor = await db.execute(query, params)
            rows = list(await cursor.fetchall())

            events = [
                {
                    "event_id": row[0],
                    "agent_id": row[1],
                    "event_type": row[2],
                    "timestamp": row[3],
                    "tool_name": row[4],
                    "input_summary": row[5],
                    "output_summary": row[6],
                    "session_id": row[7],
                    "status": row[8],
                    "parent_event_id": row[9],
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
        try:
            query = """
                SELECT event_id, agent_id, event_type, timestamp, tool_name,
                       input_summary, output_summary, session_id, parent_event_id, status
                FROM agent_events WHERE 1=1
            """
            params: list = []

            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            return [
                EventModel(
                    event_id=row[0],
                    agent_id=row[1],
                    event_type=row[2],
                    timestamp=row[3],
                    tool_name=row[4],
                    input_summary=row[5],
                    output_summary=row[6],
                    session_id=row[7],
                    parent_event_id=row[8],
                    status=row[9],
                )
                for row in rows
            ]
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
        try:
            # Build query with explicit column selection
            query = "SELECT id, type, title, status, priority, assigned_to, created_at, updated_at FROM features WHERE 1=1"
            params: list = []

            if status != "all":
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT 100"

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            features_by_status: dict = {
                "todo": [],
                "in_progress": [],
                "blocked": [],
                "done": [],
            }

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
        try:
            # Query active sessions with explicit column selection
            query = """
                SELECT session_id, agent_assigned, status, created_at, completed_at
                FROM sessions
                ORDER BY created_at DESC
                LIMIT 20
            """

            cursor = await db.execute(query)
            rows = await cursor.fetchall()

            sessions = []
            for row in rows:
                session_id = row[0]
                started_at = datetime.fromisoformat(row[3])

                # Calculate duration
                if row[4]:
                    ended_at = datetime.fromisoformat(row[4])
                    duration_seconds = (ended_at - started_at).total_seconds()
                else:
                    duration_seconds = (datetime.now() - started_at).total_seconds()

                # Count events
                event_query = "SELECT COUNT(*) FROM agent_events WHERE session_id = ?"
                event_cursor = await db.execute(event_query, (session_id,))
                event_row = await event_cursor.fetchone()
                event_count = event_row[0] if event_row else 0

                sessions.append(
                    {
                        "session_id": session_id,
                        "agent": row[1],
                        "status": row[2],
                        "started_at": row[3],
                        "ended_at": row[4],
                        "event_count": event_count,
                        "duration_seconds": duration_seconds,
                    }
                )

            # Query system stats
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
        """WebSocket endpoint for real-time event streaming."""
        await websocket.accept()
        last_timestamp: str | None = None

        try:
            while True:
                db = await get_db()
                try:
                    # Query for new events since last message with explicit column selection
                    query = """
                        SELECT event_id, agent_id, event_type, timestamp, tool_name,
                               input_summary, output_summary, session_id, status, parent_event_id
                        FROM agent_events WHERE 1=1
                    """
                    params: list = []

                    if last_timestamp:
                        query += " AND timestamp > ?"
                        params.append(last_timestamp)

                    query += " ORDER BY timestamp DESC LIMIT 100"

                    cursor = await db.execute(query, params)
                    rows = await cursor.fetchall()

                    if rows:
                        # Convert rows to list for indexing
                        rows_list = [list(row) for row in rows]
                        # Update last timestamp
                        last_timestamp = rows_list[-1][3]

                        # Send events
                        for row in rows_list:
                            event_data = {
                                "type": "event",
                                "event_id": row[0],
                                "agent_id": row[1],
                                "event_type": row[2],
                                "timestamp": row[3],
                                "tool_name": row[4],
                                "input_summary": row[5],
                                "output_summary": row[6],
                                "session_id": row[7],
                                "status": row[8],
                                "parent_event_id": row[9],
                            }
                            await websocket.send_json(event_data)
                finally:
                    await db.close()

                # Sleep before polling again
                await asyncio.sleep(1)

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
