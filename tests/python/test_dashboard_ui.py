"""
Playwright tests for HtmlGraph dashboard UI.

Note: These tests require:
1. HTMLGRAPH_UI_TESTS=1 environment variable to be set
2. Dashboard server running on http://localhost:8080

Run with: HTMLGRAPH_UI_TESTS=1 uv run pytest tests/python/test_dashboard_ui.py -v

The tests verify that the dashboard HTML structure matches expectations without
requiring complex Playwright fixtures. They use static analysis instead.
"""

import os
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("HTMLGRAPH_UI_TESTS") != "1",
    reason="UI tests require HTMLGRAPH_UI_TESTS=1 environment variable.",
)


@pytest.fixture
def dashboard_html():
    """Load the dashboard HTML file for static analysis."""
    dashboard_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "python"
        / "htmlgraph"
        / "dashboard.html"
    )
    if not dashboard_path.exists():
        pytest.skip("Dashboard HTML file not found")
    with open(dashboard_path) as f:
        return f.read()


def test_dashboard_title(dashboard_html):
    """Test that dashboard has correct page title."""
    assert "<title>HtmlGraph Dashboard</title>" in dashboard_html


def test_dashboard_heading(dashboard_html):
    """Test that dashboard has correct main heading."""
    assert '<h1 class="brand-title">HtmlGraph</h1>' in dashboard_html


def test_dashboard_tagline(dashboard_html):
    """Test that dashboard has correct tagline."""
    assert "HTML is All You Need" in dashboard_html


def test_theme_toggle_button(dashboard_html):
    """Test that theme toggle button exists in HTML."""
    assert 'id="theme-toggle"' in dashboard_html
    assert 'aria-label="Toggle theme"' in dashboard_html


def test_view_navigation_buttons(dashboard_html):
    """Test that all view navigation buttons are defined."""
    # Check for view toggle buttons with correct data-view attributes
    assert 'data-view="kanban"' in dashboard_html
    assert 'data-view="graph"' in dashboard_html
    assert 'data-view="analytics"' in dashboard_html
    assert 'data-view="agents"' in dashboard_html
    assert 'data-view="sessions"' in dashboard_html


def test_kanban_structure(dashboard_html):
    """Test that kanban view structure exists."""
    # Check for kanban column classes
    # The columns are rendered dynamically with class="track-column ${status}"
    # So we just check that the template structure exists
    assert "track-column" in dashboard_html
    assert "track-column-header" in dashboard_html
    assert "track-column-cards" in dashboard_html


def test_sessions_view_structure(dashboard_html):
    """Test that sessions view structure exists."""
    assert "Sessions" in dashboard_html
    # Sessions section should exist
    match = re.search(r'data-view="sessions"', dashboard_html)
    assert match is not None, "Sessions view button not found"


def test_feature_card_structure(dashboard_html):
    """Test that card structures are defined."""
    # Features are rendered as divs with class "track-column"
    # Check for card-related classes and structures
    assert "card" in dashboard_html.lower() or "track-column" in dashboard_html, (
        "Card structure not found in dashboard"
    )


def test_dashboard_uses_html5(dashboard_html):
    """Test that dashboard uses HTML5 doctype."""
    assert dashboard_html.startswith(
        "<!DOCTYPE html>"
    ) or dashboard_html.strip().startswith("<!DOCTYPE html>")


def test_dashboard_has_viewport_meta(dashboard_html):
    """Test that dashboard includes viewport meta tag for responsive design."""
    assert 'name="viewport"' in dashboard_html


def test_activity_feed_section(dashboard_html):
    """Test that activity feed section exists."""
    # Check for activity feed heading
    assert (
        "Agent Activity Feed" in dashboard_html or "activity" in dashboard_html.lower()
    )


@pytest.mark.skip(reason="Requires active server and Playwright fixtures")
def test_theme_toggle_interactive(dashboard_html):
    """Test theme toggle button functionality (requires running server)."""
    # This test would require Playwright fixtures and a running server
    # Keeping as placeholder for future implementation
    pass


@pytest.mark.skip(reason="Requires active server and Playwright fixtures")
def test_view_navigation_interactive(dashboard_html):
    """Test navigation between different views (requires running server)."""
    # This test would require Playwright fixtures and a running server
    # Keeping as placeholder for future implementation
    pass
