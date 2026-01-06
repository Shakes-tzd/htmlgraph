"""
HtmlGraph SQLite Backend - Phase 1

Provides SQLite schema and query builders for agent observability storage.

Main Components:
- schema.py: SQLite database schema, table creation, and CRUD operations
- queries.py: Query builders for common operations

Usage:
    from htmlgraph.db.schema import HtmlGraphDB
    from htmlgraph.db.queries import Queries

    # Initialize database
    db = HtmlGraphDB(".htmlgraph/htmlgraph.db")
    db.connect()
    db.create_tables()

    # Insert data
    db.insert_session("sess-123", "claude-code")
    db.insert_event("evt-1", "claude-code", "tool_call", "sess-123",
                    tool_name="Read", input_summary="Read file.py")

    # Query data
    events = db.get_session_events("sess-123")
    sql, params = Queries.get_tool_usage_summary("sess-123")
"""

from htmlgraph.db.queries import EventType, FeatureStatus, Priority, Queries
from htmlgraph.db.schema import HtmlGraphDB

__all__ = [
    "HtmlGraphDB",
    "Queries",
    "EventType",
    "FeatureStatus",
    "Priority",
]
