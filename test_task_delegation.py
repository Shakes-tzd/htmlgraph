#!/usr/bin/env python3
"""Test Task() delegation to Gemini spawner with proper event tracking."""

import os
import sys

# Set environment to simulate orchestrator context
os.environ["HTMLGRAPH_PROJECT_ROOT"] = os.getcwd()
os.environ["HTMLGRAPH_PARENT_SESSION"] = "test-session-123"
os.environ["HTMLGRAPH_PARENT_AGENT"] = "test-orchestrator"


def main():
    """Test Task delegation through SDK."""
    print("=" * 60)
    print("Testing Task() delegation to Gemini spawner")
    print("=" * 60)

    # This should trigger the spawner-router hook
    # which will call gemini-spawner.py
    print("\n1. Creating task delegation...")

    # Note: We can't actually call Task() from Python since it's a Claude Code tool
    # Instead, we'll simulate what the spawner-router hook does
    from htmlgraph.orchestration import HeadlessSpawner

    spawner = HeadlessSpawner()

    print("\n2. Calling Gemini spawner...")
    result = spawner.spawn_gemini(
        prompt="Test delegation event persistence", track_in_htmlgraph=True, timeout=30
    )

    print(f"\n3. Spawner result: {result.success}")
    if not result.success:
        print(f"   Error: {result.error}")
        return 1

    print(f"   Response preview: {result.response[:100]}...")

    # Query database for events
    print("\n4. Querying database for events...")
    from htmlgraph.config import get_database_path
    from htmlgraph.db.schema import HtmlGraphDB

    db = HtmlGraphDB(str(get_database_path()))
    cursor = db.connection.cursor()

    # Find all events from last minute
    cursor.execute("""
        SELECT event_id, event_type, agent_id, tool_name, input_summary
        FROM agent_events
        WHERE created_at > datetime('now', '-1 minute')
        ORDER BY created_at ASC
    """)

    events = cursor.fetchall()

    if not events:
        print("   ❌ No events found in database!")
        return 1

    print(f"\n   Found {len(events)} events:")
    for event in events:
        event_id, event_type, agent_id, tool_name, input_summary = event
        print(f"   - {event_id} | {event_type:15} | {agent_id:20} | {tool_name}")
        print(f"     Input: {input_summary[:80]}...")

    # Check for delegation event specifically
    delegation_events = [e for e in events if e[1] == "delegation"]

    if delegation_events:
        print(f"\n✅ Found {len(delegation_events)} delegation event(s)")
        for event in delegation_events:
            event_id = event[0]

            # Check for child events
            cursor.execute(
                """
                SELECT event_id, tool_name, agent_id
                FROM agent_events
                WHERE parent_event_id = ?
            """,
                (event_id,),
            )

            children = cursor.fetchall()
            print(f"\n   Delegation {event_id} has {len(children)} child events:")
            for child in children:
                print(f"   ├─ {child[0]} | {child[1]} | agent={child[2]}")
    else:
        print("\n❌ No delegation events found!")
        print("\nThis indicates the delegation event is not being persisted,")
        print("even though child events are being created.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
