from __future__ import annotations

"""
BeautifulSoup-style Find API for HtmlGraph.

Provides familiar find() and find_all() methods with keyword-based filtering.
This is a simpler alternative to QueryBuilder for common queries.

Example:
    from htmlgraph import HtmlGraph

    graph = HtmlGraph("features/")

    # Find first blocked feature
    node = graph.find(type="feature", status="blocked")

    # Find all high-priority items
    nodes = graph.find_all(priority="high")

    # Find with text search
    nodes = graph.find_all(title__contains="auth")

    # Find with numeric comparison
    nodes = graph.find_all(properties__effort__gt=8)
"""


import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node


class FindAPI:
    r"""
    BeautifulSoup-style find interface for HtmlGraph.

    Provides find() and find_all() methods with keyword argument filtering.
    Supports various lookup types using double-underscore suffixes.

    Lookup Types:
        - exact match: status="blocked"
        - contains: title__contains="auth"
        - startswith: id__startswith="feat-"
        - endswith: title__endswith="API"
        - regex: title__regex=r"User\s+"
        - gt, gte, lt, lte: effort__gt=8
        - in: priority__in=["high", "critical"]
        - isnull: agent__isnull=True

    Example:
        # Find first blocked feature
        node = graph.find(type="feature", status="blocked")

        # Find all with title containing "auth"
        nodes = graph.find_all(title__contains="auth")
    """

    def __init__(self, graph: HtmlGraph):
        self._graph = graph

    def find(self, type: str | None = None, **kwargs: Any) -> Node | None:
        """
        Find the first node matching the given criteria.

        Args:
            type: Node type filter (shorthand for type=...)
            **kwargs: Attribute filters with optional lookup suffixes

        Returns:
            First matching Node or None

        Example:
            node = graph.find(type="feature", status="blocked")
            node = graph.find(title__contains="auth")
            node = graph.find(properties__effort__gt=8)
        """
        if type is not None:
            kwargs["type"] = type

        for node in self._graph:
            if self._matches(node, kwargs):
                return node
        return None

    def find_all(
        self, type: str | None = None, limit: int | None = None, **kwargs: Any
    ) -> list[Node]:
        """
        Find all nodes matching the given criteria.

        Args:
            type: Node type filter
            limit: Maximum number of results
            **kwargs: Attribute filters with optional lookup suffixes

        Returns:
            List of matching Nodes

        Example:
            nodes = graph.find_all(type="feature", priority="high")
            nodes = graph.find_all(status__in=["todo", "blocked"], limit=10)
        """
        if type is not None:
            kwargs["type"] = type

        results = []
        for node in self._graph:
            if self._matches(node, kwargs):
                results.append(node)
                if limit and len(results) >= limit:
                    break
        return results

    def find_by_id(self, node_id: str) -> Node | None:
        """
        Find node by exact ID.

        Args:
            node_id: Node ID to find

        Returns:
            Node or None
        """
        return self._graph.get(node_id)

    def find_by_title(self, title: str, exact: bool = False) -> list[Node]:
        """
        Find nodes by title.

        Args:
            title: Title to search for
            exact: If True, match exactly. If False, case-insensitive contains.

        Returns:
            List of matching nodes
        """
        if exact:
            return self.find_all(title=title)
        else:
            return self.find_all(title__icontains=title)

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
        neighbor_ids = self._graph.get_neighbors(node_id, relationship, direction)
        nodes = [self._graph.get(nid) for nid in neighbor_ids]
        return [n for n in nodes if n is not None]

    def find_blocking(self, node_id: str) -> list[Node]:
        """
        Find nodes that are blocking the given node.

        Args:
            node_id: Node ID to find blockers for

        Returns:
            List of blocking nodes
        """
        return self.find_related(
            node_id, relationship="blocked_by", direction="outgoing"
        )

    def find_blocked_by(self, node_id: str) -> list[Node]:
        """
        Find nodes that are blocked by the given node.

        Args:
            node_id: Node ID

        Returns:
            List of nodes blocked by this node
        """
        # Nodes that have blocked_by pointing to this node
        incoming = self._graph.get_incoming_edges(node_id, "blocked_by")
        nodes = [self._graph.get(ref.source_id) for ref in incoming]
        return [n for n in nodes if n is not None]

    def _matches(self, node: Node, filters: dict[str, Any]) -> bool:
        """
        Check if a node matches all filters.

        Args:
            node: Node to check
            filters: Dict of attribute__lookup=value filters

        Returns:
            True if all filters match
        """
        for key, expected in filters.items():
            if not self._check_filter(node, key, expected):
                return False
        return True

    def _check_filter(self, node: Node, key: str, expected: Any) -> bool:
        """
        Check a single filter against a node.

        Args:
            node: Node to check
            key: Filter key (may include lookup suffix)
            expected: Expected value

        Returns:
            True if filter matches
        """
        # Parse lookup type from key
        # Check if the last part is a lookup keyword
        parts = key.split("__")

        if len(parts) == 1:
            # Simple attribute
            attr_path = parts[0]
            lookup = "exact"
        elif parts[-1] in self._lookups:
            # Last part is a lookup
            attr_path = "__".join(parts[:-1])
            lookup = parts[-1]
        else:
            # All parts are attribute path, use exact match
            attr_path = key
            lookup = "exact"

        # Get actual value
        actual = self._get_attr(node, attr_path)

        # Apply lookup
        lookup_fn = self._lookups.get(lookup, self._exact)
        result: bool = lookup_fn(actual, expected)
        return result

    def _get_attr(self, node: Node, path: str) -> Any:
        """Get attribute value supporting nested access with double underscore."""
        # Convert double underscore to dot notation for nested access
        path = path.replace("__", ".")
        parts = path.split(".")
        current = node

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

    # Lookup functions
    def _exact(self, actual: Any, expected: Any) -> bool:
        result: bool = actual == expected
        return result

    def _iexact(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return expected is None
        result: bool = str(actual).lower() == str(expected).lower()
        return result

    def _contains(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(expected) in str(actual)

    def _icontains(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(expected).lower() in str(actual).lower()

    def _startswith(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(actual).startswith(str(expected))

    def _istartswith(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(actual).lower().startswith(str(expected).lower())

    def _endswith(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(actual).endswith(str(expected))

    def _iendswith(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        return str(actual).lower().endswith(str(expected).lower())

    def _regex(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        pattern = expected if isinstance(expected, re.Pattern) else re.compile(expected)
        return bool(pattern.search(str(actual)))

    def _iregex(self, actual: Any, expected: Any) -> bool:
        if actual is None:
            return False
        pattern = (
            expected
            if isinstance(expected, re.Pattern)
            else re.compile(expected, re.IGNORECASE)
        )
        return bool(pattern.search(str(actual)))

    def _gt(self, actual: Any, expected: Any) -> bool:
        return self._compare(actual, expected, lambda a, b: a > b)

    def _gte(self, actual: Any, expected: Any) -> bool:
        return self._compare(actual, expected, lambda a, b: a >= b)

    def _lt(self, actual: Any, expected: Any) -> bool:
        return self._compare(actual, expected, lambda a, b: a < b)

    def _lte(self, actual: Any, expected: Any) -> bool:
        return self._compare(actual, expected, lambda a, b: a <= b)

    def _in(self, actual: Any, expected: Any) -> bool:
        return actual in expected

    def _not_in(self, actual: Any, expected: Any) -> bool:
        return actual not in expected

    def _isnull(self, actual: Any, expected: Any) -> bool:
        is_null = actual is None
        return is_null if expected else not is_null

    def _compare(self, actual: Any, expected: Any, op: Callable) -> bool:
        """Compare values numerically."""
        if actual is None:
            return False
        try:
            actual_num = (
                float(actual) if not isinstance(actual, (int, float)) else actual
            )
            expected_num = (
                float(expected) if not isinstance(expected, (int, float)) else expected
            )
            result: bool = op(actual_num, expected_num)
            return result
        except (ValueError, TypeError):
            result2: bool = op(str(actual), str(expected))
            return result2

    @property
    def _lookups(self) -> dict[str, Callable]:
        """Available lookup functions."""
        return {
            "exact": self._exact,
            "iexact": self._iexact,
            "contains": self._contains,
            "icontains": self._icontains,
            "startswith": self._startswith,
            "istartswith": self._istartswith,
            "endswith": self._endswith,
            "iendswith": self._iendswith,
            "regex": self._regex,
            "iregex": self._iregex,
            "gt": self._gt,
            "gte": self._gte,
            "lt": self._lt,
            "lte": self._lte,
            "in": self._in,
            "not_in": self._not_in,
            "isnull": self._isnull,
        }


# Convenience functions for direct import
def find(graph: HtmlGraph, type: str | None = None, **kwargs: Any) -> Node | None:
    """
    Find first node matching criteria.

    Args:
        graph: HtmlGraph instance
        type: Node type filter
        **kwargs: Attribute filters

    Returns:
        First matching Node or None
    """
    return FindAPI(graph).find(type=type, **kwargs)


def find_all(
    graph: HtmlGraph, type: str | None = None, limit: int | None = None, **kwargs: Any
) -> list[Node]:
    """
    Find all nodes matching criteria.

    Args:
        graph: HtmlGraph instance
        type: Node type filter
        limit: Maximum results
        **kwargs: Attribute filters

    Returns:
        List of matching Nodes
    """
    return FindAPI(graph).find_all(type=type, limit=limit, **kwargs)
