"""
PathQuery DSL - Declarative Path Expression Language for HtmlGraph.

Provides a SQL/PGQ-inspired MATCH syntax for expressing graph traversal
patterns as declarative path expressions. Compiles path expressions into
calls against existing HtmlGraph graph methods and edge index lookups.

Syntax examples:
    # Single-hop: find all features blocked by another feature
    "(Feature)-[blocked_by]->(Feature)"

    # Variable-length: find all transitive dependencies
    "(Feature)-[depends_on]->+(Feature)"

    # With node filter: find blocked high-priority features
    "(Feature WHERE status='blocked')-[blocked_by]->(Feature WHERE priority='high')"

    # Reverse direction
    "(Feature)<-[blocks]-(Feature)"

    # Multi-hop pattern
    "(Session)-[touches]->(Feature)<-[blocked_by]-(Feature)"

    # Any shortest path
    "(Feature)-[blocked_by]->*(Feature)"

Usage:
    from htmlgraph.path_query import PathQueryEngine

    engine = PathQueryEngine()
    results = engine.execute(graph, "(Feature)-[blocked_by]->(Feature)")
    for result in results:
        print(result.nodes, result.path_length)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class WhereClause:
    """A single WHERE filter condition on a node pattern.

    Attributes:
        attribute: The node attribute name to filter on (e.g. 'status', 'priority').
        value: The expected value (string comparison).
    """

    attribute: str
    value: str


@dataclass
class NodePattern:
    """Parsed representation of a node pattern in a path expression.

    A node pattern looks like ``(Label)`` or ``(Label WHERE attr='val')``.

    Attributes:
        label: Optional node type label (e.g. 'Feature', 'Session').
            An empty string means *any* node type.
        filters: List of WHERE clause conditions to apply.
    """

    label: str = ""
    filters: list[WhereClause] = field(default_factory=list)


@dataclass
class EdgePattern:
    """Parsed representation of an edge pattern in a path expression.

    An edge pattern looks like ``-[rel_type]->`` or ``<-[rel_type]-``.

    Attributes:
        relationship: The edge relationship type (e.g. 'blocked_by').
        direction: ``'outgoing'`` for ``->``, ``'incoming'`` for ``<-``.
        quantifier: ``None`` for single-hop, ``'+'`` for one-or-more
            (transitive), ``'*'`` for zero-or-more (shortest path),
            ``'?'`` for zero-or-one (optional).
    """

    relationship: str
    direction: str = "outgoing"  # "outgoing" (->) or "incoming" (<-)
    quantifier: str | None = None  # None, "+", "*", "?"


@dataclass
class PathExpression:
    """Fully parsed path expression.

    A path expression is an alternating sequence of *node patterns* and
    *edge patterns*:  ``node edge node [edge node ...]``.

    Attributes:
        nodes: Ordered list of node patterns.
        edges: Ordered list of edge patterns.  ``len(edges) == len(nodes) - 1``.
        raw: The original expression string.
    """

    nodes: list[NodePattern] = field(default_factory=list)
    edges: list[EdgePattern] = field(default_factory=list)
    raw: str = ""


@dataclass
class PathResult:
    """A single result from executing a path query.

    Attributes:
        nodes: The list of node IDs that form the matched path.
        path_length: Number of hops (edges) in the path.
        bindings: Mapping from pattern index to matched node ID(s).
    """

    nodes: list[str] = field(default_factory=list)
    path_length: int = 0
    bindings: dict[int, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# Regex patterns for tokenising the DSL string.
_NODE_PATTERN = re.compile(
    r"""\(
        \s*
        (?P<label>[A-Za-z_][A-Za-z0-9_]*)?   # optional label
        \s*
        (?:WHERE\s+(?P<where>.+?))?            # optional WHERE clause
        \s*
    \)""",
    re.VERBOSE,
)

_WHERE_CONDITION = re.compile(
    r"""(?P<attr>[A-Za-z_][A-Za-z0-9_.]*)\s*=\s*'(?P<val>[^']*)'""",
    re.VERBOSE,
)

# Edge patterns.  Arrows can appear in two forms:
#   outgoing:  -[rel]->   with optional quantifier after >
#   incoming:  <-[rel]-   with optional quantifier after second -
_EDGE_OUTGOING = re.compile(
    r"""-\[
        \s*(?P<rel>[A-Za-z_][A-Za-z0-9_]*)\s*
    \]->(?P<quant>[+*?])?""",
    re.VERBOSE,
)

_EDGE_INCOMING = re.compile(
    r"""<-\[
        \s*(?P<rel>[A-Za-z_][A-Za-z0-9_]*)\s*
    \]-(?P<quant>[+*?])?""",
    re.VERBOSE,
)


class PathQueryError(Exception):
    """Raised when a path expression cannot be parsed or executed."""


class PathQueryParser:
    """Parses a path expression string into a :class:`PathExpression`.

    The parser works by tokenising the input from left to right, alternating
    between node patterns and edge patterns.

    Example::

        parser = PathQueryParser()
        expr = parser.parse("(Feature)-[blocked_by]->(Feature)")
    """

    def parse(self, expression: str) -> PathExpression:
        """Parse a path expression string.

        Args:
            expression: The path expression DSL string.

        Returns:
            A fully parsed :class:`PathExpression`.

        Raises:
            PathQueryError: If the expression is syntactically invalid.
        """
        expression = expression.strip()
        if not expression:
            raise PathQueryError("Empty path expression")

        result = PathExpression(raw=expression)
        pos = 0
        expecting_node = True

        while pos < len(expression):
            # Skip whitespace
            while pos < len(expression) and expression[pos].isspace():
                pos += 1
            if pos >= len(expression):
                break

            if expecting_node:
                node, end = self._parse_node(expression, pos)
                result.nodes.append(node)
                pos = end
                expecting_node = False
            else:
                edge, end = self._parse_edge(expression, pos)
                result.edges.append(edge)
                pos = end
                expecting_node = True

        # Validate structure: must have at least 2 nodes and 1 edge
        if len(result.nodes) < 2:
            raise PathQueryError(
                f"Path expression must have at least two node patterns "
                f"and one edge pattern, got {len(result.nodes)} node(s) "
                f"and {len(result.edges)} edge(s): {expression!r}"
            )
        if len(result.edges) != len(result.nodes) - 1:
            raise PathQueryError(
                f"Mismatched nodes and edges: {len(result.nodes)} nodes, "
                f"{len(result.edges)} edges in: {expression!r}"
            )

        return result

    # -- private helpers ---------------------------------------------------

    def _parse_node(self, expr: str, pos: int) -> tuple[NodePattern, int]:
        """Parse a node pattern starting at *pos*.

        Returns:
            Tuple of (NodePattern, end_position).
        """
        m = _NODE_PATTERN.match(expr, pos)
        if not m:
            raise PathQueryError(
                f"Expected node pattern at position {pos}: {expr[pos : pos + 30]!r}..."
            )
        label = m.group("label") or ""
        where_str = m.group("where") or ""
        filters = self._parse_where(where_str)
        return NodePattern(label=label, filters=filters), m.end()

    def _parse_edge(self, expr: str, pos: int) -> tuple[EdgePattern, int]:
        """Parse an edge pattern starting at *pos*.

        Returns:
            Tuple of (EdgePattern, end_position).
        """
        # Try outgoing first
        m = _EDGE_OUTGOING.match(expr, pos)
        if m:
            return (
                EdgePattern(
                    relationship=m.group("rel"),
                    direction="outgoing",
                    quantifier=m.group("quant") or None,
                ),
                m.end(),
            )

        # Try incoming
        m = _EDGE_INCOMING.match(expr, pos)
        if m:
            return (
                EdgePattern(
                    relationship=m.group("rel"),
                    direction="incoming",
                    quantifier=m.group("quant") or None,
                ),
                m.end(),
            )

        raise PathQueryError(
            f"Expected edge pattern at position {pos}: {expr[pos : pos + 30]!r}..."
        )

    @staticmethod
    def _parse_where(where_str: str) -> list[WhereClause]:
        """Parse the body of a WHERE clause into a list of conditions.

        Supports ``AND``-separated conditions like
        ``status='blocked' AND priority='high'``.
        """
        if not where_str.strip():
            return []

        clauses: list[WhereClause] = []
        # Split on AND (case-insensitive)
        parts = re.split(r"\s+AND\s+", where_str, flags=re.IGNORECASE)
        for part in parts:
            m = _WHERE_CONDITION.match(part.strip())
            if not m:
                raise PathQueryError(
                    f"Invalid WHERE condition: {part.strip()!r}. "
                    f"Expected format: attribute='value'"
                )
            clauses.append(WhereClause(attribute=m.group("attr"), value=m.group("val")))
        return clauses


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PathQueryEngine:
    """Executes parsed :class:`PathExpression` objects against an HtmlGraph.

    The engine maps DSL constructs to existing HtmlGraph operations:

    * **Single-hop** edges use ``EdgeIndex.get_outgoing`` /
      ``EdgeIndex.get_incoming`` for O(1) neighbour lookups.
    * **Variable-length ``+``** (one-or-more) uses
      ``HtmlGraph.transitive_deps`` or ``HtmlGraph.ancestors``.
    * **Variable-length ``*``** (zero-or-more / shortest) uses
      ``HtmlGraph.shortest_path``.
    * **Optional ``?``** returns the direct hop if it exists, or the
      source node alone otherwise.

    Example::

        engine = PathQueryEngine()
        results = engine.execute(graph, "(Feature)-[blocked_by]->(Feature)")
    """

    def __init__(self) -> None:
        self._parser = PathQueryParser()

    def execute(
        self, graph: HtmlGraph, expression: str | PathExpression
    ) -> list[PathResult]:
        """Execute a path expression against a graph.

        Args:
            graph: The :class:`HtmlGraph` instance to query.
            expression: Either a DSL string or a pre-parsed
                :class:`PathExpression`.

        Returns:
            List of :class:`PathResult` objects for every matching path.

        Raises:
            PathQueryError: If the expression is invalid or cannot be
                executed.
        """
        if isinstance(expression, str):
            expr = self._parser.parse(expression)
        else:
            expr = expression

        # Ensure graph data is loaded
        graph._ensure_loaded()  # noqa: SLF001 — accessing private for lazy-load

        # Seed: find all candidate start nodes
        start_candidates = self._match_node_pattern(graph, expr.nodes[0])

        # Walk each hop, expanding candidates
        results: list[PathResult] = []
        for start_id in start_candidates:
            partial_paths: list[list[str]] = [[start_id]]
            for hop_idx, edge_pat in enumerate(expr.edges):
                target_node_pat = expr.nodes[hop_idx + 1]
                next_partial: list[list[str]] = []

                for path in partial_paths:
                    current_id = path[-1]
                    expanded = self._expand_hop(
                        graph, current_id, edge_pat, target_node_pat
                    )
                    for ext in expanded:
                        next_partial.append(path + ext)

                partial_paths = next_partial

            # Convert successful full paths to PathResult
            for path in partial_paths:
                results.append(
                    PathResult(
                        nodes=path,
                        path_length=len(path) - 1,
                        bindings={i: [nid] for i, nid in enumerate(path)},
                    )
                )

        return results

    # -- private helpers ---------------------------------------------------

    def _match_node_pattern(self, graph: HtmlGraph, pattern: NodePattern) -> list[str]:
        """Return IDs of all nodes matching a :class:`NodePattern`."""
        candidates: list[str] = []
        for node_id, node in graph.nodes.items():
            if pattern.label and node.type.lower() != pattern.label.lower():
                continue
            if not self._check_filters(node, pattern.filters):
                continue
            candidates.append(node_id)
        return candidates

    @staticmethod
    def _check_filters(node: object, filters: list[WhereClause]) -> bool:
        """Check whether *node* satisfies all WHERE filters."""
        for f in filters:
            val = _resolve_attribute(node, f.attribute)
            if val is None or str(val) != f.value:
                return False
        return True

    def _expand_hop(
        self,
        graph: HtmlGraph,
        current_id: str,
        edge_pat: EdgePattern,
        target_pat: NodePattern,
    ) -> list[list[str]]:
        """Expand one hop from *current_id* following *edge_pat*.

        Returns a list of path *extensions* (each a list of node IDs
        **not** including *current_id* itself).
        """
        quant = edge_pat.quantifier

        if quant is None:
            return self._expand_single(graph, current_id, edge_pat, target_pat)
        elif quant == "+":
            return self._expand_transitive(graph, current_id, edge_pat, target_pat)
        elif quant == "*":
            return self._expand_shortest(graph, current_id, edge_pat, target_pat)
        elif quant == "?":
            return self._expand_optional(graph, current_id, edge_pat, target_pat)
        else:
            raise PathQueryError(f"Unknown quantifier: {quant!r}")

    # -- single hop --------------------------------------------------------

    def _expand_single(
        self,
        graph: HtmlGraph,
        current_id: str,
        edge_pat: EdgePattern,
        target_pat: NodePattern,
    ) -> list[list[str]]:
        """Expand a single-hop (no quantifier) edge."""
        neighbor_ids = self._direct_neighbors(graph, current_id, edge_pat)

        extensions: list[list[str]] = []
        for nid in neighbor_ids:
            node = graph.get(nid)
            if node is None:
                continue
            if target_pat.label and node.type.lower() != target_pat.label.lower():
                continue
            if not self._check_filters(node, target_pat.filters):
                continue
            extensions.append([nid])
        return extensions

    # -- transitive (one-or-more "+") --------------------------------------

    def _expand_transitive(
        self,
        graph: HtmlGraph,
        current_id: str,
        edge_pat: EdgePattern,
        target_pat: NodePattern,
    ) -> list[list[str]]:
        """Expand a variable-length ``+`` (one-or-more) edge.

        Uses ``HtmlGraph.transitive_deps`` for outgoing edges and
        ``HtmlGraph.ancestors`` for incoming (reversed) edges.
        """
        if edge_pat.direction == "outgoing":
            reachable = graph.transitive_deps(current_id, edge_pat.relationship)
        else:
            reachable = set(graph.ancestors(current_id, edge_pat.relationship))

        extensions: list[list[str]] = []
        for nid in reachable:
            node = graph.get(nid)
            if node is None:
                continue
            if target_pat.label and node.type.lower() != target_pat.label.lower():
                continue
            if not self._check_filters(node, target_pat.filters):
                continue
            extensions.append([nid])
        return extensions

    # -- shortest (zero-or-more "*") ---------------------------------------

    def _expand_shortest(
        self,
        graph: HtmlGraph,
        current_id: str,
        edge_pat: EdgePattern,
        target_pat: NodePattern,
    ) -> list[list[str]]:
        """Expand ``*`` using ``HtmlGraph.shortest_path``.

        Returns the shortest path to every reachable target node that
        matches *target_pat*.
        """
        # Collect all candidates matching the target pattern
        target_ids = self._match_node_pattern(graph, target_pat)

        extensions: list[list[str]] = []
        for tid in target_ids:
            if tid == current_id:
                # zero-length path (allowed by *)
                extensions.append([tid])
                continue

            path = graph.shortest_path(
                current_id, tid, relationship=edge_pat.relationship
            )
            if path is not None and len(path) >= 2:
                # path includes current_id as first element; strip it
                extensions.append(path[1:])

        return extensions

    # -- optional (zero-or-one "?") ----------------------------------------

    def _expand_optional(
        self,
        graph: HtmlGraph,
        current_id: str,
        edge_pat: EdgePattern,
        target_pat: NodePattern,
    ) -> list[list[str]]:
        """Expand ``?`` — match zero or one hop.

        Returns direct-hop matches plus *current_id* itself if it matches
        the target pattern (zero-hop case).
        """
        results = self._expand_single(graph, current_id, edge_pat, target_pat)

        # Zero-hop: current node must match target pattern
        current_node = graph.get(current_id)
        if current_node is not None:
            matches = True
            if (
                target_pat.label
                and current_node.type.lower() != target_pat.label.lower()
            ):
                matches = False
            if not self._check_filters(current_node, target_pat.filters):
                matches = False
            if matches:
                results.append([current_id])

        return results

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _direct_neighbors(
        graph: HtmlGraph,
        node_id: str,
        edge_pat: EdgePattern,
    ) -> list[str]:
        """Get direct neighbour IDs for a single-hop edge pattern."""
        if edge_pat.direction == "outgoing":
            refs = graph.edge_index.get_outgoing(node_id, edge_pat.relationship)
            return [r.target_id for r in refs]
        else:
            refs = graph.edge_index.get_incoming(node_id, edge_pat.relationship)
            return [r.source_id for r in refs]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_attribute(node: object, attr: str) -> object | None:
    """Resolve a possibly-dotted attribute path on *node*.

    Supports plain attributes (``status``), nested dotted paths
    (``properties.effort``), and dictionary access.
    """
    parts = attr.split(".")
    current: object = node
    for part in parts:
        if current is None:
            return None
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
