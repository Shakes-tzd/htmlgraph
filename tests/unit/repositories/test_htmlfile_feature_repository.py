"""
Test HTMLFileFeatureRepository compliance.

Runs all compliance tests against HTMLFileFeatureRepository implementation.
"""

import tempfile
from pathlib import Path

import pytest
from htmlgraph.repositories import HTMLFileFeatureRepository

from .test_feature_repository_compliance import (
    FeatureRepositoryComplianceTests,
)


class TestHTMLFileFeatureRepository(FeatureRepositoryComplianceTests):
    """Test HTMLFileFeatureRepository against compliance suite."""

    @pytest.fixture
    def repo(self):
        """Create a fresh HTMLFileFeatureRepository for each test."""
        # Use temporary directory for test isolation
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = HTMLFileFeatureRepository(
                directory=Path(tmpdir) / "features", auto_load=True
            )
            yield repo
