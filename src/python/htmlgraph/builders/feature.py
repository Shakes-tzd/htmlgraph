from __future__ import annotations

"""
Feature builder for creating feature nodes.

Extends BaseBuilder with feature-specific methods like
capability management.
"""


from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.builders.base import BaseBuilder


class FeatureBuilder(BaseBuilder["FeatureBuilder"]):
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

    def __init__(self, sdk: SDK, title: str, **kwargs: Any):
        """Initialize feature builder with agent attribution and validation."""
        # Validate title before creating builder

        stripped_title = title.strip() if title else ""
        if not stripped_title:
            raise ValueError("Feature title cannot be empty or whitespace only")
        if len(stripped_title) < 3:
            raise ValueError("Feature title must be at least 3 characters")

        super().__init__(sdk, title, **kwargs)
        # Auto-assign agent from SDK for work tracking
        if sdk._agent_id:
            self._data["agent_assigned"] = sdk._agent_id
        elif "agent_assigned" not in self._data:
            # Log warning if agent not assigned (defensive check)
            import logging

            logging.warning(
                f"Creating feature '{self._data.get('title', 'Unknown')}' without agent attribution. "
                "Pass agent='name' to SDK() initialization."
            )

    def set_required_capabilities(self, capabilities: list[str]) -> FeatureBuilder:
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

    def add_capability_tag(self, tag: str) -> FeatureBuilder:
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

    def add_capability_tags(self, tags: list[str]) -> FeatureBuilder:
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
