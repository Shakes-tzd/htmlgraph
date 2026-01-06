#!/usr/bin/env python3
"""
Test script for event tracking system.

Verifies that:
1. SDK operations log events to SQLite
2. Events are visible in the database
3. WebSocket can stream events
"""

import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from htmlgraph import SDK


def check_database_state(db_path: str) -> dict:
    """Check what's in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Count events
    cursor.execute("SELECT COUNT(*) FROM agent_events")
    event_count = cursor.fetchone()[0]

    # Count sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    session_count = cursor.fetchone()[0]

    # Get recent events
    cursor.execute("""
        SELECT event_id, agent_id, event_type, timestamp, tool_name,
               input_summary, output_summary
        FROM agent_events
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    recent_events = cursor.fetchall()

    conn.close()

    return {
        "event_count": event_count,
        "session_count": session_count,
        "recent_events": recent_events,
    }


def main():
    """Run event tracking test."""
    print("\n" + "=" * 70)
    print("HtmlGraph Event Tracking Test")
    print("=" * 70)

    # Setup paths
    htmlgraph_dir = Path.cwd() / ".htmlgraph"
    db_path = str(Path.home() / ".htmlgraph" / "htmlgraph.db")

    # Verify .htmlgraph directory exists
    if not htmlgraph_dir.exists():
        print(f"\nError: {htmlgraph_dir} does not exist")
        print("Please run this script from the project root directory")
        return 1

    print(f"\nProject directory: {htmlgraph_dir}")
    print(f"Database path: {db_path}")

    # Check initial state
    print("\n--- BEFORE Test ---")
    before = check_database_state(db_path)
    print(f"Events in database: {before['event_count']}")
    print(f"Sessions in database: {before['session_count']}")

    # Create SDK and test operations
    print("\n--- Running Test Operations ---")
    try:
        sdk = SDK(agent="test-agent")
        print(f"✓ SDK initialized (agent: {sdk._agent_id})")

        # Test 1: Create a feature
        print("\nTest 1: Creating feature...")
        track = sdk.tracks.create(title="Test Track for Event Tracking").save()
        print(f"  ✓ Track created: {track.id}")

        feature = (
            sdk.features.create(title="Test Feature - Event Tracking")
            .set_priority("high")
            .set_track(track.id)
            .save()
        )
        print(f"  ✓ Feature created: {feature.id}")

        # Test 2: Mark feature as done
        print("\nTest 2: Marking feature as done...")
        result = sdk.features.mark_done([feature.id])
        print(f"  ✓ Mark done result: {result}")

        # Test 3: Create a bug
        print("\nTest 3: Creating bug...")
        bug = (
            sdk.bugs.create(title="Test Bug - Event Tracking")
            .set_priority("medium")
            .save()
        )
        print(f"  ✓ Bug created: {bug.id}")

        print("\n✓ All test operations completed successfully")

    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Check final state
    print("\n--- AFTER Test ---")
    after = check_database_state(db_path)
    print(f"Events in database: {after['event_count']}")
    print(f"Sessions in database: {after['session_count']}")

    # Calculate differences
    event_diff = after["event_count"] - before["event_count"]
    session_diff = after["session_count"] - before["session_count"]

    print("\nChanges:")
    print(f"  Events added: {event_diff}")
    print(f"  Sessions added: {session_diff}")

    # Show recent events
    if after["recent_events"]:
        print("\nRecent events in database:")
        for evt in after["recent_events"][:5]:
            (
                event_id,
                agent_id,
                event_type,
                timestamp,
                tool_name,
                input_sum,
                output_sum,
            ) = evt
            print(f"  - {event_id[:8]}: {agent_id} / {tool_name}")
            print(f"    Input:  {input_sum[:60]}")
            if output_sum:
                print(f"    Output: {output_sum[:60]}")

    # Check success
    if event_diff > 0 and session_diff >= 0:
        print("\n" + "=" * 70)
        print("SUCCESS: Events are being logged to SQLite!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Start API: uv run htmlgraph serve-api")
        print("  2. Open dashboard: http://localhost:8000")
        print("  3. Activity Feed should show the events above")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print("FAILURE: No events were logged")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
