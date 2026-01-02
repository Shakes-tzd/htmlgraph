"""
Archive search engine with three-tier optimization.

Tier 1: Bloom filters (skip 70-90% of archives)
Tier 2: SQLite FTS5 with BM25 ranking (O(log n) search)
Tier 3: Snippet extraction and highlighting

Target: 67x faster than naive multi-file search.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from htmlgraph.archive.bloom import BloomFilter
from htmlgraph.archive.fts import ArchiveFTS5Index


@dataclass
class SearchResult:
    """
    Search result from archive search.

    Attributes:
        entity_id: Entity identifier
        archive_file: Archive file containing entity
        entity_type: Type of entity (feature, bug, etc.)
        status: Entity status
        title_snippet: Title with highlighted matches
        description_snippet: Description with highlighted matches
        rank: BM25 relevance score (lower is better)
    """

    entity_id: str
    archive_file: str
    entity_type: str
    status: str
    title_snippet: str
    description_snippet: str
    rank: float


class ArchiveSearchEngine:
    """
    Orchestrates three-tier archive search.

    Workflow:
    1. Check Bloom filters to skip irrelevant archives (70-90% filtered)
    2. Search remaining archives with FTS5 + BM25 ranking
    3. Extract and highlight snippets for top results
    """

    def __init__(self, archive_dir: Path, index_dir: Path) -> None:
        """
        Initialize search engine.

        Args:
            archive_dir: Directory containing archive HTML files
            index_dir: Directory for Bloom filters and FTS5 index
        """
        self.archive_dir = archive_dir
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Initialize FTS5 index
        self.fts_index = ArchiveFTS5Index(index_dir / "archives.db")

        # Cache for Bloom filters (avoid reloading)
        self._bloom_cache: dict[str, BloomFilter] = {}

    def _get_bloom_filter(self, archive_file: str) -> BloomFilter | None:
        """
        Get Bloom filter for archive (with caching).

        Args:
            archive_file: Archive filename

        Returns:
            BloomFilter or None if not indexed
        """
        if archive_file in self._bloom_cache:
            return self._bloom_cache[archive_file]

        bloom_path = self.index_dir / f"{archive_file}.bloom"
        if bloom_path.exists():
            bloom = BloomFilter.load(bloom_path)
            self._bloom_cache[archive_file] = bloom
            return bloom

        return None

    def _filter_archives_with_bloom(
        self, query: str, archive_files: list[str]
    ) -> list[str]:
        """
        Filter archive files using Bloom filters.

        Args:
            query: Search query
            archive_files: List of all archive files

        Returns:
            Filtered list of archives that might contain query
        """
        # Tokenize query into words
        query_tokens = query.lower().split()

        candidates = []

        for archive_file in archive_files:
            bloom = self._get_bloom_filter(archive_file)

            if bloom is None:
                # No Bloom filter - include archive
                candidates.append(archive_file)
                continue

            # Check if any query token might be in archive
            might_match = any(bloom.might_contain(token) for token in query_tokens)

            if might_match:
                candidates.append(archive_file)

        return candidates

    @lru_cache(maxsize=100)
    def _cached_search(self, query: str, limit: int) -> tuple[SearchResult, ...]:
        """
        Cached search implementation.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            Tuple of SearchResult (immutable for caching)
        """
        # Get all archive files
        archive_files = [f.name for f in self.archive_dir.glob("*.html")]

        if not archive_files:
            return tuple()

        # Tier 1: Filter with Bloom filters
        candidate_archives = self._filter_archives_with_bloom(query, archive_files)

        if not candidate_archives:
            return tuple()

        # Tier 2 & 3: Search with FTS5 (includes snippet highlighting)
        results = self.fts_index.search(
            query, limit=limit, archive_files=candidate_archives
        )

        # Convert to SearchResult objects
        search_results = [
            SearchResult(
                entity_id=r["entity_id"],
                archive_file=r["archive_file"],
                entity_type=r["entity_type"],
                status=r["status"],
                title_snippet=r["title_snippet"],
                description_snippet=r["description_snippet"],
                rank=r["rank"],
            )
            for r in results
        ]

        return tuple(search_results)

    def search(
        self, query: str, include_archived: bool = True, limit: int = 10
    ) -> list[SearchResult]:
        """
        Search archives with three-tier optimization.

        Args:
            query: Search query
            include_archived: Whether to search archives (future: also search active)
            limit: Maximum results to return

        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not include_archived:
            return []

        # Use cached search
        results = self._cached_search(query, limit)
        return list(results)

    def get_search_stats(self, query: str) -> dict[str, Any]:
        """
        Get statistics about a search query.

        Args:
            query: Search query

        Returns:
            Dictionary with bloom_filtered_count, searched_count, etc.
        """
        archive_files = [f.name for f in self.archive_dir.glob("*.html")]
        total_archives = len(archive_files)

        candidate_archives = self._filter_archives_with_bloom(query, archive_files)
        searched_count = len(candidate_archives)

        bloom_filtered = total_archives - searched_count

        return {
            "total_archives": total_archives,
            "bloom_filtered": bloom_filtered,
            "searched_count": searched_count,
            "filter_rate": bloom_filtered / total_archives if total_archives > 0 else 0,
        }

    def rebuild_bloom_filters(self) -> None:
        """
        Rebuild all Bloom filters from scratch.

        Useful after archiving new entities.
        """
        # This will be implemented by ArchiveManager when creating archives
        # For now, this is a placeholder
        pass

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self._cached_search.cache_clear()
        self._bloom_cache.clear()

    def close(self) -> None:
        """Close all resources."""
        self.fts_index.close()
        self._bloom_cache.clear()

    def __enter__(self) -> "ArchiveSearchEngine":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
