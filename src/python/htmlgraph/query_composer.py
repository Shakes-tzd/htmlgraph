from __future__ import annotations

"""
Graph Query Composer for HtmlGraph.

Extends QueryBuilder capabilities with graph traversal, enabling queries
that combine attribute filtering WITH edge traversal.

Example:
    from htmlgraph import HtmlGraph

    graph = HtmlGraph("features/")

    # Find blocked features whose blockers are high-priority
    results = graph.query_composer() \\
        .where("status", "blocked") \\
        .traverse("blocked_by", direction="outgoing") \\
        .where("priority", "high") \\
        .execute()

    # Find all features transitively reachable via depends_on from a root
    results = graph.query_composer() \\
        .reachable_from("feat-001", "depends_on") \\
        .where("status", "todo") \\
        .execute()
"""

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from htmlgraph.query_builder import Condition, LogicalOp, Operator

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node


# Sentinel object to distinguish "no value passed" from None
_SENTINEL: Any = object()


@dataclass
class QueryStage:
    """A single stage in the query execution pipeline."""

    stage_type: Literal["filter", "traverse", "traverse_recursive", "reachable_from"]
    params: dict[str, Any] = field(default_factory=dict)


class GraphQueryComposer:
    """
    Composes graph traversal with attribute filtering.

    Wraps QueryBuilder condition logic and EdgeIndex traversal into
    a pipeline of stages. Each stage narrows the working set of nodes.

    Example:
        composer = GraphQueryComposer(graph)
        results = composer \\
            .where("status", "blocked") \\
            .traverse("blocked_by") \\
            .where("priority", "high") \\
            .execute()
    """

    def __init__(self, graph: HtmlGraph) -> None:
        self.graph = graph
        self._stages: list[QueryStage] = []
        # Accumulate filter conditions for the current filter group.
        # When a traverse stage is added, pending conditions are flushed
        # into a filter stage.
        self._pending_conditions: list[Condition] = []

    # ------------------------------------------------------------------
    # Attribute filtering (delegates to QueryBuilder condition logic)
    # ------------------------------------------------------------------

    def where(self, attr: str, value: Any = _SENTINEL) -> GraphQueryComposer:
        """Start or add an attribute filter on the current node set.

        Args:
            attr: Attribute name (supports dot notation for nested access).
            value: If provided, shorthand for equality check.

        Returns:
            Self for chaining.
        """
        if value is not _SENTINEL:
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.EQ,
                    value=value,
                    logical_op=LogicalOp.AND,
                )
            )
        else:
            # When no value is given, add a placeholder condition that must
            # be completed by a subsequent operator call.  For simplicity
            # we store an IS_NOT_NULL condition which acts as a "has attr"
            # check; callers who want other operators should use and_/or_.
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.IS_NOT_NULL,
                    value=None,
                    logical_op=LogicalOp.AND,
                )
            )
        return self

    def and_(self, attr: str, value: Any = _SENTINEL) -> GraphQueryComposer:
        """Add an AND condition.

        Args:
            attr: Attribute name.
            value: If provided, shorthand for equality check.

        Returns:
            Self for chaining.
        """
        if value is not _SENTINEL:
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.EQ,
                    value=value,
                    logical_op=LogicalOp.AND,
                )
            )
        else:
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.IS_NOT_NULL,
                    value=None,
                    logical_op=LogicalOp.AND,
                )
            )
        return self

    def or_(self, attr: str, value: Any = _SENTINEL) -> GraphQueryComposer:
        """Add an OR condition.

        Args:
            attr: Attribute name.
            value: If provided, shorthand for equality check.

        Returns:
            Self for chaining.
        """
        if value is not _SENTINEL:
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.EQ,
                    value=value,
                    logical_op=LogicalOp.OR,
                )
            )
        else:
            self._pending_conditions.append(
                Condition(
                    attribute=attr,
                    operator=Operator.IS_NOT_NULL,
                    value=None,
                    logical_op=LogicalOp.OR,
                )
            )
        return self

    # ------------------------------------------------------------------
    # Relationship traversal
    # ------------------------------------------------------------------

    def traverse(
        self, relationship: str, direction: str = "outgoing"
    ) -> GraphQueryComposer:
        """Follow edges of given relationship type from current result set.

        For each node in the working set, collect the nodes reachable
        by one hop via *relationship* in the specified *direction*.

        Args:
            relationship: Edge relationship type (e.g. ``"blocked_by"``).
            direction: ``"outgoing"``, ``"incoming"``, or ``"both"``.

        Returns:
            Self for chaining.
        """
        self._flush_conditions()
        self._stages.append(
            QueryStage(
                stage_type="traverse",
                params={"relationship": relationship, "direction": direction},
            )
        )
        return self

    def traverse_recursive(
        self,
        relationship: str,
        direction: str = "outgoing",
        max_depth: int = 10,
    ) -> GraphQueryComposer:
        """Follow edges recursively (transitive closure) up to *max_depth*.

        Args:
            relationship: Edge relationship type.
            direction: ``"outgoing"``, ``"incoming"``, or ``"both"``.
            max_depth: Maximum traversal depth.

        Returns:
            Self for chaining.
        """
        self._flush_conditions()
        self._stages.append(
            QueryStage(
                stage_type="traverse_recursive",
                params={
                    "relationship": relationship,
                    "direction": direction,
                    "max_depth": max_depth,
                },
            )
        )
        return self

    def reachable_from(
        self,
        node_id: str,
        relationship: str,
        direction: str = "outgoing",
        max_depth: int = 10,
    ) -> GraphQueryComposer:
        """Filter to nodes reachable from *node_id* via *relationship*.

        This resets the working set to all nodes transitively reachable
        from the given starting node (excluding the starting node itself).

        Args:
            node_id: Starting node ID.
            relationship: Edge relationship type.
            direction: ``"outgoing"``, ``"incoming"``, or ``"both"``.
            max_depth: Maximum traversal depth.

        Returns:
            Self for chaining.
        """
        self._flush_conditions()
        self._stages.append(
            QueryStage(
                stage_type="reachable_from",
                params={
                    "node_id": node_id,
                    "relationship": relationship,
                    "direction": direction,
                    "max_depth": max_depth,
                },
            )
        )
        return self

    # ------------------------------------------------------------------
    # Convenience methods
    # ------------------------------------------------------------------

    def blocked_by_chain(self, feature_id: str) -> GraphQueryComposer:
        """Find all features in the ``blocked_by`` chain from *feature_id*.

        Equivalent to ``reachable_from(feature_id, "blocked_by", "outgoing")``.

        Args:
            feature_id: Starting feature node ID.

        Returns:
            Self for chaining.
        """
        return self.reachable_from(feature_id, "blocked_by", direction="outgoing")

    def dependency_chain(self, feature_id: str) -> GraphQueryComposer:
        """Find all features in the ``depends_on`` chain from *feature_id*.

        Equivalent to ``reachable_from(feature_id, "depends_on", "outgoing")``.

        Args:
            feature_id: Starting feature node ID.

        Returns:
            Self for chaining.
        """
        return self.reachable_from(feature_id, "depends_on", direction="outgoing")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(self) -> list[Node]:
        """Execute all stages and return matching nodes.

        Returns:
            List of nodes matching the composed query.
        """
        # Flush any remaining pending conditions
        self._flush_conditions()

        self.graph._ensure_loaded()  # noqa: SLF001

        # Start with all node IDs
        working_set: set[str] = set(self.graph._nodes.keys())  # noqa: SLF001

        for stage in self._stages:
            if stage.stage_type == "filter":
                working_set = self._apply_filter(working_set, stage)
            elif stage.stage_type == "traverse":
                working_set = self._apply_traverse(working_set, stage)
            elif stage.stage_type == "traverse_recursive":
                working_set = self._apply_traverse_recursive(working_set, stage)
            elif stage.stage_type == "reachable_from":
                working_set = self._apply_reachable_from(working_set, stage)

        # Resolve IDs to Node objects, preserving only nodes that still exist
        nodes = self.graph._nodes  # noqa: SLF001
        return [nodes[nid] for nid in working_set if nid in nodes]

    def count(self) -> int:
        """Execute and return count of matches.

        Returns:
            Number of matching nodes.
        """
        return len(self.execute())

    def first(self) -> Node | None:
        """Execute and return first match or ``None``.

        Returns:
            First matching node or ``None``.
        """
        results = self.execute()
        return results[0] if results else None

    def ids(self) -> list[str]:
        """Execute and return just node IDs.

        Returns:
            List of matching node IDs.
        """
        return [node.id for node in self.execute()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flush_conditions(self) -> None:
        """Flush accumulated conditions into a filter stage."""
        if self._pending_conditions:
            self._stages.append(
                QueryStage(
                    stage_type="filter",
                    params={"conditions": list(self._pending_conditions)},
                )
            )
            self._pending_conditions = []

    def _apply_filter(self, working_set: set[str], stage: QueryStage) -> set[str]:
        """Apply attribute filter conditions to the working set."""
        conditions: list[Condition] = stage.params["conditions"]
        nodes = self.graph._nodes  # noqa: SLF001
        result: set[str] = set()

        for nid in working_set:
            node = nodes.get(nid)
            if node is None:
                continue
            if self._evaluate_conditions(node, conditions):
                result.add(nid)

        return result

    def _apply_traverse(self, working_set: set[str], stage: QueryStage) -> set[str]:
        """Follow one hop of edges from working set."""
        relationship: str = stage.params["relationship"]
        direction: str = stage.params["direction"]
        edge_index = self.graph._edge_index  # noqa: SLF001
        result: set[str] = set()

        for nid in working_set:
            if direction in ("outgoing", "both"):
                for ref in edge_index.get_outgoing(nid, relationship):
                    result.add(ref.target_id)
            if direction in ("incoming", "both"):
                for ref in edge_index.get_incoming(nid, relationship):
                    result.add(ref.source_id)

        return result

    def _apply_traverse_recursive(
        self, working_set: set[str], stage: QueryStage
    ) -> set[str]:
        """Follow edges recursively from working set with depth limit."""
        relationship: str = stage.params["relationship"]
        direction: str = stage.params["direction"]
        max_depth: int = stage.params["max_depth"]
        edge_index = self.graph._edge_index  # noqa: SLF001

        result: set[str] = set()
        # BFS from every node in working set
        queue: deque[tuple[str, int]] = deque()
        for nid in working_set:
            queue.append((nid, 0))

        visited: set[str] = set(working_set)

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue

            neighbors: set[str] = set()
            if direction in ("outgoing", "both"):
                for ref in edge_index.get_outgoing(current, relationship):
                    neighbors.add(ref.target_id)
            if direction in ("incoming", "both"):
                for ref in edge_index.get_incoming(current, relationship):
                    neighbors.add(ref.source_id)

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return result

    def _apply_reachable_from(
        self, working_set: set[str], stage: QueryStage
    ) -> set[str]:
        """Compute nodes reachable from a specific node, intersected with working set."""
        node_id: str = stage.params["node_id"]
        relationship: str = stage.params["relationship"]
        direction: str = stage.params["direction"]
        max_depth: int = stage.params["max_depth"]
        edge_index = self.graph._edge_index  # noqa: SLF001

        reachable: set[str] = set()
        visited: set[str] = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue

            neighbors: set[str] = set()
            if direction in ("outgoing", "both"):
                for ref in edge_index.get_outgoing(current, relationship):
                    neighbors.add(ref.target_id)
            if direction in ("incoming", "both"):
                for ref in edge_index.get_incoming(current, relationship):
                    neighbors.add(ref.source_id)

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    reachable.add(neighbor)
                    queue.append((neighbor, depth + 1))

        # Intersect with the current working set
        return working_set & reachable

    @staticmethod
    def _evaluate_conditions(node: Node, conditions: list[Condition]) -> bool:
        """Evaluate a list of conditions against a node.

        Reuses the ``Condition.evaluate`` method from ``query_builder.py``
        so condition evaluation logic is not duplicated.

        Args:
            node: Node to evaluate.
            conditions: Conditions to check.

        Returns:
            ``True`` if the node satisfies the combined conditions.
        """
        if not conditions:
            return True

        result: bool | None = None

        for condition in conditions:
            condition_result = condition.evaluate(node)

            # Handle NOT operator
            if condition.logical_op == LogicalOp.NOT:
                condition_result = not condition_result

            if result is None:
                result = condition_result
            elif condition.logical_op == LogicalOp.AND:
                result = result and condition_result
            elif condition.logical_op == LogicalOp.OR:
                result = result or condition_result
            elif condition.logical_op == LogicalOp.NOT:
                # NOT combined with previous result (AND NOT)
                result = result and condition_result

        return result if result is not None else True
