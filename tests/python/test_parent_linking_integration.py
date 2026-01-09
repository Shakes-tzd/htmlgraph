"""
Integration test for parent-child event linking.

Tests the actual fix: verifying that parent_event_id is set correctly
when events are recorded to SQLite.
"""

import tempfile
from pathlib import Path

import pytest
from htmlgraph.db.schema import HtmlGraphDB


def test_parent_event_id_set_in_database():
    """
    Test that parent_event_id is correctly set in database when recording events.

    This is the core test that verifies the fix for the parent-child linking issue.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))

        # Create a session
        session_id = "sess-integration-001"
        db.insert_session(session_id, "claude-code")

        # Insert parent Task event
        parent_task_id = "evt-task-parent-001"
        success = db.insert_event(
            event_id=parent_task_id,
            agent_id="claude-code",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Task",
            input_summary="Task: Delegate work to subagent",
            output_summary="Task delegated",
            parent_event_id=None,  # Root event
        )
        assert success, "Should insert parent Task event"

        # Insert child Read event with parent link
        child_read_id = "evt-read-child-001"
        success = db.insert_event(
            event_id=child_read_id,
            agent_id="general-purpose",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Read",
            input_summary="Read: /test/file.py",
            output_summary="File read successfully",
            parent_event_id=parent_task_id,  # Link to parent
        )
        assert success, "Should insert child Read event with parent link"

        # Verify in database
        conn = db.connection
        cursor = conn.cursor()

        # Check parent event has no parent
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?",
            (parent_task_id,),
        )
        result = cursor.fetchone()
        assert result is not None, "Parent event should exist"
        assert result["parent_event_id"] is None, "Parent event should have no parent"

        # Check child event has correct parent
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?",
            (child_read_id,),
        )
        result = cursor.fetchone()
        assert result is not None, "Child event should exist"
        assert result["parent_event_id"] == parent_task_id, (
            f"Child event should have parent_event_id={parent_task_id}, got {result['parent_event_id']}"
        )

        # Query children by parent
        cursor.execute(
            "SELECT COUNT(*) as count FROM agent_events WHERE parent_event_id = ?",
            (parent_task_id,),
        )
        result = cursor.fetchone()
        assert result["count"] == 1, "Parent should have 1 child event"


def test_multiple_children_same_parent():
    """Test that multiple child events can link to the same parent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))

        session_id = "sess-multi-child"
        db.insert_session(session_id, "claude-code")

        # Parent event
        parent_id = "evt-parent-002"
        db.insert_event(
            event_id=parent_id,
            agent_id="claude-code",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Task",
            input_summary="Task: Multi-step operation",
        )

        # Multiple child events
        child_ids = []
        for i in range(5):
            child_id = f"evt-child-{i:03d}"
            child_ids.append(child_id)
            db.insert_event(
                event_id=child_id,
                agent_id="general-purpose",
                event_type="tool_call",
                session_id=session_id,
                tool_name=f"Tool{i}",
                input_summary=f"Tool{i}: Operation {i}",
                parent_event_id=parent_id,
            )

        # Verify all children are linked
        cursor = db.connection.cursor()
        cursor.execute(
            "SELECT event_id FROM agent_events WHERE parent_event_id = ? ORDER BY event_id",
            (parent_id,),
        )
        results = cursor.fetchall()

        assert len(results) == 5, "Should have 5 child events"
        for i, row in enumerate(results):
            assert row["event_id"] == child_ids[i], (
                f"Child {i} should be {child_ids[i]}"
            )


def test_nested_hierarchy_three_levels():
    """Test three-level nesting: Task -> Skill -> Read."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))

        session_id = "sess-nested-three"
        db.insert_session(session_id, "claude-code")

        # Level 1: Root Task
        task_id = "evt-task-root"
        db.insert_event(
            event_id=task_id,
            agent_id="claude-code",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Task",
            input_summary="Root task",
            parent_event_id=None,
        )

        # Level 2: Skill (child of Task)
        skill_id = "evt-skill-middle"
        db.insert_event(
            event_id=skill_id,
            agent_id="general-purpose",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Skill",
            input_summary="Skill invoked",
            parent_event_id=task_id,
        )

        # Level 3: Read (child of Skill)
        read_id = "evt-read-leaf"
        db.insert_event(
            event_id=read_id,
            agent_id="specialized-agent",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Read",
            input_summary="Read file",
            parent_event_id=skill_id,
        )

        # Verify hierarchy
        cursor = db.connection.cursor()

        # Task has no parent, has 1 child (Skill)
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?", (task_id,)
        )
        assert cursor.fetchone()["parent_event_id"] is None

        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?", (task_id,)
        )
        assert cursor.fetchone()[0] == 1

        # Skill has Task as parent, has 1 child (Read)
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?", (skill_id,)
        )
        assert cursor.fetchone()["parent_event_id"] == task_id

        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?", (skill_id,)
        )
        assert cursor.fetchone()[0] == 1

        # Read has Skill as parent, has no children
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?", (read_id,)
        )
        assert cursor.fetchone()["parent_event_id"] == skill_id

        cursor.execute(
            "SELECT COUNT(*) FROM agent_events WHERE parent_event_id = ?", (read_id,)
        )
        assert cursor.fetchone()[0] == 0


def test_query_event_tree():
    """Test querying entire event tree using recursive CTE."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))

        session_id = "sess-tree"
        db.insert_session(session_id, "claude-code")

        # Build tree:
        #   Task (root)
        #     ├── Read1
        #     ├── Read2
        #     └── Edit1
        #           └── Bash1

        task_id = "evt-task-tree"
        db.insert_event(task_id, "claude", "tool_call", session_id, "Task", "Root")

        read1_id = "evt-read1"
        db.insert_event(
            read1_id,
            "agent1",
            "tool_call",
            session_id,
            "Read",
            "Read1",
            parent_event_id=task_id,
        )

        read2_id = "evt-read2"
        db.insert_event(
            read2_id,
            "agent1",
            "tool_call",
            session_id,
            "Read",
            "Read2",
            parent_event_id=task_id,
        )

        edit1_id = "evt-edit1"
        db.insert_event(
            edit1_id,
            "agent1",
            "tool_call",
            session_id,
            "Edit",
            "Edit1",
            parent_event_id=task_id,
        )

        bash1_id = "evt-bash1"
        db.insert_event(
            bash1_id,
            "agent2",
            "tool_call",
            session_id,
            "Bash",
            "Bash1",
            parent_event_id=edit1_id,
        )

        # Recursive query to get all descendants of Task
        cursor = db.connection.cursor()
        cursor.execute(
            """
            WITH RECURSIVE event_tree AS (
                -- Base case: start with the root event
                SELECT event_id, tool_name, parent_event_id, 0 as depth
                FROM agent_events
                WHERE event_id = ?

                UNION ALL

                -- Recursive case: find children
                SELECT e.event_id, e.tool_name, e.parent_event_id, t.depth + 1
                FROM agent_events e
                JOIN event_tree t ON e.parent_event_id = t.event_id
            )
            SELECT event_id, tool_name, depth FROM event_tree
            ORDER BY depth, event_id
        """,
            (task_id,),
        )

        results = cursor.fetchall()

        # Should have 5 events total: Task + 4 descendants
        assert len(results) == 5, f"Expected 5 events in tree, got {len(results)}"

        # Verify structure
        assert results[0]["tool_name"] == "Task" and results[0]["depth"] == 0
        assert results[1]["tool_name"] == "Edit" and results[1]["depth"] == 1
        assert results[2]["tool_name"] == "Read" and results[2]["depth"] == 1
        assert results[3]["tool_name"] == "Read" and results[3]["depth"] == 1
        assert results[4]["tool_name"] == "Bash" and results[4]["depth"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
