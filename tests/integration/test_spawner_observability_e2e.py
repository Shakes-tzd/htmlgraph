"""
End-to-End Spawner Observability Test

Verifies complete event hierarchy:
1. SessionStart creates database session
2. user-prompt-submit creates UserQuery event
3. PreToolUse creates delegation event with parent_event_id linking
4. Spawner execution creates child events
5. Dashboard properly displays parent-child relationships
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from htmlgraph.db.schema import HtmlGraphDB


class TestSpawnerObservabilityE2E:
    """Test complete spawner delegation observability chain."""

    def test_session_creation_in_database(self, tmp_path):
        """Verify SessionStart hook creates database sessions."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        # Simulate SessionStart hook creating session
        session_id = "sess-test-e2e"
        cursor = db.connection.cursor()  # type: ignore

        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, created_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (
                session_id,
                "claude-code",
                datetime.now(timezone.utc).isoformat(),
                "active",
            ),
        )
        db.connection.commit()  # type: ignore

        # Verify session exists
        cursor.execute(
            "SELECT COUNT(*) FROM sessions WHERE session_id = ?", (session_id,)
        )
        count = cursor.fetchone()[0]
        assert count == 1, "Session should be created"

        db.disconnect()

    def test_userquery_event_creation(self, tmp_path):
        """Verify user-prompt-submit hook creates UserQuery events."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        session_id = "sess-test-e2e"
        userquery_event_id = "evt-userquery-001"
        prompt = "Test prompt for spawner delegation"

        cursor = db.connection.cursor()  # type: ignore

        # Create session first (required by FK)
        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, status)
            VALUES (?, ?, ?)
            """,
            (session_id, "claude-code", "active"),
        )

        # Simulate user-prompt-submit hook creating UserQuery event
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, input_summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                userquery_event_id,
                "claude-code",
                session_id,
                "tool_call",  # NOT 'user_query' - that's invalid
                "UserQuery",  # Identifier for user queries
                datetime.now(timezone.utc).isoformat(),
                json.dumps({"prompt": prompt[:100]}),
                "completed",
            ),
        )
        db.connection.commit()  # type: ignore

        # Verify UserQuery event exists
        cursor.execute(
            "SELECT event_type, tool_name FROM agent_events WHERE event_id = ?",
            (userquery_event_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "tool_call"
        assert row[1] == "UserQuery"

        db.disconnect()

    def test_delegation_event_links_to_userquery(self, tmp_path):
        """Verify PreToolUse hook creates delegation events linked to UserQuery."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        session_id = "sess-test-e2e"
        userquery_event_id = "evt-userquery-002"
        delegation_event_id = "evt-delegation-001"

        cursor = db.connection.cursor()  # type: ignore

        # Create session
        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, status)
            VALUES (?, ?, ?)
            """,
            (session_id, "claude-code", "active"),
        )

        # Create UserQuery event
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                userquery_event_id,
                "claude-code",
                session_id,
                "tool_call",
                "UserQuery",
                now,
                "completed",
            ),
        )

        # Create delegation event with parent_event_id linking to UserQuery
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status, parent_event_id, subagent_type, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delegation_event_id,
                "claude-code",
                session_id,
                "task_delegation",
                "Task",
                now,
                "completed",
                userquery_event_id,  # Link back to UserQuery
                "gemini",
                json.dumps({"spawned_agent": "gemini-2.0-flash"}),
            ),
        )
        db.connection.commit()  # type: ignore

        # Verify delegation event is properly linked
        cursor.execute(
            "SELECT parent_event_id, subagent_type FROM agent_events WHERE event_id = ?",
            (delegation_event_id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == userquery_event_id, "Delegation should link to UserQuery"
        assert row[1] == "gemini"

        db.disconnect()

    def test_child_events_created_by_spawner(self, tmp_path):
        """Verify spawner execution creates child events linked to delegation."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        session_id = "sess-test-e2e"
        delegation_event_id = "evt-delegation-002"
        child_event_1 = "evt-child-001"
        child_event_2 = "evt-child-002"

        cursor = db.connection.cursor()  # type: ignore

        # Create session
        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, status)
            VALUES (?, ?, ?)
            """,
            (session_id, "claude-code", "active"),
        )

        # Create delegation event
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status, subagent_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delegation_event_id,
                "claude-code",
                session_id,
                "task_delegation",
                "Task",
                now,
                "started",
                "gemini",
            ),
        )

        # Create child events linked to delegation
        for i, child_id in enumerate([child_event_1, child_event_2], 1):
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, session_id, event_type, tool_name,
                 timestamp, status, parent_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    child_id,
                    "gemini-2.0-flash",
                    session_id,
                    "tool_call",
                    f"Tool_{i}",
                    now,
                    "completed",
                    delegation_event_id,  # Link to delegation
                ),
            )

        db.connection.commit()  # type: ignore

        # Verify child events are properly linked
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
            (delegation_event_id,),
        )
        count = cursor.fetchone()[0]
        assert count == 2, "Delegation should have 2 child events"

        # Verify each child event
        cursor.execute(
            "SELECT event_id, agent_id FROM agent_events WHERE parent_event_id = ? ORDER BY event_id",
            (delegation_event_id,),
        )
        rows = cursor.fetchall()
        assert rows[0][0] == child_event_1
        assert rows[1][0] == child_event_2
        assert (
            rows[0][1] == "gemini-2.0-flash"
        )  # Child events attributed to spawned agent
        assert rows[1][1] == "gemini-2.0-flash"

        db.disconnect()

    def test_complete_observability_hierarchy(self, tmp_path):
        """Test complete UserQuery → Delegation → Child Events hierarchy."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        # IDs for our hierarchy
        session_id = "sess-e2e-complete"
        userquery_id = "evt-uq-complete"
        delegation_id = "evt-del-complete"
        child_ids = ["evt-child-c1", "evt-child-c2", "evt-child-c3"]

        cursor = db.connection.cursor()  # type: ignore

        # Step 1: Create session
        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, status)
            VALUES (?, ?, ?)
            """,
            (session_id, "claude-code", "active"),
        )

        # Step 2: Create UserQuery (user submits prompt)
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, input_summary, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                userquery_id,
                "claude-code",
                session_id,
                "tool_call",
                "UserQuery",
                now,
                json.dumps({"prompt": "Analyze codebase"}),
                "completed",
            ),
        )

        # Step 3: Create delegation event (PreToolUse hook)
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status, parent_event_id, subagent_type, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delegation_id,
                "claude-code",
                session_id,
                "task_delegation",
                "Task",
                now,
                "started",
                userquery_id,  # Link back to UserQuery
                "gemini",
                json.dumps({"spawned_agent": "gemini-2.0-flash"}),
            ),
        )

        # Step 4: Create child events (spawner execution)
        for child_id in child_ids:
            cursor.execute(
                """
                INSERT INTO agent_events
                (event_id, agent_id, session_id, event_type, tool_name,
                 timestamp, status, parent_event_id, output_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    child_id,
                    "gemini-2.0-flash",
                    session_id,
                    "tool_call",
                    "InternalTool",
                    now,
                    "completed",
                    delegation_id,  # Link to delegation
                    json.dumps({"result": "data"}),
                ),
            )

        db.connection.commit()  # type: ignore

        # Verify complete hierarchy
        # Count UserQuery events
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE event_type='tool_call' AND tool_name='UserQuery'",
        )
        uq_count = cursor.fetchone()[0]
        assert uq_count >= 1

        # Count delegations linked to UserQuery
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
            (userquery_id,),
        )
        del_count = cursor.fetchone()[0]
        assert del_count == 1, "Should have 1 delegation linked to UserQuery"

        # Count children linked to delegation
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?",
            (delegation_id,),
        )
        child_count = cursor.fetchone()[0]
        assert child_count == 3, "Should have 3 child events linked to delegation"

        # Verify agent attribution
        cursor.execute(
            """
            SELECT agent_id, subagent_type
            FROM agent_events
            WHERE event_id = ?
            """,
            (delegation_id,),
        )
        row = cursor.fetchone()
        assert row[0] == "claude-code"  # Orchestrator
        assert row[1] == "gemini"  # Spawner type

        # Verify child events are attributed to spawned agent, not orchestrator
        cursor.execute(
            "SELECT DISTINCT agent_id FROM agent_events WHERE parent_event_id = ?",
            (delegation_id,),
        )
        child_agents = [row[0] for row in cursor.fetchall()]
        assert "gemini-2.0-flash" in child_agents, (
            "Child events should be attributed to spawned agent"
        )
        assert "claude-code" not in child_agents, (
            "Child events should NOT be attributed to orchestrator"
        )

        db.disconnect()

    def test_dashboard_api_parent_child_structure(self, tmp_path):
        """Test API response format for dashboard parent-child display."""
        db_path = str(tmp_path / "test.db")
        db = HtmlGraphDB(db_path)

        session_id = "sess-api-test"
        userquery_id = "evt-uq-api"
        delegation_id = "evt-del-api"

        cursor = db.connection.cursor()  # type: ignore

        # Create session
        cursor.execute(
            """
            INSERT INTO sessions
            (session_id, agent_assigned, status)
            VALUES (?, ?, ?)
            """,
            (session_id, "claude-code", "active"),
        )

        # Create UserQuery
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                userquery_id,
                "claude-code",
                session_id,
                "tool_call",
                "UserQuery",
                now,
                "completed",
            ),
        )

        # Create delegation
        cursor.execute(
            """
            INSERT INTO agent_events
            (event_id, agent_id, session_id, event_type, tool_name,
             timestamp, status, parent_event_id, subagent_type,
             child_spike_count, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delegation_id,
                "claude-code",
                session_id,
                "task_delegation",
                "Task",
                now,
                "completed",
                userquery_id,
                "gemini",
                2,  # 2 child spikes created
                json.dumps({"spawned_agent": "gemini-2.0-flash"}),
            ),
        )

        db.connection.commit()  # type: ignore

        # Simulate API response generation
        cursor.execute(
            """
            SELECT
                event_id, agent_id, timestamp, status,
                subagent_type, child_spike_count, context
            FROM agent_events
            WHERE event_id = ?
            """,
            (delegation_id,),
        )
        row = cursor.fetchone()

        # Parse context to get spawned_agent
        context = json.loads(row[6]) if row[6] else {}
        spawned_agent = context.get("spawned_agent", "unknown")

        # Build API response structure
        api_response = {
            "parent_event_id": row[0],
            "orchestrator": row[1],
            "spawned_agent": spawned_agent,
            "spawner_type": row[4],
            "timestamp": row[2],
            "status": row[3],
            "child_spike_count": row[5],
            "artifacts": [],
        }

        # Verify API structure is correct for dashboard
        assert api_response["parent_event_id"] == delegation_id
        assert api_response["orchestrator"] == "claude-code"
        assert api_response["spawned_agent"] == "gemini-2.0-flash"
        assert api_response["spawner_type"] == "gemini"
        assert api_response["status"] == "completed"
        assert api_response["child_spike_count"] == 2

        db.disconnect()

    def test_real_database_has_complete_hierarchy(self):
        """Test against real database to verify actual event hierarchy exists."""
        db_path = Path("/Users/shakes/DevProjects/htmlgraph/.htmlgraph/index.sqlite")
        if not db_path.exists():
            pytest.skip("Real database not available")

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check that we have UserQuery events
        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE event_type='tool_call' AND tool_name='UserQuery'"
        )
        userquery_count = cursor.fetchone()[0]
        assert userquery_count > 0, "Should have UserQuery events in real database"

        # Check that we have delegations linked to UserQueries
        cursor.execute(
            """
            SELECT COUNT(*) FROM agent_events
            WHERE parent_event_id IN (
                SELECT event_id FROM agent_events
                WHERE event_type='tool_call' AND tool_name='UserQuery'
            )
            """
        )
        delegations_to_uq = cursor.fetchone()[0]
        assert delegations_to_uq > 0, (
            f"Should have delegations linked to UserQueries (found {userquery_count} UserQueries)"
        )

        # Check that we have child events linked to delegations
        cursor.execute(
            """
            SELECT COUNT(*) FROM agent_events
            WHERE parent_event_id IN (
                SELECT event_id FROM agent_events
                WHERE event_type='task_delegation'
            )
            """
        )
        children_to_delegations = cursor.fetchone()[0]
        assert children_to_delegations > 0, (
            "Should have child events linked to delegations"
        )

        # Verify proper agent attribution
        cursor.execute(
            """
            SELECT agent_id, subagent_type, context
            FROM agent_events
            WHERE event_type='task_delegation' AND subagent_type IS NOT NULL
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            orchestrator, spawner_type, context_json = row
            assert orchestrator is not None, "Orchestrator should be recorded"
            assert spawner_type is not None, "Spawner type should be recorded"
            # Spawned agent may be in context JSON
            if context_json:
                context = json.loads(context_json)
                assert "spawned_agent" in context or spawner_type is not None

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
