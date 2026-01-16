"""
FilterService Compliance Tests

All FilterService implementations MUST pass these 10+ tests.
Tests validate the contract, filter correctness, and composition.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest
from htmlgraph.repositories.filter_service import (
    Filter,
    FilterLogic,
    FilterOperator,
    FilterService,
    FilterServiceError,
    InvalidFilterError,
)


class MockFilterService(FilterService):
    """Mock implementation for testing interface."""

    def __init__(self):
        self._filters = {}
        self._standard_filters = {
            "status_is": self.status_is,
            "priority_gte": self.priority_gte,
            "assigned_to": self.assigned_to,
        }

    def create_filter(self, field: str, operator, value):
        """Mock implementation."""
        return Filter(field=field, operator=operator, value=value)

    def custom(self, predicate):
        """Mock implementation."""
        return Filter(field=None, operator=None, value=None, predicate=predicate)

    def status_is(self, status: str) -> Filter:
        """Mock implementation."""
        return self.create_filter("status", FilterOperator.EQUALS, status)

    def priority_gte(self, priority: str) -> Filter:
        """Mock implementation."""
        return self.create_filter("priority", FilterOperator.GREATER_EQUAL, priority)

    def priority_lte(self, priority: str) -> Filter:
        """Mock implementation."""
        return self.create_filter("priority", FilterOperator.LESS_EQUAL, priority)

    def assigned_to(self, agent: str) -> Filter:
        """Mock implementation."""
        return self.create_filter("assigned_to", FilterOperator.EQUALS, agent)

    def created_after(self, date: datetime) -> Filter:
        """Mock implementation."""
        return self.create_filter("created", FilterOperator.GREATER_THAN, date)

    def created_before(self, date: datetime) -> Filter:
        """Mock implementation."""
        return self.create_filter("created", FilterOperator.LESS_THAN, date)

    def updated_after(self, date: datetime) -> Filter:
        """Mock implementation."""
        return self.create_filter("updated", FilterOperator.GREATER_THAN, date)

    def updated_before(self, date: datetime) -> Filter:
        """Mock implementation."""
        return self.create_filter("updated", FilterOperator.LESS_THAN, date)

    def any_of(self, field: str, values: list) -> Filter:
        """Mock implementation."""
        return self.create_filter(field, FilterOperator.IN, values)

    def none_of(self, field: str, values: list) -> Filter:
        """Mock implementation."""
        return self.create_filter(field, FilterOperator.NOT_IN, values)

    def text_contains(self, field: str, text: str) -> Filter:
        """Mock implementation."""
        return self.create_filter(field, FilterOperator.CONTAINS, text)

    def text_starts_with(self, field: str, prefix: str) -> Filter:
        """Mock implementation."""
        return self.create_filter(field, FilterOperator.STARTS_WITH, prefix)

    def range(self, field: str, min_value=None, max_value=None) -> Filter:
        """Mock implementation."""
        return Filter(
            field=field,
            operator="range",
            value={"min": min_value, "max": max_value},
        )

    def combine(self, filters: list[Filter], logic="and") -> Filter:
        """Mock implementation."""
        return Filter(
            field=None,
            operator=None,
            value=None,
            logic=FilterLogic[logic.upper()] if isinstance(logic, str) else logic,
            sub_filters=filters,
        )

    def all_of(self, *filters: Filter) -> Filter:
        """Mock implementation."""
        return self.combine(list(filters), FilterLogic.AND)

    def any(self, *filters: Filter) -> Filter:
        """Mock implementation."""
        return self.combine(list(filters), FilterLogic.OR)

    def not_filter(self, filter: Filter) -> Filter:
        """Mock implementation."""
        return Filter(
            field=None,
            operator=None,
            value=None,
            logic=FilterLogic.NOT,
            sub_filters=[filter],
        )

    def validate(self, filter: Filter) -> bool:
        """Mock implementation."""
        if filter.field is None and filter.predicate is None:
            return filter.logic is not None  # Compound filter
        return True

    def compile(self, filter: Filter):
        """Mock implementation."""
        if filter.predicate:
            return filter.predicate

        # Handle compound filters
        if filter.logic == FilterLogic.AND:
            sub_compiled = [self.compile(f) for f in filter.sub_filters]
            return lambda item: all(f(item) for f in sub_compiled)
        elif filter.logic == FilterLogic.OR:
            sub_compiled = [self.compile(f) for f in filter.sub_filters]
            return lambda item: any(f(item) for f in sub_compiled)
        elif filter.logic == FilterLogic.NOT:
            sub_compiled = self.compile(filter.sub_filters[0])
            return lambda item: not sub_compiled(item)

        # Simple field == value filter
        if filter.field is None:
            return lambda item: True  # No-op for invalid filters
        return lambda item: getattr(item, filter.field, None) == filter.value

    def apply(self, items: list, filter: Filter, limit=None) -> list:
        """Mock implementation."""
        compiled = self.compile(filter)
        result = [item for item in items if compiled(item)]
        return result[:limit] if limit else result

    def apply_compiled(self, items: list, compiled_filter, limit=None) -> list:
        """Mock implementation."""
        result = [item for item in items if compiled_filter(item)]
        return result[:limit] if limit else result

    def filter_count(self, items: list, filter: Filter) -> int:
        """Mock implementation."""
        return len(self.apply(items, filter))

    def describe(self, filter: Filter) -> str:
        """Mock implementation."""
        if filter.predicate:
            return "<custom filter>"
        return f"{filter.field} {filter.operator} {filter.value}"

    def get_standard_filters(self):
        """Mock implementation."""
        return self._standard_filters


class TestFilterServiceInterface:
    """Test FilterService interface contract."""

    def test_interface_defined(self):
        """FilterService interface exists and is ABC."""
        assert hasattr(FilterService, "create_filter")
        assert hasattr(FilterService, "custom")
        assert hasattr(FilterService, "apply")

    def test_filter_enums_defined(self):
        """FilterOperator and FilterLogic enums exist."""
        assert hasattr(FilterOperator, "EQUALS")
        assert hasattr(FilterOperator, "IN")
        assert hasattr(FilterLogic, "AND")
        assert hasattr(FilterLogic, "OR")

    def test_exception_types(self):
        """Exception types properly inherit."""
        assert issubclass(InvalidFilterError, FilterServiceError)

    def test_filter_dataclass_properties(self):
        """Filter dataclass has expected properties."""
        f = Filter(field="status", operator=FilterOperator.EQUALS, value="todo")
        assert f.field == "status"
        assert f.operator == FilterOperator.EQUALS
        assert f.value == "todo"
        assert f.is_custom is False
        assert f.is_compound is False


class TestAtomicFilterCreation:
    """Test atomic filter creation."""

    def test_create_filter_returns_filter(self):
        """create_filter returns Filter object."""
        service = MockFilterService()
        f = service.create_filter("status", FilterOperator.EQUALS, "todo")
        assert isinstance(f, Filter)

    def test_create_filter_with_string_operator(self):
        """create_filter accepts string operators."""
        service = MockFilterService()
        f = service.create_filter("status", "==", "todo")
        assert isinstance(f, Filter)

    def test_custom_filter_has_predicate(self):
        """custom() creates filter with predicate."""
        service = MockFilterService()

        def pred(x):
            return x.status == "todo"

        f = service.custom(pred)
        assert f.is_custom is True
        assert f.predicate is not None


class TestStandardFilters:
    """Test standard filter methods."""

    def test_status_is_creates_filter(self):
        """status_is creates status filter."""
        service = MockFilterService()
        f = service.status_is("todo")
        assert isinstance(f, Filter)
        assert f.field == "status"
        assert f.value == "todo"

    def test_priority_gte_creates_filter(self):
        """priority_gte creates priority filter."""
        service = MockFilterService()
        f = service.priority_gte("high")
        assert isinstance(f, Filter)
        assert f.field == "priority"

    def test_assigned_to_creates_filter(self):
        """assigned_to creates assignment filter."""
        service = MockFilterService()
        f = service.assigned_to("claude")
        assert isinstance(f, Filter)
        assert f.field == "assigned_to"

    def test_date_filters(self):
        """Date filters create datetime filters."""
        service = MockFilterService()
        now = datetime.now()
        f = service.created_after(now)
        assert isinstance(f, Filter)
        f = service.created_before(now)
        assert isinstance(f, Filter)

    def test_any_of_creates_in_filter(self):
        """any_of creates IN operator filter."""
        service = MockFilterService()
        f = service.any_of("status", ["todo", "in-progress"])
        assert isinstance(f, Filter)
        assert f.operator == FilterOperator.IN

    def test_text_contains_creates_filter(self):
        """text_contains creates substring filter."""
        service = MockFilterService()
        f = service.text_contains("title", "auth")
        assert isinstance(f, Filter)

    def test_range_creates_filter(self):
        """range creates numeric range filter."""
        service = MockFilterService()
        f = service.range("priority", min_value=0.5, max_value=1.0)
        assert isinstance(f, Filter)


class TestFilterComposition:
    """Test combining filters."""

    def test_combine_creates_compound_filter(self):
        """combine creates compound filter."""
        service = MockFilterService()
        f1 = service.status_is("todo")
        f2 = service.priority_gte("high")
        combined = service.combine([f1, f2])
        assert isinstance(combined, Filter)
        assert combined.is_compound is True

    def test_all_of_combines_with_and(self):
        """all_of combines filters with AND logic."""
        service = MockFilterService()
        f1 = service.status_is("todo")
        f2 = service.priority_gte("high")
        combined = service.all_of(f1, f2)
        assert combined.logic == FilterLogic.AND

    def test_any_combines_with_or(self):
        """any combines filters with OR logic."""
        service = MockFilterService()
        f1 = service.status_is("done")
        f2 = service.assigned_to("alice")
        combined = service.any(f1, f2)
        assert combined.logic == FilterLogic.OR

    def test_not_filter_negates(self):
        """not_filter negates a filter."""
        service = MockFilterService()
        f = service.status_is("done")
        negated = service.not_filter(f)
        assert negated.logic == FilterLogic.NOT


class TestFilterValidation:
    """Test filter validation."""

    def test_validate_returns_bool(self):
        """validate returns boolean."""
        service = MockFilterService()
        f = service.status_is("todo")
        result = service.validate(f)
        assert isinstance(result, bool)

    def test_validate_compound_filter(self):
        """validate handles compound filters."""
        service = MockFilterService()
        f1 = service.status_is("todo")
        f2 = service.priority_gte("high")
        combined = service.combine([f1, f2])
        assert service.validate(combined) is True


class TestFilterCompilation:
    """Test filter compilation."""

    def test_compile_returns_callable(self):
        """compile returns callable."""
        service = MockFilterService()
        f = service.status_is("todo")
        compiled = service.compile(f)
        assert callable(compiled)

    def test_compiled_filter_takes_item(self):
        """Compiled filter accepts item argument."""
        service = MockFilterService()
        f = service.status_is("todo")
        compiled = service.compile(f)
        item = Mock(status="todo")
        result = compiled(item)
        assert isinstance(result, bool)

    def test_custom_predicate_compiled(self):
        """Custom predicate can be compiled."""
        service = MockFilterService()

        def pred(x):
            return len(x.title) > 5

        f = service.custom(pred)
        compiled = service.compile(f)
        assert callable(compiled)


class TestFilterApplication:
    """Test applying filters to items."""

    def test_apply_returns_list(self):
        """apply returns list of items."""
        service = MockFilterService()
        items = [
            Mock(status="todo", priority="high"),
            Mock(status="done", priority="high"),
        ]
        f = service.status_is("todo")
        result = service.apply(items, f)
        assert isinstance(result, list)

    def test_apply_filters_correctly(self):
        """apply filters items correctly."""
        service = MockFilterService()
        items = [
            Mock(status="todo"),
            Mock(status="done"),
            Mock(status="todo"),
        ]
        f = service.status_is("todo")
        result = service.apply(items, f)
        assert len(result) == 2

    def test_apply_respects_limit(self):
        """apply respects limit parameter."""
        service = MockFilterService()
        items = [Mock(status="todo") for _ in range(10)]
        f = service.status_is("todo")
        result = service.apply(items, f, limit=5)
        assert len(result) <= 5

    def test_apply_compiled_works(self):
        """apply_compiled applies pre-compiled filter."""
        service = MockFilterService()
        items = [Mock(status="todo"), Mock(status="done")]
        f = service.status_is("todo")
        compiled = service.compile(f)
        result = service.apply_compiled(items, compiled)
        assert len(result) == 1

    def test_filter_count_returns_int(self):
        """filter_count returns integer."""
        service = MockFilterService()
        items = [Mock(status="todo"), Mock(status="done")]
        f = service.status_is("todo")
        count = service.filter_count(items, f)
        assert isinstance(count, int)
        assert count == 1


class TestFilterUtility:
    """Test utility methods."""

    def test_describe_returns_string(self):
        """describe returns human-readable string."""
        service = MockFilterService()
        f = service.status_is("todo")
        desc = service.describe(f)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_standard_filters_returns_dict(self):
        """get_standard_filters returns dict of available filters."""
        service = MockFilterService()
        filters = service.get_standard_filters()
        assert isinstance(filters, dict)
        assert len(filters) > 0


class TestFilterCorrectness:
    """Test filter correctness on real data."""

    def test_status_filter_matches_exactly(self):
        """status filter matches exact status."""
        service = MockFilterService()
        items = [
            Mock(status="todo"),
            Mock(status="in-progress"),
            Mock(status="done"),
        ]
        f = service.status_is("todo")
        result = service.apply(items, f)
        assert len(result) == 1
        assert result[0].status == "todo"

    def test_multiple_filters_both_match(self):
        """Multiple combined filters both apply."""
        service = MockFilterService()
        items = [
            Mock(status="todo", assigned_to="alice"),
            Mock(status="todo", assigned_to="bob"),
            Mock(status="done", assigned_to="alice"),
        ]
        f1 = service.status_is("todo")
        f2 = service.assigned_to("alice")
        combined = service.all_of(f1, f2)
        result = service.apply(items, combined)
        assert len(result) == 1
        assert result[0].status == "todo"
        assert result[0].assigned_to == "alice"

    def test_or_filter_matches_either(self):
        """OR filter matches if any condition matches."""
        service = MockFilterService()
        items = [
            Mock(status="done"),
            Mock(status="in-progress"),
            Mock(status="todo"),
        ]
        f1 = service.status_is("done")
        f2 = service.status_is("in-progress")
        combined = service.any(f1, f2)
        result = service.apply(items, combined)
        assert len(result) == 2


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_filter_error_inherits(self):
        """InvalidFilterError inherits from FilterServiceError."""
        assert issubclass(InvalidFilterError, FilterServiceError)

    def test_exception_can_be_raised(self):
        """InvalidFilterError can be raised and caught."""
        with pytest.raises(InvalidFilterError):
            raise InvalidFilterError("Bad filter")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
