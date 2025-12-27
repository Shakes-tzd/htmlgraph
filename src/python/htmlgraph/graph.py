"""
Graph operations for HtmlGraph.

Provides:
- File-based graph management
- CSS selector queries
- Graph algorithms (BFS, shortest path, dependency analysis)
- Bottleneck detection
"""

import hashlib
import os
import time
from collections import defaultdict, deque
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from htmlgraph.attribute_index import AttributeIndex
from htmlgraph.converter import NodeConverter
from htmlgraph.edge_index import EdgeIndex, EdgeRef
from htmlgraph.exceptions import NodeNotFoundError
from htmlgraph.find_api import FindAPI
from htmlgraph.models import Node
from htmlgraph.parser import HtmlParser
from htmlgraph.query_builder import QueryBuilder


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
        auto_load: bool = False,
        pattern: str | list[str] = "*.html",
    ):
        """
        Initialize graph from a directory.

        Args:
            directory: Directory containing HTML node files
            stylesheet_path: Default stylesheet path for new files
            auto_load: Whether to load all nodes on init (default: False for lazy loading)
            pattern: Glob pattern(s) for node files. Can be a single pattern or list.
                     Examples: "*.html", ["*.html", "*/index.html"]
        """
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.stylesheet_path = stylesheet_path
        self.pattern = pattern

        self._nodes: dict[str, Node] = {}
        self._converter = NodeConverter(directory, stylesheet_path)
        self._edge_index = EdgeIndex()
        self._query_cache: dict[str, list[Node]] = {}
        self._adjacency_cache: dict[str, dict[str, list[str]]] | None = None
        self._cache_enabled: bool = True
        self._explicitly_loaded: bool = False
        self._file_hashes: dict[str, str] = {}  # Track file content hashes

        # Performance metrics
        self._metrics = {
            "query_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "reload_count": 0,
            "single_reload_count": 0,
            "total_query_time_ms": 0.0,
            "slowest_query_ms": 0.0,
            "slowest_query_selector": "",
            "last_reload_time_ms": 0.0,
        }

        # Check for env override (backwards compatibility)
        if os.environ.get("HTMLGRAPH_EAGER_LOAD") == "1":
            auto_load = True

        if auto_load:
            self.reload()

    def _invalidate_cache(self) -> None:
        """Clear query and adjacency caches. Called when graph is modified."""
        self._query_cache.clear()
        self._adjacency_cache = None

    def _compute_file_hash(self, filepath: Path) -> str:
        """
        Compute MD5 hash of file content.

        Args:
            filepath: Path to file to hash

        Returns:
            MD5 hash as hex string
        """
        try:
            content = filepath.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def has_file_changed(self, filepath: Path | str) -> bool:
        """
        Check if a file has changed since it was last loaded.

        Args:
            filepath: Path to file to check

        Returns:
            True if file changed or not yet loaded, False if unchanged
        """
        filepath = Path(filepath)
        if not filepath.exists():
            return True

        filepath_str = str(filepath)
        current_hash = self._compute_file_hash(filepath)
        stored_hash = self._file_hashes.get(filepath_str)

        # If no stored hash or hash changed, file has changed
        return stored_hash is None or current_hash != stored_hash

    def reload(self) -> int:
        """
        Reload all nodes from disk.

        Returns:
            Number of nodes loaded
        """
        start = time.perf_counter()
        self._cache_enabled = False  # Disable during reload
        try:
            self._nodes.clear()
            self._file_hashes.clear()

            # Load all nodes and compute file hashes
            for node in self._converter.load_all(self.pattern):
                self._nodes[node.id] = node

                # Find and hash the node file
                filepath = self._find_node_file(node.id)
                if filepath:
                    file_hash = self._compute_file_hash(filepath)
                    self._file_hashes[str(filepath)] = file_hash

            # Rebuild edge index for O(1) reverse lookups
            self._edge_index.rebuild(self._nodes)

            self._explicitly_loaded = True

            # Track metrics
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._metrics["reload_count"] += 1
            self._metrics["last_reload_time_ms"] = elapsed_ms

            return len(self._nodes)
        finally:
            self._cache_enabled = True
            self._invalidate_cache()

    def _ensure_loaded(self) -> None:
        """Ensure nodes are loaded. Called lazily on first access."""
        if not self._explicitly_loaded and not self._nodes:
            self.reload()

    @property
    def nodes(self) -> dict[str, Node]:
        """Get all nodes (read-only view)."""
        return self._nodes.copy()

    def __len__(self) -> int:
        """
        Get the number of nodes in the graph.

        Enables using len() on graph instances.

        Returns:
            int: Total number of nodes

        Example:
            >>> graph = HtmlGraph("features/")
            >>> print(f"Graph has {len(graph)} nodes")
            Graph has 42 nodes
        """
        return len(self._nodes)

    def __contains__(self, node_id: str) -> bool:
        """
        Check if a node exists in the graph.

        Enables using 'in' operator on graph instances.

        Args:
            node_id: Node identifier to check

        Returns:
            bool: True if node exists, False otherwise

        Example:
            >>> graph = HtmlGraph("features/")
            >>> if "feature-001" in graph:
            ...     print("Feature exists!")
            Feature exists!
            >>> if "nonexistent" not in graph:
            ...     print("Not found")
            Not found
        """
        return node_id in self._nodes

    def __iter__(self) -> Iterator[Node]:
        """
        Iterate over all nodes in the graph.

        Enables using graphs in for loops and other iteration contexts.

        Yields:
            Node: Each node in the graph (in arbitrary order)

        Example:
            >>> graph = HtmlGraph("features/")
            >>> for node in graph:
            ...     print(f"{node.id}: {node.title} [{node.status}]")
            feature-001: User Auth [in-progress]
            feature-002: Database [done]

            >>> # Works with list comprehensions
            >>> todo_titles = [n.title for n in graph if n.status == "todo"]
            >>>
            >>> # Works with any iterable operation
            >>> high_priority = list(filter(lambda n: n.priority == "high", graph))
        """
        self._ensure_loaded()
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

        # If overwriting, remove old edges from index first
        if overwrite and node.id in self._nodes:
            self._edge_index.remove_node(node.id)

        filepath = self._converter.save(node)
        self._nodes[node.id] = node

        # Add new edges to index
        for relationship, edges in node.edges.items():
            for edge in edges:
                self._edge_index.add(node.id, edge.target_id, edge.relationship)

        self._invalidate_cache()
        return filepath

    def update(self, node: Node) -> Path:
        """
        Update an existing node.

        Args:
            node: Node with updated data

        Returns:
            Path to updated HTML file

        Raises:
            NodeNotFoundError: If node doesn't exist
        """
        if node.id not in self._nodes:
            raise NodeNotFoundError(node.type, node.id)

        # Get current outgoing edges from the edge index (source of truth)
        # This handles the case where node and self._nodes[node.id] are the same object
        old_outgoing = self._edge_index.get_outgoing(node.id)

        # Remove all old OUTGOING edges (where this node is source)
        # DO NOT use remove_node() as it removes incoming edges too!
        for edge_ref in old_outgoing:
            self._edge_index.remove(
                edge_ref.source_id, edge_ref.target_id, edge_ref.relationship
            )

        # Add new OUTGOING edges (where this node is source)
        for relationship, edges in node.edges.items():
            for edge in edges:
                self._edge_index.add(node.id, edge.target_id, edge.relationship)

        filepath = self._converter.save(node)
        self._nodes[node.id] = node
        self._invalidate_cache()
        return filepath

    def get(self, node_id: str) -> Node | None:
        """
        Get a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node instance or None if not found
        """
        self._ensure_loaded()
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
            self._metrics["single_reload_count"] += 1
        return node

    def reload_node(self, node_id: str) -> Node | None:
        """
        Reload a single node from disk without full graph reload.

        Much faster than full reload() when only one node changed.
        Updates the node in cache and refreshes its edges in the index.

        Args:
            node_id: ID of the node to reload

        Returns:
            Updated node if found and loaded, None if not found

        Example:
            >>> graph.reload_node("feat-001")  # Reload just this node
        """
        # Verify the node file exists
        filepath = self._find_node_file(node_id)
        if not filepath:
            return None

        try:
            # Remove old node's edges from index if exists
            if node_id in self._nodes:
                old_node = self._nodes[node_id]
                self._edge_index.remove_node_edges(node_id, old_node)

            # Load updated node from disk (converter.load expects node_id)
            updated_node = self._converter.load(node_id)
            if not updated_node:
                return None

            # Update cache
            self._nodes[node_id] = updated_node

            # Add new edges to index
            self._edge_index.add_node_edges(node_id, updated_node)

            # Invalidate query cache
            self._invalidate_cache()

            # Track metric
            self._metrics["single_reload_count"] += 1

            return updated_node
        except Exception:
            return None

    def _find_node_file(self, node_id: str) -> Path | None:
        """
        Find the file path for a node by ID.

        Checks common naming patterns for node files.

        Args:
            node_id: Node ID to find

        Returns:
            Path to node file, or None if not found
        """
        # Try direct match patterns
        patterns = [
            f"{node_id}.html",
            f"{node_id}/index.html",
        ]

        for pattern in patterns:
            filepath = self.directory / pattern
            if filepath.exists():
                return filepath

        # Fall back to scanning (slower but thorough)
        for filepath in self.directory.glob("*.html"):
            try:
                # Quick check of file content for ID
                content = filepath.read_text()
                if f'id="{node_id}"' in content or f"id='{node_id}'" in content:
                    return filepath
            except Exception:
                continue

        return None

    def remove(self, node_id: str) -> bool:
        """
        Remove a node from the graph.

        Args:
            node_id: Node to remove

        Returns:
            True if node was removed
        """
        if node_id in self._nodes:
            # Remove all edges involving this node from index
            self._edge_index.remove_node(node_id)
            del self._nodes[node_id]
            result = self._converter.delete(node_id)
            self._invalidate_cache()
            return result
        return False

    def delete(self, node_id: str) -> bool:
        """
        Delete a node from the graph (CRUD-style alias for remove).

        Args:
            node_id: Node to delete

        Returns:
            True if node was deleted

        Example:
            graph.delete("feature-001")
        """
        return self.remove(node_id)

    def batch_delete(self, node_ids: list[str]) -> int:
        """
        Delete multiple nodes in batch.

        Args:
            node_ids: List of node IDs to delete

        Returns:
            Number of nodes successfully deleted

        Example:
            count = graph.batch_delete(["feat-001", "feat-002", "feat-003"])
        """
        count = 0
        for node_id in node_ids:
            if self.delete(node_id):
                count += 1
        return count

    # =========================================================================
    # CSS Selector Queries
    # =========================================================================

    def query(self, selector: str) -> list[Node]:
        """
        Query nodes using CSS selector with caching and metrics.

        Selector is applied to article element of each node.
        Uses cached nodes instead of re-parsing from disk for better performance.

        Args:
            selector: CSS selector string

        Returns:
            List of matching nodes

        Example:
            graph.query("[data-status='blocked']")
            graph.query("[data-priority='high'][data-type='feature']")
        """
        self._ensure_loaded()
        self._metrics["query_count"] += 1

        # Check cache first
        if self._cache_enabled and selector in self._query_cache:
            self._metrics["cache_hits"] += 1
            return self._query_cache[selector].copy()  # Return copy to prevent mutation

        self._metrics["cache_misses"] += 1

        # Time the query
        start = time.perf_counter()

        # Perform query using cached nodes instead of disk I/O
        matching = []

        for node in self._nodes.values():
            try:
                # Convert node to HTML in-memory
                html_content = node.to_html()

                # Parse the HTML string
                parser = HtmlParser.from_string(html_content)

                # Check if selector matches
                if parser.query(f"article{selector}"):
                    matching.append(node)
            except Exception:
                # Skip nodes that fail to parse
                continue

        # Track timing
        elapsed_ms = (time.perf_counter() - start) * 1000
        self._metrics["total_query_time_ms"] += elapsed_ms

        if elapsed_ms > self._metrics["slowest_query_ms"]:
            self._metrics["slowest_query_ms"] = elapsed_ms
            self._metrics["slowest_query_selector"] = selector

        # Cache result
        if self._cache_enabled:
            self._query_cache[selector] = matching.copy()

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
        self._ensure_loaded()
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

    def query_builder(self) -> QueryBuilder:
        """
        Create a fluent query builder for complex queries.

        The query builder provides a chainable API that goes beyond
        CSS selectors with support for:
        - Logical operators (and, or, not)
        - Comparison operators (eq, gt, lt, between)
        - Text search (contains, matches)
        - Nested attribute access (properties.effort)

        Returns:
            QueryBuilder instance for building queries

        Example:
            # Find high-priority blocked features
            results = graph.query_builder() \\
                .where("status", "blocked") \\
                .and_("priority").in_(["high", "critical"]) \\
                .execute()

            # Find features with "auth" in title
            results = graph.query_builder() \\
                .where("title").contains("auth") \\
                .or_("title").contains("login") \\
                .execute()

            # Find low-completion features
            results = graph.query_builder() \\
                .where("properties.completion").lt(50) \\
                .and_("status").ne("done") \\
                .of_type("feature") \\
                .execute()
        """
        return QueryBuilder(_graph=self)

    def find(self, type: str | None = None, **kwargs) -> Node | None:
        """
        Find the first node matching the given criteria.

        BeautifulSoup-style find method with keyword argument filtering.
        Supports lookup suffixes like __contains, __gt, __in.

        Args:
            type: Node type filter (e.g., "feature", "bug")
            **kwargs: Attribute filters with optional lookup suffixes

        Returns:
            First matching Node or None

        Example:
            # Find first blocked feature
            node = graph.find(type="feature", status="blocked")

            # Find with text search
            node = graph.find(title__contains="auth")

            # Find with numeric comparison
            node = graph.find(properties__effort__gt=8)
        """
        return FindAPI(self).find(type=type, **kwargs)

    def find_all(
        self, type: str | None = None, limit: int | None = None, **kwargs
    ) -> list[Node]:
        """
        Find all nodes matching the given criteria.

        BeautifulSoup-style find_all method with keyword argument filtering.

        Args:
            type: Node type filter
            limit: Maximum number of results
            **kwargs: Attribute filters with optional lookup suffixes

        Returns:
            List of matching Nodes

        Example:
            # Find all high-priority features
            nodes = graph.find_all(type="feature", priority="high")

            # Find with multiple conditions
            nodes = graph.find_all(
                status__in=["todo", "blocked"],
                priority__in=["high", "critical"],
                limit=10
            )

            # Find with nested attribute
            nodes = graph.find_all(properties__completion__lt=50)
        """
        return FindAPI(self).find_all(type=type, limit=limit, **kwargs)

    def find_related(
        self, node_id: str, relationship: str | None = None, direction: str = "outgoing"
    ) -> list[Node]:
        """
        Find nodes related to a given node.

        Args:
            node_id: Node ID to find relations for
            relationship: Optional filter by relationship type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of related nodes
        """
        return FindAPI(self).find_related(node_id, relationship, direction)

    # =========================================================================
    # Edge Index Operations (O(1) lookups)
    # =========================================================================

    def get_incoming_edges(
        self, node_id: str, relationship: str | None = None
    ) -> list[EdgeRef]:
        """
        Get all edges pointing TO a node (O(1) lookup).

        Uses the edge index for efficient reverse lookups instead of
        scanning all nodes in the graph.

        Args:
            node_id: Node ID to find incoming edges for
            relationship: Optional filter by relationship type

        Returns:
            List of EdgeRefs for incoming edges

        Example:
            # Find all nodes that block feature-001
            blockers = graph.get_incoming_edges("feature-001", "blocked_by")
            for ref in blockers:
                blocker_node = graph.get(ref.source_id)
                print(f"{blocker_node.title} blocks feature-001")
        """
        return self._edge_index.get_incoming(node_id, relationship)

    def get_outgoing_edges(
        self, node_id: str, relationship: str | None = None
    ) -> list[EdgeRef]:
        """
        Get all edges pointing FROM a node (O(1) lookup).

        Args:
            node_id: Node ID to find outgoing edges for
            relationship: Optional filter by relationship type

        Returns:
            List of EdgeRefs for outgoing edges
        """
        return self._edge_index.get_outgoing(node_id, relationship)

    def get_neighbors(
        self, node_id: str, relationship: str | None = None, direction: str = "both"
    ) -> set[str]:
        """
        Get all neighboring node IDs connected to a node (O(1) lookup).

        Args:
            node_id: Node ID to find neighbors for
            relationship: Optional filter by relationship type
            direction: "incoming", "outgoing", or "both"

        Returns:
            Set of neighboring node IDs
        """
        return self._edge_index.get_neighbors(node_id, relationship, direction)

    @property
    def edge_index(self) -> EdgeIndex:
        """Access the edge index for advanced queries."""
        return self._edge_index

    @property
    def cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "cached_queries": len(self._query_cache),
            "cache_enabled": self._cache_enabled,
        }

    @property
    def metrics(self) -> dict:
        """
        Get performance metrics.

        Returns:
            Dict with query counts, cache stats, timing info

        Example:
            >>> graph.metrics
            {
                'query_count': 42,
                'cache_hits': 38,
                'cache_hit_rate': '90.5%',
                'avg_query_time_ms': 12.3,
                ...
            }
        """
        m = self._metrics.copy()

        # Calculate derived metrics
        if m["query_count"] > 0:
            m["cache_hit_rate"] = f"{m['cache_hits'] / m['query_count'] * 100:.1f}%"
            m["avg_query_time_ms"] = m["total_query_time_ms"] / m["query_count"]
        else:
            m["cache_hit_rate"] = "N/A"
            m["avg_query_time_ms"] = 0.0

        # Add current state
        m["nodes_loaded"] = len(self._nodes)
        m["cached_queries"] = len(self._query_cache)

        return m

    def reset_metrics(self) -> None:
        """Reset all performance metrics to zero."""
        for key in self._metrics:
            if isinstance(self._metrics[key], (int, float)):
                self._metrics[key] = 0 if isinstance(self._metrics[key], int) else 0.0
            else:
                self._metrics[key] = ""

    # =========================================================================
    # Graph Algorithms
    # =========================================================================

    def _get_adjacency_cache(self) -> dict[str, dict[str, list[str]]]:
        """
        Get or build the persistent adjacency cache.

        Builds the cache on first access and returns it on subsequent calls.
        Cache structure: {node_id: {"outgoing": [ids], "incoming": [ids]}}

        Returns:
            Dict mapping node_id to dict with "outgoing" and "incoming" neighbor lists
        """
        if self._adjacency_cache is None:
            self._adjacency_cache = {}
            for node_id in self._nodes:
                # Use edge index for efficient O(1) lookups
                outgoing = self._edge_index.get_neighbors(
                    node_id, relationship=None, direction="outgoing"
                )
                incoming = self._edge_index.get_neighbors(
                    node_id, relationship=None, direction="incoming"
                )
                self._adjacency_cache[node_id] = {
                    "outgoing": list(outgoing),
                    "incoming": list(incoming),
                }
        return self._adjacency_cache

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
        self, from_id: str, to_id: str, relationship: str | None = None
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
        self, node_id: str, relationship: str = "blocked_by"
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

    def dependents(self, node_id: str, relationship: str = "blocked_by") -> set[str]:
        """
        Find all nodes that depend on this node (O(1) lookup).

        Uses the edge index for efficient reverse lookups.

        Args:
            node_id: Node to find dependents for
            relationship: Edge type indicating dependency

        Returns:
            Set of node IDs that depend on this node
        """
        # O(1) lookup using edge index instead of O(V×E) scan
        incoming = self._edge_index.get_incoming(node_id, relationship)
        return {ref.source_id for ref in incoming}

    def find_bottlenecks(
        self, relationship: str = "blocked_by", top_n: int = 5
    ) -> list[tuple[str, int]]:
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
            blocked_count.items(), key=lambda x: x[1], reverse=True
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

    def ancestors(
        self,
        node_id: str,
        relationship: str = "blocked_by",
        max_depth: int | None = None,
    ) -> list[str]:
        """
        Get all ancestor nodes (nodes that this node depends on).

        Traverses incoming edges recursively to find all predecessors.

        Args:
            node_id: Starting node ID
            relationship: Edge type to follow (default: blocked_by)
            max_depth: Maximum traversal depth (None = unlimited)

        Returns:
            List of ancestor node IDs in BFS order (nearest first)
        """
        if node_id not in self._nodes:
            return []

        ancestors: list[str] = []
        visited: set[str] = set()
        queue = deque([(node_id, 0)])
        visited.add(node_id)

        while queue:
            current, depth = queue.popleft()

            # Skip if we've hit max depth
            if max_depth is not None and depth >= max_depth:
                continue

            # Get nodes this one depends on (outgoing blocked_by edges)
            node = self._nodes.get(current)
            if not node:
                continue

            for edge in node.edges.get(relationship, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    ancestors.append(edge.target_id)
                    if edge.target_id in self._nodes:
                        queue.append((edge.target_id, depth + 1))

        return ancestors

    def descendants(
        self,
        node_id: str,
        relationship: str = "blocked_by",
        max_depth: int | None = None,
    ) -> list[str]:
        """
        Get all descendant nodes (nodes that depend on this node).

        Traverses incoming edges (reverse direction) to find all successors.

        Args:
            node_id: Starting node ID
            relationship: Edge type to follow (default: blocked_by)
            max_depth: Maximum traversal depth (None = unlimited)

        Returns:
            List of descendant node IDs in BFS order (nearest first)
        """
        if node_id not in self._nodes:
            return []

        descendants: list[str] = []
        visited: set[str] = set()
        queue = deque([(node_id, 0)])
        visited.add(node_id)

        while queue:
            current, depth = queue.popleft()

            if max_depth is not None and depth >= max_depth:
                continue

            # Get nodes that depend on this one (incoming edges)
            incoming = self._edge_index.get_incoming(current, relationship)

            for ref in incoming:
                if ref.source_id not in visited:
                    visited.add(ref.source_id)
                    descendants.append(ref.source_id)
                    queue.append((ref.source_id, depth + 1))

        return descendants

    def subgraph(
        self, node_ids: list[str] | set[str], include_edges: bool = True
    ) -> "HtmlGraph":
        """
        Extract a subgraph containing only the specified nodes.

        Args:
            node_ids: Node IDs to include in subgraph
            include_edges: Whether to include edges between nodes (default: True)

        Returns:
            New HtmlGraph containing only specified nodes

        Example:
            # Get subgraph of a node and its dependencies
            deps = graph.transitive_deps("feature-001")
            deps.add("feature-001")
            sub = graph.subgraph(deps)
        """
        import tempfile

        # Create new graph in temp directory
        temp_dir = tempfile.mkdtemp(prefix="htmlgraph_subgraph_")
        subgraph = HtmlGraph(temp_dir, auto_load=False)

        node_ids_set = set(node_ids)

        for node_id in node_ids:
            node = self._nodes.get(node_id)
            if not node:
                continue

            # Create copy of node
            if include_edges:
                # Filter edges to only include those pointing to nodes in subgraph
                filtered_edges = {}
                for rel_type, edges in node.edges.items():
                    filtered = [e for e in edges if e.target_id in node_ids_set]
                    if filtered:
                        filtered_edges[rel_type] = filtered
                node_copy = node.model_copy(update={"edges": filtered_edges})
            else:
                node_copy = node.model_copy(update={"edges": {}})

            subgraph.add(node_copy)

        return subgraph

    def connected_component(
        self, node_id: str, relationship: str | None = None
    ) -> set[str]:
        """
        Get all nodes in the same connected component as the given node.

        Treats edges as undirected (both directions).

        Args:
            node_id: Starting node ID
            relationship: Optional filter to specific edge type

        Returns:
            Set of node IDs in the connected component
        """
        if node_id not in self._nodes:
            return set()

        component: set[str] = set()
        queue = deque([node_id])

        while queue:
            current = queue.popleft()
            if current in component:
                continue

            component.add(current)

            # Get all neighbors (both directions)
            neighbors = self._edge_index.get_neighbors(current, relationship, "both")
            for neighbor in neighbors:
                if neighbor not in component and neighbor in self._nodes:
                    queue.append(neighbor)

        return component

    def all_paths(
        self,
        from_id: str,
        to_id: str,
        relationship: str | None = None,
        max_length: int | None = None,
        max_paths: int = 100,
        timeout_seconds: float = 5.0,
    ) -> list[list[str]]:
        """
        Find all paths between two nodes.

        WARNING: This method has O(V!) worst-case complexity in dense graphs.
        Use max_paths and timeout_seconds parameters to limit execution.
        For most use cases, prefer shortest_path() instead.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            relationship: Optional edge type filter
            max_length: Maximum path length
            max_paths: Maximum number of paths to return (default 100)
            timeout_seconds: Maximum execution time (default 5.0)

        Returns:
            List of paths (each path is list of node IDs)

        Raises:
            TimeoutError: If execution exceeds timeout_seconds
        """
        if from_id not in self._nodes or to_id not in self._nodes:
            return []

        if from_id == to_id:
            return [[from_id]]

        paths: list[list[str]] = []
        adj = self._build_adjacency(relationship)
        start_time = time.time()

        def dfs(current: str, target: str, path: list[str], visited: set[str]):
            # Check timeout periodically (every recursive call)
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    f"all_paths() exceeded timeout of {timeout_seconds}s "
                    f"(found {len(paths)} paths so far)"
                )

            # Check if we've hit the max_paths limit
            if len(paths) >= max_paths:
                return

            if max_length and len(path) > max_length:
                return

            if current == target:
                paths.append(path.copy())
                return

            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, target, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(from_id, to_id, [from_id], {from_id})
        return paths

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
            round(done_count / len(self._nodes) * 100, 1) if self._nodes else 0
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
        lines.append(
            f"Total: {stats['total']} nodes | Done: {stats['completion_rate']}%"
        )

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
