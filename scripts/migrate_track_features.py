#!/usr/bin/env python3
"""
Migration script to populate features table from existing track HTML files.

This script:
1. Scans .htmlgraph/tracks/ for track HTML files
2. Parses task data from HTML (data-task attributes)
3. Inserts features into the database
4. Links features to their parent track

Usage:
    uv run python scripts/migrate_track_features.py
    uv run python scripts/migrate_track_features.py --dry-run  # Preview only
    uv run python scripts/migrate_track_features.py --track trk-28178b71  # Single track
"""

import re
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from htmlgraph.ids import generate_id
from htmlgraph.sdk import SDK


def extract_track_metadata(html_content: str) -> dict[str, str]:
    """Extract track ID, priority, and status from HTML."""
    # Extract track ID from article tag
    track_id_match = re.search(r'id="(trk-[a-f0-9]+)"', html_content)
    track_id = track_id_match.group(1) if track_id_match else "unknown"

    # Extract priority from article data attribute
    priority_match = re.search(r'data-priority="(\w+)"', html_content)
    priority = priority_match.group(1) if priority_match else "medium"

    # Extract status from article data attribute
    status_match = re.search(r'data-status="(\w+)"', html_content)
    status = status_match.group(1) if status_match else "todo"

    return {"id": track_id, "priority": priority, "status": status}


def extract_tasks_from_html(html_content: str) -> list[dict[str, Any]]:
    """
    Parse task data from track HTML.

    Returns list of task dictionaries with:
    - task_id: Original task ID from HTML (task-1-1, task-2-3, etc.)
    - title: Task description
    - status: Task status (todo, in_progress, done, etc.)
    - phase: Phase name (extracted from details summary)
    """
    tasks = []

    # Find all details blocks (phases)
    phase_blocks = re.findall(
        r'<details[^>]*data-phase="([^"]*)"[^>]*>(.*?)</details>',
        html_content,
        re.DOTALL,
    )

    for phase_id, phase_content in phase_blocks:
        # Extract phase name from summary tag
        phase_name_match = re.search(
            r"<summary>([^<]+)</summary>", phase_content, re.DOTALL
        )
        phase_name = (
            phase_name_match.group(1).strip() if phase_name_match else "Unknown Phase"
        )

        # Find all tasks within this phase
        # Updated regex to match tasks more reliably
        task_blocks = re.findall(
            r'<div data-task="([^"]+)" data-status="([^"]+)"[^>]*>(.*?)(?=<div data-task|</details>)',
            phase_content,
            re.DOTALL,
        )

        for task_id, task_status, task_content in task_blocks:
            # Extract task title from <strong> tag
            title_match = re.search(r"<strong>(.*?)</strong>", task_content, re.DOTALL)
            if title_match:
                # Clean up title (remove checkboxes, status indicators)
                title = title_match.group(1).strip()
                title = re.sub(r"^[○●✓✅⬜]+\s*", "", title)  # Remove status symbols
                title = re.sub(
                    r"\s*\(COMPLETED\)\s*$", "", title
                )  # Remove COMPLETED marker

                tasks.append(
                    {
                        "task_id": task_id,
                        "title": title,
                        "status": task_status,
                        "phase": phase_name,
                    }
                )

    return tasks


def migrate_track_features(
    track_file: Path, sdk: SDK, dry_run: bool = False
) -> tuple[int, int]:
    """
    Migrate features from a single track HTML file to database.

    Returns:
        (features_created, features_skipped) tuple
    """
    html_content = track_file.read_text(encoding="utf-8")

    # Extract track metadata
    track_meta = extract_track_metadata(html_content)
    track_id = track_meta["id"]
    priority = track_meta["priority"]
    status = track_meta["status"]

    # Extract track title from <h1> tag
    title_match = re.search(r"<h1>(.*?)</h1>", html_content, re.DOTALL)
    track_title = title_match.group(1).strip() if title_match else "Unknown Track"

    # Extract track description from first section
    desc_match = re.search(
        r'<section data-section="description">\s*<p>(.*?)</p>',
        html_content,
        re.DOTALL,
    )
    track_desc = desc_match.group(1).strip() if desc_match else ""

    print(f"\n📋 Processing track: {track_id} - {track_title}")
    print(f"   Priority: {priority}, Status: {status}")

    # Insert track record if it doesn't exist (to satisfy FOREIGN KEY constraint)
    if not dry_run and sdk._db.connection:
        cursor = sdk._db.connection.cursor()
        cursor.execute("SELECT track_id FROM tracks WHERE track_id = ?", (track_id,))
        if not cursor.fetchone():
            # Insert track record
            cursor.execute(
                """
                INSERT INTO tracks (track_id, title, description, priority, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (track_id, track_title, track_desc, priority, status),
            )
            sdk._db.connection.commit()
            print("   ✓ Created track record in database")

    # Extract tasks
    tasks = extract_tasks_from_html(html_content)
    print(f"   Found {len(tasks)} tasks")

    if dry_run:
        for task in tasks:
            print(
                f"   - [{task['status']}] {task['title'][:60]}... (from {task['phase']})"
            )
        return (0, 0)

    # Insert features into database
    features_created = 0
    features_skipped = 0

    for task in tasks:
        # Generate feature ID from task title
        feature_id = generate_id(node_type="feat", title=task["title"])

        # Check if feature already exists
        if sdk._db.connection:
            cursor = sdk._db.connection.cursor()
            cursor.execute("SELECT id FROM features WHERE id = ?", (feature_id,))
            if cursor.fetchone():
                features_skipped += 1
                continue

        # Insert feature
        success = sdk._db.insert_feature(
            feature_id=feature_id,
            feature_type="task",
            title=task["title"],
            status=task["status"],
            priority=priority,
            assigned_to=None,
            track_id=track_id,
            description=f"Task from {task['phase']}",
            steps_total=0,
            tags=None,
        )

        if success:
            features_created += 1
        else:
            features_skipped += 1

    # Ensure all changes are committed
    if sdk._db.connection:
        sdk._db.connection.commit()

    print(
        f"   ✓ Created {features_created} features, skipped {features_skipped} (already exist)"
    )
    return (features_created, features_skipped)


def main() -> None:
    """Main migration entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate features from track HTML files to database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be migrated without writing to database",
    )
    parser.add_argument(
        "--track", type=str, help="Migrate only a specific track (e.g., trk-28178b71)"
    )

    args = parser.parse_args()

    # Initialize SDK with project directory
    # Auto-discover .htmlgraph in current working directory
    project_dir = Path.cwd()
    htmlgraph_dir = project_dir / ".htmlgraph"

    if not htmlgraph_dir.exists():
        print(f"❌ No .htmlgraph directory found in {project_dir}")
        return

    db_path = htmlgraph_dir / "htmlgraph.db"
    sdk = SDK(
        agent="migration-script", directory=str(htmlgraph_dir), db_path=str(db_path)
    )
    print(f"📂 Using database: {sdk._db.db_path}")

    # Find track HTML files
    tracks_dir = sdk._directory / "tracks"
    if not tracks_dir.exists():
        print("❌ No tracks directory found")
        return

    if args.track:
        # Migrate single track
        track_file = tracks_dir / f"{args.track}.html"
        if not track_file.exists():
            print(f"❌ Track file not found: {track_file}")
            return
        track_files = [track_file]
    else:
        # Migrate all tracks
        track_files = list(tracks_dir.glob("trk-*.html"))

    print(f"🔄 Migrating {len(track_files)} track(s)...")
    if args.dry_run:
        print("   (DRY RUN - no changes will be made)")

    total_created = 0
    total_skipped = 0

    for track_file in track_files:
        created, skipped = migrate_track_features(track_file, sdk, dry_run=args.dry_run)
        total_created += created
        total_skipped += skipped

    print("\n✅ Migration complete!")
    print(f"   Total features created: {total_created}")
    print(f"   Total features skipped: {total_skipped}")

    if not args.dry_run:
        print("\n💡 Verify features in database:")
        print("   sqlite3 .htmlgraph/htmlgraph.db 'SELECT COUNT(*) FROM features;'")
        print(
            "   sqlite3 .htmlgraph/htmlgraph.db 'SELECT id, title, status FROM features LIMIT 5;'"
        )


if __name__ == "__main__":
    main()
