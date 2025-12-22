"""
Tests for QueryBuilder - Fluent query API.
"""

import pytest
import re
import tempfile
from pathlib import Path

from htmlgraph.query_builder import (
    QueryBuilder, ConditionBuilder, Condition,
    Operator, LogicalOp, _get_nested_attr
)
from htmlgraph.models import Node, Edge
from htmlgraph.graph import HtmlGraph


class TestNestedAttributeAccess:
    """Tests for nested attribute access helper."""

    def test_direct_attribute(self):
        node = Node(id="n1", title="Test", status="blocked")
        assert _get_nested_attr(node, "status") == "blocked"
        assert _get_nested_attr(node, "title") == "Test"

    def test_nested_dict_attribute(self):
        node = Node(
            id="n1", title="Test",
            properties={"effort": 8, "metadata": {"count": 5}}
        )
        assert _get_nested_attr(node, "properties.effort") == 8
        assert _get_nested_attr(node, "properties.metadata") == {"count": 5}
        assert _get_nested_attr(node, "properties.metadata.count") == 5

    def test_missing_attribute(self):
        node = Node(id="n1", title="Test")
        assert _get_nested_attr(node, "nonexistent") is None
        assert _get_nested_attr(node, "properties.missing") is None


class TestCondition:
    """Tests for individual Condition evaluation."""

    @pytest.fixture
    def sample_node(self):
        return Node(
            id="feature-1",
            title="User Authentication",
            status="in-progress",
            priority="high",
            properties={
                "effort": 8,
                "completion": 45.5,
                "tags": ["auth", "security"]
            }
        )

    def test_eq_operator(self, sample_node):
        cond = Condition(attribute="status", operator=Operator.EQ, value="in-progress")
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="status", operator=Operator.EQ, value="done")
        assert cond.evaluate(sample_node) is False

    def test_ne_operator(self, sample_node):
        cond = Condition(attribute="status", operator=Operator.NE, value="done")
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="status", operator=Operator.NE, value="in-progress")
        assert cond.evaluate(sample_node) is False

    def test_gt_operator(self, sample_node):
        cond = Condition(attribute="properties.effort", operator=Operator.GT, value=5)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="properties.effort", operator=Operator.GT, value=10)
        assert cond.evaluate(sample_node) is False

    def test_gte_operator(self, sample_node):
        cond = Condition(attribute="properties.effort", operator=Operator.GTE, value=8)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="properties.effort", operator=Operator.GTE, value=9)
        assert cond.evaluate(sample_node) is False

    def test_lt_operator(self, sample_node):
        cond = Condition(attribute="properties.completion", operator=Operator.LT, value=50)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="properties.completion", operator=Operator.LT, value=40)
        assert cond.evaluate(sample_node) is False

    def test_lte_operator(self, sample_node):
        cond = Condition(attribute="properties.completion", operator=Operator.LTE, value=45.5)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="properties.completion", operator=Operator.LTE, value=40)
        assert cond.evaluate(sample_node) is False

    def test_in_operator(self, sample_node):
        cond = Condition(attribute="priority", operator=Operator.IN, value=["high", "critical"])
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="priority", operator=Operator.IN, value=["low", "medium"])
        assert cond.evaluate(sample_node) is False

    def test_not_in_operator(self, sample_node):
        cond = Condition(attribute="priority", operator=Operator.NOT_IN, value=["low", "medium"])
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="priority", operator=Operator.NOT_IN, value=["high", "critical"])
        assert cond.evaluate(sample_node) is False

    def test_between_operator(self, sample_node):
        cond = Condition(attribute="properties.completion", operator=Operator.BETWEEN, value=(40, 50))
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="properties.completion", operator=Operator.BETWEEN, value=(50, 100))
        assert cond.evaluate(sample_node) is False

    def test_contains_operator(self, sample_node):
        cond = Condition(attribute="title", operator=Operator.CONTAINS, value="Auth")
        assert cond.evaluate(sample_node) is True  # Case-insensitive

        cond = Condition(attribute="title", operator=Operator.CONTAINS, value="Payment")
        assert cond.evaluate(sample_node) is False

    def test_starts_with_operator(self, sample_node):
        cond = Condition(attribute="title", operator=Operator.STARTS_WITH, value="user")
        assert cond.evaluate(sample_node) is True  # Case-insensitive

        cond = Condition(attribute="title", operator=Operator.STARTS_WITH, value="admin")
        assert cond.evaluate(sample_node) is False

    def test_ends_with_operator(self, sample_node):
        cond = Condition(attribute="title", operator=Operator.ENDS_WITH, value="authentication")
        assert cond.evaluate(sample_node) is True  # Case-insensitive

        cond = Condition(attribute="title", operator=Operator.ENDS_WITH, value="login")
        assert cond.evaluate(sample_node) is False

    def test_matches_operator(self, sample_node):
        cond = Condition(attribute="title", operator=Operator.MATCHES, value=r"User\s+Auth")
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="title", operator=Operator.MATCHES, value=r"^Admin")
        assert cond.evaluate(sample_node) is False

    def test_matches_with_compiled_pattern(self, sample_node):
        pattern = re.compile(r"auth", re.IGNORECASE)
        cond = Condition(attribute="title", operator=Operator.MATCHES, value=pattern)
        assert cond.evaluate(sample_node) is True

    def test_is_null_operator(self, sample_node):
        cond = Condition(attribute="agent_assigned", operator=Operator.IS_NULL)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="status", operator=Operator.IS_NULL)
        assert cond.evaluate(sample_node) is False

    def test_is_not_null_operator(self, sample_node):
        cond = Condition(attribute="status", operator=Operator.IS_NOT_NULL)
        assert cond.evaluate(sample_node) is True

        cond = Condition(attribute="agent_assigned", operator=Operator.IS_NOT_NULL)
        assert cond.evaluate(sample_node) is False


class TestQueryBuilder:
    """Tests for QueryBuilder fluent API."""

    @pytest.fixture
    def graph_with_nodes(self):
        """Create a graph with test nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            nodes = [
                Node(
                    id="feat-1",
                    title="User Authentication",
                    type="feature",
                    status="in-progress",
                    priority="high",
                    properties={"effort": 8, "completion": 45}
                ),
                Node(
                    id="feat-2",
                    title="Payment Processing",
                    type="feature",
                    status="blocked",
                    priority="critical",
                    properties={"effort": 12, "completion": 20}
                ),
                Node(
                    id="feat-3",
                    title="User Login Screen",
                    type="feature",
                    status="done",
                    priority="high",
                    properties={"effort": 4, "completion": 100}
                ),
                Node(
                    id="bug-1",
                    title="Login timeout bug",
                    type="bug",
                    status="todo",
                    priority="medium",
                    properties={"severity": "medium"}
                ),
                Node(
                    id="feat-4",
                    title="Admin Dashboard",
                    type="feature",
                    status="todo",
                    priority="low",
                    properties={"effort": 16, "completion": 0}
                ),
            ]

            for node in nodes:
                graph.add(node)

            yield graph

    def test_where_with_value(self, graph_with_nodes):
        """Test where() with direct value."""
        results = graph_with_nodes.query_builder() \
            .where("status", "blocked") \
            .execute()

        assert len(results) == 1
        assert results[0].id == "feat-2"

    def test_where_fluent(self, graph_with_nodes):
        """Test where() with fluent operator."""
        results = graph_with_nodes.query_builder() \
            .where("priority").in_(["high", "critical"]) \
            .execute()

        assert len(results) == 3  # feat-1, feat-2, feat-3

    def test_and_conditions(self, graph_with_nodes):
        """Test AND conditions."""
        results = graph_with_nodes.query_builder() \
            .where("type", "feature") \
            .and_("priority", "high") \
            .execute()

        assert len(results) == 2  # feat-1, feat-3
        ids = {r.id for r in results}
        assert ids == {"feat-1", "feat-3"}

    def test_or_conditions(self, graph_with_nodes):
        """Test OR conditions."""
        results = graph_with_nodes.query_builder() \
            .where("status", "blocked") \
            .or_("status", "done") \
            .execute()

        assert len(results) == 2  # feat-2, feat-3

    def test_not_conditions(self, graph_with_nodes):
        """Test NOT conditions."""
        results = graph_with_nodes.query_builder() \
            .where("type", "feature") \
            .not_("status").eq("done") \
            .execute()

        # 4 features total, 1 is done (feat-3), so 3 remain
        assert len(results) == 3
        ids = {r.id for r in results}
        assert "feat-3" not in ids

    def test_numeric_comparison(self, graph_with_nodes):
        """Test numeric comparisons."""
        results = graph_with_nodes.query_builder() \
            .where("properties.effort").gt(8) \
            .execute()

        assert len(results) == 2  # feat-2 (12), feat-4 (16)

    def test_between_comparison(self, graph_with_nodes):
        """Test BETWEEN comparison."""
        results = graph_with_nodes.query_builder() \
            .where("properties.completion").between(20, 50) \
            .execute()

        assert len(results) == 2  # feat-1 (45), feat-2 (20)

    def test_text_contains(self, graph_with_nodes):
        """Test text contains search."""
        results = graph_with_nodes.query_builder() \
            .where("title").contains("user") \
            .execute()

        assert len(results) == 2  # feat-1, feat-3

    def test_text_matches_regex(self, graph_with_nodes):
        """Test regex matching."""
        results = graph_with_nodes.query_builder() \
            .where("title").matches(r"^User") \
            .execute()

        assert len(results) == 2  # feat-1, feat-3

    def test_of_type_filter(self, graph_with_nodes):
        """Test type filter."""
        results = graph_with_nodes.query_builder() \
            .of_type("bug") \
            .execute()

        assert len(results) == 1
        assert results[0].id == "bug-1"

    def test_limit(self, graph_with_nodes):
        """Test limit."""
        results = graph_with_nodes.query_builder() \
            .where("type", "feature") \
            .limit(2) \
            .execute()

        assert len(results) == 2

    def test_offset(self, graph_with_nodes):
        """Test offset."""
        all_features = graph_with_nodes.query_builder() \
            .of_type("feature") \
            .execute()

        offset_results = graph_with_nodes.query_builder() \
            .of_type("feature") \
            .offset(2) \
            .execute()

        assert len(offset_results) == len(all_features) - 2

    def test_first(self, graph_with_nodes):
        """Test first() method."""
        result = graph_with_nodes.query_builder() \
            .where("status", "blocked") \
            .first()

        assert result is not None
        assert result.id == "feat-2"

    def test_first_none(self, graph_with_nodes):
        """Test first() when no results."""
        result = graph_with_nodes.query_builder() \
            .where("status", "nonexistent") \
            .first()

        assert result is None

    def test_count(self, graph_with_nodes):
        """Test count() method."""
        count = graph_with_nodes.query_builder() \
            .of_type("feature") \
            .count()

        assert count == 4

    def test_exists(self, graph_with_nodes):
        """Test exists() method."""
        exists = graph_with_nodes.query_builder() \
            .where("status", "blocked") \
            .exists()
        assert exists is True

        exists = graph_with_nodes.query_builder() \
            .where("status", "nonexistent") \
            .exists()
        assert exists is False

    def test_iteration(self, graph_with_nodes):
        """Test iteration over query results."""
        query = graph_with_nodes.query_builder().of_type("feature")
        results = list(query)
        assert len(results) == 4

    def test_to_predicate(self, graph_with_nodes):
        """Test converting query to predicate function."""
        predicate = graph_with_nodes.query_builder() \
            .where("priority", "high") \
            .of_type("feature") \
            .to_predicate()

        # Use predicate with filter
        node = Node(id="test", title="Test", type="feature", priority="high")
        assert predicate(node) is True

        node = Node(id="test", title="Test", type="feature", priority="low")
        assert predicate(node) is False

    def test_complex_query(self, graph_with_nodes):
        """Test complex multi-condition query."""
        results = graph_with_nodes.query_builder() \
            .of_type("feature") \
            .where("status").in_(["todo", "in-progress"]) \
            .and_("properties.completion").lt(50) \
            .and_("priority").in_(["high", "critical"]) \
            .execute()

        # Analysis:
        # - status in [todo, in-progress] -> feat-1 (in-progress), feat-4 (todo)
        # - completion < 50 -> feat-1 (45), feat-4 (0) [both pass]
        # - priority in [high, critical] -> feat-1 (high) [feat-4 is low]
        # Result: only feat-1
        assert len(results) == 1
        assert results[0].id == "feat-1"


class TestQueryBuilderEdgeCases:
    """Edge case tests for QueryBuilder."""

    @pytest.fixture
    def empty_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield HtmlGraph(tmpdir, auto_load=False)

    def test_empty_graph(self, empty_graph):
        """Test query on empty graph."""
        results = empty_graph.query_builder() \
            .where("status", "todo") \
            .execute()
        assert results == []

    def test_no_conditions(self, empty_graph):
        """Test query with no conditions."""
        empty_graph.add(Node(id="n1", title="Test"))
        results = empty_graph.query_builder().execute()
        assert len(results) == 1

    def test_null_value_comparison(self):
        """Test comparing against null attribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(id="n1", title="Test", agent_assigned=None))

            results = graph.query_builder() \
                .where("agent_assigned").is_null() \
                .execute()
            assert len(results) == 1

    def test_numeric_string_comparison(self):
        """Test numeric comparison with string values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(
                id="n1", title="Test",
                properties={"count": "10"}  # String, not int
            ))

            results = graph.query_builder() \
                .where("properties.count").gt(5) \
                .execute()
            assert len(results) == 1  # Should convert and compare

    def test_missing_nested_attribute(self):
        """Test query on missing nested attribute."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(id="n1", title="Test"))

            results = graph.query_builder() \
                .where("properties.nonexistent").gt(5) \
                .execute()
            assert len(results) == 0  # Missing attr fails comparison
