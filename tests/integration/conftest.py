"""
Pytest configuration and fixtures for integration tests.

Provides shared test infrastructure including database fixtures
for integration testing.
"""

import tempfile
from pathlib import Path

import pytest
from htmlgraph.db.schema import HtmlGraphDB


@pytest.fixture
def isolated_db():
    """
    Create an isolated temporary database for testing.

    Returns the path to the temporary database file which is
    automatically cleaned up after the test.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = HtmlGraphDB(str(db_path))
        db.connect()
        db.create_tables()
        db.disconnect()
        yield db_path


@pytest.fixture
def temp_graph_dir():
    """Create temporary graph directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_dir = Path(tmpdir) / ".htmlgraph"
        graph_dir.mkdir(parents=True)
        yield graph_dir
