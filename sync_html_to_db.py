#!/usr/bin/env python3
"""
Sync HTML data (features, bugs, spikes, tracks) into SQLite database.

This script scans .htmlgraph/features/, bugs/, spikes/ directories and populates
the SQLite database with the extracted metadata. It also syncs graph edges and
track relationships.
"""

import logging
import sqlite3
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Add src to path for htmlgraph imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src" / "python"))

from htmlgraph.db.edge_sync import sync_html_edges_to_sqlite
from htmlgraph.db.schema import HtmlGraphDB
from htmlgraph.parser import HtmlParser


def count_nodes(db_path: Path) -> dict:
    """Count nodes in each table before sync."""
    if not db_path.exists():
        return {"features": 0, "graph_edges": 0}

    conn = sqlite3.connect(db_path)
    counts = {}
    try:
        for table in ["features", "graph_edges"]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                counts[table] = count
            except sqlite3.OperationalError:
                counts[table] = 0
    finally:
        conn.close()
    return counts


def sync_html_features_to_sqlite(graph_dir: Path, db: HtmlGraphDB) -> int:
    """
    Scan all HTML node files and upsert into the features table.

    Handles features/, bugs/, spikes/ subdirectories.
    Extracts title, status, priority, track_id, steps info from HTML.

    Returns: Number of nodes synced
    """
    synced = 0
    subdirs = ["features", "bugs", "spikes"]

    for subdir in subdirs:
        subdir_path = graph_dir / subdir
        if not subdir_path.is_dir():
            logger.warning(f"Directory not found: {subdir_path}")
            continue

        html_files = list(subdir_path.glob("*.html"))
        logger.info(f"Found {len(html_files)} HTML files in {subdir}/")

        for html_file in html_files:
            try:
                parser = HtmlParser.from_file(html_file)
                node_id = parser.get_node_id()
                if not node_id:
                    logger.debug(f"Skipping {html_file.name}: no node_id found")
                    continue

                # Extract all metadata from article
                metadata = parser.get_node_metadata()
                if not metadata:
                    continue

                # Get basic info
                node_type = metadata.get("type", "feature")
                title = parser.get_title() or node_id
                status = metadata.get("status", "todo")
                priority = metadata.get("priority", "medium")
                track_id = metadata.get("track_id")

                # Count steps
                steps = parser.get_steps()
                steps_total = len(steps) if steps else 0

                # Insert into features table
                success = db.insert_feature(
                    feature_id=node_id,
                    feature_type=node_type,
                    title=title,
                    status=status,
                    priority=priority,
                    track_id=track_id,
                    steps_total=steps_total,
                )
                if success:
                    synced += 1

            except Exception as e:
                logger.debug(f"Error syncing {html_file.name}: {e}")
                continue

    logger.info(f"Synced {synced} nodes to features table")
    return synced


def main():
    """Main sync workflow."""
    db_path = project_root / ".htmlgraph" / "htmlgraph.db"
    graph_dir = project_root / ".htmlgraph"

    # Ensure graph_dir exists
    graph_dir.mkdir(parents=True, exist_ok=True)

    # Show before counts
    logger.info("=" * 60)
    logger.info("BEFORE SYNC")
    before = count_nodes(db_path)
    for table, count in before.items():
        logger.info(f"  {table}: {count} rows")

    # Connect to database with WAL
    db = HtmlGraphDB(db_path)
    db.connect()

    try:
        # Disable FK constraints during sync (we'll re-enable after)
        if db.connection:
            db.connection.execute("PRAGMA foreign_keys=OFF")  # type: ignore[union-attr]

        # Step 1: Sync HTML features to SQLite
        logger.info("=" * 60)
        logger.info("STEP 1: Syncing HTML features to SQLite")
        _ = sync_html_features_to_sqlite(graph_dir, db)

        # Step 2: Sync HTML edges to SQLite
        logger.info("=" * 60)
        logger.info("STEP 2: Syncing HTML graph edges to SQLite")
        _ = sync_html_edges_to_sqlite(graph_dir, db)

        # Re-enable FK constraints
        if db.connection:
            db.connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[union-attr]

        # Show after counts
        logger.info("=" * 60)
        logger.info("AFTER SYNC")
        after = count_nodes(db_path)
        for table, count in after.items():
            delta = count - before[table]
            sign = "+" if delta >= 0 else ""
            logger.info(f"  {table}: {count} rows ({sign}{delta})")

        logger.info("=" * 60)
        logger.info("Sync complete!")
        return 0

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
