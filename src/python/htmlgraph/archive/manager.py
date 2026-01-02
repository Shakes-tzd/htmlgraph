"""
Archive manager for consolidating and managing archived entities.

Provides:
- Archive creation with hybrid time+status naming (2024-Q4-completed.html)
- Archive search with three-tier optimization
- Unarchive (restore) functionality
- Cross-reference preservation
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from htmlgraph.archive.bloom import BloomFilter
from htmlgraph.archive.fts import ArchiveFTS5Index
from htmlgraph.archive.search import ArchiveSearchEngine
from htmlgraph.models import Node
from htmlgraph.parser import HtmlParser


@dataclass
class ArchiveConfig:
    """
    Configuration for archive management.

    Attributes:
        retention_days: Days before entities are eligible for archiving
        archive_period: Time period for grouping (quarter, month, year)
        entity_types: Types of entities to archive (feature, bug, etc.)
        status_filter: Only archive entities with these statuses
        auto_archive: Enable automatic archiving
    """

    retention_days: int = 90
    archive_period: Literal["quarter", "month", "year"] = "quarter"
    entity_types: list[str] = None  # type: ignore
    status_filter: list[str] = None  # type: ignore
    auto_archive: bool = False

    def __post_init__(self) -> None:
        """Set defaults for mutable fields."""
        if self.entity_types is None:
            # Support all HtmlGraph entity types
            self.entity_types = [
                "feature",
                "bug",
                "chore",
                "spike",
                "pattern",
                "session",
                "track",
                "epic",
                "phase",
                "insight",
                "metric",
            ]
        if self.status_filter is None:
            self.status_filter = ["done", "cancelled", "obsolete"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchiveConfig":
        """Create from dictionary."""
        return cls(**data)


class ArchiveManager:
    """
    Manages entity archiving and search.

    Workflow:
    1. Identify entities eligible for archiving (age + status)
    2. Group by time period (quarter, month, year)
    3. Consolidate into archive HTML files
    4. Build Bloom filters and FTS5 index
    5. Update cross-references in active entities
    """

    def __init__(self, htmlgraph_dir: Path) -> None:
        """
        Initialize archive manager.

        Args:
            htmlgraph_dir: Path to .htmlgraph directory
        """
        self.htmlgraph_dir = htmlgraph_dir
        self.archive_dir = htmlgraph_dir / "archives"
        self.index_dir = htmlgraph_dir / "archive-index"
        self.config_path = htmlgraph_dir / "config.json"

        # Create directories
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Initialize search engine
        self.search_engine = ArchiveSearchEngine(self.archive_dir, self.index_dir)

    def _load_config(self) -> ArchiveConfig:
        """Load configuration from disk."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                data = json.load(f)
                return ArchiveConfig.from_dict(data.get("archive", {}))
        return ArchiveConfig()

    def _save_config(self) -> None:
        """Save configuration to disk."""
        # Load existing config or create new
        if self.config_path.exists():
            with open(self.config_path) as f:
                config_data = json.load(f)
        else:
            config_data = {}

        # Update archive section
        config_data["archive"] = self.config.to_dict()

        # Save
        with open(self.config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    def set_config(self, config: ArchiveConfig) -> None:
        """
        Update configuration.

        Args:
            config: New configuration
        """
        self.config = config
        self._save_config()

    def _get_period_name(self, dt: datetime) -> str:
        """
        Get period name for a datetime.

        Args:
            dt: Datetime to get period for

        Returns:
            Period string (e.g., "2024-Q4", "2024-12", "2024")
        """
        if self.config.archive_period == "quarter":
            quarter = (dt.month - 1) // 3 + 1
            return f"{dt.year}-Q{quarter}"
        elif self.config.archive_period == "month":
            return f"{dt.year}-{dt.month:02d}"
        else:  # year
            return str(dt.year)

    def _get_eligible_entities(
        self, entity_type: str, older_than_days: int | None = None
    ) -> list[tuple[Path, Node]]:
        """
        Get entities eligible for archiving.

        Args:
            entity_type: Type of entity (feature, bug, etc.)
            older_than_days: Override retention days

        Returns:
            List of (filepath, node) tuples
        """
        days = (
            older_than_days
            if older_than_days is not None
            else self.config.retention_days
        )
        cutoff_date = datetime.now() - timedelta(days=days)

        entity_dir = self.htmlgraph_dir / f"{entity_type}s"
        if not entity_dir.exists():
            return []

        eligible = []

        for filepath in entity_dir.glob("*.html"):
            try:
                # Parse entity
                from htmlgraph.converter import html_to_node

                node = html_to_node(filepath)

                # Check status filter
                if node.status not in self.config.status_filter:
                    continue

                # Check age (use updated timestamp)
                if node.updated < cutoff_date:
                    eligible.append((filepath, node))

            except Exception:
                # Skip unparseable files
                continue

        return eligible

    def _create_archive_html(
        self,
        archive_file: str,
        entities: list[Node],
        period: str,
        status: str,
    ) -> str:
        """
        Create consolidated archive HTML file.

        Args:
            archive_file: Archive filename
            entities: List of entities to include
            period: Time period (e.g., "2024-Q4")
            status: Status filter (e.g., "completed")

        Returns:
            HTML content as string
        """
        # Sort entities by updated date (newest first)
        sorted_entities = sorted(entities, key=lambda e: e.updated, reverse=True)

        # Build table of contents
        toc_items = "\n".join(
            f'<li><a href="#{e.id}">{e.title}</a> ({e.type})</li>'
            for e in sorted_entities
        )

        # Build entity sections
        entity_sections = []
        for entity in sorted_entities:
            # Generate full HTML for entity
            entity_html = entity.to_html()

            # Extract the <article> content
            # We'll wrap it in a section for better structure
            entity_sections.append(
                f'<section id="{entity.id}" class="archived-entity">\n{entity_html}\n</section>'
            )

        entities_html = "\n\n".join(entity_sections)

        # Create archive HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Archive: {period} ({status})</title>
    <link rel="stylesheet" href="../styles.css">
    <style>
        .archive-banner {{
            background: #f0f0f0;
            border: 2px solid #ccc;
            padding: 1rem;
            margin-bottom: 2rem;
            border-radius: 4px;
        }}
        .archive-search {{
            width: 100%;
            padding: 0.5rem;
            font-size: 1rem;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}
        .archived-entity {{
            border-bottom: 2px solid #eee;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
        }}
        .toc {{
            background: #f9f9f9;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
        }}
    </style>
</head>
<body>
    <div class="archive-banner">
        <h1>📦 Archive: {period} - {status.title()}</h1>
        <p><strong>{len(entities)}</strong> archived entities</p>
        <input type="text" class="archive-search" id="searchInput" placeholder="Search this archive...">
    </div>

    <div class="toc">
        <h2>Contents</h2>
        <ul>
            {toc_items}
        </ul>
    </div>

    {entities_html}

    <script>
        // Client-side search
        const searchInput = document.getElementById('searchInput');
        const entities = document.querySelectorAll('.archived-entity');

        searchInput.addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();

            entities.forEach(entity => {{
                const text = entity.textContent.toLowerCase();
                if (text.includes(query)) {{
                    entity.style.display = 'block';
                }} else {{
                    entity.style.display = 'none';
                }}
            }});
        }});
    </script>
</body>
</html>"""

        return html

    def archive_entities(
        self,
        entity_types: list[str] | None = None,
        status_filter: list[str] | None = None,
        older_than_days: int | None = None,
        period: Literal["quarter", "month", "year"] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """
        Archive eligible entities.

        Args:
            entity_types: Types to archive (default: config)
            status_filter: Statuses to archive (default: config)
            older_than_days: Age threshold (default: config)
            period: Grouping period (default: config)
            dry_run: Preview without making changes

        Returns:
            Dictionary with archived_count, archive_files, etc.
        """
        types = entity_types or self.config.entity_types
        statuses = status_filter or self.config.status_filter
        period_type = period or self.config.archive_period

        # Temporarily override config for this operation
        original_period = self.config.archive_period
        self.config.archive_period = period_type

        # Group entities by period and status
        archives: dict[str, list[Node]] = {}
        entity_files: dict[str, list[Path]] = {}

        for entity_type in types:
            eligible = self._get_eligible_entities(entity_type, older_than_days)

            for filepath, node in eligible:
                if node.status not in statuses:
                    continue

                period_name = self._get_period_name(node.updated)
                archive_key = f"{period_name}-{node.status}"

                if archive_key not in archives:
                    archives[archive_key] = []
                    entity_files[archive_key] = []

                archives[archive_key].append(node)
                entity_files[archive_key].append(filepath)

        # Restore original config
        self.config.archive_period = original_period

        if dry_run:
            return {
                "dry_run": True,
                "would_archive": sum(len(entities) for entities in archives.values()),
                "archive_files": list(archives.keys()),
                "details": {key: len(entities) for key, entities in archives.items()},
            }

        # Create archive files
        created_archives = []

        for archive_key, entities in archives.items():
            archive_file = f"{archive_key}.html"
            archive_path = self.archive_dir / archive_file

            # Extract period and status from key
            parts = archive_key.rsplit("-", 1)
            period_name = parts[0]
            status = parts[1]

            # Create HTML
            html = self._create_archive_html(
                archive_file, entities, period_name, status
            )

            # Write to disk
            with open(archive_path, "w") as f:
                f.write(html)

            # Build Bloom filter
            bloom = BloomFilter(expected_items=len(entities))
            entity_dicts = [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.content or "",
                }
                for e in entities
            ]
            bloom.build_for_archive(entity_dicts)
            bloom.save(self.index_dir / f"{archive_file}.bloom")

            # Index in FTS5
            fts_index = ArchiveFTS5Index(self.index_dir / "archives.db")
            content_dicts = [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.content or "",
                    "content": " ".join(s.description for s in e.steps),
                    "type": e.type,
                    "status": e.status,
                    "created": e.created.isoformat(),
                    "updated": e.updated.isoformat(),
                }
                for e in entities
            ]
            fts_index.index_archive(archive_file, content_dicts)
            fts_index.close()

            # Delete original files
            for filepath in entity_files[archive_key]:
                filepath.unlink()

            created_archives.append(archive_file)

        # Clear search cache (new archives added)
        self.search_engine.clear_cache()

        return {
            "dry_run": False,
            "archived_count": sum(len(entities) for entities in archives.values()),
            "archive_files": created_archives,
            "details": {key: len(entities) for key, entities in archives.items()},
        }

    def unarchive(self, entity_id: str) -> bool:
        """
        Restore an archived entity to active status.

        Args:
            entity_id: Entity to restore

        Returns:
            True if restored, False if not found
        """

        # Find entity in FTS5 index
        fts_index = ArchiveFTS5Index(self.index_dir / "archives.db")
        metadata = fts_index.get_entity_metadata(entity_id)
        fts_index.close()

        if not metadata:
            return False

        archive_file = metadata["archive_file"]
        archive_path = self.archive_dir / archive_file

        if not archive_path.exists():
            return False

        # Parse archive HTML
        parser = HtmlParser.from_file(archive_path)

        # Find entity section by ID
        sections = parser.query(f"section#{entity_id}")
        if not sections:
            return False

        # Extract the article element from section
        articles = sections[0].query("article")
        if not articles:
            return False

        # Get article HTML string and create temp file
        import tempfile

        from htmlgraph.converter import html_to_node

        article_html = str(articles[0])

        # Write to temp file for parsing
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as tmp:
            # Wrap article in minimal HTML document
            tmp.write(
                f"<!DOCTYPE html><html><head><meta charset='UTF-8'></head><body>{article_html}</body></html>"
            )
            tmp_path = Path(tmp.name)

        try:
            node = html_to_node(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        # Determine target directory
        entity_type = node.type
        target_dir = self.htmlgraph_dir / f"{entity_type}s"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        target_path = target_dir / f"{entity_id}.html"

        # Write entity file
        with open(target_path, "w") as f:
            f.write(node.to_html())

        # TODO: Remove from archive HTML and update indexes
        # For now, leave in archive (duplicate is acceptable)

        return True

    def get_archive_stats(self) -> dict[str, Any]:
        """
        Get statistics about archives.

        Returns:
            Dictionary with archive_count, entity_count, size_mb, etc.
        """
        archive_files = list(self.archive_dir.glob("*.html"))
        total_size = sum(f.stat().st_size for f in archive_files)

        # Get FTS5 stats
        fts_index = ArchiveFTS5Index(self.index_dir / "archives.db")
        fts_stats = fts_index.get_stats()
        fts_index.close()

        # Get Bloom filter stats
        bloom_files = list(self.index_dir.glob("*.bloom"))
        bloom_size = sum(f.stat().st_size for f in bloom_files)

        return {
            "archive_count": len(archive_files),
            "entity_count": fts_stats["entity_count"],
            "total_size_mb": total_size / (1024 * 1024),
            "fts_size_mb": fts_stats["db_size_mb"],
            "bloom_size_kb": bloom_size / 1024,
            "bloom_count": len(bloom_files),
        }

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search archived entities.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of search results
        """
        results = self.search_engine.search(query, include_archived=True, limit=limit)

        return [
            {
                "entity_id": r.entity_id,
                "archive_file": r.archive_file,
                "entity_type": r.entity_type,
                "status": r.status,
                "title_snippet": r.title_snippet,
                "description_snippet": r.description_snippet,
                "rank": r.rank,
            }
            for r in results
        ]

    def close(self) -> None:
        """Close all resources."""
        self.search_engine.close()
