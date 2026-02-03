#!/usr/bin/env python3
"""
Backfill tracks from HTML files into SQLite database.

This script:
1. Scans .htmlgraph/tracks/ for track HTML files
2. Parses track metadata (title, description, priority, status)
3. Inserts tracks into the tracks table
4. Preserves created_at timestamps from file metadata

Usage:
    uv run python scripts/backfill_tracks.py
    uv run python scripts/backfill_tracks.py --dry-run  # Preview only
    uv run python scripts/backfill_tracks.py --track trk-28178b71  # Single track
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from htmlgraph.sdk import SDK


def extract_track_metadata(html_content: str, track_file: Path) -> dict[str, Any]:
    """
    Extract track metadata from HTML content.

    Returns dict with:
    - track_id: Track ID (trk-xxxxx)
    - title: Track title from <h1>
    - description: Track description from first section
    - priority: Priority level (low, medium, high, critical)
    - status: Track status (todo, in_progress, blocked, done, cancelled)
    - created_at: File creation timestamp
    """
    # Extract track ID from article tag
    track_id_match = re.search(r'id="(trk-[a-f0-9]+)"', html_content)
    if not track_id_match:
        raise ValueError(f"No track ID found in {track_file}")
    track_id = track_id_match.group(1)

    # Extract title from <h1> tag
    title_match = re.search(r"<h1>(.*?)</h1>", html_content, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Unknown Track"

    # Extract description from first section
    desc_match = re.search(
        r'<section data-section="description">\s*<p>(.*?)</p>',
        html_content,
        re.DOTALL,
    )
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract priority from article data attribute
    priority_match = re.search(r'data-priority="(\w+)"', html_content)
    priority = priority_match.group(1) if priority_match else "medium"

    # Validate priority
    if priority not in ["low", "medium", "high", "critical"]:
        print(f"   ⚠️  Invalid priority '{priority}', defaulting to 'medium'")
        priority = "medium"

    # Extract status from article data attribute
    status_match = re.search(r'data-status="(\w+)"', html_content)
    status = status_match.group(1) if status_match else "todo"

    # Validate status
    if status not in ["todo", "in_progress", "blocked", "done", "cancelled"]:
        print(f"   ⚠️  Invalid status '{status}', defaulting to 'todo'")
        status = "todo"

    # Extract created_at from badge (fallback to file mtime)
    created_match = re.search(
        r'<span class="badge">Created: ([\d-]+)</span>',
        html_content,
    )
    if created_match:
        created_at = datetime.strptime(created_match.group(1), "%Y-%m-%d")
    else:
        # Fallback to file modification time
        created_at = datetime.fromtimestamp(track_file.stat().st_mtime)

    return {
        "track_id": track_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "created_at": created_at,
    }


def backfill_track(track_file: Path, sdk: SDK, dry_run: bool = False) -> bool:
    """
    Backfill a single track from HTML file to database.

    Returns:
        True if track was inserted, False if skipped
    """
    html_content = track_file.read_text(encoding="utf-8")

    try:
        metadata = extract_track_metadata(html_content, track_file)
    except ValueError as e:
        print(f"❌ Error parsing {track_file.name}: {e}")
        return False

    track_id = metadata["track_id"]
    title = metadata["title"]
    priority = metadata["priority"]
    status = metadata["status"]
    created_at = metadata["created_at"]

    print(f"\n📋 {track_id} - {title}")
    print(f"   Priority: {priority}, Status: {status}, Created: {created_at.date()}")

    if dry_run:
        return True

    # Check if track already exists
    if sdk._db.connection:
        cursor = sdk._db.connection.cursor()
        cursor.execute("SELECT track_id FROM tracks WHERE track_id = ?", (track_id,))
        if cursor.fetchone():
            print("   ⏭️  Already exists, skipping")
            return False

        # Insert track record
        try:
            cursor.execute(
                """
                INSERT INTO tracks (
                    track_id, title, description, priority, status,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    track_id,
                    title,
                    metadata["description"],
                    priority,
                    status,
                    created_at.isoformat(),
                    created_at.isoformat(),  # updated_at = created_at initially
                ),
            )
            sdk._db.connection.commit()
            print("   ✅ Inserted into database")
            return True
        except Exception as e:
            print(f"   ❌ Error inserting: {e}")
            return False

    return False


def main() -> None:
    """Main backfill entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backfill tracks from HTML files to database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be migrated without writing to database",
    )
    parser.add_argument(
        "--track", type=str, help="Backfill only a specific track (e.g., trk-28178b71)"
    )

    args = parser.parse_args()

    # Initialize SDK with project directory
    project_dir = Path.cwd()
    htmlgraph_dir = project_dir / ".htmlgraph"

    if not htmlgraph_dir.exists():
        print(f"❌ No .htmlgraph directory found in {project_dir}")
        sys.exit(1)

    db_path = htmlgraph_dir / "htmlgraph.db"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    sdk = SDK(
        agent="backfill-tracks", directory=str(htmlgraph_dir), db_path=str(db_path)
    )
    print(f"📂 Using database: {sdk._db.db_path}")

    # Find track HTML files
    tracks_dir = sdk._directory / "tracks"
    if not tracks_dir.exists():
        print("❌ No tracks directory found")
        sys.exit(1)

    if args.track:
        # Backfill single track
        track_file = tracks_dir / f"{args.track}.html"
        if not track_file.exists():
            print(f"❌ Track file not found: {track_file}")
            sys.exit(1)
        track_files = [track_file]
    else:
        # Backfill all tracks
        track_files = sorted(tracks_dir.glob("trk-*.html"))

    print(f"\n🔄 Backfilling {len(track_files)} track(s)...")
    if args.dry_run:
        print("   (DRY RUN - no changes will be made)")

    tracks_inserted = 0
    tracks_skipped = 0

    for track_file in track_files:
        if backfill_track(track_file, sdk, dry_run=args.dry_run):
            tracks_inserted += 1
        else:
            tracks_skipped += 1

    print("\n" + "=" * 60)
    print("✅ Backfill complete!")
    print(f"   Tracks inserted: {tracks_inserted}")
    print(f"   Tracks skipped: {tracks_skipped}")
    print(f"   Total tracks processed: {len(track_files)}")

    if not args.dry_run and tracks_inserted > 0:
        print("\n💡 Verify tracks in database:")
        print("   sqlite3 .htmlgraph/htmlgraph.db 'SELECT COUNT(*) FROM tracks;'")
        print(
            "   sqlite3 .htmlgraph/htmlgraph.db 'SELECT track_id, title, status FROM tracks LIMIT 5;'"
        )


if __name__ == "__main__":
    main()
