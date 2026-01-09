"""
Pytest configuration and fixtures for HtmlGraph test suite.

This module provides shared test infrastructure including environment variable
cleanup to ensure test isolation and prevent environment pollution between tests.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def cleanup_env_vars():
    """
    Clean up HtmlGraph environment variables before and after each test.

    This fixture ensures that environment variables set during one test don't
    pollute subsequent tests, which is critical for tests that verify parent-child
    event relationships and session linking.

    Also ensures database timestamps are distinct between tests by adding a small
    sleep after each test (SQLite CURRENT_TIMESTAMP has 1-second resolution).

    HtmlGraph environment variables managed:
    - HTMLGRAPH_PARENT_ACTIVITY: Parent event ID for event linking
    - HTMLGRAPH_PARENT_SESSION: Parent session ID
    - HTMLGRAPH_PARENT_SESSION_ID: Alternative parent session ID
    - HTMLGRAPH_PARENT_AGENT: Parent agent identifier
    - HTMLGRAPH_PARENT_EVENT: Parent event identifier
    - HTMLGRAPH_PARENT_TRACK: Parent track identifier
    - HTMLGRAPH_AGENT: Current agent name
    - HTMLGRAPH_SUBAGENT_TYPE: Subagent type identifier
    """
    env_vars = [
        "HTMLGRAPH_PARENT_ACTIVITY",
        "HTMLGRAPH_PARENT_SESSION",
        "HTMLGRAPH_PARENT_SESSION_ID",
        "HTMLGRAPH_PARENT_AGENT",
        "HTMLGRAPH_PARENT_EVENT",
        "HTMLGRAPH_PARENT_TRACK",
        "HTMLGRAPH_AGENT",
        "HTMLGRAPH_SUBAGENT_TYPE",
    ]

    # Clean before test - preserve original values
    original_values = {}
    for var in env_vars:
        original_values[var] = os.environ.pop(var, None)

    yield

    # Clean after test - restore original values if they existed
    for var in env_vars:
        # Remove any value set during the test
        if var in os.environ:
            del os.environ[var]
        # Restore original value if it existed before the test
        if original_values[var] is not None:
            os.environ[var] = original_values[var]
