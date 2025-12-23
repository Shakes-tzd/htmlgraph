"""
Feature builder for creating feature nodes.

Extends BaseBuilder with feature-specific methods like
capability management.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class FeatureBuilder(BaseBuilder['FeatureBuilder']):
    """
    Fluent builder for creating features.

    Inherits common builder methods from BaseBuilder and adds
    feature-specific capabilities like required_capabilities and
    capability_tags for routing.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> feature = sdk.features.create("User Authentication") \\
        ...     .set_priority("high") \\
        ...     .add_steps(["Create auth endpoint", "Add middleware"]) \\
        ...     .set_required_capabilities(["python", "security"]) \\
        ...     .save()
    """

    node_type = "feature"

    def set_required_capabilities(self, capabilities: list[str]) -> 'FeatureBuilder':
        """
        Set required capabilities for this feature.

        Used by routing system to match features to agents with
        appropriate skills.

        Args:
            capabilities: List of capability strings (e.g., ['python', 'testing'])

        Returns:
            Self for method chaining

        Example:
            >>> feature.set_required_capabilities(["python", "fastapi", "postgresql"])
        """
        self._data["required_capabilities"] = capabilities
        return self

    def add_capability_tag(self, tag: str) -> 'FeatureBuilder':
        """
        Add a capability tag for flexible matching.

        Tags allow fuzzy matching in routing (e.g., "backend" matches
        both "python" and "nodejs" capabilities).

        Args:
            tag: Tag string (e.g., 'frontend', 'backend', 'database')

        Returns:
            Self for method chaining

        Example:
            >>> feature.add_capability_tag("backend").add_capability_tag("api")
        """
        if "capability_tags" not in self._data:
            self._data["capability_tags"] = []
        self._data["capability_tags"].append(tag)
        return self

    def add_capability_tags(self, tags: list[str]) -> 'FeatureBuilder':
        """
        Add multiple capability tags.

        Args:
            tags: List of tag strings

        Returns:
            Self for method chaining

        Example:
            >>> feature.add_capability_tags(["frontend", "react", "typescript"])
        """
        if "capability_tags" not in self._data:
            self._data["capability_tags"] = []
        self._data["capability_tags"].extend(tags)
        return self
