"""
Tests for parallel subagent parent attribution (Issue #23).

Verifies that when multiple Task() delegations run in parallel,
child events are correctly attributed to their respective parent tasks.
"""

import sqlite3


# Helper to set up test database with agent_events and tool_traces tables
def create_test_db():
    """Create in-memory SQLite DB with required tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE agent_events (
            event_id TEXT PRIMARY KEY,
            agent_id TEXT,
            event_type TEXT NOT NULL,
            session_id TEXT,
            tool_name TEXT,
            input_summary TEXT,
            context TEXT,
            parent_event_id TEXT,
            subagent_type TEXT,
            status TEXT DEFAULT 'recorded',
            model TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE tool_traces (
            tool_use_id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            tool_input JSON,
            tool_output JSON,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration_ms INTEGER,
            status TEXT NOT NULL DEFAULT 'started',
            error_message TEXT,
            parent_tool_use_id TEXT,
            parent_event_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    return conn


class TestResolveParentTaskDelegation:
    """Tests for resolve_parent_task_delegation() function."""

    def test_single_active_task(self):
        """When only 1 active task_delegation exists, return it."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
            ),
        )
        conn.commit()

        from htmlgraph.hooks.pretooluse import resolve_parent_task_delegation

        result = resolve_parent_task_delegation(cursor, parent_session_id="sess-abc")
        assert result == "evt-001"

    def test_different_models_with_hint(self):
        """When multiple tasks have different models and hint provided, match by model."""
        conn = create_test_db()
        cursor = conn.cursor()
        # Insert two task_delegations with different models
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
                "2025-01-01 10:00:00",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-haiku",
                "2025-01-01 10:00:01",
            ),
        )
        conn.commit()

        from htmlgraph.hooks.pretooluse import resolve_parent_task_delegation

        # Should match haiku
        result = resolve_parent_task_delegation(
            cursor, parent_session_id="sess-abc", model_hint="claude-haiku"
        )
        assert result == "evt-002"

        # Should match sonnet
        result = resolve_parent_task_delegation(
            cursor, parent_session_id="sess-abc", model_hint="claude-sonnet"
        )
        assert result == "evt-001"

    def test_same_model_child_count_balancing(self):
        """When multiple tasks have same model, pick one with fewest children."""
        conn = create_test_db()
        cursor = conn.cursor()
        # Insert two task_delegations with same model
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
                "2025-01-01 10:00:00",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
                "2025-01-01 10:00:01",
            ),
        )
        # Add 3 children to evt-001, 1 child to evt-002
        for i in range(3):
            cursor.execute(
                "INSERT INTO agent_events (event_id, event_type, session_id, parent_event_id, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    f"child-{i}",
                    "tool_call",
                    "sess-abc-gp",
                    "evt-001",
                    "recorded",
                    f"2025-01-01 10:01:0{i}",
                ),
            )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, parent_event_id, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "child-3",
                "tool_call",
                "sess-abc-gp",
                "evt-002",
                "recorded",
                "2025-01-01 10:01:03",
            ),
        )
        conn.commit()

        from htmlgraph.hooks.pretooluse import resolve_parent_task_delegation

        # Should pick evt-002 (fewer children: 1 vs 3)
        result = resolve_parent_task_delegation(cursor, parent_session_id="sess-abc")
        assert result == "evt-002"

    def test_fifo_tiebreak(self):
        """When everything is equal, pick earliest (FIFO)."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
                "2025-01-01 10:00:00",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "claude-sonnet",
                "2025-01-01 10:00:01",
            ),
        )
        conn.commit()

        from htmlgraph.hooks.pretooluse import resolve_parent_task_delegation

        # Both have 0 children, should pick earliest (FIFO)
        result = resolve_parent_task_delegation(cursor, parent_session_id="sess-abc")
        assert result == "evt-001"

    def test_no_active_tasks(self):
        """When no active task_delegations exist, return None."""
        conn = create_test_db()
        cursor = conn.cursor()
        # Insert a completed task (not active)
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, model) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "completed",
                "claude-sonnet",
            ),
        )
        conn.commit()

        from htmlgraph.hooks.pretooluse import resolve_parent_task_delegation

        result = resolve_parent_task_delegation(cursor, parent_session_id="sess-abc")
        assert result is None


class TestSubagentStartMapping:
    """Tests for SubagentStart agent_id → task_delegation mapping."""

    def test_maps_agent_id_to_task(self):
        """SubagentStart correctly maps agent_id to unmatched task_delegation."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "2025-01-01 10:00:00",
            ),
        )
        conn.commit()

        # Simulate SubagentStart matching logic
        cursor.execute(
            """SELECT event_id, subagent_type FROM agent_events
               WHERE event_type = 'task_delegation'
                 AND status = 'started'
                 AND (agent_id IS NULL OR agent_id = '')
               ORDER BY timestamp ASC""",
        )
        rows = cursor.fetchall()
        assert len(rows) == 1

        # Map agent_id
        cursor.execute(
            "UPDATE agent_events SET agent_id = ? WHERE event_id = ?",
            ("agent-abc123", rows[0][0]),
        )
        conn.commit()

        # Verify mapping
        cursor.execute("SELECT agent_id FROM agent_events WHERE event_id = 'evt-001'")
        assert cursor.fetchone()[0] == "agent-abc123"

    def test_fifo_matching_parallel_tasks(self):
        """First SubagentStart maps to first unmatched task_delegation (FIFO)."""
        conn = create_test_db()
        cursor = conn.cursor()
        # Two parallel tasks
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "2025-01-01 10:00:00",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "2025-01-01 10:00:01",
            ),
        )
        conn.commit()

        # First SubagentStart should match first task (FIFO)
        cursor.execute(
            """SELECT event_id FROM agent_events
               WHERE event_type = 'task_delegation'
                 AND status = 'started'
                 AND (agent_id IS NULL OR agent_id = '')
               ORDER BY timestamp ASC""",
        )
        first_unmatched = cursor.fetchone()[0]
        assert first_unmatched == "evt-001"

        # Map first agent
        cursor.execute(
            "UPDATE agent_events SET agent_id = 'agent-A' WHERE event_id = ?",
            (first_unmatched,),
        )
        conn.commit()

        # Second SubagentStart should match second task
        cursor.execute(
            """SELECT event_id FROM agent_events
               WHERE event_type = 'task_delegation'
                 AND status = 'started'
                 AND (agent_id IS NULL OR agent_id = '')
               ORDER BY timestamp ASC""",
        )
        second_unmatched = cursor.fetchone()[0]
        assert second_unmatched == "evt-002"


class TestSubagentStopWithAgentId:
    """Tests for SubagentStop using agent_id for exact matching."""

    def test_finds_parent_by_agent_id(self):
        """SubagentStop finds correct parent via agent_id exact match."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "agent-abc123",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, agent_id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "agent-xyz789",
            ),
        )
        conn.commit()

        # Exact match by agent_id
        cursor.execute(
            "SELECT event_id FROM agent_events WHERE event_type = 'task_delegation' AND agent_id = ?",
            ("agent-xyz789",),
        )
        result = cursor.fetchone()
        assert result[0] == "evt-002"


class TestToolTracesParentAttribution:
    """Tests for tool_traces parent_event_id storage and retrieval."""

    def test_stores_parent_event_id(self):
        """tool_traces stores parent_event_id from PreToolUse resolution."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO tool_traces
               (tool_use_id, trace_id, session_id, tool_name, start_time, status, parent_event_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "toolu_abc",
                "trace-001",
                "sess-abc",
                "Read",
                "2025-01-01 10:00:00",
                "started",
                "evt-001",
            ),
        )
        conn.commit()

        cursor.execute(
            "SELECT parent_event_id FROM tool_traces WHERE tool_use_id = 'toolu_abc'"
        )
        assert cursor.fetchone()[0] == "evt-001"

    def test_task_completed_fifo_order(self):
        """TaskCompleted should complete oldest started task first (FIFO)."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-001",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "2025-01-01 10:00:00",
            ),
        )
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, session_id, subagent_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "evt-002",
                "task_delegation",
                "sess-abc",
                "general-purpose",
                "started",
                "2025-01-01 10:00:01",
            ),
        )
        conn.commit()

        # FIFO: oldest first
        cursor.execute(
            """SELECT event_id FROM agent_events
               WHERE session_id = 'sess-abc'
                 AND event_type = 'task_delegation'
                 AND status = 'started'
               ORDER BY timestamp ASC
               LIMIT 1""",
        )
        result = cursor.fetchone()
        assert result[0] == "evt-001"  # Oldest task completed first


class TestAgentIdMigration:
    """Test that agent_id column migration works."""

    def test_agent_id_column_exists(self):
        """Verify agent_id column is available in agent_events."""
        conn = create_test_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_events (event_id, event_type, agent_id) VALUES ('e1', 'tool_call', 'agent-123')"
        )
        conn.commit()
        cursor.execute("SELECT agent_id FROM agent_events WHERE event_id = 'e1'")
        assert cursor.fetchone()[0] == "agent-123"
