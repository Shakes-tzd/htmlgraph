"""
Feature collection for managing feature work items.

Extends BaseCollection with feature-specific builder support.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
    from htmlgraph.builders import FeatureBuilder

from htmlgraph.collections.base import BaseCollection


class FeatureCollection(BaseCollection['FeatureCollection']):
    """
    Collection interface for features with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new features.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> feature = sdk.features.create("User Authentication") \\
        ...     .set_priority("high") \\
        ...     .add_steps(["Design schema", "Implement API", "Add tests"]) \\
        ...     .save()
        >>>
        >>> # Query features
        >>> high_priority = sdk.features.where(status="todo", priority="high")
        >>> all_features = sdk.features.all()
    """

    _collection_name = "features"
    _node_type = "feature"

    def __init__(self, sdk: 'SDK'):
        """
        Initialize feature collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "features", "feature")
        self._sdk = sdk

    def create(self, title: str, **kwargs) -> FeatureBuilder:
        """
        Create a new feature with fluent interface.

        Args:
            title: Feature title
            **kwargs: Additional feature properties

        Returns:
            FeatureBuilder for method chaining

        Example:
            >>> feature = sdk.features.create("User Auth") \\
            ...     .set_priority("high") \\
            ...     .add_steps(["Login", "Logout"]) \\
            ...     .save()
        """
        from htmlgraph.builders import FeatureBuilder
        return FeatureBuilder(self._sdk, title, **kwargs)
