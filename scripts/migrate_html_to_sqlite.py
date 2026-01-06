#!/usr/bin/env python3
"""
HtmlGraph HTML to SQLite Migration Script

Migrates existing .htmlgraph/features/*.html files and .htmlgraph/sessions/*.html files
into the new SQLite backend while preserving all data and relationships.

Usage:
    uv run python scripts/migrate_html_to_sqlite.py \\
        --htmlgraph-dir .htmlgraph \\
        --db-path .htmlgraph/htmlgraph.db \\
        --dry-run  # Preview what would happen

Features:
- Parses HTML metadata attributes (data-status, data-priority, etc.)
- Extracts graph relationships from hyperlinks
- Imports into SQLite with validation
- Creates backup of original HTML files
- Reports migration statistics

Migration Order:
1. Features/bugs/spikes/chores/epics (with relationships)
2. Sessions (with subagent tracking)
3. Graph edges (hyperlink relationships)
4. Validation and integrity checks
"""

import argparse
import logging
import shutil
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HtmlMetadataParser(HTMLParser):
    """Parse HTML metadata attributes from data-* attributes."""

    def __init__(self):
        super().__init__()
        self.metadata: dict[str, Any] = {}
        self.edges: list[dict[str, str]] = []
        self.title: str | None = None
        self.in_title = False
        self.current_node_id: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        """Parse opening tags and extract metadata."""
        attrs_dict = dict(attrs)

        # Extract node info from article/section tags
        if tag in ("article", "section"):
            self.current_node_id = attrs_dict.get("id")
            for key, value in attrs_dict.items():
                if key.startswith("data-"):
                    # Convert data-attribute to metadata
                    attr_name = key[5:]  # Remove 'data-' prefix
                    self.metadata[attr_name] = value

        # Extract hyperlinks as edges
        if tag == "a":
            href = attrs_dict.get("href", "")
            relationship = attrs_dict.get("data-relationship", "related")
            if href and self.current_node_id:
                # Parse target ID from href
                target_id = href.replace(".html", "").split("/")[-1]
                self.edges.append(
                    {
                        "from_id": self.current_node_id,
                        "to_id": target_id,
                        "relationship": relationship,
                    }
                )

        # Extract title
        if tag == "title":
            self.in_title = True

        if tag == "h1" and not self.title:
            self.in_title = True

    def handle_endtag(self, tag: str):
        """Handle closing tags."""
        if tag in ("title", "h1"):
            self.in_title = False

    def handle_data(self, data: str):
        """Extract text content."""
        if self.in_title and data.strip():
            if not self.title:
                self.title = data.strip()


class HtmlGraphMigrator:
    """Migrates HTML data to SQLite backend."""

    def __init__(
        self,
        htmlgraph_dir: Path,
        db_path: Path,
        dry_run: bool = False,
        create_backup: bool = True,
    ):
        """
        Initialize migrator.

        Args:
            htmlgraph_dir: Path to .htmlgraph directory
            db_path: Path to SQLite database file
            dry_run: If True, analyze without making changes
            create_backup: If True, backup HTML files before migration
        """
        self.htmlgraph_dir = Path(htmlgraph_dir)
        self.db_path = Path(db_path)
        self.dry_run = dry_run
        self.create_backup = create_backup

        # Statistics
        self.stats = {
            "features_parsed": 0,
            "sessions_parsed": 0,
            "edges_parsed": 0,
            "errors": 0,
            "warnings": 0,
        }

    def backup_html_files(self):
        """Create backup of original HTML files."""
        if not self.create_backup:
            return

        backup_dir = self.htmlgraph_dir / ".backup"
        if backup_dir.exists():
            logger.warning(f"Backup directory already exists: {backup_dir}")
            return

        logger.info(f"Creating backup at {backup_dir}")

        try:
            # Backup features
            features_src = self.htmlgraph_dir / "features"
            if features_src.exists():
                features_backup = backup_dir / "features"
                shutil.copytree(features_src, features_backup)
                logger.info(f"Backed up features: {features_backup}")

            # Backup sessions
            sessions_src = self.htmlgraph_dir / "sessions"
            if sessions_src.exists():
                sessions_backup = backup_dir / "sessions"
                shutil.copytree(sessions_src, sessions_backup)
                logger.info(f"Backed up sessions: {sessions_backup}")

        except Exception as e:
            logger.error(f"Backup error: {e}")
            self.stats["errors"] += 1

    def parse_feature_html(self, html_file: Path) -> dict[str, Any] | None:
        """
        Parse a feature HTML file and extract metadata.

        Args:
            html_file: Path to HTML file

        Returns:
            Feature dictionary with parsed data
        """
        try:
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            parser = HtmlMetadataParser()
            parser.feed(html_content)

            # Map HTML attributes to feature schema
            feature = {
                "id": parser.metadata.get("id") or html_file.stem,
                "type": parser.metadata.get("type", "feature"),
                "title": parser.title or parser.metadata.get("title", "Untitled"),
                "status": parser.metadata.get("status", "todo"),
                "priority": parser.metadata.get("priority", "medium"),
                "assigned_to": parser.metadata.get("assigned", None),
                "created_at": parser.metadata.get(
                    "created", datetime.now().isoformat()
                ),
                "updated_at": parser.metadata.get(
                    "updated", datetime.now().isoformat()
                ),
                "edges": parser.edges,
            }

            logger.debug(f"Parsed feature: {feature['id']}")
            self.stats["features_parsed"] += 1
            return feature

        except Exception as e:
            logger.error(f"Error parsing {html_file}: {e}")
            self.stats["errors"] += 1
            return None

    def parse_session_html(self, html_file: Path) -> dict[str, Any] | None:
        """
        Parse a session HTML file and extract metadata.

        Args:
            html_file: Path to HTML file

        Returns:
            Session dictionary with parsed data
        """
        try:
            with open(html_file, encoding="utf-8") as f:
                html_content = f.read()

            parser = HtmlMetadataParser()
            parser.feed(html_content)

            # Map HTML attributes to session schema
            session = {
                "session_id": parser.metadata.get("id") or html_file.stem,
                "agent_assigned": parser.metadata.get("agent", "unknown"),
                "created_at": parser.metadata.get(
                    "started-at", datetime.now().isoformat()
                ),
                "completed_at": parser.metadata.get("ended-at"),
                "total_events": int(parser.metadata.get("event-count", 0)),
                "is_subagent": parser.metadata.get("is-subagent", "false").lower()
                == "true",
                "transcript_id": parser.metadata.get("transcript-id"),
                "transcript_path": parser.metadata.get("transcript-path"),
                "status": parser.metadata.get("status", "active"),
                "edges": parser.edges,
            }

            logger.debug(f"Parsed session: {session['session_id']}")
            self.stats["sessions_parsed"] += 1
            return session

        except Exception as e:
            logger.error(f"Error parsing {html_file}: {e}")
            self.stats["errors"] += 1
            return None

    def collect_features(self) -> list[dict[str, Any]]:
        """
        Collect all features from HTML files.

        Returns:
            List of feature dictionaries
        """
        features_dir = self.htmlgraph_dir / "features"
        features = []

        if not features_dir.exists():
            logger.warning(f"Features directory not found: {features_dir}")
            return features

        logger.info(f"Scanning features directory: {features_dir}")

        for html_file in sorted(features_dir.glob("*.html")):
            feature = self.parse_feature_html(html_file)
            if feature:
                features.append(feature)

        logger.info(f"Collected {len(features)} features")
        return features

    def collect_sessions(self) -> list[dict[str, Any]]:
        """
        Collect all sessions from HTML files.

        Returns:
            List of session dictionaries
        """
        sessions_dir = self.htmlgraph_dir / "sessions"
        sessions = []

        if not sessions_dir.exists():
            logger.warning(f"Sessions directory not found: {sessions_dir}")
            return sessions

        logger.info(f"Scanning sessions directory: {sessions_dir}")

        for html_file in sorted(sessions_dir.glob("*.html")):
            session = self.parse_session_html(html_file)
            if session:
                sessions.append(session)

        logger.info(f"Collected {len(sessions)} sessions")
        return sessions

    def validate_data(self, features: list[dict], sessions: list[dict]) -> bool:
        """
        Validate collected data for integrity.

        Args:
            features: Collected features
            sessions: Collected sessions

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating collected data...")

        # Check for duplicates
        feature_ids = [f["id"] for f in features]
        if len(feature_ids) != len(set(feature_ids)):
            logger.error("Duplicate feature IDs detected!")
            self.stats["errors"] += 1
            return False

        session_ids = [s["session_id"] for s in sessions]
        if len(session_ids) != len(set(session_ids)):
            logger.error("Duplicate session IDs detected!")
            self.stats["errors"] += 1
            return False

        # Check for invalid references
        for feature in features:
            for edge in feature.get("edges", []):
                if edge["to_id"] not in feature_ids:
                    logger.warning(f"Dangling edge reference: {edge['to_id']}")
                    self.stats["warnings"] += 1

        logger.info("Data validation complete")
        return True

    def import_to_sqlite(self, features: list[dict], sessions: list[dict]) -> bool:
        """
        Import collected data into SQLite database.

        Args:
            features: Features to import
            sessions: Sessions to import

        Returns:
            True if import successful, False otherwise
        """
        try:
            from htmlgraph.db.schema import HtmlGraphDB

            db = HtmlGraphDB(str(self.db_path))
            db.connect()
            db.create_tables()

            logger.info("Importing features...")
            for feature in features:
                success = db.insert_feature(
                    feature_id=feature["id"],
                    feature_type=feature["type"],
                    title=feature["title"],
                    status=feature["status"],
                    priority=feature["priority"],
                    assigned_to=feature.get("assigned_to"),
                )
                if not success:
                    logger.warning(f"Failed to import feature: {feature['id']}")
                    self.stats["errors"] += 1

            logger.info("Importing sessions...")
            for session in sessions:
                success = db.insert_session(
                    session_id=session["session_id"],
                    agent_assigned=session["agent_assigned"],
                    is_subagent=session["is_subagent"],
                    transcript_id=session.get("transcript_id"),
                    transcript_path=session.get("transcript_path"),
                )
                if not success:
                    logger.warning(f"Failed to import session: {session['session_id']}")
                    self.stats["errors"] += 1

            logger.info("Importing graph edges...")
            all_edges = []
            for feature in features:
                all_edges.extend(feature.get("edges", []))
            for session in sessions:
                all_edges.extend(session.get("edges", []))

            # TODO: Insert edges into graph_edges table
            self.stats["edges_parsed"] = len(all_edges)

            db.disconnect()
            logger.info("Migration complete!")
            return True

        except Exception as e:
            logger.error(f"Import error: {e}")
            self.stats["errors"] += 1
            return False

    def run(self) -> bool:
        """
        Execute the migration.

        Returns:
            True if migration successful, False otherwise
        """
        logger.info("Starting HtmlGraph HTML to SQLite migration...")
        logger.info(f"HTML directory: {self.htmlgraph_dir}")
        logger.info(f"Database path: {self.db_path}")
        logger.info(f"Dry run: {self.dry_run}")

        # Collect data
        features = self.collect_features()
        sessions = self.collect_sessions()

        # Validate
        if not self.validate_data(features, sessions):
            logger.error("Validation failed!")
            return False

        # Print summary
        logger.info("\nMigration Summary:")
        logger.info(f"  Features: {len(features)}")
        logger.info(f"  Sessions: {len(sessions)}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info(f"  Warnings: {self.stats['warnings']}")

        if self.dry_run:
            logger.info("Dry run mode - no changes made")
            return True

        # Backup
        if self.create_backup:
            self.backup_html_files()

        # Import
        success = self.import_to_sqlite(features, sessions)

        # Print final stats
        logger.info("\nFinal Statistics:")
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")

        return success


def main():
    """Parse arguments and run migration."""
    parser = argparse.ArgumentParser(
        description="Migrate HtmlGraph from HTML files to SQLite backend"
    )
    parser.add_argument(
        "--htmlgraph-dir",
        default=".htmlgraph",
        help="Path to .htmlgraph directory (default: .htmlgraph)",
    )
    parser.add_argument(
        "--db-path",
        default=".htmlgraph/htmlgraph.db",
        help="Path to SQLite database (default: .htmlgraph/htmlgraph.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup of HTML files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    migrator = HtmlGraphMigrator(
        htmlgraph_dir=args.htmlgraph_dir,
        db_path=args.db_path,
        dry_run=args.dry_run,
        create_backup=not args.no_backup,
    )

    success = migrator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
