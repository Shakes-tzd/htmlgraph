"""
Graph operations for HtmlGraph.

Provides:
- File-based graph management
- CSS selector queries
- Graph algorithms (BFS, shortest path, dependency analysis)
- Bottleneck detection
"""

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable, Iterator

from htmlgraph.models import Node, Edge
from htmlgraph.converter import html_to_node, node_to_html, NodeConverter
from htmlgraph.parser import HtmlParser


class HtmlGraph:
    """
    File-based graph database using HTML files.

    Each HTML file is a node, hyperlinks are edges.
    Queries use CSS selectors.

    Example:
        graph = HtmlGraph("features/")
        graph.add(node)
        blocked = graph.query("[data-status='blocked']")
        path = graph.shortest_path("feature-001", "feature-010")
    """

    def __init__(
        self,
        directory: Path | str,
        stylesheet_path: str = "../styles.css",
        auto_load: bool = True,
        pattern: str | list[str] = "*.html"
    ):
        """
        Initialize graph from a directory.

        Args:
            directory: Directory containing HTML node files
            stylesheet_path: Default stylesheet path for new files
            auto_load: Whether to load all nodes on init
            pattern: Glob pattern(s) for node files. Can be a single pattern or list.
                     Examples: "*.html", ["*.html", "*/index.html"]
        """
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stylesheet_path = stylesheet_path
        self.pattern = pattern

        self._nodes: dict[str, Node] = {}
        self._converter = NodeConverter(directory, stylesheet_path)

        if auto_load:
            self.reload()

    def reload(self) -> int:
        """
        Reload all nodes from disk.

        Returns:
            Number of nodes loaded
        """
        self._nodes.clear()
        for node in self._converter.load_all(self.pattern):
            self._nodes[node.id] = node
        return len(self._nodes)

    @property
    def nodes(self) -> dict[str, Node]:
        """Get all nodes (read-only view)."""
        return self._nodes.copy()

    def __len__(self) -> int:
        """Number of nodes in graph."""
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        """Check if node exists."""
        return node_id in self._nodes

    def __iter__(self) -> Iterator[Node]:
        """Iterate over all nodes."""
        return iter(self._nodes.values())

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def add(self, node: Node, overwrite: bool = False) -> Path:
        """
        Add a node to the graph (creates HTML file).

        Args:
            node: Node to add
            overwrite: Whether to overwrite existing node

        Returns:
            Path to created HTML file

        Raises:
            ValueError: If node exists and overwrite=False
        """
        if node.id in self._nodes and not overwrite:
            raise ValueError(f"Node already exists: {node.id}")

        filepath = self._converter.save(node)
        self._nodes[node.id] = node
        return filepath

    def update(self, node: Node) -> Path:
        """
        Update an existing node.

        Args:
            node: Node with updated data

        Returns:
            Path to updated HTML file

        Raises:
            KeyError: If node doesn't exist
        """
        if node.id not in self._nodes:
            raise KeyError(f"Node not found: {node.id}")

        filepath = self._converter.save(node)
        self._nodes[node.id] = node
        return filepath

    def get(self, node_id: str) -> Node | None:
        """
        Get a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node instance or None if not found
        """
        return self._nodes.get(node_id)

    def get_or_load(self, node_id: str) -> Node | None:
        """
        Get node from cache or load from disk.

        Useful when graph might be modified externally.
        """
        if node_id in self._nodes:
            return self._nodes[node_id]

        node = self._converter.load(node_id)
        if node:
            self._nodes[node_id] = node
        return node

    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the graph.

        Args:
            node_id: Node to remove

        Returns:
            True if node was removed
        """
        if node_id in self._nodes:
            del self._nodes[node_id]
            return self._converter.delete(node_id)
        return False

    # =========================================================================
    # CSS Selector Queries
    # =========================================================================

    def query(self, selector: str) -> list[Node]:
        """
        Query nodes using CSS selector.

        Selector is applied to article element of each node.

        Args:
            selector: CSS selector string

        Returns:
            List of matching nodes

        Example:
            graph.query("[data-status='blocked']")
            graph.query("[data-priority='high'][data-type='feature']")
        """
        matching = []

        patterns = [self.pattern] if isinstance(self.pattern, str) else self.pattern
        for pat in patterns:
            for filepath in self.directory.glob(pat):
                if filepath.is_file():
                    try:
                        parser = HtmlParser.from_file(filepath)
                        # Query for article matching selector
                        if parser.query(f"article{selector}"):
                            node_id = parser.get_node_id()
                            if node_id and node_id in self._nodes:
                                matching.append(self._nodes[node_id])
                    except Exception:
                        continue

        return matching

    def query_one(self, selector: str) -> Node | None:
        """Query for single node matching selector."""
        results = self.query(selector)
        return results[0] if results else None

    def filter(self, predicate: Callable[[Node], bool]) -> list[Node]:
        """
        Filter nodes using a Python predicate function.

        Args:
            predicate: Function that takes Node and returns bool

        Returns:
            List of nodes where predicate returns True

        Example:
            graph.filter(lambda n: n.status == "todo" and n.priority == "high")
        """
        return [node for node in self._nodes.values() if predicate(node)]

    def by_status(self, status: str) -> list[Node]:
        """Get all nodes with given status."""
        return self.filter(lambda n: n.status == status)

    def by_type(self, node_type: str) -> list[Node]:
        """Get all nodes with given type."""
        return self.filter(lambda n: n.type == node_type)

    def by_priority(self, priority: str) -> list[Node]:
        """Get all nodes with given priority."""
        return self.filter(lambda n: n.priority == priority)

    # =========================================================================
    # Graph Algorithms
    # =========================================================================

    def _build_adjacency(self, relationship: str | None = None) -> dict[str, set[str]]:
        """
        Build adjacency list from edges.

        Args:
            relationship: Filter to specific relationship type, or None for all

        Returns:
            Dict mapping node_id to set of connected node_ids
        """
        adj: dict[str, set[str]] = defaultdict(set)

        for node in self._nodes.values():
            for rel_type, edges in node.edges.items():
                if relationship and rel_type != relationship:
                    continue
                for edge in edges:
                    adj[node.id].add(edge.target_id)

        return adj

    def shortest_path(
        self,
        from_id: str,
        to_id: str,
        relationship: str | None = None
    ) -> list[str] | None:
        """
        Find shortest path between two nodes using BFS.

        Args:
            from_id: Starting node ID
            to_id: Target node ID
            relationship: Optional filter to specific edge type

        Returns:
            List of node IDs representing path, or None if no path exists
        """
        if from_id not in self._nodes or to_id not in self._nodes:
            return None

        if from_id == to_id:
            return [from_id]

        adj = self._build_adjacency(relationship)

        # BFS
        queue = deque([(from_id, [from_id])])
        visited = {from_id}

        while queue:
            current, path = queue.popleft()

            for neighbor in adj.get(current, []):
                if neighbor == to_id:
                    return path + [neighbor]

                if neighbor not in visited and neighbor in self._nodes:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def transitive_deps(
        self,
        node_id: str,
        relationship: str = "blocked_by"
    ) -> set[str]:
        """
        Get all transitive dependencies of a node.

        Follows edges recursively to find all nodes that must be
        completed before this one.

        Args:
            node_id: Starting node ID
            relationship: Edge type to follow (default: blocked_by)

        Returns:
            Set of all dependency node IDs
        """
        if node_id not in self._nodes:
            return set()

        deps: set[str] = set()
        queue = deque([node_id])

        while queue:
            current = queue.popleft()
            node = self._nodes.get(current)
            if not node:
                continue

            for edge in node.edges.get(relationship, []):
                if edge.target_id not in deps:
                    deps.add(edge.target_id)
                    if edge.target_id in self._nodes:
                        queue.append(edge.target_id)

        return deps

    def dependents(
        self,
        node_id: str,
        relationship: str = "blocked_by"
    ) -> set[str]:
        """
        Find all nodes that depend on this node.

        Args:
            node_id: Node to find dependents for
            relationship: Edge type indicating dependency

        Returns:
            Set of node IDs that depend on this node
        """
        dependents: set[str] = set()

        for other_id, node in self._nodes.items():
            if other_id == node_id:
                continue

            for edge in node.edges.get(relationship, []):
                if edge.target_id == node_id:
                    dependents.add(other_id)
                    break

        return dependents

    def find_bottlenecks(self, relationship: str = "blocked_by", top_n: int = 5) -> list[tuple[str, int]]:
        """
        Find nodes that block the most other nodes.

        Args:
            relationship: Edge type indicating blocking
            top_n: Number of top bottlenecks to return

        Returns:
            List of (node_id, blocked_count) tuples, sorted by count descending
        """
        blocked_count: dict[str, int] = defaultdict(int)

        for node in self._nodes.values():
            for edge in node.edges.get(relationship, []):
                blocked_count[edge.target_id] += 1

        sorted_bottlenecks = sorted(
            blocked_count.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_bottlenecks[:top_n]

    def find_cycles(self, relationship: str = "blocked_by") -> list[list[str]]:
        """
        Detect cycles in the graph.

        Args:
            relationship: Edge type to check for cycles

        Returns:
            List of cycles, each as a list of node IDs
        """
        adj = self._build_adjacency(relationship)
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])

            path.pop()
            rec_stack.remove(node)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def topological_sort(self, relationship: str = "blocked_by") -> list[str] | None:
        """
        Return nodes in topological order (dependencies first).

        Args:
            relationship: Edge type indicating dependency

        Returns:
            List of node IDs in dependency order, or None if cycles exist
        """
        # Build in-degree map
        in_degree: dict[str, int] = {node_id: 0 for node_id in self._nodes}

        for node in self._nodes.values():
            for edge in node.edges.get(relationship, []):
                if edge.target_id in in_degree:
                    in_degree[node.id] = in_degree.get(node.id, 0) + 1

        # Start with nodes having no dependencies
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result: list[str] = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree of dependents
            for dependent in self.dependents(node_id, relationship):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for cycles
        if len(result) != len(self._nodes):
            return None

        return result

    # =========================================================================
    # Statistics & Analysis
    # =========================================================================

    def stats(self) -> dict[str, Any]:
        """
        Get graph statistics.

        Returns dict with:
        - total: Total node count
        - by_status: Count per status
        - by_type: Count per type
        - by_priority: Count per priority
        - completion_rate: Overall completion percentage
        - edge_count: Total number of edges
        """
        stats = {
            "total": len(self._nodes),
            "by_status": defaultdict(int),
            "by_type": defaultdict(int),
            "by_priority": defaultdict(int),
            "edge_count": 0,
        }

        done_count = 0
        for node in self._nodes.values():
            stats["by_status"][node.status] += 1
            stats["by_type"][node.type] += 1
            stats["by_priority"][node.priority] += 1

            for edges in node.edges.values():
                stats["edge_count"] += len(edges)

            if node.status == "done":
                done_count += 1

        stats["completion_rate"] = (
            round(done_count / len(self._nodes) * 100, 1)
            if self._nodes else 0
        )

        # Convert defaultdicts to regular dicts
        stats["by_status"] = dict(stats["by_status"])
        stats["by_type"] = dict(stats["by_type"])
        stats["by_priority"] = dict(stats["by_priority"])

        return stats

    def to_context(self, max_nodes: int = 20) -> str:
        """
        Generate lightweight context for AI agents.

        Args:
            max_nodes: Maximum nodes to include

        Returns:
            Compact string representation of graph state
        """
        lines = ["# Graph Summary"]
        stats = self.stats()
        lines.append(f"Total: {stats['total']} nodes | Done: {stats['completion_rate']}%")

        # Status breakdown
        status_parts = [f"{s}: {c}" for s, c in stats["by_status"].items()]
        lines.append(f"Status: {' | '.join(status_parts)}")

        lines.append("")

        # Top priority items
        high_priority = self.filter(
            lambda n: n.priority in ("high", "critical") and n.status != "done"
        )[:max_nodes]

        if high_priority:
            lines.append("## High Priority Items")
            for node in high_priority:
                lines.append(f"- {node.id}: {node.title} [{node.status}]")

        return "\n".join(lines)

    # =========================================================================
    # Export
    # =========================================================================

    def to_json(self) -> list[dict[str, Any]]:
        """Export all nodes as JSON-serializable list."""
        from htmlgraph.converter import node_to_dict
        return [node_to_dict(node) for node in self._nodes.values()]

    def to_mermaid(self, relationship: str | None = None) -> str:
        """
        Export graph as Mermaid diagram.

        Args:
            relationship: Optional filter to specific edge type

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        for node in self._nodes.values():
            # Node definition with status styling
            node_label = f"{node.id}[{node.title}]"
            lines.append(f"    {node_label}")

            # Edges
            for rel_type, edges in node.edges.items():
                if relationship and rel_type != relationship:
                    continue
                for edge in edges:
                    arrow = "-->" if rel_type != "blocked_by" else "-.->|blocked|"
                    lines.append(f"    {node.id} {arrow} {edge.target_id}")

        return "\n".join(lines)
