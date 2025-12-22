"""
Tests for Graph Traversal methods.
"""

import pytest
import tempfile
from pathlib import Path

from htmlgraph.models import Node, Edge
from htmlgraph.graph import HtmlGraph


class TestAncestorsDescendants:
    """Tests for ancestors() and descendants() methods."""

    @pytest.fixture
    def dependency_graph(self):
        """
        Create a graph with dependency relationships:

        a -> b -> d
         \-> c -> d
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Node d depends on nothing
            node_d = Node(id="d", title="Node D")

            # Node b and c depend on d
            node_b = Node(
                id="b", title="Node B",
                edges={"blocked_by": [Edge(target_id="d", relationship="blocked_by")]}
            )
            node_c = Node(
                id="c", title="Node C",
                edges={"blocked_by": [Edge(target_id="d", relationship="blocked_by")]}
            )

            # Node a depends on b and c
            node_a = Node(
                id="a", title="Node A",
                edges={"blocked_by": [
                    Edge(target_id="b", relationship="blocked_by"),
                    Edge(target_id="c", relationship="blocked_by")
                ]}
            )

            graph.add(node_d)
            graph.add(node_b)
            graph.add(node_c)
            graph.add(node_a)

            yield graph

    def test_ancestors_simple(self, dependency_graph):
        """Test finding ancestors."""
        # a depends on b, c, which depend on d
        ancestors = dependency_graph.ancestors("a")
        assert set(ancestors) == {"b", "c", "d"}

    def test_ancestors_with_depth_limit(self, dependency_graph):
        """Test ancestors with max_depth."""
        # With depth 1, should only get direct dependencies
        ancestors = dependency_graph.ancestors("a", max_depth=1)
        assert set(ancestors) == {"b", "c"}

    def test_ancestors_of_root(self, dependency_graph):
        """Test ancestors of node with no dependencies."""
        ancestors = dependency_graph.ancestors("d")
        assert ancestors == []

    def test_ancestors_nonexistent(self, dependency_graph):
        """Test ancestors of nonexistent node."""
        ancestors = dependency_graph.ancestors("nonexistent")
        assert ancestors == []

    def test_descendants_simple(self, dependency_graph):
        """Test finding descendants."""
        # d is depended on by b, c, which are depended on by a
        descendants = dependency_graph.descendants("d")
        assert set(descendants) == {"b", "c", "a"}

    def test_descendants_with_depth_limit(self, dependency_graph):
        """Test descendants with max_depth."""
        # With depth 1, should only get direct dependents
        descendants = dependency_graph.descendants("d", max_depth=1)
        assert set(descendants) == {"b", "c"}

    def test_descendants_of_leaf(self, dependency_graph):
        """Test descendants of node with no dependents."""
        descendants = dependency_graph.descendants("a")
        assert descendants == []

    def test_descendants_nonexistent(self, dependency_graph):
        """Test descendants of nonexistent node."""
        descendants = dependency_graph.descendants("nonexistent")
        assert descendants == []


class TestSubgraph:
    """Tests for subgraph() method."""

    @pytest.fixture
    def graph(self):
        """Create a graph with multiple nodes and edges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            nodes = [
                Node(
                    id="a", title="Node A",
                    edges={"related": [
                        Edge(target_id="b", relationship="related"),
                        Edge(target_id="c", relationship="related")
                    ]}
                ),
                Node(
                    id="b", title="Node B",
                    edges={"related": [Edge(target_id="c", relationship="related")]}
                ),
                Node(id="c", title="Node C"),
                Node(id="d", title="Node D"),  # Isolated
            ]

            for node in nodes:
                graph.add(node)

            yield graph

    def test_subgraph_basic(self, graph):
        """Test basic subgraph extraction."""
        sub = graph.subgraph(["a", "b"])

        assert len(sub) == 2
        assert "a" in sub
        assert "b" in sub
        assert "c" not in sub

    def test_subgraph_preserves_edges(self, graph):
        """Test that subgraph preserves edges between included nodes."""
        sub = graph.subgraph(["a", "b", "c"])

        node_a = sub.get("a")
        assert node_a is not None
        # Edge to b and c should be preserved
        assert len(node_a.edges.get("related", [])) == 2

    def test_subgraph_filters_edges(self, graph):
        """Test that edges to excluded nodes are filtered."""
        sub = graph.subgraph(["a", "b"])

        node_a = sub.get("a")
        # Edge to c should be filtered out
        edges = node_a.edges.get("related", [])
        target_ids = {e.target_id for e in edges}
        assert "c" not in target_ids
        assert "b" in target_ids

    def test_subgraph_no_edges(self, graph):
        """Test subgraph with include_edges=False."""
        sub = graph.subgraph(["a", "b"], include_edges=False)

        node_a = sub.get("a")
        assert len(node_a.edges) == 0

    def test_subgraph_empty(self, graph):
        """Test empty subgraph."""
        sub = graph.subgraph([])
        assert len(sub) == 0

    def test_subgraph_nonexistent_nodes(self, graph):
        """Test subgraph with nonexistent nodes."""
        sub = graph.subgraph(["a", "nonexistent"])
        assert len(sub) == 1
        assert "a" in sub


class TestConnectedComponent:
    """Tests for connected_component() method."""

    @pytest.fixture
    def graph_with_components(self):
        """
        Create a graph with two components:
        Component 1: a <-> b <-> c
        Component 2: d <-> e
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Component 1
            graph.add(Node(
                id="a", title="A",
                edges={"related": [Edge(target_id="b", relationship="related")]}
            ))
            graph.add(Node(
                id="b", title="B",
                edges={"related": [
                    Edge(target_id="a", relationship="related"),
                    Edge(target_id="c", relationship="related")
                ]}
            ))
            graph.add(Node(
                id="c", title="C",
                edges={"related": [Edge(target_id="b", relationship="related")]}
            ))

            # Component 2
            graph.add(Node(
                id="d", title="D",
                edges={"related": [Edge(target_id="e", relationship="related")]}
            ))
            graph.add(Node(
                id="e", title="E",
                edges={"related": [Edge(target_id="d", relationship="related")]}
            ))

            yield graph

    def test_connected_component(self, graph_with_components):
        """Test finding connected component."""
        comp = graph_with_components.connected_component("a")
        assert comp == {"a", "b", "c"}

    def test_connected_component_other(self, graph_with_components):
        """Test finding other connected component."""
        comp = graph_with_components.connected_component("d")
        assert comp == {"d", "e"}

    def test_connected_component_any_start(self, graph_with_components):
        """Test that starting from any node in component gives same result."""
        comp_a = graph_with_components.connected_component("a")
        comp_b = graph_with_components.connected_component("b")
        comp_c = graph_with_components.connected_component("c")

        assert comp_a == comp_b == comp_c

    def test_connected_component_nonexistent(self, graph_with_components):
        """Test connected component of nonexistent node."""
        comp = graph_with_components.connected_component("nonexistent")
        assert comp == set()


class TestAllPaths:
    """Tests for all_paths() method."""

    @pytest.fixture
    def graph_with_paths(self):
        """
        Create a graph with multiple paths:
        a -> b -> d
         \-> c -/
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            graph.add(Node(
                id="a", title="A",
                edges={"next": [
                    Edge(target_id="b", relationship="next"),
                    Edge(target_id="c", relationship="next")
                ]}
            ))
            graph.add(Node(
                id="b", title="B",
                edges={"next": [Edge(target_id="d", relationship="next")]}
            ))
            graph.add(Node(
                id="c", title="C",
                edges={"next": [Edge(target_id="d", relationship="next")]}
            ))
            graph.add(Node(id="d", title="D"))

            yield graph

    def test_all_paths(self, graph_with_paths):
        """Test finding all paths."""
        paths = graph_with_paths.all_paths("a", "d", relationship="next")

        assert len(paths) == 2
        assert ["a", "b", "d"] in paths
        assert ["a", "c", "d"] in paths

    def test_all_paths_same_node(self, graph_with_paths):
        """Test path from node to itself."""
        paths = graph_with_paths.all_paths("a", "a")
        assert paths == [["a"]]

    def test_all_paths_no_path(self, graph_with_paths):
        """Test when no path exists."""
        paths = graph_with_paths.all_paths("d", "a")
        assert paths == []

    def test_all_paths_with_max_length(self, graph_with_paths):
        """Test paths with max length constraint."""
        # max_length is the maximum number of nodes in the path
        # Paths a->b->d and a->c->d both have 3 nodes
        paths = graph_with_paths.all_paths("a", "d", relationship="next", max_length=3)

        assert len(paths) == 2

    def test_all_paths_with_short_max_length(self, graph_with_paths):
        """Test that short max_length filters out longer paths."""
        # With max_length=2, only paths with 2 nodes max (a->d direct)
        # Since there's no direct path, should return empty
        paths = graph_with_paths.all_paths("a", "d", relationship="next", max_length=2)
        assert len(paths) == 0

    def test_all_paths_nonexistent(self, graph_with_paths):
        """Test paths with nonexistent nodes."""
        paths = graph_with_paths.all_paths("nonexistent", "d")
        assert paths == []


class TestTraversalIntegration:
    """Integration tests for traversal methods."""

    @pytest.fixture
    def complex_graph(self):
        """Create a more complex graph for integration testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Create a dependency chain: auth -> db -> api -> frontend
            graph.add(Node(id="frontend", title="Frontend",
                          edges={"blocked_by": [Edge(target_id="api", relationship="blocked_by")]}))
            graph.add(Node(id="api", title="API",
                          edges={"blocked_by": [Edge(target_id="db", relationship="blocked_by")]}))
            graph.add(Node(id="db", title="Database",
                          edges={"blocked_by": [Edge(target_id="auth", relationship="blocked_by")]}))
            graph.add(Node(id="auth", title="Auth"))

            yield graph

    def test_dependency_chain_traversal(self, complex_graph):
        """Test traversing dependency chain."""
        # Frontend depends on auth transitively
        ancestors = complex_graph.ancestors("frontend")
        assert ancestors == ["api", "db", "auth"]

        # Auth blocks everything transitively
        descendants = complex_graph.descendants("auth")
        assert descendants == ["db", "api", "frontend"]

    def test_subgraph_from_dependencies(self, complex_graph):
        """Test creating subgraph from dependencies."""
        # Get subgraph of api and its dependencies
        deps = set(complex_graph.ancestors("api"))
        deps.add("api")

        sub = complex_graph.subgraph(deps)
        assert len(sub) == 3  # api, db, auth
        assert "frontend" not in sub

    def test_transitive_deps_vs_ancestors(self, complex_graph):
        """Test that transitive_deps and ancestors are consistent."""
        # They should return the same nodes
        t_deps = complex_graph.transitive_deps("frontend")
        ancestors = set(complex_graph.ancestors("frontend"))

        assert t_deps == ancestors
