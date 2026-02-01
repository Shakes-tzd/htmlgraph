"""
Bounded path-finding and cycle detection for HtmlGraph.

Provides safe, deterministic graph traversal algorithms with built-in
cycle avoidance and depth bounds. Replaces timeout-based safety guards
with structural guarantees:

- BFS for shortest paths: O(V+E) guaranteed
- DFS with per-path visited tracking for bounded enumeration
- Cycle detection with configurable depth limits

All algorithms terminate deterministically via depth bounds,
never requiring timeouts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.edge_index import EdgeRef
    from htmlgraph.graph import HtmlGraph


@dataclass
class PathResult:
    """
    Result of a path-finding operation.

    Represents an ordered sequence of nodes connected by edges,
    forming a path through the graph.

    Attributes:
        nodes: Ordered list of node IDs in the path (source first, target last).
        edges: List of EdgeRef objects for each edge traversed.
        length: Number of edges in the path (len(nodes) - 1).
        relationship_types: Distinct edge relationship types used in this path.
    """

    nodes: list[str]
    edges: list[EdgeRef]
    length: int
    relationship_types: list[str]


@dataclass
class CycleResult:
    """
    Result of a cycle detection operation.

    Represents a cycle found in the graph, identified by the sequence
    of nodes that form a closed loop.

    Attributes:
        cycle: Node IDs forming the cycle. The first and last element
               are the same node, closing the loop.
        length: Number of edges in the cycle.
        edge_types: Distinct relationship types in the cycle.
        involves_node: The node that was queried or that participates
                       in this cycle.
    """

    cycle: list[str]
    length: int
    edge_types: list[str]
    involves_node: str


@dataclass
class BoundedPathFinder:
    """
    Safe, bounded graph traversal with cycle avoidance.

    Provides deterministic path-finding and cycle detection algorithms
    that terminate based on depth bounds rather than timeouts.

    All methods use the graph's EdgeIndex for efficient O(1) neighbor
    lookups and support optional edge-type filtering.

    Example:
        >>> from htmlgraph.graph import HtmlGraph
        >>> graph = HtmlGraph("features/", auto_load=True)
        >>> finder = BoundedPathFinder(graph)
        >>> path = finder.any_shortest("feat-001", "feat-010")
        >>> if path:
        ...     print(f"Shortest path: {' -> '.join(path.nodes)}")
        >>> cycles = finder.find_cycles("feat-001")
        >>> for c in cycles:
        ...     print(f"Cycle of length {c.length}: {c.cycle}")
    """

    graph: HtmlGraph
    max_depth: int = 20

    # Internal caches, not part of __init__ signature
    _adjacency_cache: dict[str, dict[str, list[_NeighborInfo]]] = field(
        default_factory=dict, init=False, repr=False
    )

    def _get_neighbors(
        self,
        node_id: str,
        edge_types: list[str] | None,
        direction: str = "outgoing",
    ) -> list[_NeighborInfo]:
        """
        Get neighbors of a node with edge metadata, using the EdgeIndex.

        Args:
            node_id: The node to get neighbors for.
            edge_types: If provided, only follow edges with these relationship types.
            direction: "outgoing" follows edges from node_id, "incoming" follows
                       edges pointing to node_id.

        Returns:
            List of _NeighborInfo with neighbor_id and the EdgeRef.
        """

        results: list[_NeighborInfo] = []
        if direction == "outgoing":
            refs = self.graph._edge_index.get_outgoing(node_id)
            for ref in refs:
                if edge_types is None or ref.relationship in edge_types:
                    results.append(_NeighborInfo(ref.target_id, ref))
        else:  # incoming
            refs = self.graph._edge_index.get_incoming(node_id)
            for ref in refs:
                if edge_types is None or ref.relationship in edge_types:
                    results.append(_NeighborInfo(ref.source_id, ref))
        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def any_shortest(
        self,
        from_id: str,
        to_id: str,
        edge_types: list[str] | None = None,
    ) -> PathResult | None:
        """
        Find ANY shortest path between two nodes using BFS.

        Guaranteed O(V+E) time complexity with built-in cycle avoidance
        via the BFS visited set.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            edge_types: If provided, only traverse edges with these relationship types.

        Returns:
            A PathResult for one shortest path, or None if no path exists.
        """
        if from_id not in self.graph._nodes or to_id not in self.graph._nodes:
            return None

        if from_id == to_id:
            return PathResult(
                nodes=[from_id], edges=[], length=0, relationship_types=[]
            )

        # BFS: queue entries are (current_node, path_of_nodes, path_of_edges)
        queue: deque[tuple[str, list[str], list[EdgeRef]]] = deque()
        queue.append((from_id, [from_id], []))
        visited: set[str] = {from_id}

        while queue:
            current, path_nodes, path_edges = queue.popleft()

            for info in self._get_neighbors(current, edge_types, "outgoing"):
                neighbor = info.neighbor_id
                edge_ref = info.edge_ref

                new_nodes = path_nodes + [neighbor]
                new_edges = path_edges + [edge_ref]

                if neighbor == to_id:
                    rel_types = sorted(set(e.relationship for e in new_edges))
                    return PathResult(
                        nodes=new_nodes,
                        edges=new_edges,
                        length=len(new_edges),
                        relationship_types=rel_types,
                    )

                if neighbor not in visited and neighbor in self.graph._nodes:
                    visited.add(neighbor)
                    queue.append((neighbor, new_nodes, new_edges))

        return None

    def all_shortest(
        self,
        from_id: str,
        to_id: str,
        edge_types: list[str] | None = None,
    ) -> list[PathResult]:
        """
        Find ALL shortest paths (same minimum length) between two nodes.

        Uses BFS to determine the shortest distance, then enumerates all
        paths of exactly that length. The BFS phase is O(V+E); the
        enumeration phase explores only paths within the shortest distance
        bound.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            edge_types: If provided, only traverse edges with these relationship types.

        Returns:
            List of PathResult objects, all having the same minimum length.
            Empty list if no path exists.
        """
        if from_id not in self.graph._nodes or to_id not in self.graph._nodes:
            return []

        if from_id == to_id:
            return [
                PathResult(nodes=[from_id], edges=[], length=0, relationship_types=[])
            ]

        # Phase 1: BFS to find shortest distance and predecessor map.
        # For each node, record ALL predecessors at the shortest distance.
        dist: dict[str, int] = {from_id: 0}
        # predecessors maps node -> list of (predecessor_node, edge_ref)
        predecessors: dict[str, list[tuple[str, EdgeRef]]] = {}
        queue: deque[str] = deque([from_id])

        while queue:
            current = queue.popleft()
            current_dist = dist[current]

            for info in self._get_neighbors(current, edge_types, "outgoing"):
                neighbor = info.neighbor_id
                edge_ref = info.edge_ref

                if neighbor not in self.graph._nodes:
                    continue

                new_dist = current_dist + 1

                if neighbor not in dist:
                    # First time reaching this node
                    dist[neighbor] = new_dist
                    predecessors[neighbor] = [(current, edge_ref)]
                    queue.append(neighbor)
                elif dist[neighbor] == new_dist:
                    # Same shortest distance, add alternative predecessor
                    predecessors[neighbor].append((current, edge_ref))

        if to_id not in dist:
            return []

        # Phase 2: Backtrack from to_id to from_id using predecessors.
        results: list[PathResult] = []

        def _backtrack(
            node: str,
            path_nodes: list[str],
            path_edges: list[EdgeRef],
        ) -> None:
            if node == from_id:
                # Reverse to get source-to-target order
                final_nodes = list(reversed(path_nodes))
                final_edges = list(reversed(path_edges))
                rel_types = sorted(set(e.relationship for e in final_edges))
                results.append(
                    PathResult(
                        nodes=final_nodes,
                        edges=final_edges,
                        length=len(final_edges),
                        relationship_types=rel_types,
                    )
                )
                return

            for pred_node, edge_ref in predecessors.get(node, []):
                path_nodes.append(pred_node)
                path_edges.append(edge_ref)
                _backtrack(pred_node, path_nodes, path_edges)
                path_nodes.pop()
                path_edges.pop()

        _backtrack(to_id, [to_id], [])
        return results

    def bounded_paths(
        self,
        from_id: str,
        to_id: str,
        max_depth: int | None = None,
        max_results: int = 100,
        edge_types: list[str] | None = None,
    ) -> list[PathResult]:
        """
        Find paths up to max_depth with built-in cycle avoidance per path.

        Replaces all_paths() with a deterministic depth bound instead of
        a timeout. Each path independently tracks visited nodes to allow
        different paths to share intermediate nodes while preventing
        cycles within any single path.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            max_depth: Maximum path length in edges. Defaults to self.max_depth.
            max_results: Maximum number of paths to return (default 100).
            edge_types: If provided, only traverse edges with these relationship types.

        Returns:
            List of PathResult objects, up to max_results.
        """
        depth_limit = max_depth if max_depth is not None else self.max_depth

        if from_id not in self.graph._nodes or to_id not in self.graph._nodes:
            return []

        if from_id == to_id:
            return [
                PathResult(nodes=[from_id], edges=[], length=0, relationship_types=[])
            ]

        results: list[PathResult] = []

        def _dfs(
            current: str,
            path_nodes: list[str],
            path_edges: list[EdgeRef],
            visited: set[str],
        ) -> None:
            if len(results) >= max_results:
                return

            if len(path_edges) > depth_limit:
                return

            if current == to_id:
                rel_types = sorted(set(e.relationship for e in path_edges))
                results.append(
                    PathResult(
                        nodes=list(path_nodes),
                        edges=list(path_edges),
                        length=len(path_edges),
                        relationship_types=rel_types,
                    )
                )
                return

            # Don't go deeper if we're at the depth limit
            if len(path_edges) >= depth_limit:
                return

            for info in self._get_neighbors(current, edge_types, "outgoing"):
                neighbor = info.neighbor_id
                if neighbor not in visited and neighbor in self.graph._nodes:
                    visited.add(neighbor)
                    path_nodes.append(neighbor)
                    path_edges.append(info.edge_ref)
                    _dfs(neighbor, path_nodes, path_edges, visited)
                    path_edges.pop()
                    path_nodes.pop()
                    visited.remove(neighbor)

        _dfs(from_id, [from_id], [], {from_id})
        return results

    def find_cycles(
        self,
        node_id: str | None = None,
        edge_types: list[str] | None = None,
        max_cycle_length: int = 10,
    ) -> list[CycleResult]:
        """
        Detect cycles in the graph.

        If node_id is provided, finds cycles that include that specific node.
        Otherwise, finds all cycles up to max_cycle_length in the entire graph.

        Uses DFS with depth bounding for deterministic termination.
        Inspired by SQL/PGQ ownership-cycle detection patterns.

        Args:
            node_id: If provided, only find cycles involving this node.
            edge_types: If provided, only follow edges with these relationship types.
            max_cycle_length: Maximum cycle length to search for (default 10).

        Returns:
            List of CycleResult objects describing each cycle found.
        """
        if node_id is not None:
            return self._find_cycles_for_node(node_id, edge_types, max_cycle_length)

        # Find cycles for all nodes
        all_cycles: list[CycleResult] = []
        seen_cycles: set[tuple[str, ...]] = set()

        for nid in self.graph._nodes:
            for cycle_result in self._find_cycles_for_node(
                nid, edge_types, max_cycle_length
            ):
                # Normalize cycle for deduplication: rotate so smallest ID is first
                cycle_nodes = cycle_result.cycle[:-1]  # Remove closing duplicate
                if not cycle_nodes:
                    continue
                min_idx = cycle_nodes.index(min(cycle_nodes))
                normalized = tuple(cycle_nodes[min_idx:] + cycle_nodes[:min_idx])

                if normalized not in seen_cycles:
                    seen_cycles.add(normalized)
                    all_cycles.append(cycle_result)

        return all_cycles

    def _find_cycles_for_node(
        self,
        node_id: str,
        edge_types: list[str] | None,
        max_cycle_length: int,
    ) -> list[CycleResult]:
        """
        Find all cycles involving a specific node, up to max_cycle_length.

        Uses iterative DFS from node_id looking for paths that return to it.

        Args:
            node_id: The node to find cycles for.
            edge_types: Optional edge type filter.
            max_cycle_length: Maximum edges in a cycle.

        Returns:
            List of CycleResult objects for cycles involving node_id.
        """
        if node_id not in self.graph._nodes:
            return []

        results: list[CycleResult] = []

        def _dfs(
            current: str,
            path: list[str],
            path_edges: list[EdgeRef],
            visited: set[str],
        ) -> None:
            if len(path_edges) > max_cycle_length:
                return

            for info in self._get_neighbors(current, edge_types, "outgoing"):
                neighbor = info.neighbor_id
                candidate_length = len(path_edges) + 1

                if neighbor == node_id:
                    # Found a cycle back to start (includes self-loops)
                    if candidate_length <= max_cycle_length:
                        cycle_path = path + [node_id]
                        all_edges = path_edges + [info.edge_ref]
                        edge_type_set = sorted(set(e.relationship for e in all_edges))
                        results.append(
                            CycleResult(
                                cycle=cycle_path,
                                length=len(all_edges),
                                edge_types=edge_type_set,
                                involves_node=node_id,
                            )
                        )
                elif (
                    neighbor not in visited
                    and neighbor in self.graph._nodes
                    and candidate_length < max_cycle_length
                ):
                    visited.add(neighbor)
                    path.append(neighbor)
                    path_edges.append(info.edge_ref)
                    _dfs(neighbor, path, path_edges, visited)
                    path_edges.pop()
                    path.pop()
                    visited.remove(neighbor)

        _dfs(node_id, [node_id], [], {node_id})
        return results

    def reachable_set(
        self,
        from_id: str,
        edge_types: list[str] | None = None,
        direction: str = "outgoing",
        max_depth: int | None = None,
    ) -> set[str]:
        """
        Find all nodes reachable from a starting node within a depth bound.

        Uses BFS for level-by-level exploration. Useful for transitive
        dependency analysis with limits.

        Args:
            from_id: Starting node ID.
            edge_types: If provided, only follow edges with these relationship types.
            direction: "outgoing" follows edges from source, "incoming" follows
                       edges pointing to source.
            max_depth: Maximum traversal depth. Defaults to self.max_depth.

        Returns:
            Set of reachable node IDs (does not include from_id itself).
        """
        depth_limit = max_depth if max_depth is not None else self.max_depth

        if from_id not in self.graph._nodes:
            return set()

        reachable: set[str] = set()
        visited: set[str] = {from_id}
        queue: deque[tuple[str, int]] = deque([(from_id, 0)])

        while queue:
            current, depth = queue.popleft()

            if depth >= depth_limit:
                continue

            for info in self._get_neighbors(current, edge_types, direction):
                neighbor = info.neighbor_id
                if neighbor not in visited and neighbor in self.graph._nodes:
                    visited.add(neighbor)
                    reachable.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return reachable


@dataclass
class _NeighborInfo:
    """Internal helper pairing a neighbor ID with its edge reference."""

    neighbor_id: str
    edge_ref: EdgeRef
