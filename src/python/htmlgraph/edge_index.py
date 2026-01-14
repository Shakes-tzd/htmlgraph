from __future__ import annotations

"""
Edge Index for O(1) reverse edge lookups.

Provides efficient bi-directional edge queries by maintaining
an inverse index of edges. This enables O(1) lookups for:
- Finding all nodes that point TO a given node (incoming edges)
- Finding all nodes that a given node points FROM (outgoing edges)

Without this index, finding incoming edges requires scanning all nodes
in the graph - O(V×E) complexity.
"""


from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.models import Edge, Node


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
        """
        Compute hash for EdgeRef.

        Enables using EdgeRef in sets and as dict keys.

        Returns:
            int: Hash value based on source_id, target_id, and relationship

        Example:
            >>> ref1 = EdgeRef("feat-001", "feat-002", "blocked_by")
            >>> ref2 = EdgeRef("feat-001", "feat-002", "blocked_by")
            >>> refs = {ref1, ref2}  # Set deduplication works
            >>> len(refs)
            1
        """
        return hash((self.source_id, self.target_id, self.relationship))

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another EdgeRef.

        Enables using == operator and set membership checks.

        Args:
            other: Object to compare with

        Returns:
            bool: True if both EdgeRefs have same source, target, and relationship

        Example:
            >>> ref1 = EdgeRef("feat-001", "feat-002", "blocked_by")
            >>> ref2 = EdgeRef("feat-001", "feat-002", "blocked_by")
            >>> ref1 == ref2
            True
            >>> ref3 = EdgeRef("feat-001", "feat-003", "blocked_by")
            >>> ref1 == ref3
            False
        """
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

    _incoming: dict[str, list[EdgeRef]] = field(
        default_factory=lambda: defaultdict(list)
    )
    _outgoing: dict[str, list[EdgeRef]] = field(
        default_factory=lambda: defaultdict(list)
    )
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
        ref = EdgeRef(
            source_id=source_id, target_id=target_id, relationship=relationship
        )

        # Avoid duplicates
        if ref not in self._incoming[target_id]:
            self._incoming[target_id].append(ref)
            self._outgoing[source_id].append(ref)
            self._edge_count += 1

        return ref

    def add_edge(self, source_id: str, edge: Edge) -> EdgeRef:
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
        ref = EdgeRef(
            source_id=source_id, target_id=target_id, relationship=relationship
        )

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

    def remove_edge(self, source_id: str, edge: Edge) -> bool:
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

    def add_node_edges(self, node_id: str, node: Node) -> int:
        """
        Add a single node's outgoing edges to the index.

        Args:
            node_id: Node ID
            node: Node object with edges to add

        Returns:
            Number of edges added
        """
        added = 0
        for rel_type, edges in node.edges.items():
            for edge in edges:
                self.add(node_id, edge.target_id, rel_type)
                added += 1
        return added

    def add_node(self, node_id: str, node: Node) -> int:
        """
        Add all edges from a single node to the index.

        Alias for add_node_edges() to match requested API.

        Args:
            node_id: The node's ID
            node: The node object with edges attribute

        Returns:
            Number of edges added
        """
        return self.add_node_edges(node_id, node)

    def remove_node_edges(self, node_id: str, node: Node) -> int:
        """
        Remove a single node's outgoing edges from the index.

        Args:
            node_id: Node ID
            node: Node object with edges to remove

        Returns:
            Number of edges removed
        """
        removed = 0
        for rel_type, edges in node.edges.items():
            for edge in edges:
                if self.remove(node_id, edge.target_id, rel_type):
                    removed += 1
        return removed

    def update_node(
        self, node_id: str, old_node: Node, new_node: Node
    ) -> tuple[int, int]:
        """
        Update a node's edges atomically (remove old, add new).

        This is an atomic operation that removes all edges from the old node
        and adds all edges from the new node. Useful for updating a node
        without leaving orphaned edges.

        Args:
            node_id: The node's ID
            old_node: The previous node object
            new_node: The updated node object

        Returns:
            Tuple of (removed_count, added_count)

        Example:
            >>> old = Node(id="feat-001", edges={"blocks": [Edge(target_id="feat-002")]})
            >>> new = Node(id="feat-001", edges={"blocks": [Edge(target_id="feat-003")]})
            >>> removed, added = index.update_node("feat-001", old, new)
            >>> print(f"Removed {removed}, added {added}")
            Removed 1, added 1
        """
        removed = self.remove_node_edges(node_id, old_node)
        added = self.add_node_edges(node_id, new_node)
        return (removed, added)

    def get_incoming(
        self, target_id: str, relationship: str | None = None
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
        self, source_id: str, relationship: str | None = None
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
        self, node_id: str, relationship: str | None = None, direction: str = "both"
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

    def has_edge(
        self, source_id: str, target_id: str, relationship: str | None = None
    ) -> bool:
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

    def rebuild(self, nodes: dict[str, Node]) -> int:
        """
        Rebuild the entire index from a node dictionary.

        Optimized to use add_node_edges() for cleaner code.

        Args:
            nodes: Dictionary mapping node_id to Node objects

        Returns:
            Number of edges indexed
        """
        self.clear()

        for node_id, node in nodes.items():
            self.add_node_edges(node_id, node)

        return self._edge_count

    def clear(self) -> None:
        """Clear all entries from the index."""
        self._incoming.clear()
        self._outgoing.clear()
        self._edge_count = 0

    def __len__(self) -> int:
        """
        Get the total number of edges in the index.

        Enables using len() on EdgeIndex instances.

        Returns:
            int: Total number of edges indexed

        Example:
            >>> index = EdgeIndex()
            >>> index.rebuild(graph.nodes)
            >>> print(f"Index contains {len(index)} edges")
            Index contains 156 edges
        """
        return self._edge_count

    def __iter__(self) -> Iterator[EdgeRef]:
        """
        Iterate over all unique edges in the index.

        Enables using EdgeIndex in for loops and other iteration contexts.
        Deduplicates edges to avoid returning the same edge twice.

        Yields:
            EdgeRef: Each unique edge in the index

        Example:
            >>> index = EdgeIndex()
            >>> index.rebuild(graph.nodes)
            >>> for edge in index:
            ...     print(f"{edge.source_id} --{edge.relationship}--> {edge.target_id}")
            feat-001 --blocked_by--> feat-002
            feat-003 --related--> feat-001

            >>> # Works with comprehensions
            >>> blocked_by = [e for e in index if e.relationship == "blocked_by"]
            >>> blocking_count = len([e for e in index if e.relationship == "blocks"])
        """
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
            "relationships": list(set(ref.relationship for ref in self)),
        }
