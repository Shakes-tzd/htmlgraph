"""
Epic collection for managing large body of work items.

Extends BaseCollection with epic-specific builder support.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
    from htmlgraph.builders.epic import EpicBuilder

from htmlgraph.collections.base import BaseCollection


class EpicCollection(BaseCollection['EpicCollection']):
    """
    Collection interface for epics with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new epics.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> epic = sdk.epics.create("v2.0 Release") \\
        ...     .set_priority("high") \\
        ...     .set_target_date(date(2025, 6, 1)) \\
        ...     .add_child_features(["feat-001", "feat-002"]) \\
        ...     .save()
        >>>
        >>> # Query epics
        >>> active_epics = sdk.epics.where(status="in-progress")
    """

    _collection_name = "epics"
    _node_type = "epic"

    def __init__(self, sdk: 'SDK'):
        """
        Initialize epic collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "epics", "epic")
        self._sdk = sdk

    def create(self, title: str, **kwargs) -> 'EpicBuilder':
        """
        Create a new epic with fluent interface.

        Args:
            title: Epic title/summary
            **kwargs: Additional epic properties

        Returns:
            EpicBuilder for method chaining

        Example:
            >>> epic = sdk.epics.create("Mobile App Launch") \\
            ...     .set_business_value("Expand to mobile users") \\
            ...     .set_success_criteria(["10k downloads", "4.5 rating"]) \\
            ...     .save()
        """
        from htmlgraph.builders.epic import EpicBuilder
        return EpicBuilder(self._sdk, title, **kwargs)
