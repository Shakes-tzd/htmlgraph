"""
Test MemoryFeatureRepository compliance.

Runs all compliance tests against MemoryFeatureRepository implementation.
"""

import pytest
from htmlgraph.repositories import MemoryFeatureRepository

from .test_feature_repository_compliance import (
    FeatureRepositoryComplianceTests,
)


class TestMemoryFeatureRepository(FeatureRepositoryComplianceTests):
    """Test MemoryFeatureRepository against compliance suite."""

    @pytest.fixture
    def repo(self):
        """Create a fresh MemoryFeatureRepository for each test."""
        return MemoryFeatureRepository(auto_load=True)
