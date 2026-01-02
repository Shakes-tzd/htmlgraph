"""
SQLite FTS5 full-text search index for archive content.

Uses BM25 ranking for relevance scoring with O(log n) search performance.
Provides snippet extraction with highlighting for matched terms.
"""

import sqlite3
from pathlib import Path
from typing import Any


class ArchiveFTS5Index:
    """
    Full-text search index using SQLite FTS5.

    Features:
    - Porter stemming for better matching
    - Unicode61 tokenization for international text
    - BM25 ranking for relevance scoring
    - Snippet extraction with highlighting
    - Metadata table for quick lookups
    """

    def __init__(self, db_path: Path) -> None:
        """
        Initialize FTS5 index.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create FTS5 tables if they don't exist."""
        conn = self._get_connection()

        # Create FTS5 virtual table with porter stemming
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts USING fts5(
                entity_id UNINDEXED,
                title,
                description,
                content,
                tokenize='porter unicode61'
            )
            """
        )

        # Create metadata table for quick lookups
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS archive_metadata (
                entity_id TEXT PRIMARY KEY,
                archive_file TEXT NOT NULL,
                entity_type TEXT,
                status TEXT,
                created TEXT,
                updated TEXT
            )
            """
        )

        # Create index on archive_file for filtering
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_archive_file
            ON archive_metadata(archive_file)
            """
        )

        conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (create if needed)."""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        return self.conn

    def index_archive(self, archive_file: str, entities: list[dict[str, Any]]) -> None:
        """
        Index entities from an archive file.

        Args:
            archive_file: Name of archive file (e.g., '2024-Q4-completed.html')
            entities: List of entity dictionaries
        """
        conn = self._get_connection()

        for entity in entities:
            entity_id = entity.get("id", "")
            title = entity.get("title", "")
            description = entity.get("description", "")
            content = entity.get("content", "")

            # Insert into FTS5 table
            conn.execute(
                """
                INSERT INTO archive_fts (entity_id, title, description, content)
                VALUES (?, ?, ?, ?)
                """,
                (entity_id, title, description, content),
            )

            # Insert into metadata table
            conn.execute(
                """
                INSERT OR REPLACE INTO archive_metadata
                (entity_id, archive_file, entity_type, status, created, updated)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_id,
                    archive_file,
                    entity.get("type", ""),
                    entity.get("status", ""),
                    entity.get("created", ""),
                    entity.get("updated", ""),
                ),
            )

        conn.commit()

    def search(
        self,
        query: str,
        limit: int = 10,
        archive_files: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search indexed archives with BM25 ranking.

        Args:
            query: Search query
            limit: Maximum number of results
            archive_files: Optional list of archive files to search

        Returns:
            List of results with entity_id, title, rank, snippet, archive_file
        """
        conn = self._get_connection()

        # Build query with optional archive file filter
        if archive_files:
            placeholders = ",".join("?" * len(archive_files))
            sql = f"""
                SELECT
                    fts.entity_id,
                    meta.archive_file,
                    meta.entity_type,
                    meta.status,
                    snippet(archive_fts, 1, '<mark>', '</mark>', '...', 32) as title_snippet,
                    snippet(archive_fts, 2, '<mark>', '</mark>', '...', 64) as description_snippet,
                    bm25(archive_fts) as rank
                FROM archive_fts fts
                JOIN archive_metadata meta ON fts.entity_id = meta.entity_id
                WHERE archive_fts MATCH ?
                  AND meta.archive_file IN ({placeholders})
                ORDER BY rank
                LIMIT ?
            """
            params = [query] + archive_files + [limit]
        else:
            sql = """
                SELECT
                    fts.entity_id,
                    meta.archive_file,
                    meta.entity_type,
                    meta.status,
                    snippet(archive_fts, 1, '<mark>', '</mark>', '...', 32) as title_snippet,
                    snippet(archive_fts, 2, '<mark>', '</mark>', '...', 64) as description_snippet,
                    bm25(archive_fts) as rank
                FROM archive_fts fts
                JOIN archive_metadata meta ON fts.entity_id = meta.entity_id
                WHERE archive_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            params = [query, limit]

        cursor = conn.execute(sql, params)

        results = []
        for row in cursor:
            results.append(
                {
                    "entity_id": row["entity_id"],
                    "archive_file": row["archive_file"],
                    "entity_type": row["entity_type"],
                    "status": row["status"],
                    "title_snippet": row["title_snippet"],
                    "description_snippet": row["description_snippet"],
                    "rank": row["rank"],
                }
            )

        return results

    def get_entity_metadata(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get metadata for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            Metadata dictionary or None if not found
        """
        conn = self._get_connection()

        cursor = conn.execute(
            """
            SELECT entity_id, archive_file, entity_type, status, created, updated
            FROM archive_metadata
            WHERE entity_id = ?
            """,
            (entity_id,),
        )

        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def remove_archive(self, archive_file: str) -> None:
        """
        Remove all entities from a specific archive file.

        Args:
            archive_file: Archive file to remove
        """
        conn = self._get_connection()

        # Get entity IDs to remove
        cursor = conn.execute(
            "SELECT entity_id FROM archive_metadata WHERE archive_file = ?",
            (archive_file,),
        )
        entity_ids = [row["entity_id"] for row in cursor]

        # Remove from FTS5
        for entity_id in entity_ids:
            conn.execute("DELETE FROM archive_fts WHERE entity_id = ?", (entity_id,))

        # Remove from metadata
        conn.execute(
            "DELETE FROM archive_metadata WHERE archive_file = ?", (archive_file,)
        )

        conn.commit()

    def get_stats(self) -> dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dictionary with entity count, archive count, etc.
        """
        conn = self._get_connection()

        # Count entities
        cursor = conn.execute("SELECT COUNT(*) as count FROM archive_metadata")
        entity_count = cursor.fetchone()["count"]

        # Count archives
        cursor = conn.execute(
            "SELECT COUNT(DISTINCT archive_file) as count FROM archive_metadata"
        )
        archive_count = cursor.fetchone()["count"]

        # Get database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "entity_count": entity_count,
            "archive_count": archive_count,
            "db_size_bytes": db_size,
            "db_size_mb": db_size / (1024 * 1024),
        }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "ArchiveFTS5Index":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
