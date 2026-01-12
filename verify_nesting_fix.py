#!/usr/bin/env python3
"""
Verification script to test tool call nesting with subagent session persistence.
This script:
1. Creates a feature to track the verification work
2. Delegates a task that will generate multiple tool calls
3. Queries the database to verify parent_event_id linking
4. Reports results
"""

# Add src to path for imports
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from htmlgraph import SDK
from htmlgraph.config import get_database_path
from htmlgraph.db.schema import HtmlGraphDB


def verify_nesting():
    """Verify that tool calls are properly nested under Task delegations."""

    print("\n" + "=" * 70)
    print("TOOL NESTING VERIFICATION - Testing Subagent Session Persistence")
    print("=" * 70)

    # Initialize SDK and database
    sdk = SDK(agent="claude")
    db = HtmlGraphDB(str(get_database_path()))

    # 1. Create a feature to track this verification
    print("\n1️⃣  Creating verification feature...")
    try:
        # Use existing track or create new one
        tracks = sdk.tracks.list()
        if tracks:
            track = tracks[0]
        else:
            track = sdk.tracks.create("Verification").save()

        feature = (
            sdk.features.create("Verify tool call nesting fix")
            .set_track(track.id)
            .set_priority("high")
            .save()
        )
        print(f"   ✓ Feature created: {feature.id}")
    except Exception as e:
        print(f"   Note: Could not create feature: {e}")
        feature = None

    # 2. Get current time for comparison
    print(f"\n2️⃣  Timestamp before task delegation: {time.time():.2f}")

    # 3. Create and run a simple delegated task
    print("\n3️⃣  Running delegated task (will generate tool calls)...")
    print("   Task: Search for a simple pattern in codebase")

    try:
        # Use Task to delegate work - this will generate tool calls
        from htmlgraph.orchestration import delegate_with_id

        task_id, prompt = delegate_with_id(
            "Test tool nesting",
            "Search for all Python files with 'def setup' to verify tool call nesting works correctly.",
            "general-purpose",
        )

        print(f"   Task ID: {task_id}")
        print(f"   Delegating with prompt: {prompt[:80]}...")

        # For verification, we'll just show what would happen
        # The actual Task() delegation happens when Claude Code runs this
        print(f"   (Note: In real execution, this would run Task({task_id}))")

    except Exception as e:
        print(f"   Warning: Could not create delegation helper: {e}")

    # 4. Wait a moment for events to be recorded
    print("\n4️⃣  Waiting for events to be recorded (2 seconds)...")
    time.sleep(2)

    # 5. Query database to check nesting
    print("\n5️⃣  Querying database for event hierarchy...")

    try:
        cursor = db.connection.cursor()

        # Get all events from recent task delegations
        cursor.execute("""
            SELECT
                event_id,
                event_type,
                tool_name,
                parent_event_id,
                status,
                timestamp
            FROM agent_events
            WHERE timestamp >= datetime('now', '-5 seconds')
            ORDER BY timestamp DESC
        """)

        events = cursor.fetchall()

        if not events:
            print("   ⚠️  No recent events found in database")
            print("   (This may be normal if no Task delegation was run)")
        else:
            print(f"\n   Found {len(events)} recent events:")
            print("\n   Event Type | Tool Name | Parent Event | Status | Time")
            print("   " + "-" * 65)

            task_delegation_ids = set()
            tool_call_parents = []

            for event_id, event_type, tool_name, parent_event_id, status, ts in events:
                parent_str = parent_event_id or "NULL"
                if parent_event_id and parent_event_id.startswith("evt-"):
                    parent_str = f"✓ {parent_event_id[:8]}..."

                print(
                    f"   {event_type[:12]:12} | {str(tool_name)[:9]:9} | {parent_str:12} | {status:6} | {ts}"
                )

                # Track task delegations and tool calls
                if event_type == "task_delegation":
                    task_delegation_ids.add(event_id)
                elif tool_name and event_type == "tool_call":
                    tool_call_parents.append((tool_name, parent_event_id))

        # 6. Analyze nesting quality
        print("\n6️⃣  Analyzing nesting quality...")

        cursor.execute("""
            SELECT
                event_type,
                tool_name,
                COUNT(*) as count,
                SUM(CASE WHEN parent_event_id LIKE 'evt-%' THEN 1 ELSE 0 END) as nested,
                SUM(CASE WHEN parent_event_id IS NULL THEN 1 ELSE 0 END) as no_parent
            FROM agent_events
            WHERE timestamp >= datetime('now', '-5 seconds')
            GROUP BY event_type, tool_name
            ORDER BY timestamp DESC
        """)

        analysis = cursor.fetchall()

        if analysis:
            print("\n   Event Statistics:")
            print("   Type | Tool | Total | ✓ Nested | ✗ No Parent")
            print("   " + "-" * 50)

            for event_type, tool_name, total, nested, no_parent in analysis:
                nested = nested or 0
                no_parent = no_parent or 0
                tool_str = str(tool_name)[:10] if tool_name else "N/A"
                print(
                    f"   {str(event_type)[:12]:12} | {tool_str:10} | {total:5} | {nested:8} | {no_parent:8}"
                )

        # 7. Check for task delegations with proper children
        print("\n7️⃣  Checking task delegation → tool call relationships...")

        cursor.execute("""
            SELECT
                d.event_id as delegation_id,
                d.subagent_type,
                d.status,
                COUNT(DISTINCT t.event_id) as tool_call_count
            FROM agent_events d
            LEFT JOIN agent_events t ON (
                t.parent_event_id = d.event_id
                AND t.event_type = 'tool_call'
            )
            WHERE d.event_type = 'task_delegation'
              AND d.timestamp >= datetime('now', '-5 seconds')
            GROUP BY d.event_id
            ORDER BY d.timestamp DESC
        """)

        delegations = cursor.fetchall()

        if delegations:
            print(f"\n   Found {len(delegations)} task delegations:")
            for del_id, subagent_type, status, tool_count in delegations:
                del_short = del_id[:8] if del_id else "N/A"
                check = "✓" if tool_count and tool_count > 0 else "✗"
                print(
                    f"   {check} {del_short}... ({subagent_type}) status={status} → {tool_count} tool calls"
                )

        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)

        if delegations and delegations[0][3] and delegations[0][3] > 0:
            print(
                "\n✅ SUCCESS: Tool calls are properly nested under task delegations!"
            )
            return True
        else:
            print("\n❌ ISSUE: Tool calls are not properly nested.")
            print("   This may indicate the fix hasn't taken effect yet.")
            print("   (Claude Code may need to be restarted to load v0.26.10)")
            return False

    except Exception as e:
        print(f"\n❌ ERROR querying database: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_nesting()
    sys.exit(0 if success else 1)
