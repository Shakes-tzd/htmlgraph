"""
Tests for archive search engine.

Covers:
- Bloom filter accuracy and performance
- FTS5 search with BM25 ranking
- Multi-archive search
- Snippet highlighting
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from htmlgraph.archive import ArchiveManager, BloomFilter
from htmlgraph.archive.fts import ArchiveFTS5Index
from htmlgraph.archive.search import ArchiveSearchEngine
from htmlgraph.models import Node


@pytest.fixture
def temp_index_dir() -> Path:
    """Create a temporary index directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_entities_data() -> list[dict]:
    """Sample entities as dictionaries for testing."""
    return [
        {
            "id": "feat-001",
            "title": "User Authentication System",
            "description": "Implement OAuth 2.0 and JWT authentication",
            "content": "Add login routes middleware session management",
            "type": "feature",
            "status": "done",
            "created": "2024-01-01T00:00:00",
            "updated": "2024-03-01T00:00:00",
        },
        {
            "id": "feat-002",
            "title": "Database Migration",
            "description": "Migrate from SQLite to PostgreSQL",
            "content": "Setup Alembic migrations write migration scripts",
            "type": "feature",
            "status": "done",
            "created": "2024-02-01T00:00:00",
            "updated": "2024-04-01T00:00:00",
        },
        {
            "id": "bug-001",
            "title": "Login Redirect Issue",
            "description": "Users not redirected after login",
            "content": "Fix redirect logic in auth middleware",
            "type": "bug",
            "status": "cancelled",
            "created": "2024-01-15T00:00:00",
            "updated": "2024-02-15T00:00:00",
        },
    ]


def test_bloom_filter_basic() -> None:
    """Test basic Bloom filter functionality."""
    bloom = BloomFilter(expected_items=100, false_positive_rate=0.01)

    # Add items
    bloom.add("authentication")
    bloom.add("database")
    bloom.add("login")

    # Check membership
    assert bloom.might_contain("authentication") is True
    assert bloom.might_contain("database") is True
    assert bloom.might_contain("login") is True

    # Should not contain
    # Note: False positives possible but rare with low FPR
    assert bloom.might_contain("nonexistent-item-xyz-123") is False


def test_bloom_filter_build_for_archive(sample_entities_data: list[dict]) -> None:
    """Test building Bloom filter from entities."""
    bloom = BloomFilter(expected_items=10)

    bloom.build_for_archive(sample_entities_data)

    # Should contain entity IDs
    assert bloom.might_contain("feat-001") is True
    assert bloom.might_contain("feat-002") is True

    # Should contain title tokens
    assert bloom.might_contain("authentication") is True
    assert bloom.might_contain("database") is True

    # Should contain description tokens
    assert bloom.might_contain("oauth") is True
    assert bloom.might_contain("postgresql") is True


def test_bloom_filter_save_load(temp_index_dir: Path) -> None:
    """Test Bloom filter persistence."""
    bloom = BloomFilter(expected_items=50)
    bloom.add("test-item-1")
    bloom.add("test-item-2")

    # Save
    bloom_path = temp_index_dir / "test.bloom"
    bloom.save(bloom_path)

    assert bloom_path.exists()

    # Load
    loaded = BloomFilter.load(bloom_path)

    assert loaded.might_contain("test-item-1") is True
    assert loaded.might_contain("test-item-2") is True


def test_bloom_filter_stats() -> None:
    """Test Bloom filter statistics."""
    bloom = BloomFilter(expected_items=100, false_positive_rate=0.01)

    for i in range(50):
        bloom.add(f"item-{i}")

    stats = bloom.get_stats()

    assert stats["expected_items"] == 100
    assert stats["items_added"] == 50
    assert stats["utilization"] == 0.5
    assert stats["bytes_used"] > 0


def test_fts5_index_and_search(
    temp_index_dir: Path, sample_entities_data: list[dict]
) -> None:
    """Test FTS5 indexing and searching."""
    db_path = temp_index_dir / "test.db"
    index = ArchiveFTS5Index(db_path)

    # Index entities
    index.index_archive("2024-Q1-done.html", sample_entities_data)

    # Search for "authentication"
    results = index.search("authentication", limit=10)

    assert len(results) > 0
    assert any(r["entity_id"] == "feat-001" for r in results)

    index.close()


def test_fts5_bm25_ranking(
    temp_index_dir: Path, sample_entities_data: list[dict]
) -> None:
    """Test BM25 ranking order."""
    db_path = temp_index_dir / "test.db"
    index = ArchiveFTS5Index(db_path)

    # Index entities
    index.index_archive("2024-Q1.html", sample_entities_data)

    # Search for "authentication" (should rank feat-001 higher)
    results = index.search("authentication login", limit=10)

    # Verify results are ordered by rank (lower is better in BM25)
    if len(results) >= 2:
        assert results[0]["rank"] <= results[1]["rank"]

    index.close()


def test_fts5_snippet_highlighting(
    temp_index_dir: Path, sample_entities_data: list[dict]
) -> None:
    """Test snippet extraction with highlighting."""
    db_path = temp_index_dir / "test.db"
    index = ArchiveFTS5Index(db_path)

    # Index entities
    index.index_archive("2024-Q1.html", sample_entities_data)

    # Search
    results = index.search("authentication", limit=10)

    assert len(results) > 0

    # Check for highlighting markup
    for result in results:
        if "authentication" in result["title_snippet"].lower():
            # Should have <mark> tags
            assert "<mark>" in result["title_snippet"]
            assert "</mark>" in result["title_snippet"]

    index.close()


def test_fts5_get_entity_metadata(
    temp_index_dir: Path, sample_entities_data: list[dict]
) -> None:
    """Test getting entity metadata."""
    db_path = temp_index_dir / "test.db"
    index = ArchiveFTS5Index(db_path)

    # Index entities
    index.index_archive("2024-Q1.html", sample_entities_data)

    # Get metadata
    metadata = index.get_entity_metadata("feat-001")

    assert metadata is not None
    assert metadata["entity_id"] == "feat-001"
    assert metadata["archive_file"] == "2024-Q1.html"
    assert metadata["entity_type"] == "feature"

    index.close()


def test_fts5_remove_archive(
    temp_index_dir: Path, sample_entities_data: list[dict]
) -> None:
    """Test removing archive from index."""
    db_path = temp_index_dir / "test.db"
    index = ArchiveFTS5Index(db_path)

    # Index entities
    index.index_archive("2024-Q1.html", sample_entities_data)

    # Verify indexed
    results = index.search("authentication", limit=10)
    assert len(results) > 0

    # Remove archive
    index.remove_archive("2024-Q1.html")

    # Verify removed
    results = index.search("authentication", limit=10)
    assert len(results) == 0

    index.close()


def test_search_engine_bloom_filter_filtering(temp_index_dir: Path) -> None:
    """Test that Bloom filters skip irrelevant archives."""
    archive_dir = temp_index_dir / "archives"
    archive_dir.mkdir()

    engine = ArchiveSearchEngine(archive_dir, temp_index_dir)

    # Create a Bloom filter with specific items
    bloom = BloomFilter(expected_items=10)
    bloom.add("authentication")
    bloom.add("login")
    bloom.save(temp_index_dir / "2024-Q1.html.bloom")

    # Create another Bloom filter without those items
    bloom2 = BloomFilter(expected_items=10)
    bloom2.add("database")
    bloom2.add("migration")
    bloom2.save(temp_index_dir / "2024-Q2.html.bloom")

    # Create dummy archive files
    (archive_dir / "2024-Q1.html").write_text("<html></html>")
    (archive_dir / "2024-Q2.html").write_text("<html></html>")

    # Filter archives
    candidates = engine._filter_archives_with_bloom(
        "authentication", ["2024-Q1.html", "2024-Q2.html"]
    )

    # Should include Q1 (has "authentication") but likely not Q2
    assert "2024-Q1.html" in candidates

    engine.close()


def test_search_engine_get_stats(temp_index_dir: Path) -> None:
    """Test search statistics."""
    archive_dir = temp_index_dir / "archives"
    archive_dir.mkdir()

    engine = ArchiveSearchEngine(archive_dir, temp_index_dir)

    # Create Bloom filters
    bloom = BloomFilter(expected_items=10)
    bloom.add("test")
    bloom.save(temp_index_dir / "2024-Q1.html.bloom")

    # Create archive file
    (archive_dir / "2024-Q1.html").write_text("<html></html>")

    # Get stats
    stats = engine.get_search_stats("test")

    assert stats["total_archives"] == 1
    assert stats["bloom_filtered"] >= 0
    assert stats["searched_count"] >= 0

    engine.close()


def test_search_engine_cache(temp_index_dir: Path) -> None:
    """Test search result caching."""
    archive_dir = temp_index_dir / "archives"
    archive_dir.mkdir()

    engine = ArchiveSearchEngine(archive_dir, temp_index_dir)

    # First search (cache miss)
    results1 = engine.search("test", limit=10)

    # Second search (cache hit - should be same)
    results2 = engine.search("test", limit=10)

    assert results1 == results2

    # Clear cache
    engine.clear_cache()

    # Third search (cache miss again)
    results3 = engine.search("test", limit=10)

    assert results3 == results1

    engine.close()


def test_archive_manager_integration(temp_index_dir: Path) -> None:
    """Test full integration with ArchiveManager."""
    # Create temp htmlgraph dir
    htmlgraph_dir = temp_index_dir / ".htmlgraph"
    htmlgraph_dir.mkdir()

    # Create entity directories
    features_dir = htmlgraph_dir / "features"
    features_dir.mkdir()

    # Create old entities
    old_date = datetime.now() - timedelta(days=100)

    entities = [
        Node(
            id="feat-001",
            title="User Authentication",
            type="feature",
            status="done",
            created=old_date,
            updated=old_date,
            content="OAuth 2.0 implementation",
        ),
        Node(
            id="feat-002",
            title="Database Setup",
            type="feature",
            status="done",
            created=old_date,
            updated=old_date,
            content="PostgreSQL migration",
        ),
    ]

    # Write entity files
    for entity in entities:
        filepath = features_dir / f"{entity.id}.html"
        with open(filepath, "w") as f:
            f.write(entity.to_html())

    # Archive
    manager = ArchiveManager(htmlgraph_dir)
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Search
    results = manager.search("authentication", limit=10)

    assert len(results) > 0
    assert any(r["entity_id"] == "feat-001" for r in results)

    # Get stats
    search_stats = manager.search_engine.get_search_stats("authentication")

    assert search_stats["total_archives"] > 0

    manager.close()
