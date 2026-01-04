"""Tests for the computational reflection module."""

from unittest.mock import MagicMock

import pytest
from htmlgraph.reflection import (
    ComputationalReflection,
    ReflectionItem,
    get_reflection_context,
)


class TestReflectionItem:
    """Tests for ReflectionItem dataclass."""

    def test_to_dict(self):
        """Test ReflectionItem serialization."""
        item = ReflectionItem(
            category="blocker",
            priority=5,
            title="Test blocker",
            detail="This is blocking work",
            source_id="feat-123",
        )
        result = item.to_dict()

        assert result["category"] == "blocker"
        assert result["priority"] == 5
        assert result["title"] == "Test blocker"
        assert result["detail"] == "This is blocking work"
        assert result["source_id"] == "feat-123"

    def test_to_dict_without_source_id(self):
        """Test ReflectionItem serialization without source_id."""
        item = ReflectionItem(
            category="anti_pattern",
            priority=3,
            title="Avoid: Edit-Edit-Edit",
            detail="Multiple edits without testing",
        )
        result = item.to_dict()

        assert result["source_id"] is None


class TestComputationalReflection:
    """Tests for ComputationalReflection class."""

    @pytest.fixture
    def mock_sdk(self):
        """Create a mock SDK for testing."""
        sdk = MagicMock()
        sdk.find_bottlenecks.return_value = []
        sdk.features.where.return_value = []
        sdk.sessions.all.return_value = []
        sdk.spikes.all.return_value = []
        sdk.recommend_next_work.return_value = []
        return sdk

    def test_get_actionable_context_empty(self, mock_sdk):
        """Test getting context when no history exists."""
        reflection = ComputationalReflection(mock_sdk)
        context = reflection.get_actionable_context()

        assert "summary" in context
        assert "items" in context
        assert "injected_at" in context
        assert context["item_count"] == 0

    def test_get_actionable_context_with_bottleneck(self, mock_sdk):
        """Test getting context with a bottleneck."""
        mock_sdk.find_bottlenecks.return_value = [
            {
                "id": "feat-123",
                "title": "Authentication Feature",
                "blocks_count": 3,
            }
        ]

        reflection = ComputationalReflection(mock_sdk)
        context = reflection.get_actionable_context()

        assert context["item_count"] >= 1
        assert any(item["category"] == "blocker" for item in context["items"])

    def test_get_actionable_context_with_recommendation(self, mock_sdk):
        """Test getting context with a recommendation."""
        mock_sdk.recommend_next_work.return_value = [
            {
                "id": "feat-456",
                "title": "Next Feature",
                "reasons": ["Critical priority"],
            }
        ]

        reflection = ComputationalReflection(mock_sdk)
        context = reflection.get_actionable_context()

        assert context["item_count"] >= 1
        assert any(item["category"] == "recommendation" for item in context["items"])

    def test_max_items_limit(self, mock_sdk):
        """Test that max items is respected."""
        # Create many bottlenecks
        mock_sdk.find_bottlenecks.return_value = [
            {"id": f"feat-{i}", "title": f"Feature {i}", "blocks_count": i}
            for i in range(10)
        ]

        reflection = ComputationalReflection(mock_sdk)
        context = reflection.get_actionable_context()

        assert context["item_count"] <= ComputationalReflection.MAX_ITEMS

    def test_format_for_injection_empty(self, mock_sdk):
        """Test formatting empty context."""
        reflection = ComputationalReflection(mock_sdk)
        formatted = reflection.format_for_injection()

        # Empty context should return empty string
        assert formatted == ""

    def test_format_for_injection_with_items(self, mock_sdk):
        """Test formatting context with items."""
        mock_sdk.find_bottlenecks.return_value = [
            {
                "id": "feat-123",
                "title": "Blocking Feature",
                "blocks_count": 3,
            }
        ]

        reflection = ComputationalReflection(mock_sdk)
        formatted = reflection.format_for_injection()

        assert "## Computed Reflections" in formatted
        assert "Summary:" in formatted
        assert "Blocking Feature" in formatted

    def test_caching(self, mock_sdk):
        """Test that results are cached."""
        reflection = ComputationalReflection(mock_sdk)

        # First call
        reflection.get_actionable_context()

        # Second call should use cache
        reflection.get_actionable_context()

        # SDK methods should only be called once
        assert mock_sdk.find_bottlenecks.call_count == 1

    def test_build_summary_blockers(self, mock_sdk):
        """Test summary building with blockers."""
        reflection = ComputationalReflection(mock_sdk)
        items = [
            ReflectionItem(
                category="blocker",
                priority=5,
                title="Blocker 1",
                detail="Details",
            ),
            ReflectionItem(
                category="blocker",
                priority=4,
                title="Blocker 2",
                detail="Details",
            ),
        ]

        summary = reflection._build_summary(items)
        assert "2 blockers" in summary

    def test_build_summary_empty(self, mock_sdk):
        """Test summary building with no items."""
        reflection = ComputationalReflection(mock_sdk)
        summary = reflection._build_summary([])
        assert summary == "No actionable context found."


class TestGetReflectionContext:
    """Tests for the convenience function."""

    def test_get_reflection_context(self):
        """Test the get_reflection_context convenience function."""
        mock_sdk = MagicMock()
        mock_sdk.find_bottlenecks.return_value = []
        mock_sdk.features.where.return_value = []
        mock_sdk.sessions.all.return_value = []
        mock_sdk.spikes.all.return_value = []
        mock_sdk.recommend_next_work.return_value = [
            {
                "id": "feat-789",
                "title": "Recommended Task",
                "reasons": ["High priority"],
            }
        ]

        result = get_reflection_context(mock_sdk)

        # Should return formatted string
        assert isinstance(result, str)
        if result:  # May be empty if no items
            assert "Computed Reflections" in result
