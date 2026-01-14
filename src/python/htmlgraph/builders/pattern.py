from __future__ import annotations

"""
Pattern builder for creating workflow pattern nodes.

Extends BaseBuilder with pattern-specific methods for
tracking optimal and anti-pattern tool sequences.
"""


from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import Pattern
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder
from htmlgraph.ids import generate_id


class PatternBuilder(BaseBuilder["PatternBuilder"]):
    """
    Fluent builder for creating workflow patterns.

    Patterns represent observed tool usage sequences that are
    either optimal (should encourage) or anti-patterns (should warn against).

    Example:
        >>> sdk = SDK(agent="claude")
        >>> pattern = sdk.patterns.create("Efficient Testing Pattern") \\
        ...     .set_pattern_type("optimal") \\
        ...     .set_sequence(["Edit", "Bash", "Edit"]) \\
        ...     .set_success_rate(0.92) \\
        ...     .set_recommendation("Write tests, run them, fix failures") \\
        ...     .save()
    """

    node_type = "pattern"

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize pattern builder with pattern-specific defaults."""
        super().__init__(sdk, title, **kwargs)
        # Set pattern-specific defaults
        if "pattern_type" not in self._data:
            self._data["pattern_type"] = "neutral"
        if "sequence" not in self._data:
            self._data["sequence"] = []
        if "detection_count" not in self._data:
            self._data["detection_count"] = 0

    def set_pattern_type(self, ptype: str) -> PatternBuilder:
        """
        Set pattern type: optimal, anti-pattern, or neutral.

        Args:
            ptype: Pattern classification (optimal/anti-pattern/neutral)

        Returns:
            Self for method chaining

        Example:
            >>> pattern.set_pattern_type("optimal")
        """
        self._data["pattern_type"] = ptype
        return self

    def set_sequence(self, sequence: list[str]) -> PatternBuilder:
        """
        Set the tool sequence for this pattern.

        Args:
            sequence: List of tool names in order (e.g., ["Edit", "Bash", "Read"])

        Returns:
            Self for method chaining

        Example:
            >>> pattern.set_sequence(["Edit", "Bash", "Bash", "Edit"])
        """
        self._data["sequence"] = sequence
        return self

    def set_success_rate(self, rate: float) -> PatternBuilder:
        """
        Set success rate (0.0-1.0).

        Args:
            rate: Success rate as decimal (0.0 = 0%, 1.0 = 100%)

        Returns:
            Self for method chaining

        Example:
            >>> pattern.set_success_rate(0.85)
        """
        self._data["success_rate"] = rate
        return self

    def set_recommendation(self, rec: str) -> PatternBuilder:
        """
        Set recommendation text for when this pattern is detected.

        Args:
            rec: Recommendation message

        Returns:
            Self for method chaining

        Example:
            >>> pattern.set_recommendation("Consider running tests after changes")
        """
        self._data["recommendation"] = rec
        return self

    def increment_detection(self) -> PatternBuilder:
        """
        Increment detection count (number of times pattern was observed).

        Returns:
            Self for method chaining

        Example:
            >>> pattern.increment_detection()
        """
        self._data["detection_count"] = self._data.get("detection_count", 0) + 1
        return self

    def set_detection_count(self, count: int) -> PatternBuilder:
        """
        Set detection count directly.

        Args:
            count: Number of times pattern was detected

        Returns:
            Self for method chaining
        """
        self._data["detection_count"] = count
        return self

    def set_first_detected(self, dt: datetime) -> PatternBuilder:
        """
        Set first detection timestamp.

        Args:
            dt: Timestamp of first detection

        Returns:
            Self for method chaining
        """
        self._data["first_detected"] = dt
        return self

    def set_last_detected(self, dt: datetime) -> PatternBuilder:
        """
        Set last detection timestamp.

        Args:
            dt: Timestamp of last detection

        Returns:
            Self for method chaining
        """
        self._data["last_detected"] = dt
        return self

    def save(self) -> Pattern:
        """
        Save the pattern and return the Node instance.

        Overrides BaseBuilder.save() to ensure patterns are saved
        to the patterns directory.

        Returns:
            Created Pattern node instance
        """
        # Generate collision-resistant ID if not provided
        if "id" not in self._data:
            self._data["id"] = generate_id(
                node_type="pattern",
                title=self._data.get("title", ""),
            )

        # Import Pattern here to avoid circular imports
        from htmlgraph.models import Pattern

        node = Pattern(**self._data)

        # Save to the patterns collection
        if hasattr(self._sdk, "patterns") and self._sdk.patterns is not None:
            graph = self._sdk.patterns._ensure_graph()
            graph.add(node)
        else:
            # Fallback: create new graph
            from htmlgraph.graph import HtmlGraph

            graph_path = self._sdk._directory / "patterns"
            graph = HtmlGraph(graph_path, auto_load=False)
            graph.add(node)

        return node
