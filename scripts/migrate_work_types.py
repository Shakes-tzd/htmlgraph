#!/usr/bin/env python3
"""
Migration script for Phase 1: Work Type Classification.

This script:
1. Adds work_type to existing events based on feature_id inference
2. Calculates work_breakdown for existing sessions
3. Calculates primary_work_type for existing sessions

Usage:
    uv run python scripts/migrate_work_types.py

Options:
    --dry-run    Show what would be migrated without making changes
    --events-dir Path to events directory (default: .htmlgraph/events)
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

from htmlgraph.work_type_utils import infer_work_type_from_id


def migrate_events(events_dir: Path, dry_run: bool = False) -> dict:
    """
    Add work_type to existing events based on feature_id.

    Returns:
        Statistics about the migration
    """
    stats = {
        "total_events": 0,
        "updated_events": 0,
        "already_typed": 0,
        "inferred_types": {},
        "sessions_processed": 0
    }

    # Process all JSONL files in events directory
    for jsonl_file in events_dir.glob("*.jsonl"):
        stats["sessions_processed"] += 1

        # Read all events from file
        events = []
        with jsonl_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    stats["total_events"] += 1

                    # Check if already has work_type
                    if event.get("work_type"):
                        stats["already_typed"] += 1
                        events.append(event)
                        continue

                    # Infer work_type from feature_id
                    feature_id = event.get("feature_id")
                    if feature_id:
                        work_type = infer_work_type_from_id(feature_id)
                        if work_type:
                            event["work_type"] = work_type
                            stats["updated_events"] += 1
                            stats["inferred_types"][work_type] = stats["inferred_types"].get(work_type, 0) + 1

                    events.append(event)

                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

        # Write back to file if not dry run
        if not dry_run and stats["updated_events"] > 0:
            # Create backup first
            backup_file = jsonl_file.with_suffix(".jsonl.bak")
            jsonl_file.rename(backup_file)

            # Write updated events
            with jsonl_file.open("w", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

            print(f"✓ Migrated {jsonl_file.name}")

    return stats


def migrate_sessions(dry_run: bool = False) -> dict:
    """
    Calculate work_breakdown and primary_work_type for existing sessions.

    Returns:
        Statistics about the migration
    """
    from htmlgraph import SDK
    from htmlgraph.converter import html_to_session, session_to_html

    sdk = SDK()
    sessions_dir = Path(".htmlgraph/sessions")

    stats = {
        "total_sessions": 0,
        "updated_sessions": 0,
        "sessions_with_breakdown": {}
    }

    if not sessions_dir.exists():
        return stats

    # Process all session HTML files
    for session_file in sessions_dir.glob("*.html"):
        stats["total_sessions"] += 1

        try:
            # Read session from HTML
            session = html_to_session(session_file)

            # Check if already has work_breakdown
            if session.work_breakdown:
                continue

            # Calculate work breakdown
            breakdown = session.calculate_work_breakdown()
            if breakdown:
                primary = session.calculate_primary_work_type()

                # Update session
                session.work_breakdown = breakdown
                session.primary_work_type = primary

                stats["updated_sessions"] += 1
                stats["sessions_with_breakdown"][session.id] = {
                    "primary": primary,
                    "breakdown": breakdown
                }

                # Write back to file if not dry run
                if not dry_run:
                    html = session_to_html(session)
                    session_file.write_text(html, encoding="utf-8")
                    print(f"✓ Updated session {session.id}")

        except Exception as e:
            print(f"⚠ Error processing {session_file.name}: {e}")
            continue

    return stats


def main():
    parser = argparse.ArgumentParser(description="Migrate existing data to Phase 1 work type classification")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--events-dir", default=".htmlgraph/events", help="Path to events directory")
    args = parser.parse_args()

    events_dir = Path(args.events_dir)

    if not events_dir.exists():
        print(f"❌ Events directory not found: {events_dir}")
        return 1

    print("🚀 Starting Phase 1 Work Type Classification Migration")
    print(f"   Events directory: {events_dir}")
    print(f"   Dry run: {args.dry_run}")
    print()

    # Migrate events
    print("📝 Migrating events...")
    event_stats = migrate_events(events_dir, dry_run=args.dry_run)

    print()
    print("Event Migration Results:")
    print(f"  Total events processed: {event_stats['total_events']}")
    print(f"  Events updated: {event_stats['updated_events']}")
    print(f"  Already typed: {event_stats['already_typed']}")
    print(f"  Sessions processed: {event_stats['sessions_processed']}")

    if event_stats['inferred_types']:
        print()
        print("  Inferred work types:")
        for work_type, count in event_stats['inferred_types'].items():
            print(f"    {work_type}: {count}")

    # Migrate sessions
    print()
    print("📊 Migrating sessions...")
    session_stats = migrate_sessions(dry_run=args.dry_run)

    print()
    print("Session Migration Results:")
    print(f"  Total sessions: {session_stats['total_sessions']}")
    print(f"  Sessions updated: {session_stats['updated_sessions']}")

    if session_stats['sessions_with_breakdown']:
        print()
        print("  Session work breakdowns:")
        for session_id, data in list(session_stats['sessions_with_breakdown'].items())[:5]:
            print(f"    {session_id}:")
            print(f"      Primary: {data['primary']}")
            print(f"      Breakdown: {data['breakdown']}")

        if len(session_stats['sessions_with_breakdown']) > 5:
            remaining = len(session_stats['sessions_with_breakdown']) - 5
            print(f"    ... and {remaining} more sessions")

    print()
    if args.dry_run:
        print("🔍 Dry run complete. No changes were made.")
        print("   Run without --dry-run to apply changes.")
    else:
        print("✅ Migration complete!")
        print(f"   Updated {event_stats['updated_events']} events")
        print(f"   Updated {session_stats['updated_sessions']} sessions")

    return 0


if __name__ == "__main__":
    exit(main())
