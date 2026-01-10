#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
Test script to verify UserQuery event creation in HtmlGraph database.

This script:
1. Creates a test UserQuery event via the hook logic
2. Verifies the event is in the database
3. Checks delegation parent linking
4. Tests the full hierarchy: UserQuery → Delegation → Child Events
"""

import sys
import uuid

from htmlgraph.db.schema import HtmlGraphDB


def test_user_query_event_creation():
    """Test creating a UserQuery event in the database."""
    print("\n" + "=" * 70)
    print("TEST 1: UserQuery Event Creation")
    print("=" * 70)

    try:
        # Initialize database
        db = HtmlGraphDB()
        session_id = f"test-sess-{uuid.uuid4().hex[:8]}"

        # Ensure session exists
        db.insert_session(
            session_id=session_id,
            agent_assigned="test-agent",
        )

        # Create a UserQuery event (simulating what user-prompt-submit.py does)
        user_query_event_id = f"uq-{uuid.uuid4().hex[:8]}"
        prompt = "Implement a test feature for HtmlGraph"

        success = db.insert_event(
            event_id=user_query_event_id,
            agent_id="user",
            event_type="tool_call",
            session_id=session_id,
            tool_name="UserQuery",
            input_summary=prompt[:200],
            context={
                "prompt": prompt[:500],
                "session": session_id,
            },
        )

        if success:
            print(f"✅ UserQuery event created: {user_query_event_id}")
        else:
            print("❌ Failed to create UserQuery event")
            return False

        # Verify event exists in database
        cursor = db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            "SELECT event_id, tool_name, agent_id FROM agent_events WHERE event_id = ?",
            (user_query_event_id,),
        )
        row = cursor.fetchone()

        if row:
            event_id, tool_name, agent_id = row
            print("✅ Event verified in database:")
            print(f"   - event_id: {event_id}")
            print(f"   - tool_name: {tool_name}")
            print(f"   - agent_id: {agent_id}")
            return True
        else:
            print("❌ Event not found in database")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_delegation_parent_linking():
    """Test that delegations link to UserQuery events as parents."""
    print("\n" + "=" * 70)
    print("TEST 2: Delegation Parent Linking")
    print("=" * 70)

    try:
        db = HtmlGraphDB()
        session_id = f"test-sess-{uuid.uuid4().hex[:8]}"

        # Create session
        db.insert_session(
            session_id=session_id,
            agent_assigned="test-agent",
        )

        # Create UserQuery event (parent)
        user_query_event_id = f"uq-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=user_query_event_id,
            agent_id="user",
            event_type="tool_call",
            session_id=session_id,
            tool_name="UserQuery",
            input_summary="Test query",
            context={"prompt": "Test prompt"},
        )
        print(f"✅ Created UserQuery event: {user_query_event_id}")

        # Create a Task delegation with UserQuery as parent
        task_event_id = f"evt-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=task_event_id,
            agent_id="claude-code",
            event_type="task_delegation",
            session_id=session_id,
            tool_name="Task",
            input_summary="Delegate: Implement feature",
            parent_event_id=user_query_event_id,  # Link to UserQuery
            subagent_type="general-purpose",
        )
        print(f"✅ Created Task delegation: {task_event_id}")
        print(f"   - parent_event_id: {user_query_event_id}")

        # Verify the linking
        cursor = db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            """SELECT event_id, parent_event_id, event_type
               FROM agent_events
               WHERE event_id = ? AND parent_event_id = ?""",
            (task_event_id, user_query_event_id),
        )
        row = cursor.fetchone()

        if row:
            event_id, parent_id, event_type = row
            print("✅ Delegation properly linked:")
            print(f"   - event_id: {event_id}")
            print(f"   - parent_event_id: {parent_id}")
            print(f"   - event_type: {event_type}")
            return True
        else:
            print("❌ Delegation not linked to UserQuery")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_full_hierarchy():
    """Test the full hierarchy: UserQuery → Delegation → Child Events."""
    print("\n" + "=" * 70)
    print("TEST 3: Full Event Hierarchy")
    print("=" * 70)

    try:
        db = HtmlGraphDB()
        session_id = f"test-sess-{uuid.uuid4().hex[:8]}"

        # Create session
        db.insert_session(
            session_id=session_id,
            agent_assigned="test-agent",
        )

        # 1. Create UserQuery event (root of hierarchy)
        user_query_id = f"uq-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=user_query_id,
            agent_id="user",
            event_type="tool_call",
            session_id=session_id,
            tool_name="UserQuery",
            input_summary="Test: Build something",
        )
        print(f"✅ 1. UserQuery (root): {user_query_id}")

        # 2. Create Task delegation (child of UserQuery)
        task_id = f"evt-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=task_id,
            agent_id="claude-code",
            event_type="task_delegation",
            session_id=session_id,
            tool_name="Task",
            input_summary="Delegate to subagent",
            parent_event_id=user_query_id,  # Link to UserQuery
            subagent_type="general-purpose",
        )
        print(f"✅ 2. Task Delegation: {task_id}")
        print(f"      parent: {user_query_id}")

        # 3. Create child events from subagent (children of Task)
        child_event_id = f"evt-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=child_event_id,
            agent_id="general-purpose",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Read",
            input_summary="Read: /some/file.py",
            parent_event_id=task_id,  # Link to Task delegation
        )
        print(f"✅ 3. Child Event: {child_event_id}")
        print(f"      parent: {task_id}")

        # Verify the full hierarchy
        cursor = db.connection.cursor()  # type: ignore[union-attr]

        # Check UserQuery exists
        cursor.execute(
            "SELECT event_id FROM agent_events WHERE event_id = ? AND event_type = 'tool_call'",
            (user_query_id,),
        )
        if not cursor.fetchone():
            print("❌ UserQuery event not found")
            return False

        # Check Task links to UserQuery
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?", (task_id,)
        )
        task_parent = cursor.fetchone()
        if not task_parent or task_parent[0] != user_query_id:
            print(f"❌ Task not linked to UserQuery: {task_parent}")
            return False

        # Check Child links to Task
        cursor.execute(
            "SELECT parent_event_id FROM agent_events WHERE event_id = ?",
            (child_event_id,),
        )
        child_parent = cursor.fetchone()
        if not child_parent or child_parent[0] != task_id:
            print(f"❌ Child not linked to Task: {child_parent}")
            return False

        print("\n✅ Full hierarchy verified:")
        print("   UserQuery (root)")
        print("   ├── Task Delegation")
        print("   │   └── Read (child event)")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_query_hierarchy():
    """Test querying the hierarchy to verify navigability."""
    print("\n" + "=" * 70)
    print("TEST 4: Query Hierarchy Navigation")
    print("=" * 70)

    try:
        db = HtmlGraphDB()
        session_id = f"test-sess-{uuid.uuid4().hex[:8]}"

        # Create session
        db.insert_session(
            session_id=session_id,
            agent_assigned="test-agent",
        )

        # Create hierarchy
        user_query_id = f"uq-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=user_query_id,
            agent_id="user",
            event_type="tool_call",
            session_id=session_id,
            tool_name="UserQuery",
            input_summary="Query: Find bugs",
        )

        task_id = f"evt-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=task_id,
            agent_id="claude-code",
            event_type="task_delegation",
            session_id=session_id,
            tool_name="Task",
            input_summary="Delegate",
            parent_event_id=user_query_id,
        )

        child_id = f"evt-{uuid.uuid4().hex[:8]}"
        db.insert_event(
            event_id=child_id,
            agent_id="subagent",
            event_type="tool_call",
            session_id=session_id,
            tool_name="Bash",
            input_summary="Run test",
            parent_event_id=task_id,
        )

        # Query: Find all children of UserQuery
        cursor = db.connection.cursor()  # type: ignore[union-attr]
        cursor.execute(
            """SELECT event_id, tool_name, event_type
               FROM agent_events
               WHERE parent_event_id = ?
               ORDER BY timestamp ASC""",
            (user_query_id,),
        )
        direct_children = cursor.fetchall()
        print(f"✅ Direct children of UserQuery: {len(direct_children)}")
        for row in direct_children:
            print(f"   - {row[0]} ({row[1]}): {row[2]}")

        # Query: Find all descendants of UserQuery
        cursor.execute(
            """WITH RECURSIVE descendants AS (
                 SELECT event_id, parent_event_id, tool_name, event_type, 0 as depth
                 FROM agent_events
                 WHERE event_id = ?
                 UNION ALL
                 SELECT ae.event_id, ae.parent_event_id, ae.tool_name, ae.event_type, d.depth + 1
                 FROM agent_events ae
                 JOIN descendants d ON ae.parent_event_id = d.event_id
               )
               SELECT event_id, tool_name, event_type, depth FROM descendants
               ORDER BY depth, event_id""",
            (user_query_id,),
        )
        all_descendants = cursor.fetchall()
        print(f"✅ All descendants of UserQuery (recursive): {len(all_descendants)}")
        for row in all_descendants:
            depth = row[3]
            indent = "  " * depth
            print(f"   {indent}- {row[0]} ({row[1]}): {row[2]}")

        if len(direct_children) >= 1 and len(all_descendants) >= 3:
            return True
        else:
            print("❌ Hierarchy query incomplete")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("HtmlGraph UserQuery Event Tests")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("UserQuery Creation", test_user_query_event_creation()))
    results.append(("Delegation Linking", test_delegation_parent_linking()))
    results.append(("Full Hierarchy", test_full_hierarchy()))
    results.append(("Query Navigation", test_query_hierarchy()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 70)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
