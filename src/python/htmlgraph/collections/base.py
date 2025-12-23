"""
Base collection class for managing nodes.

Provides common collection functionality for all node types
with lazy-loading, filtering, and batch operations.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic, Any, Iterator
from contextlib import contextmanager
from datetime import datetime

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK
    from htmlgraph.models import Node

CollectionT = TypeVar('CollectionT', bound='BaseCollection')


class BaseCollection(Generic[CollectionT]):
    """
    Generic collection interface for any node type.

    Provides common functionality for managing collections of nodes:
    - Lazy-loading of graph data
    - Filtering and querying
    - Batch operations (update, delete, assign)
    - Agent claim/release workflow

    Subclasses should override `_collection_name` and `_node_type` class attributes.

    Example:
        >>> class FeatureCollection(BaseCollection['FeatureCollection']):
        ...     _collection_name = "features"
        ...     _node_type = "feature"
        ...
        >>> sdk = SDK(agent="claude")
        >>> features = sdk.features.where(status="todo", priority="high")
    """

    _collection_name: str = "nodes"  # Override in subclasses
    _node_type: str = "node"  # Override in subclasses

    def __init__(self, sdk: 'SDK', collection_name: str | None = None, node_type: str | None = None):
        """
        Initialize a collection.

        Args:
            sdk: Parent SDK instance
            collection_name: Name of the collection (e.g., "features", "bugs")
                           Defaults to class attribute if not provided
            node_type: Node type to filter by (e.g., "feature", "bug")
                      Defaults to class attribute if not provided
        """
        self._sdk = sdk
        self._collection_name = collection_name or self._collection_name
        self._node_type = node_type or self._node_type
        self._graph = None  # Lazy-loaded

    def _ensure_graph(self):
        """Lazy-load the graph for this collection."""
        if self._graph is None:
            from htmlgraph.graph import HtmlGraph
            collection_path = self._sdk._directory / self._collection_name
            self._graph = HtmlGraph(collection_path, auto_load=True)
        return self._graph

    def get(self, node_id: str) -> Node | None:
        """
        Get a node by ID.

        Args:
            node_id: Node ID to retrieve

        Returns:
            Node if found, None otherwise

        Example:
            >>> feature = sdk.features.get("feat-001")
        """
        return self._ensure_graph().get(node_id)

    @contextmanager
    def edit(self, node_id: str) -> Iterator[Node]:
        """
        Context manager for editing a node.

        Auto-saves on exit.

        Args:
            node_id: Node ID to edit

        Yields:
            The node to edit

        Raises:
            ValueError: If node not found

        Example:
            >>> with sdk.features.edit("feat-001") as feature:
            ...     feature.status = "in-progress"
        """
        graph = self._ensure_graph()
        node = graph.get(node_id)
        if not node:
            raise ValueError(f"{self._node_type.capitalize()} {node_id} not found")

        yield node

        # Auto-save on exit
        graph.update(node)

    def where(
        self,
        status: str | None = None,
        priority: str | None = None,
        track: str | None = None,
        assigned_to: str | None = None,
        **extra_filters
    ) -> list[Node]:
        """
        Query nodes with filters.

        Args:
            status: Filter by status (e.g., "todo", "in-progress", "done")
            priority: Filter by priority (e.g., "low", "medium", "high")
            track: Filter by track_id
            assigned_to: Filter by agent_assigned
            **extra_filters: Additional attribute filters

        Returns:
            List of matching nodes

        Example:
            >>> high_priority = sdk.features.where(status="todo", priority="high")
            >>> assigned = sdk.features.where(assigned_to="claude")
        """
        def matches(node: Node) -> bool:
            if node.type != self._node_type:
                return False
            if status and getattr(node, 'status', None) != status:
                return False
            if priority and getattr(node, 'priority', None) != priority:
                return False
            if track and getattr(node, "track_id", None) != track:
                return False
            if assigned_to and getattr(node, 'agent_assigned', None) != assigned_to:
                return False

            # Check extra filters
            for key, value in extra_filters.items():
                if getattr(node, key, None) != value:
                    return False

            return True

        return self._ensure_graph().filter(matches)

    def all(self) -> list[Node]:
        """
        Get all nodes of this type.

        Returns:
            List of all nodes in this collection

        Example:
            >>> all_features = sdk.features.all()
        """
        return [n for n in self._ensure_graph() if n.type == self._node_type]

    def delete(self, node_id: str) -> bool:
        """
        Delete a node.

        Args:
            node_id: Node ID to delete

        Returns:
            True if deleted, False if not found

        Example:
            >>> sdk.features.delete("feat-001")
        """
        graph = self._ensure_graph()
        return graph.delete(node_id)

    def batch_delete(self, node_ids: list[str]) -> int:
        """
        Delete multiple nodes in batch.

        Args:
            node_ids: List of node IDs to delete

        Returns:
            Number of nodes successfully deleted

        Example:
            >>> count = sdk.features.batch_delete(["feat-001", "feat-002", "feat-003"])
            >>> print(f"Deleted {count} features")
        """
        graph = self._ensure_graph()
        return graph.batch_delete(node_ids)

    def update(self, node: Node) -> Node:
        """
        Update a node.

        Args:
            node: Node to update

        Returns:
            Updated node

        Example:
            >>> feature.status = "done"
            >>> sdk.features.update(feature)
        """
        node.updated = datetime.now()
        self._ensure_graph().update(node)
        return node

    def batch_update(
        self,
        node_ids: list[str],
        updates: dict[str, Any]
    ) -> int:
        """
        Vectorized batch update operation.

        Args:
            node_ids: List of node IDs to update
            updates: Dictionary of attribute: value pairs to update

        Returns:
            Number of nodes successfully updated

        Example:
            >>> sdk.features.batch_update(
            ...     ["feat-1", "feat-2"],
            ...     {"status": "done", "agent_assigned": "claude"}
            ... )
        """
        graph = self._ensure_graph()
        now = datetime.now()
        count = 0

        # Vectorized retrieval
        nodes = [graph.get(nid) for nid in node_ids]

        # Batch update
        for node in nodes:
            if node:
                # Apply all updates
                for attr, value in updates.items():
                    setattr(node, attr, value)
                node.updated = now
                graph.update(node)
                count += 1

        return count

    def mark_done(self, node_ids: list[str]) -> int:
        """
        Batch mark nodes as done.

        Args:
            node_ids: List of node IDs to mark as done

        Returns:
            Number of nodes updated

        Example:
            >>> sdk.features.mark_done(["feat-001", "feat-002"])
        """
        return self.batch_update(node_ids, {"status": "done"})

    def assign(self, node_ids: list[str], agent: str) -> int:
        """
        Batch assign nodes to an agent.

        Args:
            node_ids: List of node IDs to assign
            agent: Agent ID to assign to

        Returns:
            Number of nodes assigned

        Example:
            >>> sdk.features.assign(["feat-001", "feat-002"], "claude")
        """
        updates = {
            "agent_assigned": agent,
            "status": "in-progress"
        }
        return self.batch_update(node_ids, updates)

    def claim(self, node_id: str, agent: str | None = None) -> Node:
        """
        Claim a node for an agent.

        Args:
            node_id: Node ID to claim
            agent: Agent ID (defaults to SDK agent)

        Returns:
            The claimed Node

        Raises:
            ValueError: If agent not provided and SDK has no agent
            ValueError: If node not found
            ValueError: If node already claimed by different agent

        Example:
            >>> feature = sdk.features.claim("feat-001")
            >>> feature = sdk.features.claim("feat-002", agent="gemini")
        """
        agent = agent or self._sdk.agent
        if not agent:
            raise ValueError("Agent ID required for claiming")

        graph = self._ensure_graph()
        node = graph.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        if node.agent_assigned and node.agent_assigned != agent:
            raise ValueError(f"Node {node_id} is already claimed by {node.agent_assigned}")

        node.agent_assigned = agent
        node.claimed_at = datetime.now()
        node.status = "in-progress"
        node.updated = datetime.now()
        graph.update(node)
        return node

    def release(self, node_id: str) -> Node:
        """
        Release a claimed node.

        Args:
            node_id: Node ID to release

        Returns:
            The released Node

        Raises:
            ValueError: If node not found

        Example:
            >>> feature = sdk.features.release("feat-001")
        """
        graph = self._ensure_graph()
        node = graph.get(node_id)
        if not node:
            raise ValueError(f"Node {node_id} not found")

        node.agent_assigned = None
        node.claimed_at = None
        node.claimed_by_session = None
        node.status = "todo"
        node.updated = datetime.now()
        graph.update(node)
        return node
