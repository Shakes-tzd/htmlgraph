from __future__ import annotations

"""
Pattern collection for managing workflow patterns.

Extends BaseCollection with pattern-specific query methods.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import Node
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class PatternCollection(BaseCollection["PatternCollection"]):
    """
    Collection interface for workflow patterns.

    Provides all base collection methods plus pattern-specific
    queries for finding optimal patterns and anti-patterns.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> pattern = sdk.patterns.create("File-then-Edit Pattern") \\
        ...     .set_sequence(["Read", "Edit"]) \\
        ...     .save()
        >>>
        >>> # Query patterns
        >>> optimal = sdk.patterns.get_optimal_patterns()
        >>> anti = sdk.patterns.get_anti_patterns()
    """

    _collection_name = "patterns"
    _node_type = "pattern"

    def __init__(self, sdk: SDK):
        """
        Initialize pattern collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "patterns", "pattern")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders import PatternBuilder

        self._builder_class = PatternBuilder

    def find_by_sequence(self, sequence: list[str]) -> list[Node]:
        """
        Find patterns matching a specific tool sequence.

        Args:
            sequence: List of tool names in order (e.g., ["Read", "Edit"])

        Returns:
            List of patterns with matching sequence

        Example:
            >>> patterns = sdk.patterns.find_by_sequence(["Read", "Edit"])
        """
        seq_str = "->".join(sequence)
        return [
            p
            for p in self.all()
            if hasattr(p, "sequence") and "->".join(p.sequence) == seq_str
        ]

    def get_anti_patterns(self) -> list[Node]:
        """
        Get all anti-patterns.

        Returns:
            List of anti-pattern nodes

        Example:
            >>> anti_patterns = sdk.patterns.get_anti_patterns()
        """
        return self.where(pattern_type="anti-pattern")

    def get_optimal_patterns(self) -> list[Node]:
        """
        Get all optimal patterns.

        Returns:
            List of optimal pattern nodes

        Example:
            >>> optimal = sdk.patterns.get_optimal_patterns()
        """
        return self.where(pattern_type="optimal")
