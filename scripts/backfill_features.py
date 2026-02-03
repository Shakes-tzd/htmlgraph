#!/usr/bin/env python3
"""
Backfill Features from HTML to SQLite Database

Migrates feature HTML files to the SQLite features table.
Filters out test artifacts (Test Feature 1, Test Feature 2, etc.)

Usage:
    uv run python scripts/backfill_features.py
    uv run python scripts/backfill_features.py --dry-run
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class FeatureHTMLParser(HTMLParser):
    """Parse feature HTML files to extract metadata."""

    def __init__(self):
        super().__init__()
        self.metadata: dict[str, Any] = {}
        self.title: str | None = None
        self.description: str | None = None
        self.in_title = False
        self.in_h1 = False
        self.current_step_count = 0
        self.completed_step_count = 0
        self.in_steps = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]):
        """Parse opening tags and extract metadata."""
        attrs_dict = dict(attrs)

        # Extract metadata from article tag
        if tag == "article":
            for key, value in attrs_dict.items():
                if key.startswith("data-"):
                    attr_name = key[5:]  # Remove 'data-' prefix
                    self.metadata[attr_name] = value

        # Track title elements
        if tag in ("title", "h1"):
            if tag == "h1":
                self.in_h1 = True
            else:
                self.in_title = True

        # Count steps
        if tag == "section" and attrs_dict.get("data-steps"):
            self.in_steps = True
        elif tag == "li" and self.in_steps:
            self.current_step_count += 1
            if attrs_dict.get("data-completed") == "true":
                self.completed_step_count += 1

    def handle_endtag(self, tag: str):
        """Handle closing tags."""
        if tag in ("title", "h1"):
            self.in_title = False
            self.in_h1 = False
        elif tag == "section":
            self.in_steps = False

    def handle_data(self, data: str):
        """Extract text content."""
        if (self.in_title or self.in_h1) and data.strip():
            if not self.title:
                self.title = data.strip()


def is_test_feature(title: str) -> bool:
    """
    Check if a feature is a test artifact.

    Test patterns:
    - "Test Feature 1", "Test Feature 2"
    - "Delegation Test Feature X"
    - "Test Feature - X"
    - "Final Test Feature X"
    - "Real-Time Test Feature X"
    - "Orchestration Feature X"
    - "Feature X (completed/in-progress)" (generic test names)
    - Generic names like "Example Feature", "Demo Feature"
    """
    test_patterns = [
        r"^Test Feature",
        r"^Delegation Test Feature",
        r"^Final Test Feature",
        r"^Real-Time Test Feature",
        r"^Orchestration Feature \d+$",
        r"^Feature \d+ \(",  # "Feature 1 (completed)", "Feature 2 (in-progress)"
        r"^Example Feature",
        r"^Demo Feature",
    ]

    for pattern in test_patterns:
        if re.match(pattern, title, re.IGNORECASE):
            return True

    return False


def parse_feature_html(html_file: Path) -> dict[str, Any] | None:
    """Parse a feature HTML file and extract metadata."""
    try:
        with open(html_file, encoding="utf-8") as f:
            html_content = f.read()

        parser = FeatureHTMLParser()
        parser.feed(html_content)

        # Extract feature ID from filename or metadata
        feature_id = parser.metadata.get("id") or html_file.stem

        # Get title
        title = parser.title or parser.metadata.get("title", "Untitled")

        # Skip test features
        if is_test_feature(title):
            return None

        # Get status and normalize it
        status = parser.metadata.get("status", "todo")
        # Map archived to cancelled (archived not in schema)
        if status == "archived":
            status = "cancelled"

        # Map to database schema
        feature = {
            "id": feature_id,
            "type": parser.metadata.get("type", "feature"),
            "title": title,
            "description": parser.description,
            "status": status,
            "priority": parser.metadata.get("priority", "medium"),
            "assigned_to": parser.metadata.get("agent-assigned"),
            "track_id": parser.metadata.get("track-id"),
            "created_at": parser.metadata.get("created"),
            "updated_at": parser.metadata.get("updated"),
            "completed_at": parser.metadata.get("completed-at"),
            "steps_total": parser.current_step_count,
            "steps_completed": parser.completed_step_count,
            "parent_feature_id": parser.metadata.get("parent-feature-id"),
        }

        return feature

    except Exception as e:
        print(f"Error parsing {html_file}: {e}", file=sys.stderr)
        return None


def backfill_features(db_path: Path, features_dir: Path, dry_run: bool = False):
    """Backfill features from HTML files to SQLite database."""

    # Collect all feature files
    html_files = sorted(features_dir.glob("feat-*.html"))
    print(f"Found {len(html_files)} feature HTML files")

    # Parse all features
    features = []
    test_features_skipped = 0
    parse_errors = 0

    for html_file in html_files:
        feature = parse_feature_html(html_file)
        if feature:
            features.append(feature)
        elif feature is None:
            # Check if it was skipped as test or errored
            try:
                with open(html_file, encoding="utf-8") as f:
                    content = f.read()
                if "Test Feature" in content or "Delegation Test" in content:
                    test_features_skipped += 1
            except:
                parse_errors += 1

    print(f"Parsed {len(features)} real features")
    print(f"Skipped {test_features_skipped} test features")
    if parse_errors > 0:
        print(f"Parse errors: {parse_errors}")

    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print("Sample features that would be imported:")
        for feature in features[:5]:
            print(f"  - {feature['id']}: {feature['title']} ({feature['status']})")
        print(f"\nTotal: {len(features)} features would be imported")
        return

    # Insert into database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0
    errors = 0

    for feature in features:
        try:
            # Check if already exists
            cursor.execute("SELECT id FROM features WHERE id = ?", (feature["id"],))
            if cursor.fetchone():
                skipped += 1
                continue

            # Insert feature
            cursor.execute(
                """
                INSERT INTO features (
                    id, type, title, description, status, priority,
                    assigned_to, track_id, created_at, updated_at, completed_at,
                    steps_total, steps_completed, parent_feature_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feature["id"],
                    feature["type"],
                    feature["title"],
                    feature["description"],
                    feature["status"],
                    feature["priority"],
                    feature["assigned_to"],
                    feature["track_id"],
                    feature["created_at"],
                    feature["updated_at"],
                    feature["completed_at"],
                    feature["steps_total"],
                    feature["steps_completed"],
                    feature["parent_feature_id"],
                ),
            )
            inserted += 1

        except Exception as e:
            print(f"Error inserting {feature['id']}: {e}", file=sys.stderr)
            errors += 1

    conn.commit()
    conn.close()

    # Print summary
    print("\n=== MIGRATION SUMMARY ===")
    print(f"Inserted: {inserted}")
    print(f"Skipped (already exists): {skipped}")
    print(f"Errors: {errors}")
    print(f"Total features in database: {inserted + skipped}")

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM features")
    total = cursor.fetchone()[0]
    conn.close()

    print(f"\n✅ Verification: {total} features in database")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Backfill features from HTML to SQLite")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be imported without making changes",
    )
    parser.add_argument(
        "--htmlgraph-dir",
        type=Path,
        default=Path(".htmlgraph"),
        help="Path to .htmlgraph directory (default: .htmlgraph)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path(".htmlgraph/htmlgraph.db"),
        help="Path to SQLite database (default: .htmlgraph/htmlgraph.db)",
    )

    args = parser.parse_args()

    features_dir = args.htmlgraph_dir / "features"
    if not features_dir.exists():
        print(f"Error: Features directory not found: {features_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.db_path.exists():
        print(f"Error: Database not found: {args.db_path}", file=sys.stderr)
        sys.exit(1)

    backfill_features(args.db_path, features_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
