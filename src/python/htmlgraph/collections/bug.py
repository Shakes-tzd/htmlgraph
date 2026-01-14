from __future__ import annotations

"""
Bug collection for managing bug report work items.

Extends BaseCollection with bug-specific builder support.
"""


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK

from htmlgraph.collections.base import BaseCollection


class BugCollection(BaseCollection["BugCollection"]):
    """
    Collection interface for bugs with builder support.

    Provides all base collection methods plus a fluent builder
    interface for creating new bugs.

    Example:
        >>> sdk = SDK(agent="claude")
        >>> bug = sdk.bugs.create("Login button broken") \\
        ...     .set_priority("critical") \\
        ...     .set_severity("high") \\
        ...     .set_repro_steps(["Go to login", "Click button"]) \\
        ...     .save()
        >>>
        >>> # Query bugs
        >>> critical_bugs = sdk.bugs.where(priority="critical")
    """

    _collection_name = "bugs"
    _node_type = "bug"

    def __init__(self, sdk: SDK):
        """
        Initialize bug collection.

        Args:
            sdk: Parent SDK instance
        """
        super().__init__(sdk, "bugs", "bug")
        self._sdk = sdk

        # Set builder class for create() method
        from htmlgraph.builders.bug import BugBuilder

        self._builder_class = BugBuilder
