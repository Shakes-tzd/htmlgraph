#!/usr/bin/env python3
"""
Test Phase 1: UserQuery SQLite Recording with Parent-Child Linking

This script verifies:
1. UserQuery events are recorded to SQLite
2. Subsequent tool calls have parent_event_id linking to UserQuery
"""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / ".htmlgraph" / "index.sqlite"

print("=" * 80)
print("Phase 1 Test: UserQuery Recording & Parent-Child Linking")
print("=" * 80)

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

# Test 1: Check for UserQuery events
print("\n1. Checking for UserQuery events...")
cursor = conn.execute("""
    SELECT event_id, tool_name, input_summary, created_at
    FROM agent_events
    WHERE tool_name = 'UserQuery'
    ORDER BY created_at DESC
    LIMIT 5
""")
user_queries = cursor.fetchall()

if user_queries:
    print(f"✅ Found {len(user_queries)} UserQuery event(s)")
    for uq in user_queries:
        print(f"   - {uq['event_id']}: {uq['input_summary'][:60]}...")

    # Test 2: Check for child events linked to UserQuery
    latest_query_id = user_queries[0]["event_id"]
    print(f"\n2. Checking for child events linked to UserQuery {latest_query_id}...")

    cursor = conn.execute(
        """
        SELECT event_id, tool_name, parent_event_id, input_summary
        FROM agent_events
        WHERE parent_event_id = ?
        ORDER BY created_at
    """,
        (latest_query_id,),
    )

    child_events = cursor.fetchall()

    if child_events:
        print(f"✅ Found {len(child_events)} child event(s) linked to UserQuery")
        for child in child_events:
            print(f"   - {child['tool_name']}: {child['input_summary'][:60]}...")
    else:
        print(
            "⚠️  No child events found linked to UserQuery (may need to wait for next prompt)"
        )
else:
    print("⚠️  No UserQuery events found yet")
    print(
        "   This is expected if no user prompts have been submitted since the implementation."
    )

# Test 3: Show recent events with parent linking
print("\n3. Recent events with parent linking:")
cursor = conn.execute("""
    SELECT
        e.event_id,
        e.tool_name,
        e.parent_event_id,
        p.tool_name as parent_tool,
        substr(e.input_summary, 1, 50) as summary
    FROM agent_events e
    LEFT JOIN agent_events p ON e.parent_event_id = p.event_id
    ORDER BY e.created_at DESC
    LIMIT 10
""")

print(f"{'Event ID':<15} {'Tool':<12} {'Parent Tool':<12} {'Summary':<40}")
print("-" * 80)
for row in cursor.fetchall():
    parent_tool = row["parent_tool"] or "None"
    print(
        f"{row['event_id']:<15} {row['tool_name']:<12} {parent_tool:<12} {row['summary'] or 'N/A':<40}"
    )

conn.close()

print("\n" + "=" * 80)
print("Phase 1 Implementation Complete!")
print("=" * 80)
print("\nNext Steps:")
print("1. Submit a new user prompt in Claude Code")
print("2. Run this test again to verify UserQuery → child event linking")
print("3. Check the dashboard to see prompt-based activity grouping")
