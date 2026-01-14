from __future__ import annotations

"""
Fluent Query Builder for HtmlGraph.

Provides a chainable API for building complex queries that go beyond
CSS selector capabilities. Supports logical operators, numeric comparisons,
text search, and nested attribute access.

Example:
    from htmlgraph import HtmlGraph

    graph = HtmlGraph("features/")

    # Find high-priority blocked features
    results = graph.query_builder() \\
        .where("status", "blocked") \\
        .and_("priority").in_(["high", "critical"]) \\
        .and_("completion").lt(50) \\
        .execute()

    # Find features with "auth" in title
    results = graph.query_builder() \\
        .where("title").contains("auth") \\
        .or_("title").contains("login") \\
        .execute()
"""


import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node


class Operator(Enum):
    """Query operators for comparisons."""

    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NOT_IN = "not_in"  # Not in list
    BETWEEN = "between"  # Between two values (inclusive)
    CONTAINS = "contains"  # String contains
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # Regex match
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class LogicalOp(Enum):
    """Logical operators for combining conditions."""

    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class Condition:
    """A single query condition."""

    attribute: str
    operator: Operator
    value: Any = None
    logical_op: LogicalOp = LogicalOp.AND

    def evaluate(self, node: Node) -> bool:
        """Evaluate this condition against a node."""
        # Get attribute value with nested access support
        actual = _get_nested_attr(node, self.attribute)

        # Handle null checks first
        if self.operator == Operator.IS_NULL:
            return actual is None
        if self.operator == Operator.IS_NOT_NULL:
            return actual is not None

        # If actual is None and we're doing a comparison, it fails
        if actual is None:
            return False

        # Evaluate based on operator
        if self.operator == Operator.EQ:
            result: bool = actual == self.value
            return result
        elif self.operator == Operator.NE:
            result2: bool = actual != self.value
            return result2
        elif self.operator == Operator.GT:
            return _compare_numeric(actual, self.value, lambda a, b: a > b)
        elif self.operator == Operator.GTE:
            return _compare_numeric(actual, self.value, lambda a, b: a >= b)
        elif self.operator == Operator.LT:
            return _compare_numeric(actual, self.value, lambda a, b: a < b)
        elif self.operator == Operator.LTE:
            return _compare_numeric(actual, self.value, lambda a, b: a <= b)
        elif self.operator == Operator.IN:
            return actual in self.value
        elif self.operator == Operator.NOT_IN:
            return actual not in self.value
        elif self.operator == Operator.BETWEEN:
            low, high = self.value
            return _compare_numeric(
                actual, low, lambda a, b: a >= b
            ) and _compare_numeric(actual, high, lambda a, b: a <= b)
        elif self.operator == Operator.CONTAINS:
            return self.value.lower() in str(actual).lower()
        elif self.operator == Operator.STARTS_WITH:
            return str(actual).lower().startswith(self.value.lower())
        elif self.operator == Operator.ENDS_WITH:
            return str(actual).lower().endswith(self.value.lower())
        elif self.operator == Operator.MATCHES:
            pattern = (
                self.value
                if isinstance(self.value, re.Pattern)
                else re.compile(self.value)
            )
            return bool(pattern.search(str(actual)))

        return False


def _get_nested_attr(obj: Any, path: str) -> Any:
    """
    Get a nested attribute using dot notation.

    Supports:
    - Direct attributes: "status", "priority"
    - Nested attributes: "properties.effort", "properties.metadata.count"
    - Dictionary access: properties["key"]

    Args:
        obj: Object to get attribute from
        path: Dot-separated path to attribute

    Returns:
        Attribute value or None if not found
    """
    parts = path.split(".")
    current = obj

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


def _compare_numeric(actual: Any, expected: Any, comparator: Callable) -> bool:
    """
    Compare values numerically, handling type conversion.

    Args:
        actual: Actual value from node
        expected: Expected value to compare against
        comparator: Comparison function (e.g., lambda a, b: a > b)

    Returns:
        True if comparison succeeds
    """
    try:
        # Convert to float for numeric comparison
        actual_num = float(actual) if not isinstance(actual, (int, float)) else actual
        expected_num = (
            float(expected) if not isinstance(expected, (int, float)) else expected
        )
        result: bool = comparator(actual_num, expected_num)
        return result
    except (ValueError, TypeError):
        # Fall back to string comparison
        result2: bool = comparator(str(actual), str(expected))
        return result2


@dataclass
class ConditionBuilder:
    """
    Builder for a single condition with fluent interface.

    Used when you need to specify an operator after the attribute.

    Example:
        query.where("priority").in_(["high", "critical"])
        query.where("completion").gt(50)
    """

    _query_builder: QueryBuilder
    _attribute: str
    _logical_op: LogicalOp = LogicalOp.AND

    def eq(self, value: Any) -> QueryBuilder:
        """Equal to value."""
        return self._add_condition(Operator.EQ, value)

    def ne(self, value: Any) -> QueryBuilder:
        """Not equal to value."""
        return self._add_condition(Operator.NE, value)

    def gt(self, value: Any) -> QueryBuilder:
        """Greater than value."""
        return self._add_condition(Operator.GT, value)

    def gte(self, value: Any) -> QueryBuilder:
        """Greater than or equal to value."""
        return self._add_condition(Operator.GTE, value)

    def lt(self, value: Any) -> QueryBuilder:
        """Less than value."""
        return self._add_condition(Operator.LT, value)

    def lte(self, value: Any) -> QueryBuilder:
        """Less than or equal to value."""
        return self._add_condition(Operator.LTE, value)

    def in_(self, values: list) -> QueryBuilder:
        """Value is in list."""
        return self._add_condition(Operator.IN, values)

    def not_in(self, values: list) -> QueryBuilder:
        """Value is not in list."""
        return self._add_condition(Operator.NOT_IN, values)

    def between(self, low: Any, high: Any) -> QueryBuilder:
        """Value is between low and high (inclusive)."""
        return self._add_condition(Operator.BETWEEN, (low, high))

    def contains(self, substring: str) -> QueryBuilder:
        """String contains substring (case-insensitive)."""
        return self._add_condition(Operator.CONTAINS, substring)

    def starts_with(self, prefix: str) -> QueryBuilder:
        """String starts with prefix (case-insensitive)."""
        return self._add_condition(Operator.STARTS_WITH, prefix)

    def ends_with(self, suffix: str) -> QueryBuilder:
        """String ends with suffix (case-insensitive)."""
        return self._add_condition(Operator.ENDS_WITH, suffix)

    def matches(self, pattern: str | re.Pattern) -> QueryBuilder:
        """String matches regex pattern."""
        return self._add_condition(Operator.MATCHES, pattern)

    def is_null(self) -> QueryBuilder:
        """Attribute is None/null."""
        return self._add_condition(Operator.IS_NULL, None)

    def is_not_null(self) -> QueryBuilder:
        """Attribute is not None/null."""
        return self._add_condition(Operator.IS_NOT_NULL, None)

    def _add_condition(self, operator: Operator, value: Any) -> QueryBuilder:
        """Add condition and return query builder for chaining."""
        condition = Condition(
            attribute=self._attribute,
            operator=operator,
            value=value,
            logical_op=self._logical_op,
        )
        self._query_builder._conditions.append(condition)
        return self._query_builder


@dataclass
class QueryBuilder:
    """
    Fluent query builder for HtmlGraph.

    Provides a chainable API for building complex queries with:
    - Logical operators (and, or, not)
    - Comparison operators (eq, gt, lt, between)
    - Text search (contains, matches)
    - Nested attribute access

    Example:
        results = graph.query_builder() \\
            .where("status", "blocked") \\
            .and_("priority").in_(["high", "critical"]) \\
            .and_("properties.effort").lt(8) \\
            .execute()
    """

    _graph: HtmlGraph
    _conditions: list[Condition] = field(default_factory=list)
    _type_filter: str | None = None
    _limit: int | None = None
    _offset: int = 0

    def where(
        self, attribute: str, value: Any = None
    ) -> QueryBuilder | ConditionBuilder:
        """
        Start a query condition.

        Can be called in two ways:
        1. where("status", "blocked") - direct equality check
        2. where("priority").in_(["high", "critical"]) - fluent operator

        Args:
            attribute: Attribute to filter on (supports dot notation)
            value: Optional value for equality check

        Returns:
            QueryBuilder if value provided, ConditionBuilder for fluent operators
        """
        if value is not None:
            # Direct equality check
            condition = Condition(
                attribute=attribute,
                operator=Operator.EQ,
                value=value,
                logical_op=LogicalOp.AND,
            )
            self._conditions.append(condition)
            return self
        else:
            # Return condition builder for fluent operator
            return ConditionBuilder(
                _query_builder=self, _attribute=attribute, _logical_op=LogicalOp.AND
            )

    def and_(
        self, attribute: str, value: Any = None
    ) -> QueryBuilder | ConditionBuilder:
        """
        Add an AND condition.

        Args:
            attribute: Attribute to filter on
            value: Optional value for equality check

        Returns:
            QueryBuilder if value provided, ConditionBuilder for fluent operators
        """
        if value is not None:
            condition = Condition(
                attribute=attribute,
                operator=Operator.EQ,
                value=value,
                logical_op=LogicalOp.AND,
            )
            self._conditions.append(condition)
            return self
        else:
            return ConditionBuilder(
                _query_builder=self, _attribute=attribute, _logical_op=LogicalOp.AND
            )

    def or_(self, attribute: str, value: Any = None) -> QueryBuilder | ConditionBuilder:
        """
        Add an OR condition.

        Args:
            attribute: Attribute to filter on
            value: Optional value for equality check

        Returns:
            QueryBuilder if value provided, ConditionBuilder for fluent operators
        """
        if value is not None:
            condition = Condition(
                attribute=attribute,
                operator=Operator.EQ,
                value=value,
                logical_op=LogicalOp.OR,
            )
            self._conditions.append(condition)
            return self
        else:
            return ConditionBuilder(
                _query_builder=self, _attribute=attribute, _logical_op=LogicalOp.OR
            )

    def not_(self, attribute: str) -> ConditionBuilder:
        """
        Add a NOT condition.

        Example:
            query.not_("status").eq("done")  # status != done

        Args:
            attribute: Attribute to negate condition on

        Returns:
            ConditionBuilder for specifying the condition
        """
        return ConditionBuilder(
            _query_builder=self, _attribute=attribute, _logical_op=LogicalOp.NOT
        )

    def of_type(self, node_type: str) -> QueryBuilder:
        """
        Filter by node type.

        Args:
            node_type: Node type to filter by (e.g., "feature", "task")

        Returns:
            Self for chaining
        """
        self._type_filter = node_type
        return self

    def limit(self, count: int) -> QueryBuilder:
        """
        Limit number of results.

        Args:
            count: Maximum number of results

        Returns:
            Self for chaining
        """
        self._limit = count
        return self

    def offset(self, skip: int) -> QueryBuilder:
        """
        Skip first N results.

        Args:
            skip: Number of results to skip

        Returns:
            Self for chaining
        """
        self._offset = skip
        return self

    def execute(self) -> list[Node]:
        """
        Execute the query and return matching nodes.

        Returns:
            List of nodes matching all conditions
        """
        results = []

        for node in self._graph:
            # Type filter
            if self._type_filter and node.type != self._type_filter:
                continue

            # Evaluate conditions
            if self._evaluate_conditions(node):
                results.append(node)

        # Apply offset and limit
        if self._offset:
            results = results[self._offset :]
        if self._limit:
            results = results[: self._limit]

        return results

    def first(self) -> Node | None:
        """
        Execute query and return first matching node.

        Returns:
            First matching node or None
        """
        self._limit = 1
        results = self.execute()
        return results[0] if results else None

    def count(self) -> int:
        """
        Execute query and return count of matching nodes.

        Returns:
            Number of matching nodes
        """
        # Temporarily remove limit for count
        old_limit = self._limit
        self._limit = None
        results = self.execute()
        self._limit = old_limit
        return len(results)

    def exists(self) -> bool:
        """
        Check if any nodes match the query.

        Returns:
            True if at least one node matches
        """
        return self.first() is not None

    def _evaluate_conditions(self, node: Node) -> bool:
        """
        Evaluate all conditions against a node.

        Uses short-circuit evaluation:
        - AND: fails fast on first false
        - OR: succeeds fast on first true

        Args:
            node: Node to evaluate

        Returns:
            True if node matches all conditions
        """
        if not self._conditions:
            return True

        # Process conditions with their logical operators
        result = None

        for condition in self._conditions:
            condition_result = condition.evaluate(node)

            # Handle NOT operator
            if condition.logical_op == LogicalOp.NOT:
                condition_result = not condition_result

            if result is None:
                # First condition
                result = condition_result
            elif condition.logical_op == LogicalOp.AND:
                result = result and condition_result
            elif condition.logical_op == LogicalOp.OR:
                result = result or condition_result
            elif condition.logical_op == LogicalOp.NOT:
                # NOT with previous result (AND NOT)
                result = result and condition_result

        return result if result is not None else True

    def __iter__(self) -> Iterator[Node]:
        """
        Iterate over query results.

        Enables using QueryBuilder directly in for loops without calling execute().
        This provides a more Pythonic interface similar to Django ORM or SQLAlchemy.

        Yields:
            Node: Each node matching the query

        Example:
            >>> # Instead of: for node in graph.query_builder().execute()
            >>> # You can do:
            >>> query = graph.query_builder().where("status", "todo").and_("priority", "high")
            >>> for node in query:
            ...     print(f"{node.id}: {node.title}")
            feat-001: User Authentication
            feat-002: Database Migration

            >>> # Works with comprehensions
            >>> titles = [n.title for n in query]
            >>>
            >>> # Works with any iterable operation
            >>> first = next(iter(query), None)
        """
        return iter(self.execute())

    def to_predicate(self) -> Callable[[Node], bool]:
        """
        Convert query to a predicate function.

        Useful for combining with other filtering methods.

        Returns:
            Function that takes a Node and returns bool
        """

        def predicate(node: Node) -> bool:
            if self._type_filter and node.type != self._type_filter:
                return False
            return self._evaluate_conditions(node)

        return predicate
