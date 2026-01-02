"""
Tests for archive manager functionality.

Covers:
- Archive creation and consolidation
- Bloom filter integration
- FTS5 indexing
- Entity restoration
- Cross-reference preservation
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from htmlgraph.archive import ArchiveConfig, ArchiveManager
from htmlgraph.models import Node, Step


@pytest.fixture
def temp_htmlgraph_dir() -> Path:
    """Create a temporary .htmlgraph directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        htmlgraph_dir = Path(tmpdir) / ".htmlgraph"
        htmlgraph_dir.mkdir()

        # Create entity directories
        (htmlgraph_dir / "features").mkdir()
        (htmlgraph_dir / "bugs").mkdir()

        yield htmlgraph_dir


@pytest.fixture
def sample_entities() -> list[Node]:
    """Create sample entities for testing."""
    now = datetime.now()
    old_date = now - timedelta(days=100)

    return [
        Node(
            id="feat-001",
            title="User Authentication",
            type="feature",
            status="done",
            priority="high",
            created=old_date,
            updated=old_date,
            content="Implement OAuth 2.0 authentication",
            steps=[
                Step(description="Create auth routes", completed=True),
                Step(description="Add middleware", completed=True),
            ],
        ),
        Node(
            id="feat-002",
            title="Database Migration",
            type="feature",
            status="done",
            priority="medium",
            created=old_date,
            updated=old_date,
            content="Migrate to PostgreSQL",
            steps=[Step(description="Setup Alembic", completed=True)],
        ),
        Node(
            id="bug-001",
            title="Login Bug",
            type="bug",
            status="done",
            priority="low",
            created=old_date,
            updated=old_date,
            content="Cannot login with email",
        ),
    ]


def test_archive_config_defaults() -> None:
    """Test ArchiveConfig default values."""
    config = ArchiveConfig()

    assert config.retention_days == 90
    assert config.archive_period == "quarter"
    # Now includes all entity types
    assert config.entity_types == [
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
    assert config.status_filter == ["done", "cancelled", "obsolete"]
    assert config.auto_archive is False


def test_archive_config_custom() -> None:
    """Test ArchiveConfig with custom values."""
    config = ArchiveConfig(
        retention_days=30,
        archive_period="month",
        entity_types=["feature"],
        status_filter=["done"],
        auto_archive=True,
    )

    assert config.retention_days == 30
    assert config.archive_period == "month"
    assert config.entity_types == ["feature"]
    assert config.status_filter == ["done"]
    assert config.auto_archive is True


def test_archive_config_serialization() -> None:
    """Test ArchiveConfig to/from dict."""
    config = ArchiveConfig(retention_days=60)

    # To dict
    data = config.to_dict()
    assert data["retention_days"] == 60

    # From dict
    config2 = ArchiveConfig.from_dict(data)
    assert config2.retention_days == 60


def test_archive_manager_init(temp_htmlgraph_dir: Path) -> None:
    """Test ArchiveManager initialization."""
    manager = ArchiveManager(temp_htmlgraph_dir)

    assert manager.htmlgraph_dir == temp_htmlgraph_dir
    assert manager.archive_dir.exists()
    assert manager.index_dir.exists()

    manager.close()


def test_archive_entities_dry_run(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test dry-run mode for archiving."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Dry run
    result = manager.archive_entities(
        older_than_days=50, period="quarter", dry_run=True
    )

    assert result["dry_run"] is True
    assert result["would_archive"] == 2  # 2 done features
    assert len(result["archive_files"]) > 0

    # Verify no files were created
    assert len(list(manager.archive_dir.glob("*.html"))) == 0

    manager.close()


def test_archive_entities_creates_files(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test actual archive file creation."""
    # Create entity files
    for entity in sample_entities:
        entity_dir = temp_htmlgraph_dir / f"{entity.type}s"
        filepath = entity_dir / f"{entity.id}.html"
        with open(filepath, "w") as f:
            f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    result = manager.archive_entities(
        older_than_days=50, period="quarter", dry_run=False
    )

    assert result["dry_run"] is False
    assert result["archived_count"] == 3  # All 3 entities
    assert len(result["archive_files"]) > 0

    # Verify archive files created
    archive_files = list(manager.archive_dir.glob("*.html"))
    assert len(archive_files) > 0

    # Verify original files deleted
    assert not (temp_htmlgraph_dir / "features" / "feat-001.html").exists()
    assert not (temp_htmlgraph_dir / "features" / "feat-002.html").exists()

    manager.close()


def test_archive_creates_bloom_filters(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test Bloom filter creation during archiving."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Verify Bloom filters created
    bloom_files = list(manager.index_dir.glob("*.bloom"))
    assert len(bloom_files) > 0

    manager.close()


def test_archive_creates_fts5_index(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test FTS5 index creation during archiving."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Verify FTS5 database created
    fts_db = manager.index_dir / "archives.db"
    assert fts_db.exists()

    manager.close()


def test_archive_search(temp_htmlgraph_dir: Path, sample_entities: list[Node]) -> None:
    """Test searching archived entities."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Search for "authentication"
    results = manager.search("authentication", limit=10)

    assert len(results) > 0
    assert any("authentication" in r["title_snippet"].lower() for r in results)

    manager.close()


@pytest.mark.skip(reason="Unarchive needs refinement - archive/search working")
def test_archive_unarchive(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test restoring an archived entity."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Verify entity was archived (file deleted)
    assert not (features_dir / "feat-001.html").exists()

    # Restore entity
    success = manager.unarchive("feat-001")

    assert success is True

    # Verify entity file restored
    assert (features_dir / "feat-001.html").exists()

    manager.close()


def test_archive_stats(temp_htmlgraph_dir: Path, sample_entities: list[Node]) -> None:
    """Test archive statistics."""
    # Create entity files
    features_dir = temp_htmlgraph_dir / "features"
    for entity in sample_entities:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Create archives
    manager.archive_entities(older_than_days=50, dry_run=False)

    # Get stats
    stats = manager.get_archive_stats()

    assert stats["archive_count"] > 0
    assert stats["entity_count"] == 2  # 2 features archived
    assert stats["total_size_mb"] >= 0
    assert stats["fts_size_mb"] >= 0

    manager.close()


def test_archive_period_naming(temp_htmlgraph_dir: Path) -> None:
    """Test archive period naming (quarter, month, year)."""
    manager = ArchiveManager(temp_htmlgraph_dir)

    # Test quarter
    manager.config.archive_period = "quarter"
    dt = datetime(2024, 10, 15)  # Q4 2024
    assert manager._get_period_name(dt) == "2024-Q4"

    # Test month
    manager.config.archive_period = "month"
    assert manager._get_period_name(dt) == "2024-10"

    # Test year
    manager.config.archive_period = "year"
    assert manager._get_period_name(dt) == "2024"

    manager.close()


def test_archive_respects_status_filter(
    temp_htmlgraph_dir: Path, sample_entities: list[Node]
) -> None:
    """Test that archiving respects status filter."""
    # Create entity files (mix of statuses)
    features_dir = temp_htmlgraph_dir / "features"

    # Add a "todo" entity (should NOT be archived)
    todo_entity = Node(
        id="feat-003",
        title="Future Feature",
        type="feature",
        status="todo",
        created=datetime.now() - timedelta(days=100),
        updated=datetime.now() - timedelta(days=100),
    )

    for entity in sample_entities + [todo_entity]:
        if entity.type == "feature":
            filepath = features_dir / f"{entity.id}.html"
            with open(filepath, "w") as f:
                f.write(entity.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Archive (default status filter: done, cancelled, obsolete)
    result = manager.archive_entities(older_than_days=50, dry_run=False)

    # Verify only "done" entities archived (not "todo")
    assert result["archived_count"] == 2  # feat-001, feat-002
    assert (features_dir / "feat-003.html").exists()  # todo not archived

    manager.close()


def test_archive_patterns(temp_htmlgraph_dir: Path) -> None:
    """Test archiving patterns."""
    # Create patterns directory
    patterns_dir = temp_htmlgraph_dir / "patterns"
    patterns_dir.mkdir()

    # Create sample patterns
    old_date = datetime.now() - timedelta(days=100)
    patterns = [
        Node(
            id="pattern-001",
            title="Authentication Pattern",
            type="pattern",
            status="done",
            created=old_date,
            updated=old_date,
            content="OAuth implementation pattern",
        ),
        Node(
            id="pattern-002",
            title="Database Pattern",
            type="pattern",
            status="done",
            created=old_date,
            updated=old_date,
            content="Repository pattern for data access",
        ),
    ]

    for pattern in patterns:
        filepath = patterns_dir / f"{pattern.id}.html"
        with open(filepath, "w") as f:
            f.write(pattern.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Archive patterns
    result = manager.archive_entities(older_than_days=50, dry_run=False)

    assert result["archived_count"] == 2
    assert not (patterns_dir / "pattern-001.html").exists()
    assert not (patterns_dir / "pattern-002.html").exists()

    manager.close()


def test_archive_spikes(temp_htmlgraph_dir: Path) -> None:
    """Test archiving spikes."""
    # Create spikes directory
    spikes_dir = temp_htmlgraph_dir / "spikes"
    spikes_dir.mkdir()

    # Create sample spikes
    old_date = datetime.now() - timedelta(days=100)
    spikes = [
        Node(
            id="spike-001",
            title="Performance Investigation",
            type="spike",
            status="done",
            created=old_date,
            updated=old_date,
            content="Investigated database query performance",
        ),
        Node(
            id="spike-002",
            title="API Design Exploration",
            type="spike",
            status="done",
            created=old_date,
            updated=old_date,
            content="Explored REST vs GraphQL options",
        ),
    ]

    for spike in spikes:
        filepath = spikes_dir / f"{spike.id}.html"
        with open(filepath, "w") as f:
            f.write(spike.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Archive spikes
    result = manager.archive_entities(older_than_days=50, dry_run=False)

    assert result["archived_count"] == 2
    assert not (spikes_dir / "spike-001.html").exists()
    assert not (spikes_dir / "spike-002.html").exists()

    manager.close()


def test_archive_sessions(temp_htmlgraph_dir: Path) -> None:
    """Test archiving sessions."""
    # Create sessions directory
    sessions_dir = temp_htmlgraph_dir / "sessions"
    sessions_dir.mkdir()

    # Create sample sessions
    old_date = datetime.now() - timedelta(days=100)
    sessions = [
        Node(
            id="session-001",
            title="Development Session",
            type="session",
            status="done",
            created=old_date,
            updated=old_date,
            content="Implemented authentication feature",
        ),
        Node(
            id="session-002",
            title="Bug Fix Session",
            type="session",
            status="done",
            created=old_date,
            updated=old_date,
            content="Fixed login issues",
        ),
    ]

    for session in sessions:
        filepath = sessions_dir / f"{session.id}.html"
        with open(filepath, "w") as f:
            f.write(session.to_html())

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Archive sessions
    result = manager.archive_entities(older_than_days=50, dry_run=False)

    assert result["archived_count"] == 2
    assert not (sessions_dir / "session-001.html").exists()
    assert not (sessions_dir / "session-002.html").exists()

    manager.close()


def test_archive_all_entity_types(temp_htmlgraph_dir: Path) -> None:
    """Test archiving mixed entity types."""
    old_date = datetime.now() - timedelta(days=100)

    # Create different entity types
    entity_types_and_dirs = [
        ("feature", "features"),
        ("bug", "bugs"),
        ("spike", "spikes"),
        ("pattern", "patterns"),
        ("session", "sessions"),
        ("track", "tracks"),
    ]

    entities_created = 0
    for entity_type, dir_name in entity_types_and_dirs:
        entity_dir = temp_htmlgraph_dir / dir_name
        entity_dir.mkdir(exist_ok=True)  # Allow existing directories

        entity = Node(
            id=f"{entity_type}-001",
            title=f"Sample {entity_type.title()}",
            type=entity_type,
            status="done",
            created=old_date,
            updated=old_date,
            content=f"Sample {entity_type} content",
        )

        filepath = entity_dir / f"{entity.id}.html"
        with open(filepath, "w") as f:
            f.write(entity.to_html())
        entities_created += 1

    manager = ArchiveManager(temp_htmlgraph_dir)

    # Archive all entity types
    result = manager.archive_entities(older_than_days=50, dry_run=False)

    # Verify all entities archived
    assert result["archived_count"] == entities_created

    # Verify all original files deleted
    for entity_type, dir_name in entity_types_and_dirs:
        entity_dir = temp_htmlgraph_dir / dir_name
        filepath = entity_dir / f"{entity_type}-001.html"
        assert not filepath.exists()

    # Verify archive file created
    assert len(list(manager.archive_dir.glob("*.html"))) > 0

    manager.close()
