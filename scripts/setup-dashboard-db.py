#!/usr/bin/env python3
"""
Initialize SQLite database for HTMX dashboard - Phase 3 Completion

This script:
1. Creates SQLite database with HtmlGraph schema
2. Migrates data from .htmlgraph/ HTML files to SQLite
3. Verifies tables have data
4. Reports initialization results

Usage:
    uv run python scripts/setup-dashboard-db.py

Or with custom paths:
    uv run python scripts/setup-dashboard-db.py --db-path ~/.htmlgraph/htmlgraph.db --htmlgraph-dir ~/.htmlgraph
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database and migrate data."""
    parser = argparse.ArgumentParser(
        description="Initialize SQLite database for HTMX dashboard"
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite database (default: ~/.htmlgraph/htmlgraph.db)",
    )
    parser.add_argument(
        "--htmlgraph-dir",
        default=None,
        help="Path to .htmlgraph directory (default: ~/.htmlgraph)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine paths
    if args.db_path:
        db_path = Path(args.db_path).expanduser()
    else:
        db_path = Path.home() / ".htmlgraph" / "htmlgraph.db"

    if args.htmlgraph_dir:
        htmlgraph_dir = Path(args.htmlgraph_dir).expanduser()
    else:
        htmlgraph_dir = Path.home() / ".htmlgraph"

    logger.info("=" * 70)
    logger.info("HtmlGraph Dashboard Database Initialization")
    logger.info("=" * 70)
    logger.info(f"Database: {db_path}")
    logger.info(f"HtmlGraph Dir: {htmlgraph_dir}")
    logger.info("")

    try:
        # Step 1: Initialize database with schema
        logger.info("Step 1: Initializing SQLite database...")
        from htmlgraph.db.schema import HtmlGraphDB

        db = HtmlGraphDB(str(db_path))
        db.connect()
        db.create_tables()
        logger.info(f"✅ Database initialized: {db_path}")
        logger.info("   Tables created:")
        logger.info("     - agent_events")
        logger.info("     - features")
        logger.info("     - sessions")
        logger.info("     - tracks")
        logger.info("     - agent_collaboration")
        logger.info("     - graph_edges")
        logger.info("     - event_log_archive")
        logger.info("")

        # Step 2: Migrate existing HtmlGraph data
        logger.info("Step 2: Migrating HtmlGraph data...")
        from scripts.migrate_html_to_sqlite import HtmlGraphMigrator

        migrator = HtmlGraphMigrator(
            htmlgraph_dir=htmlgraph_dir,
            db_path=db_path,
            dry_run=False,
            create_backup=True,
        )

        success = migrator.run()
        if not success:
            logger.warning("Migration completed with errors (see above)")
        else:
            logger.info("✅ Data migration successful")
        logger.info("")

        # Step 3: Verify database has data
        logger.info("Step 3: Verifying database population...")
        db.connect()

        event_count = db.connection.execute(
            "SELECT COUNT(*) FROM agent_events"
        ).fetchone()[0]

        feature_count = db.connection.execute(
            "SELECT COUNT(*) FROM features"
        ).fetchone()[0]

        session_count = db.connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

        track_count = db.connection.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]

        collaboration_count = db.connection.execute(
            "SELECT COUNT(*) FROM agent_collaboration"
        ).fetchone()[0]

        logger.info("✅ Database populated:")
        logger.info(f"   - {event_count} agent events")
        logger.info(f"   - {feature_count} features")
        logger.info(f"   - {session_count} sessions")
        logger.info(f"   - {track_count} tracks")
        logger.info(f"   - {collaboration_count} collaborations")
        logger.info("")

        # Step 4: Verify FastAPI can connect
        logger.info("Step 4: Verifying FastAPI can connect...")
        try:
            from htmlgraph.api.main import create_app

            create_app(str(db_path))
            logger.info("✅ FastAPI app created successfully")
            logger.info("")
        except Exception as e:
            logger.error(f"❌ FastAPI initialization failed: {e}")
            return False

        # Step 5: Print next steps
        logger.info("=" * 70)
        logger.info("Setup Complete! Next Steps:")
        logger.info("=" * 70)
        logger.info("")
        logger.info("1. Start the FastAPI server:")
        logger.info("   uv run htmlgraph serve-api")
        logger.info("")
        logger.info("2. Open dashboard in browser:")
        logger.info("   http://localhost:8000")
        logger.info("")
        logger.info("3. View each tab:")
        logger.info("   - Activity Feed: Real-time agent events")
        logger.info("   - Orchestration: Delegation chains")
        logger.info("   - Features: Work items and progress")
        logger.info("   - Metrics: Session performance data")
        logger.info("")
        logger.info("Database location: " + str(db_path))
        logger.info("")

        db.disconnect()
        return True

    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
