from __future__ import annotations

"""
Chore collection for managing maintenance task work items.

Extends BaseCollection with chore-specific builder support.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class ChoreCollection(BaseCollection["ChoreCollection"]):
    """
    Collection interface for chores with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new chores.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> chore = sdk.chores.create("Update dependencies") \\
        ...     .set_priority("low") \\
        ...     .set_chore_type("maintenance") \\
        ...     .set_recurring(interval_days=30) \\
        ...     .save()
        >>>
        >>> # Query chores
        >>> maintenance = sdk.chores.where(status="todo")
    """

    _collection_name = "chores"
    _node_type = "chore"

    def __init__(self, sdk: SDK):
        """
        Initialize chore collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "chores", "chore")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders.chore import ChoreBuilder

        self._builder_class = ChoreBuilder
