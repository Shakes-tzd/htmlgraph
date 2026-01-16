"""
Test SQLiteFeatureRepository compliance.

Runs all compliance tests against SQLiteFeatureRepository implementation.
"""

import tempfile
from pathlib import Path

import pytest
from htmlgraph.repositories import SQLiteFeatureRepository

from .test_feature_repository_compliance import (
    FeatureRepositoryComplianceTests,
)


class TestSQLiteFeatureRepository(FeatureRepositoryComplianceTests):
    """Test SQLiteFeatureRepository against compliance suite."""

    @pytest.fixture
    def repo(self):
        """Create a fresh SQLiteFeatureRepository for each test."""
        # Use temporary database for test isolation
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = SQLiteFeatureRepository(db_path=db_path, auto_load=True)
            yield repo
