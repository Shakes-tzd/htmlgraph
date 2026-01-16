"""
StandardFilterService - Unified filtering with pre-compilation and optimization.

Stateless service providing filter creation, composition, and application.
Thread-safe with compiled filter caching for performance.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from .filter_service import (
    Filter,
    FilterLogic,
    FilterOperator,
    FilterService,
    InvalidFilterError,
)

# Priority mapping for comparison
PRIORITY_MAP = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class StandardFilterService(FilterService):
    """
    Standard implementation of FilterService.

    Features:
    - Stateless operation (thread-safe)
    - Pre-compilation of filters for performance
    - Support for all standard operators
    - Boolean combination (AND/OR/NOT)
    - Custom predicate support

    Performance:
    - create_filter(): O(1)
    - compile(): O(1) with caching
    - apply(): O(n) where n = items
    - apply_compiled(): O(n) with minimal overhead
    """

    def __init__(self) -> None:
        """Initialize filter service."""
        self._compiled_cache: dict[str, Callable[[Any], bool]] = {}

    # ===== ATOMIC FILTER CREATION =====

    def create_filter(
        self, field: str, operator: FilterOperator | str, value: Any
    ) -> Filter:
        """Create atomic filter for single field."""
        # Convert string operator to FilterOperator
        if isinstance(operator, str):
            try:
                operator = FilterOperator(operator)
            except ValueError:
                raise InvalidFilterError(f"Invalid operator: {operator}")

        # Validate operator
        if not isinstance(operator, FilterOperator):
            raise InvalidFilterError("Operator must be FilterOperator or string")

        return Filter(
            field=field,
            operator=operator,
            value=value,
            predicate=None,
            logic=None,
            sub_filters=None,
        )

    def custom(self, predicate: Callable[[Any], bool]) -> Filter:
        """Create custom filter with arbitrary predicate."""
        return Filter(
            field="",
            operator=FilterOperator.EQUALS,
            value=None,
            predicate=predicate,
            logic=None,
            sub_filters=None,
        )

    # ===== STANDARD FILTERS (COMMON PATTERNS) =====

    def status_is(self, status: str) -> Filter:
        """Filter by exact status match."""
        return self.create_filter("status", FilterOperator.EQUALS, status)

    def priority_gte(self, priority: str) -> Filter:
        """Filter by priority >= threshold."""
        priority_value = PRIORITY_MAP.get(priority.lower(), 0)
        return Filter(
            field="priority",
            operator=FilterOperator.GREATER_EQUAL,
            value=priority_value,
            predicate=lambda item: PRIORITY_MAP.get(
                getattr(item, "priority", "low").lower(), 0
            )
            >= priority_value,
        )

    def priority_lte(self, priority: str) -> Filter:
        """Filter by priority <= threshold."""
        priority_value = PRIORITY_MAP.get(priority.lower(), 0)
        return Filter(
            field="priority",
            operator=FilterOperator.LESS_EQUAL,
            value=priority_value,
            predicate=lambda item: PRIORITY_MAP.get(
                getattr(item, "priority", "low").lower(), 0
            )
            <= priority_value,
        )

    def assigned_to(self, agent: str) -> Filter:
        """Filter by assignment to specific agent."""
        return self.create_filter("assigned_to", FilterOperator.EQUALS, agent)

    def created_after(self, date: datetime) -> Filter:
        """Filter by creation date after threshold."""
        return self.create_filter("created_at", FilterOperator.GREATER_THAN, date)

    def created_before(self, date: datetime) -> Filter:
        """Filter by creation date before threshold."""
        return self.create_filter("created_at", FilterOperator.LESS_THAN, date)

    def updated_after(self, date: datetime) -> Filter:
        """Filter by last update after threshold."""
        return self.create_filter("updated_at", FilterOperator.GREATER_THAN, date)

    def updated_before(self, date: datetime) -> Filter:
        """Filter by last update before threshold."""
        return self.create_filter("updated_at", FilterOperator.LESS_THAN, date)

    def any_of(self, field: str, values: list[Any]) -> Filter:
        """Filter where field value is in set (IN operator)."""
        return self.create_filter(field, FilterOperator.IN, values)

    def none_of(self, field: str, values: list[Any]) -> Filter:
        """Filter where field value is NOT in set (NOT IN operator)."""
        return self.create_filter(field, FilterOperator.NOT_IN, values)

    def text_contains(self, field: str, text: str) -> Filter:
        """Filter where text field contains substring."""
        return self.create_filter(field, FilterOperator.CONTAINS, text)

    def text_starts_with(self, field: str, prefix: str) -> Filter:
        """Filter where text field starts with prefix."""
        return self.create_filter(field, FilterOperator.STARTS_WITH, prefix)

    def range(
        self, field: str, min_value: Any | None = None, max_value: Any | None = None
    ) -> Filter:
        """Filter where numeric field is in range."""
        filters = []

        if min_value is not None:
            filters.append(
                self.create_filter(field, FilterOperator.GREATER_EQUAL, min_value)
            )

        if max_value is not None:
            filters.append(
                self.create_filter(field, FilterOperator.LESS_EQUAL, max_value)
            )

        if not filters:
            raise InvalidFilterError("range() requires at least min_value or max_value")

        if len(filters) == 1:
            return filters[0]

        return self.combine(filters, FilterLogic.AND)

    # ===== FILTER COMPOSITION =====

    def combine(
        self, filters: list[Filter], logic: FilterLogic | str = FilterLogic.AND
    ) -> Filter:
        """Combine multiple filters with boolean logic."""
        if not filters:
            raise InvalidFilterError("combine() requires at least one filter")

        # Convert string logic to FilterLogic
        if isinstance(logic, str):
            try:
                logic = FilterLogic(logic.lower())
            except ValueError:
                raise InvalidFilterError(f"Invalid logic: {logic}")

        if len(filters) == 1:
            return filters[0]

        return Filter(
            field="",
            operator=FilterOperator.EQUALS,
            value=None,
            predicate=None,
            logic=logic,
            sub_filters=filters,
        )

    def all_of(self, *filters: Filter) -> Filter:
        """Shorthand for combine(filters, AND)."""
        return self.combine(list(filters), FilterLogic.AND)

    def any(self, *filters: Filter) -> Filter:
        """Shorthand for combine(filters, OR)."""
        return self.combine(list(filters), FilterLogic.OR)

    def not_filter(self, filter: Filter) -> Filter:
        """Negate a filter (logical NOT)."""
        return Filter(
            field="",
            operator=FilterOperator.EQUALS,
            value=None,
            predicate=None,
            logic=FilterLogic.NOT,
            sub_filters=[filter],
        )

    # ===== FILTER VALIDATION & COMPILATION =====

    def validate(self, filter: Filter) -> bool:
        """Validate filter is well-formed and applicable."""
        try:
            # Custom predicate filters always valid if predicate exists
            if filter.is_custom:
                return filter.predicate is not None

            # Compound filters
            if filter.is_compound:
                if filter.logic is None or filter.sub_filters is None:
                    return False
                # Recursively validate sub-filters
                return all(self.validate(f) for f in filter.sub_filters)

            # Atomic filters
            if not filter.field:
                return False

            if not isinstance(filter.operator, FilterOperator):
                return False

            return True

        except Exception:
            return False

    def compile(self, filter: Filter) -> Callable[[Any], bool]:
        """Pre-compile filter to fast callable."""
        if not self.validate(filter):
            raise InvalidFilterError("Invalid filter cannot be compiled")

        # Generate cache key
        cache_key = self._filter_cache_key(filter)

        # Check cache
        if cache_key in self._compiled_cache:
            return self._compiled_cache[cache_key]

        # Compile filter
        compiled = self._compile_filter(filter)

        # Cache result
        self._compiled_cache[cache_key] = compiled

        return compiled

    def _filter_cache_key(self, filter: Filter) -> str:
        """Generate cache key for filter."""
        if filter.is_custom:
            return f"custom:{id(filter.predicate)}"

        if (
            filter.is_compound
            and filter.sub_filters is not None
            and filter.logic is not None
        ):
            sub_keys = [self._filter_cache_key(f) for f in filter.sub_filters]
            return f"{filter.logic.value}:({','.join(sub_keys)})"

        op_value = (
            filter.operator.value
            if isinstance(filter.operator, FilterOperator)
            else filter.operator
        )
        return f"{filter.field}:{op_value}:{filter.value}"

    def _compile_filter(self, filter: Filter) -> Callable[[Any], bool]:
        """Internal: compile filter to callable."""
        # Custom predicate
        if filter.is_custom and filter.predicate is not None:
            return filter.predicate

        # Compound filters
        if filter.is_compound and filter.sub_filters is not None:
            compiled_subs = [self.compile(f) for f in filter.sub_filters]

            if filter.logic == FilterLogic.AND:
                return lambda item: all(f(item) for f in compiled_subs)
            elif filter.logic == FilterLogic.OR:
                return lambda item: any(f(item) for f in compiled_subs)
            elif filter.logic == FilterLogic.NOT:
                return lambda item: not compiled_subs[0](item)

        # Atomic filters
        field = filter.field
        operator = filter.operator
        value = filter.value

        def apply_filter(item: Any) -> bool:
            try:
                item_value = getattr(item, field, None)

                if operator == FilterOperator.EQUALS:
                    return bool(item_value == value)
                elif operator == FilterOperator.NOT_EQUALS:
                    return bool(item_value != value)
                elif operator == FilterOperator.GREATER_THAN:
                    return bool(item_value > value)
                elif operator == FilterOperator.GREATER_EQUAL:
                    return bool(item_value >= value)
                elif operator == FilterOperator.LESS_THAN:
                    return bool(item_value < value)
                elif operator == FilterOperator.LESS_EQUAL:
                    return bool(item_value <= value)
                elif operator == FilterOperator.IN:
                    return bool(item_value in value)
                elif operator == FilterOperator.NOT_IN:
                    return bool(item_value not in value)
                elif operator == FilterOperator.CONTAINS:
                    return bool(value in str(item_value))
                elif operator == FilterOperator.STARTS_WITH:
                    return bool(str(item_value).startswith(value))
                elif operator == FilterOperator.ENDS_WITH:
                    return bool(str(item_value).endswith(value))

                return False

            except (AttributeError, TypeError, ValueError):
                return False

        return apply_filter

    # ===== FILTER APPLICATION =====

    def apply(
        self, items: list[Any], filter: Filter, limit: int | None = None
    ) -> list[Any]:
        """Apply filter to item list."""
        compiled = self.compile(filter)
        return self.apply_compiled(items, compiled, limit)

    def apply_compiled(
        self,
        items: list[Any],
        compiled_filter: Callable[[Any], bool],
        limit: int | None = None,
    ) -> list[Any]:
        """Apply pre-compiled filter to items."""
        result = []

        for item in items:
            if compiled_filter(item):
                result.append(item)

                # Early termination if limit reached
                if limit is not None and len(result) >= limit:
                    break

        return result

    def filter_count(self, items: list[Any], filter: Filter) -> int:
        """Count items matching filter without materializing list."""
        compiled = self.compile(filter)
        count = 0

        for item in items:
            if compiled(item):
                count += 1

        return count

    # ===== UTILITY METHODS =====

    def describe(self, filter: Filter) -> str:
        """Get human-readable description of filter."""
        if filter.is_custom:
            return "custom predicate"

        if filter.is_compound and filter.sub_filters is not None:
            sub_descriptions = [self.describe(f) for f in filter.sub_filters]

            if filter.logic == FilterLogic.AND:
                return f"({' AND '.join(sub_descriptions)})"
            elif filter.logic == FilterLogic.OR:
                return f"({' OR '.join(sub_descriptions)})"
            elif filter.logic == FilterLogic.NOT:
                return f"NOT ({sub_descriptions[0]})"

        # Atomic filter
        op_map: dict[FilterOperator, str] = {
            FilterOperator.EQUALS: "is",
            FilterOperator.NOT_EQUALS: "is not",
            FilterOperator.GREATER_THAN: ">",
            FilterOperator.GREATER_EQUAL: ">=",
            FilterOperator.LESS_THAN: "<",
            FilterOperator.LESS_EQUAL: "<=",
            FilterOperator.IN: "in",
            FilterOperator.NOT_IN: "not in",
            FilterOperator.CONTAINS: "contains",
            FilterOperator.STARTS_WITH: "starts with",
            FilterOperator.ENDS_WITH: "ends with",
        }
        op_str = (
            op_map.get(filter.operator, str(filter.operator))
            if isinstance(filter.operator, FilterOperator)
            else str(filter.operator)
        )

        return f"{filter.field} {op_str} '{filter.value}'"

    def get_standard_filters(self) -> dict[str, Callable]:
        """Get all available standard filters."""
        return {
            "status_is": self.status_is,
            "priority_gte": self.priority_gte,
            "priority_lte": self.priority_lte,
            "assigned_to": self.assigned_to,
            "created_after": self.created_after,
            "created_before": self.created_before,
            "updated_after": self.updated_after,
            "updated_before": self.updated_before,
            "any_of": self.any_of,
            "none_of": self.none_of,
            "text_contains": self.text_contains,
            "text_starts_with": self.text_starts_with,
            "range": self.range,
        }
