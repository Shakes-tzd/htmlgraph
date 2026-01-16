"""
Concrete Track Repository Implementation Tests.

Tests all three TrackRepository implementations against compliance suite.
"""

import pytest
from htmlgraph.repositories import (
    HTMLFileTrackRepository,
    MemoryTrackRepository,
    SQLiteTrackRepository,
)

from tests.unit.repositories.test_track_repository_compliance import (
    TrackRepositoryComplianceTests,
)


class TestMemoryTrackRepository(TrackRepositoryComplianceTests):
    """Test MemoryTrackRepository implementation."""

    @pytest.fixture
    def repo(self):
        """Provide MemoryTrackRepository instance."""
        return MemoryTrackRepository()


class TestHTMLFileTrackRepository(TrackRepositoryComplianceTests):
    """Test HTMLFileTrackRepository implementation."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Provide HTMLFileTrackRepository instance with temp directory."""
        tracks_dir = tmp_path / "tracks"
        tracks_dir.mkdir(exist_ok=True)
        return HTMLFileTrackRepository(tracks_dir)


class TestSQLiteTrackRepository(TrackRepositoryComplianceTests):
    """Test SQLiteTrackRepository implementation."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Provide SQLiteTrackRepository instance with temp database."""
        db_path = tmp_path / "test.db"
        return SQLiteTrackRepository(db_path)
