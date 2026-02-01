"""
Graph Pattern Matching Engine for HtmlGraph.

Provides a declarative API inspired by SQL/PGQ's MATCH clause for finding
structural patterns across the graph. Patterns are built using a fluent
builder and executed against an HtmlGraph instance.

Example:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.pattern_matcher import GraphPattern

    graph = HtmlGraph("features/", auto_load=True)

    # Find features blocked by high-priority work
    pattern = GraphPattern()
    pattern.node("f1", label="feature", filters={"status": "blocked"})
    pattern.edge("b", source="f1", target="f2", relationship="blocked_by")
    pattern.node("f2", label="feature", filters={"priority": "high"})

    results = pattern.match(graph)
    for result in results:
        blocker = result.get_node("f1")
        blocking = result.get_node("f2")
        print(f"{blocker.title} is blocked by {blocking.title}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from htmlgraph.edge_index import EdgeRef
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node


@dataclass
class NodePattern:
    """
    A pattern for matching a single graph node.

    Attributes:
        variable: Binding variable name used to reference this node in
            results and edge patterns (e.g., "f1", "src").
        label: Optional node type filter. When set, only nodes whose
            ``type`` attribute matches this value are considered candidates.
        filters: Optional attribute filters. Keys are attribute names
            (supporting dot notation for nested access, e.g.,
            "properties.effort") and values are expected values. All
            filters must match for a node to be a candidate.
    """

    variable: str
    label: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)

    def matches(self, node: Node) -> bool:
        """
        Check whether a node satisfies this pattern.

        Args:
            node: The node to check.

        Returns:
            True if the node matches the label and all attribute filters.
        """
        # Check label (maps to node.type)
        if self.label is not None and node.type != self.label:
            return False

        # Check attribute filters
        for attr, expected in self.filters.items():
            actual = _get_nested_attr(node, attr)
            if actual != expected:
                return False

        return True


@dataclass
class EdgePattern:
    """
    A pattern for matching a graph edge between two node variables.

    Attributes:
        variable: Binding variable name for this edge in results.
        source: Variable name of the source node pattern.
        target: Variable name of the target node pattern.
        relationship: Optional edge relationship type filter.
        direction: Edge traversal direction relative to the source node.
            ``"outgoing"`` means source -> target, ``"incoming"`` means
            target -> source, ``"both"`` matches either direction.
        quantifier: Edge repetition quantifier.
            ``"one"`` matches exactly one edge hop,
            ``"one_or_more"`` matches one or more hops (transitive),
            ``"zero_or_more"`` matches zero or more hops (reflexive transitive).
    """

    variable: str
    source: str
    target: str
    relationship: str | None = None
    direction: Literal["outgoing", "incoming", "both"] = "outgoing"
    quantifier: Literal["one", "one_or_more", "zero_or_more"] = "one"


@dataclass
class MatchResult:
    """
    A single result from pattern matching.

    Contains the bindings from pattern variables to matched graph entities
    (nodes and edges).

    Attributes:
        bindings: Mapping from variable names to matched Node or EdgeRef
            instances.
        path_length: Total number of edges traversed in this match.
    """

    bindings: dict[str, Node | EdgeRef] = field(default_factory=dict)
    path_length: int = 0

    def get_node(self, variable: str) -> Node:
        """
        Retrieve a matched node by its pattern variable name.

        Args:
            variable: The variable name assigned in the pattern.

        Returns:
            The matched Node instance.

        Raises:
            KeyError: If the variable is not found in bindings.
            TypeError: If the binding is not a Node.
        """
        from htmlgraph.models import Node as NodeModel

        value = self.bindings[variable]
        if not isinstance(value, NodeModel):
            raise TypeError(
                f"Binding '{variable}' is not a Node, got {type(value).__name__}"
            )
        return value

    def get_edge(self, variable: str) -> EdgeRef:
        """
        Retrieve a matched edge reference by its pattern variable name.

        Args:
            variable: The variable name assigned in the pattern.

        Returns:
            The matched EdgeRef instance.

        Raises:
            KeyError: If the variable is not found in bindings.
            TypeError: If the binding is not an EdgeRef.
        """
        from htmlgraph.edge_index import EdgeRef as EdgeRefClass

        value = self.bindings[variable]
        if not isinstance(value, EdgeRefClass):
            raise TypeError(
                f"Binding '{variable}' is not an EdgeRef, got {type(value).__name__}"
            )
        return value


class GraphPattern:
    """
    Fluent builder for constructing graph patterns.

    Graph patterns describe structural shapes to find in the graph,
    consisting of node patterns (with optional type and attribute filters)
    and edge patterns (with optional relationship and direction filters).

    Example:
        pattern = GraphPattern()
        pattern.node("a", label="feature", filters={"status": "blocked"})
        pattern.edge("e", source="a", target="b", relationship="blocked_by")
        pattern.node("b", label="feature", filters={"priority": "high"})

        results = pattern.match(graph)
    """

    def __init__(self) -> None:
        self._node_patterns: list[NodePattern] = []
        self._edge_patterns: list[EdgePattern] = []
        self._node_pattern_map: dict[str, NodePattern] = {}
        self._columns: list[str] | None = None

    def node(
        self,
        variable: str,
        label: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> GraphPattern:
        """
        Add a node pattern to the graph pattern.

        Args:
            variable: Binding variable name for this node.
            label: Optional node type filter (matches ``Node.type``).
            filters: Optional attribute filters as key-value pairs.

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If a node pattern with the same variable already exists.
        """
        if variable in self._node_pattern_map:
            raise ValueError(f"Duplicate node variable: '{variable}'")

        np = NodePattern(variable=variable, label=label, filters=filters or {})
        self._node_patterns.append(np)
        self._node_pattern_map[variable] = np
        return self

    def edge(
        self,
        variable: str,
        source: str,
        target: str,
        relationship: str | None = None,
        direction: Literal["outgoing", "incoming", "both"] = "outgoing",
        quantifier: Literal["one", "one_or_more", "zero_or_more"] = "one",
    ) -> GraphPattern:
        """
        Add an edge pattern connecting two node variables.

        Args:
            variable: Binding variable name for this edge.
            source: Variable name of the source node pattern.
            target: Variable name of the target node pattern.
            relationship: Optional edge relationship type filter.
            direction: Edge traversal direction (``"outgoing"``,
                ``"incoming"``, or ``"both"``).
            quantifier: Edge repetition quantifier (``"one"``,
                ``"one_or_more"``, or ``"zero_or_more"``).

        Returns:
            Self for method chaining.
        """
        ep = EdgePattern(
            variable=variable,
            source=source,
            target=target,
            relationship=relationship,
            direction=direction,
            quantifier=quantifier,
        )
        self._edge_patterns.append(ep)
        return self

    def columns(self, *attrs: str) -> GraphPattern:
        """
        Specify which bindings to project in results.

        When set, only the specified variables will appear in the
        ``MatchResult.bindings`` dictionary. If not called, all bindings
        are included.

        Args:
            *attrs: Variable names to include in results.

        Returns:
            Self for method chaining.
        """
        self._columns = list(attrs)
        return self

    def match(self, graph: HtmlGraph) -> list[MatchResult]:
        """
        Execute this pattern against a graph and return all matches.

        Args:
            graph: The HtmlGraph instance to search.

        Returns:
            List of MatchResult instances, one per unique match found.
        """
        matcher = PatternMatcher(pattern=self, graph=graph)
        return matcher.execute()


class PatternMatcher:
    """
    Engine that executes a GraphPattern against an HtmlGraph.

    The matcher works by:
    1. Ordering node patterns by their appearance in edge patterns to
       determine a traversal plan.
    2. Finding candidate nodes for the first node pattern.
    3. For each candidate, traversing edges using the EdgeIndex to find
       matching neighbors.
    4. Checking neighbor attribute filters.
    5. Building MatchResult bindings for all valid complete matches.

    Args:
        pattern: The GraphPattern to execute.
        graph: The HtmlGraph to search.
    """

    def __init__(self, pattern: GraphPattern, graph: HtmlGraph) -> None:
        self._pattern = pattern
        self._graph = graph

    def execute(self) -> list[MatchResult]:
        """
        Execute the pattern and return all matches.

        Returns:
            List of MatchResult instances.
        """
        # Ensure graph nodes are loaded
        self._graph._ensure_loaded()

        node_patterns = self._pattern._node_patterns
        edge_patterns = self._pattern._edge_patterns

        if not node_patterns:
            return []

        # Build traversal order from edge patterns
        traversal_plan = self._build_traversal_plan(node_patterns, edge_patterns)

        # Start matching from the first node pattern in the plan
        first_var = traversal_plan[0][0]
        first_np = self._pattern._node_pattern_map[first_var]

        # Find all candidates for the first node pattern
        candidates = self._find_candidates(first_np)

        # For each candidate, expand through the traversal plan
        results: list[MatchResult] = []
        for candidate in candidates:
            initial_bindings: dict[str, Any] = {first_var: candidate}
            self._expand(traversal_plan, 1, initial_bindings, 0, results)

        # Apply column projection if specified
        if self._pattern._columns is not None:
            projected_cols = set(self._pattern._columns)
            for result in results:
                result.bindings = {
                    k: v for k, v in result.bindings.items() if k in projected_cols
                }

        return results

    def _build_traversal_plan(
        self,
        node_patterns: list[NodePattern],
        edge_patterns: list[EdgePattern],
    ) -> list[tuple[str, EdgePattern | None]]:
        """
        Build an ordered traversal plan from node and edge patterns.

        The plan is a list of ``(node_variable, edge_pattern_or_None)`` tuples.
        The first entry has ``None`` for the edge (it's the starting point).
        Subsequent entries describe which edge to traverse and which node
        variable to bind next.

        Args:
            node_patterns: List of node patterns in the graph pattern.
            edge_patterns: List of edge patterns in the graph pattern.

        Returns:
            Ordered traversal plan.
        """
        if not edge_patterns:
            # No edges: just return all node patterns as independent matches
            return [(np.variable, None) for np in node_patterns]

        # Build a plan by following edge patterns in order
        visited_vars: set[str] = set()
        plan: list[tuple[str, EdgePattern | None]] = []

        # Start with the source of the first edge
        first_edge = edge_patterns[0]
        start_var = first_edge.source
        plan.append((start_var, None))
        visited_vars.add(start_var)

        for ep in edge_patterns:
            # Determine which end is the "next" node to visit
            if ep.source in visited_vars and ep.target not in visited_vars:
                plan.append((ep.target, ep))
                visited_vars.add(ep.target)
            elif ep.target in visited_vars and ep.source not in visited_vars:
                plan.append((ep.source, ep))
                visited_vars.add(ep.source)
            elif ep.source not in visited_vars:
                # Neither end visited yet - start a new component
                plan.append((ep.source, None))
                visited_vars.add(ep.source)
                plan.append((ep.target, ep))
                visited_vars.add(ep.target)
            # else: both already visited (cross-edge), skip for now

        # Add any node patterns not yet in the plan (disconnected nodes)
        for np in node_patterns:
            if np.variable not in visited_vars:
                plan.append((np.variable, None))
                visited_vars.add(np.variable)

        return plan

    def _find_candidates(self, node_pattern: NodePattern) -> list[Node]:
        """
        Find all nodes matching a node pattern.

        Args:
            node_pattern: The node pattern to match against.

        Returns:
            List of candidate nodes.
        """
        candidates: list[Node] = []
        for node in self._graph._nodes.values():
            if node_pattern.matches(node):
                candidates.append(node)
        return candidates

    def _expand(
        self,
        plan: list[tuple[str, EdgePattern | None]],
        step_index: int,
        bindings: dict[str, Any],
        edge_count: int,
        results: list[MatchResult],
    ) -> None:
        """
        Recursively expand partial matches through the traversal plan.

        Args:
            plan: The traversal plan.
            step_index: Current index into the plan.
            bindings: Current variable bindings (variable -> Node or EdgeRef).
            edge_count: Running count of edges traversed.
            results: Accumulator for complete match results.
        """
        if step_index >= len(plan):
            # All steps satisfied - record result
            results.append(MatchResult(bindings=dict(bindings), path_length=edge_count))
            return

        next_var, edge_pattern = plan[step_index]
        next_np = self._pattern._node_pattern_map.get(next_var)

        if edge_pattern is None:
            # No edge to traverse - find independent candidates
            if next_np is None:
                return
            for candidate in self._find_candidates(next_np):
                # Ensure no duplicate node bindings
                if any(
                    isinstance(v, type(candidate))
                    and hasattr(v, "id")
                    and v.id == candidate.id
                    for v in bindings.values()
                ):
                    continue
                bindings[next_var] = candidate
                self._expand(plan, step_index + 1, bindings, edge_count, results)
                del bindings[next_var]
            return

        # Traverse edge from bound source/target to find the next node
        self._traverse_edge(
            edge_pattern,
            next_var,
            next_np,
            plan,
            step_index,
            bindings,
            edge_count,
            results,
        )

    def _traverse_edge(
        self,
        edge_pattern: EdgePattern,
        next_var: str,
        next_np: NodePattern | None,
        plan: list[tuple[str, EdgePattern | None]],
        step_index: int,
        bindings: dict[str, Any],
        edge_count: int,
        results: list[MatchResult],
    ) -> None:
        """
        Traverse an edge pattern to find matching neighbor nodes.

        Args:
            edge_pattern: The edge pattern to traverse.
            next_var: The variable to bind the discovered node to.
            next_np: Optional node pattern the discovered node must match.
            plan: The full traversal plan.
            step_index: Current step index.
            bindings: Current variable bindings.
            edge_count: Running edge count.
            results: Result accumulator.
        """
        from htmlgraph.edge_index import EdgeRef as EdgeRefClass

        # Determine which bound node to traverse from
        source_var = edge_pattern.source
        target_var = edge_pattern.target

        if source_var in bindings and next_var == target_var:
            # Forward traversal: source is bound, looking for target
            bound_node = bindings[source_var]
            bound_node_id: str = bound_node.id
            ref_pairs = self._get_edge_refs_with_neighbors(
                bound_node_id, edge_pattern, traversal="forward"
            )
            for ref, neighbor_id in ref_pairs:
                neighbor = self._graph._nodes.get(neighbor_id)
                if neighbor is None:
                    continue
                if next_np is not None and not next_np.matches(neighbor):
                    continue
                bindings[next_var] = neighbor
                bindings[edge_pattern.variable] = ref
                self._expand(plan, step_index + 1, bindings, edge_count + 1, results)
                del bindings[next_var]
                del bindings[edge_pattern.variable]

        elif target_var in bindings and next_var == source_var:
            # Reverse traversal: target is bound, looking for source
            bound_node = bindings[target_var]
            bound_node_id = bound_node.id
            ref_pairs = self._get_edge_refs_with_neighbors(
                bound_node_id, edge_pattern, traversal="reverse"
            )
            for ref, neighbor_id in ref_pairs:
                neighbor = self._graph._nodes.get(neighbor_id)
                if neighbor is None:
                    continue
                if next_np is not None and not next_np.matches(neighbor):
                    continue
                bindings[next_var] = neighbor
                bindings[edge_pattern.variable] = EdgeRefClass(
                    source_id=neighbor_id,
                    target_id=bound_node_id,
                    relationship=ref.relationship,
                )
                self._expand(plan, step_index + 1, bindings, edge_count + 1, results)
                del bindings[next_var]
                del bindings[edge_pattern.variable]

    def _get_edge_refs_with_neighbors(
        self,
        node_id: str,
        edge_pattern: EdgePattern,
        traversal: Literal["forward", "reverse"],
    ) -> list[tuple[EdgeRef, str]]:
        """
        Get matching edge references with their neighbor node IDs.

        For each matching edge, returns a tuple of ``(EdgeRef, neighbor_id)``
        where ``neighbor_id`` is the ID of the node on the *other* end of the
        edge from ``node_id``.

        Args:
            node_id: The node ID to look up edges for.
            edge_pattern: The edge pattern with direction and relationship filters.
            traversal: Whether we are going forward (outgoing from node_id)
                or reverse (incoming to node_id).

        Returns:
            List of ``(EdgeRef, neighbor_id)`` tuples.
        """
        direction = edge_pattern.direction
        relationship = edge_pattern.relationship
        edge_index = self._graph._edge_index

        pairs: list[tuple[EdgeRef, str]] = []

        if traversal == "forward":
            # Forward: source is bound (node_id), looking for targets
            if direction in ("outgoing", "both"):
                for ref in edge_index.get_outgoing(node_id, relationship):
                    pairs.append((ref, ref.target_id))
            if direction in ("incoming", "both"):
                for ref in edge_index.get_incoming(node_id, relationship):
                    pairs.append((ref, ref.source_id))
        else:
            # Reverse: target is bound (node_id), looking for sources
            if direction in ("outgoing", "both"):
                for ref in edge_index.get_incoming(node_id, relationship):
                    pairs.append((ref, ref.source_id))
            if direction in ("incoming", "both"):
                for ref in edge_index.get_outgoing(node_id, relationship):
                    pairs.append((ref, ref.target_id))

        return pairs


def _get_nested_attr(obj: Any, path: str) -> Any:
    """
    Get a nested attribute using dot notation.

    Supports:
    - Direct attributes: "status", "priority"
    - Nested attributes: "properties.effort"
    - Dictionary access: properties["key"]

    Args:
        obj: Object to get attribute from.
        path: Dot-separated path to attribute.

    Returns:
        Attribute value or None if not found.
    """
    parts = path.split(".")
    current: Any = obj

    for part in parts:
        if current is None:
            return None

        # Try object attribute first
        if hasattr(current, part):
            current = getattr(current, part)
        # Then try dictionary access
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

    return current
