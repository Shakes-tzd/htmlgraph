"""
Edge Index for O(1) reverse edge lookups.

Provides efficient bi-directional edge queries by maintaining
an inverse index of edges. This enables O(1) lookups for:
- Finding all nodes that point TO a given node (incoming edges)
- Finding all nodes that a given node points FROM (outgoing edges)

Without this index, finding incoming edges requires scanning all nodes
in the graph - O(V×E) complexity.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from htmlgraph.models import Node, Edge


@dataclass
class EdgeRef:
    """
    A lightweight reference to an edge in the graph.

    Stores the essential information needed to identify and traverse
    an edge without holding a reference to the full Edge object.
    """
    source_id: str
    target_id: str
    relationship: str

    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.relationship))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EdgeRef):
            return False
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.relationship == other.relationship
        )


@dataclass
class EdgeIndex:
    """
    Bi-directional edge index for efficient graph traversal.

    Maintains two indexes:
    - _incoming: target_id -> list of EdgeRefs pointing TO this node
    - _outgoing: source_id -> list of EdgeRefs pointing FROM this node

    The outgoing index is redundant with Node.edges but useful for
    graph-level operations and consistency checks.

    Example:
        index = EdgeIndex()
        index.rebuild(graph.nodes)

        # O(1) lookup of all nodes blocking feature-001
        blockers = index.get_incoming("feature-001", relationship="blocked_by")

        # O(1) lookup of all nodes that feature-001 blocks
        blocked = index.get_outgoing("feature-001", relationship="blocks")
    """

    _incoming: dict[str, list[EdgeRef]] = field(default_factory=lambda: defaultdict(list))
    _outgoing: dict[str, list[EdgeRef]] = field(default_factory=lambda: defaultdict(list))
    _edge_count: int = 0

    def add(self, source_id: str, target_id: str, relationship: str) -> EdgeRef:
        """
        Add an edge to the index.

        Args:
            source_id: Node ID where edge originates
            target_id: Node ID where edge points to
            relationship: Edge relationship type (e.g., "blocked_by", "related")

        Returns:
            EdgeRef for the added edge
        """
        ref = EdgeRef(source_id=source_id, target_id=target_id, relationship=relationship)

        # Avoid duplicates
        if ref not in self._incoming[target_id]:
            self._incoming[target_id].append(ref)
            self._outgoing[source_id].append(ref)
            self._edge_count += 1

        return ref

    def add_edge(self, source_id: str, edge: 'Edge') -> EdgeRef:
        """
        Add an edge object to the index.

        Args:
            source_id: Node ID where edge originates
            edge: Edge object to add

        Returns:
            EdgeRef for the added edge
        """
        return self.add(source_id, edge.target_id, edge.relationship)

    def remove(self, source_id: str, target_id: str, relationship: str) -> bool:
        """
        Remove an edge from the index.

        Args:
            source_id: Node ID where edge originates
            target_id: Node ID where edge points to
            relationship: Edge relationship type

        Returns:
            True if edge was removed, False if not found
        """
        ref = EdgeRef(source_id=source_id, target_id=target_id, relationship=relationship)

        removed = False
        if target_id in self._incoming and ref in self._incoming[target_id]:
            self._incoming[target_id].remove(ref)
            removed = True

        if source_id in self._outgoing and ref in self._outgoing[source_id]:
            self._outgoing[source_id].remove(ref)
            removed = True

        if removed:
            self._edge_count -= 1

        return removed

    def remove_edge(self, source_id: str, edge: 'Edge') -> bool:
        """
        Remove an edge object from the index.

        Args:
            source_id: Node ID where edge originates
            edge: Edge object to remove

        Returns:
            True if edge was removed, False if not found
        """
        return self.remove(source_id, edge.target_id, edge.relationship)

    def remove_node(self, node_id: str) -> int:
        """
        Remove all edges involving a node (both incoming and outgoing).

        Args:
            node_id: Node ID to remove all edges for

        Returns:
            Number of edges removed
        """
        removed = 0

        # Remove outgoing edges from this node
        if node_id in self._outgoing:
            for ref in self._outgoing[node_id]:
                if ref.target_id in self._incoming:
                    try:
                        self._incoming[ref.target_id].remove(ref)
                        removed += 1
                    except ValueError:
                        pass
            del self._outgoing[node_id]

        # Remove incoming edges to this node
        if node_id in self._incoming:
            for ref in self._incoming[node_id]:
                if ref.source_id in self._outgoing:
                    try:
                        self._outgoing[ref.source_id].remove(ref)
                        removed += 1
                    except ValueError:
                        pass
            del self._incoming[node_id]

        self._edge_count -= removed
        return removed

    def get_incoming(
        self,
        target_id: str,
        relationship: str | None = None
    ) -> list[EdgeRef]:
        """
        Get all edges pointing TO a node (O(1) lookup).

        Args:
            target_id: Node ID to find incoming edges for
            relationship: Optional filter by relationship type

        Returns:
            List of EdgeRefs for incoming edges

        Example:
            # Find all nodes that block feature-001
            blockers = index.get_incoming("feature-001", "blocked_by")
            for ref in blockers:
                print(f"{ref.source_id} blocks feature-001")
        """
        edges = self._incoming.get(target_id, [])

        if relationship is not None:
            return [e for e in edges if e.relationship == relationship]

        return list(edges)

    def get_outgoing(
        self,
        source_id: str,
        relationship: str | None = None
    ) -> list[EdgeRef]:
        """
        Get all edges pointing FROM a node (O(1) lookup).

        Args:
            source_id: Node ID to find outgoing edges for
            relationship: Optional filter by relationship type

        Returns:
            List of EdgeRefs for outgoing edges
        """
        edges = self._outgoing.get(source_id, [])

        if relationship is not None:
            return [e for e in edges if e.relationship == relationship]

        return list(edges)

    def get_neighbors(
        self,
        node_id: str,
        relationship: str | None = None,
        direction: str = "both"
    ) -> set[str]:
        """
        Get all neighboring node IDs connected to a node.

        Args:
            node_id: Node ID to find neighbors for
            relationship: Optional filter by relationship type
            direction: "incoming", "outgoing", or "both"

        Returns:
            Set of neighboring node IDs
        """
        neighbors: set[str] = set()

        if direction in ("incoming", "both"):
            for ref in self.get_incoming(node_id, relationship):
                neighbors.add(ref.source_id)

        if direction in ("outgoing", "both"):
            for ref in self.get_outgoing(node_id, relationship):
                neighbors.add(ref.target_id)

        return neighbors

    def has_edge(self, source_id: str, target_id: str, relationship: str | None = None) -> bool:
        """
        Check if an edge exists between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship: Optional relationship type to check

        Returns:
            True if edge exists
        """
        for ref in self._outgoing.get(source_id, []):
            if ref.target_id == target_id:
                if relationship is None or ref.relationship == relationship:
                    return True
        return False

    def rebuild(self, nodes: dict[str, 'Node']) -> int:
        """
        Rebuild the entire index from a node dictionary.

        Args:
            nodes: Dictionary mapping node_id to Node objects

        Returns:
            Number of edges indexed
        """
        self.clear()

        for node_id, node in nodes.items():
            for relationship, edges in node.edges.items():
                for edge in edges:
                    self.add(node_id, edge.target_id, edge.relationship)

        return self._edge_count

    def clear(self) -> None:
        """Clear all entries from the index."""
        self._incoming.clear()
        self._outgoing.clear()
        self._edge_count = 0

    def __len__(self) -> int:
        """Return number of edges in the index."""
        return self._edge_count

    def __iter__(self) -> Iterator[EdgeRef]:
        """Iterate over all edges in the index."""
        seen: set[EdgeRef] = set()
        for refs in self._outgoing.values():
            for ref in refs:
                if ref not in seen:
                    seen.add(ref)
                    yield ref

    def stats(self) -> dict:
        """
        Get index statistics.

        Returns:
            Dictionary with index statistics
        """
        return {
            "edge_count": self._edge_count,
            "nodes_with_incoming": len(self._incoming),
            "nodes_with_outgoing": len(self._outgoing),
            "relationships": list(set(ref.relationship for ref in self))
        }
