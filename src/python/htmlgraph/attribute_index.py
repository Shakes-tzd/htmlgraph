from __future__ import annotations

"""
Attribute Index for O(1) attribute-based lookups.

Provides efficient attribute-based queries by maintaining
indexes for common node attributes. This enables O(1) lookups for:
- Finding all nodes with a specific status
- Finding all nodes with a specific priority
- Finding all nodes with a specific type

Without this index, finding nodes by attribute requires scanning
all nodes in the graph - O(n) complexity.
"""


from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import Node


@dataclass
class AttributeIndex:
    """
    Attribute-based index for efficient node lookups.

    Maintains indexes for common node attributes:
    - _by_status: Maps status value to set of node IDs
    - _by_priority: Maps priority value to set of node IDs
    - _by_type: Maps type value to set of node IDs

    The indexes are lazy-built on first access and updated
    incrementally as nodes are added/modified/removed.

    Example:
        index = AttributeIndex()
        index.rebuild(graph.nodes)

        # O(1) lookup of all todo nodes
        todo_ids = index.get_by_status("todo")

        # O(1) lookup of all high-priority nodes
        high_priority_ids = index.get_by_priority("high")
    """

    _by_status: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _by_priority: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _by_type: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _is_built: bool = False

    def add_node(self, node_id: str, node: Node) -> None:
        """
        Add a node to all relevant indexes.

        Args:
            node_id: Node ID
            node: Node object with attributes to index
        """
        self._by_status[node.status].add(node_id)
        self._by_priority[node.priority].add(node_id)
        self._by_type[node.type].add(node_id)

    def remove_node(self, node_id: str, node: Node) -> None:
        """
        Remove a node from all indexes.

        Args:
            node_id: Node ID
            node: Node object with attributes to remove
        """
        self._by_status[node.status].discard(node_id)
        self._by_priority[node.priority].discard(node_id)
        self._by_type[node.type].discard(node_id)

        # Clean up empty sets
        if not self._by_status[node.status]:
            del self._by_status[node.status]
        if not self._by_priority[node.priority]:
            del self._by_priority[node.priority]
        if not self._by_type[node.type]:
            del self._by_type[node.type]

    def update_node(self, node_id: str, old_node: Node, new_node: Node) -> None:
        """
        Update a node's indexed attributes.

        Removes old attributes and adds new ones atomically.

        Args:
            node_id: Node ID
            old_node: Previous node object
            new_node: Updated node object
        """
        # Remove old attributes
        self._by_status[old_node.status].discard(node_id)
        self._by_priority[old_node.priority].discard(node_id)
        self._by_type[old_node.type].discard(node_id)

        # Add new attributes
        self._by_status[new_node.status].add(node_id)
        self._by_priority[new_node.priority].add(node_id)
        self._by_type[new_node.type].add(node_id)

        # Clean up empty sets from old values
        if not self._by_status[old_node.status]:
            del self._by_status[old_node.status]
        if not self._by_priority[old_node.priority]:
            del self._by_priority[old_node.priority]
        if not self._by_type[old_node.type]:
            del self._by_type[old_node.type]

    def get_by_status(self, status: str) -> set[str]:
        """
        Get all node IDs with a specific status (O(1) lookup).

        Args:
            status: Status value to search for (e.g., "todo", "in-progress", "done")

        Returns:
            Set of node IDs with the given status
        """
        return self._by_status.get(status, set()).copy()

    def get_by_priority(self, priority: str) -> set[str]:
        """
        Get all node IDs with a specific priority (O(1) lookup).

        Args:
            priority: Priority value to search for (e.g., "low", "medium", "high")

        Returns:
            Set of node IDs with the given priority
        """
        return self._by_priority.get(priority, set()).copy()

    def get_by_type(self, node_type: str) -> set[str]:
        """
        Get all node IDs with a specific type (O(1) lookup).

        Args:
            node_type: Type value to search for (e.g., "feature", "bug", "task")

        Returns:
            Set of node IDs with the given type
        """
        return self._by_type.get(node_type, set()).copy()

    def rebuild(self, nodes: dict[str, Node]) -> None:
        """
        Rebuild the entire index from a node dictionary.

        Args:
            nodes: Dictionary mapping node_id to Node objects
        """
        self.clear()

        for node_id, node in nodes.items():
            self.add_node(node_id, node)

        self._is_built = True

    def ensure_built(self, nodes: dict[str, Node]) -> None:
        """
        Ensure index is built (lazy initialization).

        Args:
            nodes: Dictionary mapping node_id to Node objects
        """
        if not self._is_built:
            self.rebuild(nodes)

    def clear(self) -> None:
        """Clear all indexes."""
        self._by_status.clear()
        self._by_priority.clear()
        self._by_type.clear()
        self._is_built = False

    @property
    def is_built(self) -> bool:
        """Check if index has been built."""
        return self._is_built

    def stats(self) -> dict:
        """
        Get index statistics.

        Returns:
            Dictionary with index statistics
        """
        return {
            "is_built": self._is_built,
            "statuses": list(self._by_status.keys()),
            "priorities": list(self._by_priority.keys()),
            "types": list(self._by_type.keys()),
            "total_nodes_by_status": {
                status: len(ids) for status, ids in self._by_status.items()
            },
            "total_nodes_by_priority": {
                priority: len(ids) for priority, ids in self._by_priority.items()
            },
            "total_nodes_by_type": {
                node_type: len(ids) for node_type, ids in self._by_type.items()
            },
        }
