"""
Tests for Find API - BeautifulSoup-style find methods.
"""

import pytest
import tempfile
from pathlib import Path

from htmlgraph.find_api import FindAPI, find, find_all
from htmlgraph.models import Node, Edge
from htmlgraph.graph import HtmlGraph


class TestFindAPIBasic:
    """Tests for basic find operations."""

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

    def test_find_by_type(self, graph_with_nodes):
        """Test find with type filter."""
        node = graph_with_nodes.find(type="bug")
        assert node is not None
        assert node.id == "bug-1"

    def test_find_by_status(self, graph_with_nodes):
        """Test find with status filter."""
        node = graph_with_nodes.find(status="blocked")
        assert node is not None
        assert node.id == "feat-2"

    def test_find_multiple_filters(self, graph_with_nodes):
        """Test find with multiple filters."""
        node = graph_with_nodes.find(type="feature", priority="high", status="done")
        assert node is not None
        assert node.id == "feat-3"

    def test_find_no_match(self, graph_with_nodes):
        """Test find returns None when no match."""
        node = graph_with_nodes.find(type="nonexistent")
        assert node is None

    def test_find_all_by_type(self, graph_with_nodes):
        """Test find_all with type filter."""
        nodes = graph_with_nodes.find_all(type="feature")
        assert len(nodes) == 4

    def test_find_all_by_priority(self, graph_with_nodes):
        """Test find_all with priority filter."""
        nodes = graph_with_nodes.find_all(priority="high")
        assert len(nodes) == 2  # feat-1, feat-3

    def test_find_all_with_limit(self, graph_with_nodes):
        """Test find_all with limit."""
        nodes = graph_with_nodes.find_all(type="feature", limit=2)
        assert len(nodes) == 2


class TestFindAPILookups:
    """Tests for find with lookup suffixes."""

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
            ]

            for node in nodes:
                graph.add(node)

            yield graph

    def test_contains_lookup(self, graph_with_nodes):
        """Test __contains lookup."""
        nodes = graph_with_nodes.find_all(title__contains="User")
        assert len(nodes) == 2  # feat-1, feat-3

    def test_icontains_lookup(self, graph_with_nodes):
        """Test __icontains (case-insensitive) lookup."""
        nodes = graph_with_nodes.find_all(title__icontains="user")
        assert len(nodes) == 2

    def test_startswith_lookup(self, graph_with_nodes):
        """Test __startswith lookup."""
        nodes = graph_with_nodes.find_all(title__startswith="User")
        assert len(nodes) == 2

    def test_endswith_lookup(self, graph_with_nodes):
        """Test __endswith lookup."""
        nodes = graph_with_nodes.find_all(title__endswith="Processing")
        assert len(nodes) == 1
        assert nodes[0].id == "feat-2"

    def test_regex_lookup(self, graph_with_nodes):
        """Test __regex lookup."""
        nodes = graph_with_nodes.find_all(title__regex=r"User\s+\w+")
        assert len(nodes) == 2

    def test_gt_lookup(self, graph_with_nodes):
        """Test __gt (greater than) lookup."""
        nodes = graph_with_nodes.find_all(properties__effort__gt=8)
        assert len(nodes) == 1
        assert nodes[0].id == "feat-2"

    def test_gte_lookup(self, graph_with_nodes):
        """Test __gte (greater than or equal) lookup."""
        nodes = graph_with_nodes.find_all(properties__effort__gte=8)
        assert len(nodes) == 2  # feat-1 (8), feat-2 (12)

    def test_lt_lookup(self, graph_with_nodes):
        """Test __lt (less than) lookup."""
        nodes = graph_with_nodes.find_all(properties__completion__lt=50)
        assert len(nodes) == 2  # feat-1 (45), feat-2 (20)

    def test_lte_lookup(self, graph_with_nodes):
        """Test __lte (less than or equal) lookup."""
        nodes = graph_with_nodes.find_all(properties__completion__lte=45)
        assert len(nodes) == 2

    def test_in_lookup(self, graph_with_nodes):
        """Test __in lookup."""
        nodes = graph_with_nodes.find_all(status__in=["blocked", "done"])
        assert len(nodes) == 2  # feat-2, feat-3

    def test_not_in_lookup(self, graph_with_nodes):
        """Test __not_in lookup."""
        nodes = graph_with_nodes.find_all(status__not_in=["done"])
        assert len(nodes) == 2  # feat-1, feat-2

    def test_isnull_lookup(self, graph_with_nodes):
        """Test __isnull lookup."""
        nodes = graph_with_nodes.find_all(agent_assigned__isnull=True)
        assert len(nodes) == 3  # All have no agent


class TestFindAPINestedAttributes:
    """Tests for nested attribute access."""

    @pytest.fixture
    def graph_with_nested(self):
        """Create a graph with nested properties."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            nodes = [
                Node(
                    id="n1",
                    title="Node 1",
                    properties={
                        "metadata": {"version": 1, "author": "alice"},
                        "effort": 8
                    }
                ),
                Node(
                    id="n2",
                    title="Node 2",
                    properties={
                        "metadata": {"version": 2, "author": "bob"},
                        "effort": 12
                    }
                ),
            ]

            for node in nodes:
                graph.add(node)

            yield graph

    def test_nested_exact(self, graph_with_nested):
        """Test exact match on nested attribute."""
        nodes = graph_with_nested.find_all(properties__effort=8)
        assert len(nodes) == 1
        assert nodes[0].id == "n1"

    def test_deeply_nested(self, graph_with_nested):
        """Test deeply nested attribute access."""
        nodes = graph_with_nested.find_all(properties__metadata__author="alice")
        assert len(nodes) == 1
        assert nodes[0].id == "n1"

    def test_nested_with_lookup(self, graph_with_nested):
        """Test nested attribute with lookup suffix."""
        nodes = graph_with_nested.find_all(properties__metadata__version__gt=1)
        assert len(nodes) == 1
        assert nodes[0].id == "n2"


class TestFindAPIRelated:
    """Tests for relationship-based find methods."""

    @pytest.fixture
    def graph_with_relations(self):
        """Create a graph with node relationships."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Create nodes with edges
            node_a = Node(
                id="feat-a",
                title="Feature A",
                type="feature",
                edges={
                    "blocks": [
                        Edge(target_id="feat-b", relationship="blocks"),
                        Edge(target_id="feat-c", relationship="blocks")
                    ]
                }
            )
            node_b = Node(
                id="feat-b",
                title="Feature B",
                type="feature",
                edges={
                    "blocked_by": [Edge(target_id="feat-a", relationship="blocked_by")]
                }
            )
            node_c = Node(
                id="feat-c",
                title="Feature C",
                type="feature",
                edges={
                    "blocked_by": [Edge(target_id="feat-a", relationship="blocked_by")],
                    "related": [Edge(target_id="feat-b", relationship="related")]
                }
            )

            graph.add(node_a)
            graph.add(node_b)
            graph.add(node_c)

            yield graph

    def test_find_related_outgoing(self, graph_with_relations):
        """Test find_related with outgoing direction."""
        related = graph_with_relations.find_related("feat-a", direction="outgoing")
        ids = {n.id for n in related}
        assert ids == {"feat-b", "feat-c"}

    def test_find_related_with_type(self, graph_with_relations):
        """Test find_related filtered by relationship type."""
        related = graph_with_relations.find_related(
            "feat-c",
            relationship="related",
            direction="outgoing"
        )
        assert len(related) == 1
        assert related[0].id == "feat-b"

    def test_find_related_incoming(self, graph_with_relations):
        """Test find_related with incoming direction."""
        # feat-b has incoming "blocks" edge from feat-a
        related = graph_with_relations.find_related("feat-b", direction="incoming")
        ids = {n.id for n in related}
        assert "feat-a" in ids


class TestFindAPIConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture
    def graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(id="n1", title="Test 1", status="todo"))
            graph.add(Node(id="n2", title="Test 2", status="done"))
            yield graph

    def test_find_function(self, graph):
        """Test module-level find() function."""
        node = find(graph, status="todo")
        assert node is not None
        assert node.id == "n1"

    def test_find_all_function(self, graph):
        """Test module-level find_all() function."""
        nodes = find_all(graph)
        assert len(nodes) == 2


class TestFindByIdAndTitle:
    """Tests for find_by_id and find_by_title methods."""

    @pytest.fixture
    def graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(id="feat-1", title="User Authentication"))
            graph.add(Node(id="feat-2", title="User Login"))
            graph.add(Node(id="bug-1", title="Login Bug"))
            yield graph

    def test_find_by_id(self, graph):
        """Test FindAPI.find_by_id()."""
        api = FindAPI(graph)
        node = api.find_by_id("feat-1")
        assert node is not None
        assert node.title == "User Authentication"

    def test_find_by_id_not_found(self, graph):
        """Test find_by_id returns None for missing id."""
        api = FindAPI(graph)
        node = api.find_by_id("nonexistent")
        assert node is None

    def test_find_by_title_contains(self, graph):
        """Test find_by_title with contains search."""
        api = FindAPI(graph)
        nodes = api.find_by_title("User")
        assert len(nodes) == 2  # User Authentication, User Login

    def test_find_by_title_exact(self, graph):
        """Test find_by_title with exact match."""
        api = FindAPI(graph)
        nodes = api.find_by_title("User Authentication", exact=True)
        assert len(nodes) == 1
        assert nodes[0].id == "feat-1"


class TestGraphFindMethods:
    """Tests for find methods on HtmlGraph."""

    @pytest.fixture
    def graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)
            graph.add(Node(
                id="feat-1",
                title="User Auth",
                type="feature",
                status="blocked",
                priority="high"
            ))
            graph.add(Node(
                id="feat-2",
                title="Payment",
                type="feature",
                status="todo",
                priority="medium"
            ))
            yield graph

    def test_graph_find(self, graph):
        """Test HtmlGraph.find() method."""
        node = graph.find(type="feature", status="blocked")
        assert node is not None
        assert node.id == "feat-1"

    def test_graph_find_all(self, graph):
        """Test HtmlGraph.find_all() method."""
        nodes = graph.find_all(type="feature")
        assert len(nodes) == 2

    def test_graph_find_with_lookup(self, graph):
        """Test HtmlGraph.find() with lookup suffix."""
        node = graph.find(title__contains="Auth")
        assert node is not None
        assert node.id == "feat-1"
