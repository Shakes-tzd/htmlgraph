#!/usr/bin/env python3
"""Verification script for spawner internal activity tracking.

This script tests the spawner event tracking implementation by:
1. Checking that delegation events exist
2. Verifying that child events are properly linked to parent delegation events
3. Displaying the event hierarchy
4. Providing statistics on tracked activities
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src" / "python"))


def verify_spawner_tracking():
    """Verify spawner internal activity tracking in database."""
    try:
        from htmlgraph.db.schema import HtmlGraphDB

        db = HtmlGraphDB()

        print("\n=== SPAWNER EVENT TRACKING VERIFICATION ===\n")

        # 1. Get all delegation events
        print("1. DELEGATION EVENTS (Parent Events)")
        print("-" * 80)

        cursor = db.connection.cursor()
        cursor.execute(
            """
            SELECT event_id, agent_id, event_type, tool_name, input_summary,
                   status, execution_duration_seconds, cost_tokens, created_at
            FROM agent_events
            WHERE event_type = 'delegation'
            ORDER BY created_at DESC
            LIMIT 20
        """
        )

        delegation_events = cursor.fetchall()
        if not delegation_events:
            print("No delegation events found in database.\n")
            return False

        delegation_map = {}
        for row in delegation_events:
            event_id = row[0]
            delegation_map[event_id] = dict(row)
            print(f"Event ID: {event_id}")
            print(f"  Agent: {row[1]}")
            print(f"  Type: {row[2]}")
            print(f"  Tool: {row[3]}")
            print(f"  Input: {row[4][:100] if row[4] else 'N/A'}...")
            print(f"  Status: {row[5]}")
            print(f"  Duration: {row[6]:.2f}s" if row[6] else "  Duration: N/A")
            print(f"  Tokens: {row[7]}")
            print()

        # 2. Get child events linked to delegation events
        print("\n2. CHILD EVENTS (Linked to Delegation Events)")
        print("-" * 80)

        for delegation_id in delegation_map.keys():
            cursor.execute(
                """
                SELECT event_id, agent_id, event_type, tool_name, input_summary,
                       status, execution_duration_seconds, parent_event_id, created_at
                FROM agent_events
                WHERE parent_event_id = ?
                ORDER BY created_at ASC
            """,
                (delegation_id,),
            )

            child_events = cursor.fetchall()
            if child_events:
                print(f"\nDelegation Event: {delegation_id}")
                print(f"  Child Events: {len(child_events)}")
                for i, child_row in enumerate(child_events, 1):
                    print(f"\n  [{i}] Event ID: {child_row[0]}")
                    print(f"      Agent: {child_row[1]}")
                    print(f"      Type: {child_row[2]}")
                    print(f"      Tool: {child_row[3]}")
                    print(
                        f"      Input: {child_row[4][:80] if child_row[4] else 'N/A'}..."
                    )
                    print(f"      Status: {child_row[5]}")
                    print(
                        f"      Duration: {child_row[6]:.2f}s"
                        if child_row[6]
                        else "      Duration: N/A"
                    )
                    print(f"      Parent: {child_row[7]}")

        # 3. Event hierarchy summary
        print("\n\n3. EVENT HIERARCHY SUMMARY")
        print("-" * 80)

        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT CASE WHEN event_type = 'delegation' THEN event_id END) as delegation_count,
                COUNT(DISTINCT CASE WHEN parent_event_id IS NOT NULL THEN event_id END) as child_event_count,
                COUNT(*) as total_events
            FROM agent_events
            WHERE event_type IN ('delegation', 'tool_use')
        """
        )

        stats = cursor.fetchone()
        if stats:
            print(f"Total Delegation Events: {stats[0]}")
            print(f"Total Child Events: {stats[1]}")
            print(f"Total Events (Delegations + Children): {stats[2]}")

        # 4. Spawner-specific breakdown
        print("\n\n4. SPAWNER BREAKDOWN")
        print("-" * 80)

        cursor.execute(
            """
            SELECT
                json_extract(context, '$.spawner_type') as spawner_type,
                COUNT(*) as count
            FROM agent_events
            WHERE event_type = 'delegation' AND json_extract(context, '$.spawner_type') IS NOT NULL
            GROUP BY spawner_type
            ORDER BY count DESC
        """
        )

        spawner_stats = cursor.fetchall()
        if spawner_stats:
            for spawner_type, count in spawner_stats:
                print(f"{spawner_type}: {count} delegation event(s)")

        # 5. Parent-child linking verification
        print("\n\n5. PARENT-CHILD LINKING VERIFICATION")
        print("-" * 80)

        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT parent_event_id) as delegations_with_children,
                COUNT(*) as total_child_events
            FROM agent_events
            WHERE parent_event_id IS NOT NULL
        """
        )

        link_stats = cursor.fetchone()
        if link_stats:
            delegations_with_children = link_stats[0]
            total_child_events = link_stats[1]
            print(f"Delegation events with child events: {delegations_with_children}")
            print(f"Total child events linked: {total_child_events}")
            if delegations_with_children > 0:
                print(
                    f"Average children per delegation: {total_child_events / delegations_with_children:.1f}"
                )

        # 6. Recent activity (last 10 events)
        print("\n\n6. RECENT ACTIVITY (Last 10 Events)")
        print("-" * 80)

        cursor.execute(
            """
            SELECT event_id, agent_id, event_type, tool_name, status,
                   parent_event_id, created_at
            FROM agent_events
            ORDER BY created_at DESC
            LIMIT 10
        """
        )

        recent = cursor.fetchall()
        for i, row in enumerate(recent, 1):
            print(f"{i}. {row[0]}")
            print(f"   Agent: {row[1]}, Type: {row[2]}, Tool: {row[3]}")
            print(f"   Status: {row[4]}, Parent: {row[5] or 'None'}")

        print("\n\n=== VERIFICATION COMPLETE ===\n")
        return True

    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_spawner_tracking()
    sys.exit(0 if success else 1)
