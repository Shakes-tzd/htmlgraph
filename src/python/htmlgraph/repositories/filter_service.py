"""
FilterService - Unified interface for all filtering operations.

Consolidates 39+ filter duplications across CLI, SDK, and Collections.
Single source of truth for all filter logic.

Provides:
- Atomic filter creation and composition
- Standard filters (status, priority, assigned_to, dates)
- Custom predicates and complex queries
- Filter compilation for performance
- Boolean combinations (AND, OR, NOT)

All implementations MUST pass FilterServiceComplianceTests.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class FilterOperator(Enum):
    """Standard filter operators."""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


class FilterLogic(Enum):
    """Combination logic for multiple filters."""

    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class Filter:
    """
    Atomic filter with field, operator, and value.

    Supports:
    - Single field filtering (status == 'todo')
    - Range filtering (priority >= 'high')
    - List membership (assigned_to in ['alice', 'bob'])
    - Custom predicates (lambda f: len(f.title) > 10)
    """

    field: str  # Attribute name or None for custom
    operator: FilterOperator | str  # Filter operator
    value: Any  # Value to filter by
    predicate: Callable[[Any], bool] | None = None  # Custom predicate function
    logic: FilterLogic | None = None  # Combination logic (for compound filters)
    sub_filters: list["Filter"] | None = None  # For compound filters

    def __call__(self, item: Any) -> bool:
        """Apply filter to item. Allows: filter(item) syntax."""
        raise NotImplementedError("Use compiled filter or apply() method")

    @property
    def is_custom(self) -> bool:
        """True if this is a custom predicate filter."""
        return self.predicate is not None

    @property
    def is_compound(self) -> bool:
        """True if this combines multiple filters."""
        return self.logic is not None and self.sub_filters is not None


class FilterServiceError(Exception):
    """Base exception for filter operations."""

    pass


class InvalidFilterError(FilterServiceError):
    """Raised when filter configuration is invalid."""

    pass


class FilterService(ABC):
    """
    Unified interface for all filtering operations.

    Consolidates duplicated filter logic from:
    - CLI commands (filter by status, priority, etc.)
    - SDK collections (multiple filtering methods)
    - Work item queries
    - Analytics recommendations

    CONTRACT:
    1. **Correctness**: Filters return exactly matching items
    2. **Consistency**: Same filter always returns same results
    3. **Completeness**: All standard filters supported
    4. **Composability**: Filters can be combined safely
    5. **Performance**: Filters compiled once, applied efficiently

    FILTER TYPES:
    1. **Atomic**: Single field filter (status == 'todo')
    2. **Standard**: Pre-built common filters (status_is, priority_gte, etc.)
    3. **Custom**: User-provided predicates (lambda f: f.title.startswith('API'))
    4. **Compound**: Multiple filters combined (AND, OR, NOT)

    PERFORMANCE:
    - create_filter(): O(1) validation
    - compile(): O(1) filter->callable conversion
    - apply(): O(n) where n = items
    - apply() with compiled filter: O(n*k) where k = filter complexity
    - apply() with index: O(log n) if available

    THREAD SAFETY:
    - Filters are immutable after creation
    - Safe to share compiled filters across threads
    - apply() thread-safe on separate item lists
    """

    # ===== ATOMIC FILTER CREATION =====

    @abstractmethod
    def create_filter(
        self, field: str, operator: FilterOperator | str, value: Any
    ) -> Filter:
        """
        Create atomic filter for single field.

        Args:
            field: Attribute name to filter by
            operator: FilterOperator or string operator ("==", "!=", ">", etc.)
            value: Value to compare against

        Returns:
            Filter object ready to apply or combine

        Raises:
            InvalidFilterError: If operator or field invalid

        Performance: O(1)

        Examples:
            >>> filter1 = service.create_filter("status", "==", "todo")
            >>> filter2 = service.create_filter("priority", ">=", "high")
            >>> filter3 = service.create_filter("assigned_to", "in", ["alice", "bob"])
        """
        ...

    @abstractmethod
    def custom(self, predicate: Callable[[Any], bool]) -> Filter:
        """
        Create custom filter with arbitrary predicate.

        For filtering not covered by standard filters.

        Args:
            predicate: Function taking item, returning True if matches

        Returns:
            Custom Filter object

        Examples:
            >>> by_length = service.custom(lambda f: len(f.title) > 10)
            >>> by_date = service.custom(lambda f: (datetime.now() - f.created).days < 7)
            >>> by_keyword = service.custom(lambda f: "auth" in f.title.lower())
        """
        ...

    # ===== STANDARD FILTERS (COMMON PATTERNS) =====

    @abstractmethod
    def status_is(self, status: str) -> Filter:
        """
        Filter by exact status match.

        Args:
            status: Status value ('todo', 'in-progress', 'done', etc.)

        Returns:
            Filter matching items with exact status

        Examples:
            >>> repo.apply(items, service.status_is("todo"))
        """
        ...

    @abstractmethod
    def priority_gte(self, priority: str) -> Filter:
        """
        Filter by priority >= threshold.

        Args:
            priority: Minimum priority ('low', 'medium', 'high', 'critical')

        Returns:
            Filter matching items with priority >= threshold

        Examples:
            >>> high_priority = service.priority_gte("high")
            >>> items = repo.apply(all_items, high_priority)
        """
        ...

    @abstractmethod
    def priority_lte(self, priority: str) -> Filter:
        """
        Filter by priority <= threshold.

        Args:
            priority: Maximum priority ('low', 'medium', 'high', 'critical')

        Returns:
            Filter matching items with priority <= threshold
        """
        ...

    @abstractmethod
    def assigned_to(self, agent: str) -> Filter:
        """
        Filter by assignment to specific agent.

        Args:
            agent: Agent ID (e.g., 'claude', 'gpt4')

        Returns:
            Filter matching items assigned to agent

        Examples:
            >>> my_work = service.assigned_to("claude")
        """
        ...

    @abstractmethod
    def created_after(self, date: datetime) -> Filter:
        """
        Filter by creation date after threshold.

        Args:
            date: Cutoff datetime

        Returns:
            Filter matching items created > date

        Examples:
            >>> this_week = service.created_after(datetime.now() - timedelta(days=7))
        """
        ...

    @abstractmethod
    def created_before(self, date: datetime) -> Filter:
        """
        Filter by creation date before threshold.

        Args:
            date: Cutoff datetime

        Returns:
            Filter matching items created < date
        """
        ...

    @abstractmethod
    def updated_after(self, date: datetime) -> Filter:
        """
        Filter by last update after threshold.

        Args:
            date: Cutoff datetime

        Returns:
            Filter matching items updated > date
        """
        ...

    @abstractmethod
    def updated_before(self, date: datetime) -> Filter:
        """
        Filter by last update before threshold.

        Args:
            date: Cutoff datetime

        Returns:
            Filter matching items updated < date
        """
        ...

    @abstractmethod
    def any_of(self, field: str, values: list[Any]) -> Filter:
        """
        Filter where field value is in set (IN operator).

        Args:
            field: Attribute to check
            values: List of acceptable values

        Returns:
            Filter matching items where field in values

        Examples:
            >>> statuses = service.any_of("status", ["todo", "in-progress"])
            >>> teams = service.any_of("assigned_to", ["team-a", "team-b"])
        """
        ...

    @abstractmethod
    def none_of(self, field: str, values: list[Any]) -> Filter:
        """
        Filter where field value is NOT in set (NOT IN operator).

        Args:
            field: Attribute to check
            values: List of excluded values

        Returns:
            Filter matching items where field not in values

        Examples:
            >>> exclude_done = service.none_of("status", ["done"])
        """
        ...

    @abstractmethod
    def text_contains(self, field: str, text: str) -> Filter:
        """
        Filter where text field contains substring.

        Args:
            field: Attribute to check
            text: Substring to search for

        Returns:
            Filter matching items where field contains text

        Examples:
            >>> auth_related = service.text_contains("title", "auth")
        """
        ...

    @abstractmethod
    def text_starts_with(self, field: str, prefix: str) -> Filter:
        """
        Filter where text field starts with prefix.

        Args:
            field: Attribute to check
            prefix: Required prefix

        Returns:
            Filter matching items where field starts with prefix
        """
        ...

    @abstractmethod
    def range(
        self, field: str, min_value: Any | None = None, max_value: Any | None = None
    ) -> Filter:
        """
        Filter where numeric field is in range.

        Args:
            field: Numeric attribute to check
            min_value: Minimum value (inclusive, None = no minimum)
            max_value: Maximum value (inclusive, None = no maximum)

        Returns:
            Filter matching items in range

        Examples:
            >>> high_impact = service.range("impact_score", min_value=0.8)
            >>> this_quarter = service.range("priority_score", min_value=0.5, max_value=1.0)
        """
        ...

    # ===== FILTER COMPOSITION =====

    @abstractmethod
    def combine(
        self, filters: list[Filter], logic: FilterLogic | str = FilterLogic.AND
    ) -> Filter:
        """
        Combine multiple filters with boolean logic.

        Args:
            filters: List of Filter objects to combine
            logic: Combination logic ('and', 'or', 'not')

        Returns:
            Compound Filter that applies all filters

        Raises:
            InvalidFilterError: If incompatible filters

        Examples:
            >>> status_todo = service.status_is("todo")
            >>> high_priority = service.priority_gte("high")
            >>> combined = service.combine([status_todo, high_priority])
            >>> important_work = repo.apply(items, combined)

            >>> recent = service.created_after(datetime.now() - timedelta(days=7))
            >>> exclude_done = service.none_of("status", ["done"])
            >>> recent_active = service.combine([recent, exclude_done])
        """
        ...

    @abstractmethod
    def all_of(self, *filters: Filter) -> Filter:
        """
        Shorthand for combine(filters, AND).

        Filters must ALL match for item to pass.

        Examples:
            >>> f1 = service.status_is("todo")
            >>> f2 = service.priority_gte("high")
            >>> f3 = service.assigned_to("claude")
            >>> result = service.all_of(f1, f2, f3)
        """
        ...

    @abstractmethod
    def any(self, *filters: Filter) -> Filter:
        """
        Shorthand for combine(filters, OR).

        If ANY filter matches, item passes.

        Examples:
            >>> f1 = service.status_is("done")
            >>> f2 = service.assigned_to("alice")
            >>> result = service.any(f1, f2)  # Done items OR Alice's items
        """
        ...

    @abstractmethod
    def not_filter(self, filter: Filter) -> Filter:
        """
        Negate a filter (logical NOT).

        Args:
            filter: Filter to negate

        Returns:
            Filter that matches items NOT matching input filter

        Examples:
            >>> not_done = service.not_filter(service.status_is("done"))
            >>> not_critical = service.not_filter(service.priority_gte("critical"))
        """
        ...

    # ===== FILTER VALIDATION & COMPILATION =====

    @abstractmethod
    def validate(self, filter: Filter) -> bool:
        """
        Validate filter is well-formed and applicable.

        Checks:
        - Valid operators
        - Valid field names (if known)
        - Compatible value types

        Args:
            filter: Filter to validate

        Returns:
            True if valid, False if invalid

        Examples:
            >>> f = service.create_filter("status", "==", "todo")
            >>> assert service.validate(f)
        """
        ...

    @abstractmethod
    def compile(self, filter: Filter) -> Callable[[Any], bool]:
        """
        Pre-compile filter to fast callable.

        Optimization: convert filter to native Python function
        for faster application. Can cache result.

        Args:
            filter: Filter to compile

        Returns:
            Callable that takes item and returns True/False

        Raises:
            InvalidFilterError: If filter invalid

        Performance: O(1) compilation, O(1) per application

        Examples:
            >>> f = service.create_filter("status", "==", "todo")
            >>> compiled = service.compile(f)
            >>> matching = [item for item in items if compiled(item)]
        """
        ...

    # ===== FILTER APPLICATION =====

    @abstractmethod
    def apply(
        self, items: list[Any], filter: Filter, limit: int | None = None
    ) -> list[Any]:
        """
        Apply filter to item list.

        Args:
            items: List of items to filter
            filter: Filter to apply
            limit: Max results to return (None = all)

        Returns:
            List of items matching filter

        Performance: O(n) worst case, O(k) best case with early termination

        Examples:
            >>> todo_items = service.apply(all_items, service.status_is("todo"))
            >>> top_10 = service.apply(all_items, service.priority_gte("high"), limit=10)
        """
        ...

    @abstractmethod
    def apply_compiled(
        self,
        items: list[Any],
        compiled_filter: Callable[[Any], bool],
        limit: int | None = None,
    ) -> list[Any]:
        """
        Apply pre-compiled filter to items.

        More efficient than apply() when using same filter multiple times.

        Args:
            items: List of items to filter
            compiled_filter: Pre-compiled filter from compile()
            limit: Max results (None = all)

        Returns:
            List of matching items

        Performance: O(n) with minimal overhead

        Examples:
            >>> compiled = service.compile(service.status_is("todo"))
            >>> batch1 = service.apply_compiled(items1, compiled)
            >>> batch2 = service.apply_compiled(items2, compiled)
        """
        ...

    @abstractmethod
    def filter_count(self, items: list[Any], filter: Filter) -> int:
        """
        Count items matching filter without materializing list.

        Args:
            items: List of items to count
            filter: Filter to apply

        Returns:
            Number of matching items

        Performance: O(n) but avoids list allocation

        Examples:
            >>> todo_count = service.filter_count(items, service.status_is("todo"))
        """
        ...

    # ===== UTILITY METHODS =====

    @abstractmethod
    def describe(self, filter: Filter) -> str:
        """
        Get human-readable description of filter.

        Useful for logging, UI display, debugging.

        Args:
            filter: Filter to describe

        Returns:
            Human-readable string

        Examples:
            >>> f = service.create_filter("status", "==", "todo")
            >>> print(service.describe(f))  # "status is 'todo'"
        """
        ...

    @abstractmethod
    def get_standard_filters(self) -> dict[str, Callable]:
        """
        Get all available standard filters.

        Returns:
            Dict of filter_name -> filter_factory_method

        Examples:
            >>> filters = service.get_standard_filters()
            >>> for name in filters.keys():
            ...     print(f"Available: {name}")
        """
        ...
