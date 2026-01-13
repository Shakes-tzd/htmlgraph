#!/usr/bin/env python3
"""
Populate features table with bugs, spikes, and tracks from HTML files.

This script scans .htmlgraph/{bugs,spikes,tracks}/ directories and
extracts metadata from HTML files to populate the features table
with all work item types.
"""

import re
import sqlite3
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path


class WorkItemHTMLParser(HTMLParser):
    """Extract metadata from HtmlGraph work item HTML files."""

    def __init__(self):
        super().__init__()
        self.metadata = {}
        self.in_article = False
        self.in_title_h1 = False
        self.in_description = False
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.in_article = True
            attrs_dict = dict(attrs)
            self.metadata = {
                "id": attrs_dict.get("id", ""),
                "type": attrs_dict.get("data-type", "feature"),
                "status": attrs_dict.get("data-status", "todo"),
                "priority": attrs_dict.get("data-priority", "medium"),
                "created": attrs_dict.get("data-created", ""),
                "updated": attrs_dict.get("data-updated", ""),
            }
        elif tag == "title" and not self.title:
            self.in_title_h1 = True
        elif tag == "h1" and self.in_article and not self.title:
            self.in_title_h1 = True
        elif tag == "section" and self.in_article:
            attrs_dict = dict(attrs)
            if attrs_dict.get("data-content") is not None:
                self.in_description = True

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_article = False
        elif tag in ("title", "h1"):
            self.in_title_h1 = False
        elif tag == "section":
            self.in_description = False

    def handle_data(self, data):
        if self.in_title_h1:
            self.title += data.strip()
        elif self.in_description:
            self.description += data.strip()


def extract_metadata_from_html(html_path: Path) -> dict:
    """Extract work item metadata from HTML file."""
    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    parser = WorkItemHTMLParser()
    parser.feed(content)

    # Clean up description (remove excessive whitespace)
    description = re.sub(r"\s+", " ", parser.description).strip()
    if len(description) > 500:
        description = description[:497] + "..."

    # Map status values to database enum
    status_mapping = {
        "completed": "done",
        "active": "in_progress",
        "in-progress": "in_progress",
        "planned": "todo",
    }
    raw_status = parser.metadata.get("status", "todo")
    status = status_mapping.get(raw_status, raw_status)

    return {
        "id": parser.metadata.get("id", html_path.stem),
        "type": parser.metadata.get("type", "feature"),
        "title": parser.title or html_path.stem,
        "description": description,
        "status": status,
        "priority": parser.metadata.get("priority", "medium"),
        "created_at": parser.metadata.get("created", datetime.utcnow().isoformat()),
        "updated_at": parser.metadata.get("updated", datetime.utcnow().isoformat()),
    }


def populate_database(db_path: Path, htmlgraph_dir: Path):
    """Populate features table with work items from HTML files."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Scan directories
    work_item_dirs = {
        "bugs": htmlgraph_dir / "bugs",
        "spikes": htmlgraph_dir / "spikes",
        "tracks": htmlgraph_dir / "tracks",
    }

    total_added = 0
    total_skipped = 0

    for item_type, directory in work_item_dirs.items():
        if not directory.exists():
            print(f"⚠️  Directory not found: {directory}")
            continue

        html_files = list(directory.glob("*.html"))
        print(f"\n📂 Processing {len(html_files)} {item_type} from {directory}")

        for html_file in html_files:
            try:
                metadata = extract_metadata_from_html(html_file)

                # Check if already exists
                cursor.execute(
                    "SELECT id FROM features WHERE id = ?", (metadata["id"],)
                )
                if cursor.fetchone():
                    total_skipped += 1
                    continue

                # Insert into features table
                cursor.execute(
                    """
                    INSERT INTO features (
                        id, type, title, description, status, priority,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        metadata["id"],
                        metadata["type"],
                        metadata["title"],
                        metadata["description"],
                        metadata["status"],
                        metadata["priority"],
                        metadata["created_at"],
                        metadata["updated_at"],
                    ),
                )

                total_added += 1
                print(
                    f"  ✅ Added {metadata['type']}: {metadata['id']} - {metadata['title'][:50]}"
                )

            except Exception as e:
                print(f"  ❌ Error processing {html_file.name}: {e}")

    conn.commit()
    conn.close()

    print("\n✨ Summary:")
    print(f"   Added: {total_added} work items")
    print(f"   Skipped: {total_skipped} (already in database)")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    db_path = project_root / ".htmlgraph" / "htmlgraph.db"
    htmlgraph_dir = project_root / ".htmlgraph"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        exit(1)

    print("🚀 Populating features table with work items from HTML files...")
    populate_database(db_path, htmlgraph_dir)
    print("\n✅ Done!")
