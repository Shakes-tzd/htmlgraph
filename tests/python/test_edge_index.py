"""
Tests for EdgeIndex - O(1) reverse edge lookups.
"""

import pytest
from htmlgraph.edge_index import EdgeIndex, EdgeRef
from htmlgraph.models import Node, Edge
from htmlgraph.graph import HtmlGraph
import tempfile
from pathlib import Path


class TestEdgeRef:
    """Tests for EdgeRef dataclass."""

    def test_edge_ref_creation(self):
        ref = EdgeRef(source_id="a", target_id="b", relationship="blocks")
        assert ref.source_id == "a"
        assert ref.target_id == "b"
        assert ref.relationship == "blocks"

    def test_edge_ref_equality(self):
        ref1 = EdgeRef(source_id="a", target_id="b", relationship="blocks")
        ref2 = EdgeRef(source_id="a", target_id="b", relationship="blocks")
        ref3 = EdgeRef(source_id="a", target_id="b", relationship="related")

        assert ref1 == ref2
        assert ref1 != ref3

    def test_edge_ref_hashable(self):
        ref = EdgeRef(source_id="a", target_id="b", relationship="blocks")
        s = {ref}
        assert ref in s


class TestEdgeIndexBasic:
    """Tests for basic EdgeIndex operations."""

    def test_add_edge(self):
        index = EdgeIndex()
        ref = index.add("node-a", "node-b", "blocks")

        assert ref.source_id == "node-a"
        assert ref.target_id == "node-b"
        assert ref.relationship == "blocks"
        assert len(index) == 1

    def test_add_edge_object(self):
        index = EdgeIndex()
        edge = Edge(target_id="node-b", relationship="blocks")
        ref = index.add_edge("node-a", edge)

        assert ref.source_id == "node-a"
        assert ref.target_id == "node-b"
        assert len(index) == 1

    def test_add_duplicate_edge(self):
        index = EdgeIndex()
        index.add("node-a", "node-b", "blocks")
        index.add("node-a", "node-b", "blocks")  # Duplicate

        assert len(index) == 1  # Should not add duplicate

    def test_remove_edge(self):
        index = EdgeIndex()
        index.add("node-a", "node-b", "blocks")
        assert len(index) == 1

        removed = index.remove("node-a", "node-b", "blocks")
        assert removed is True
        assert len(index) == 0

    def test_remove_nonexistent_edge(self):
        index = EdgeIndex()
        removed = index.remove("node-a", "node-b", "blocks")
        assert removed is False

    def test_remove_node(self):
        index = EdgeIndex()
        index.add("node-a", "node-b", "blocks")
        index.add("node-a", "node-c", "related")
        index.add("node-d", "node-a", "depends")

        assert len(index) == 3

        removed = index.remove_node("node-a")
        assert removed == 3
        assert len(index) == 0

    def test_clear(self):
        index = EdgeIndex()
        index.add("a", "b", "rel")
        index.add("c", "d", "rel")

        index.clear()
        assert len(index) == 0


class TestEdgeIndexLookups:
    """Tests for O(1) lookup operations."""

    @pytest.fixture
    def populated_index(self):
        """Create an index with test data."""
        index = EdgeIndex()
        # node-a blocks node-b and node-c
        index.add("node-a", "node-b", "blocks")
        index.add("node-a", "node-c", "blocks")
        # node-d blocks node-b
        index.add("node-d", "node-b", "blocks")
        # node-e is related to node-b
        index.add("node-e", "node-b", "related")
        return index

    def test_get_incoming_all(self, populated_index):
        """Test getting all incoming edges."""
        incoming = populated_index.get_incoming("node-b")
        assert len(incoming) == 3  # blocks from a, d; related from e

        source_ids = {ref.source_id for ref in incoming}
        assert source_ids == {"node-a", "node-d", "node-e"}

    def test_get_incoming_by_relationship(self, populated_index):
        """Test filtering incoming edges by relationship."""
        incoming = populated_index.get_incoming("node-b", relationship="blocks")
        assert len(incoming) == 2

        source_ids = {ref.source_id for ref in incoming}
        assert source_ids == {"node-a", "node-d"}

    def test_get_incoming_empty(self, populated_index):
        """Test getting incoming for node with no incoming edges."""
        incoming = populated_index.get_incoming("node-a")
        assert len(incoming) == 0

    def test_get_outgoing_all(self, populated_index):
        """Test getting all outgoing edges."""
        outgoing = populated_index.get_outgoing("node-a")
        assert len(outgoing) == 2

        target_ids = {ref.target_id for ref in outgoing}
        assert target_ids == {"node-b", "node-c"}

    def test_get_outgoing_by_relationship(self, populated_index):
        """Test filtering outgoing edges by relationship."""
        outgoing = populated_index.get_outgoing("node-a", relationship="blocks")
        assert len(outgoing) == 2

    def test_get_neighbors_both(self, populated_index):
        """Test getting neighbors in both directions."""
        neighbors = populated_index.get_neighbors("node-b")
        # Incoming: a, d, e; Outgoing: none
        assert neighbors == {"node-a", "node-d", "node-e"}

    def test_get_neighbors_incoming_only(self, populated_index):
        """Test getting only incoming neighbors."""
        neighbors = populated_index.get_neighbors("node-b", direction="incoming")
        assert neighbors == {"node-a", "node-d", "node-e"}

    def test_get_neighbors_outgoing_only(self, populated_index):
        """Test getting only outgoing neighbors."""
        neighbors = populated_index.get_neighbors("node-a", direction="outgoing")
        assert neighbors == {"node-b", "node-c"}

    def test_has_edge(self, populated_index):
        """Test checking edge existence."""
        assert populated_index.has_edge("node-a", "node-b") is True
        assert populated_index.has_edge("node-a", "node-b", "blocks") is True
        assert populated_index.has_edge("node-a", "node-b", "related") is False
        assert populated_index.has_edge("node-b", "node-a") is False


class TestEdgeIndexRebuild:
    """Tests for rebuilding index from nodes."""

    def test_rebuild_from_nodes(self):
        """Test rebuilding index from node dictionary."""
        nodes = {
            "a": Node(
                id="a",
                title="Node A",
                edges={
                    "blocks": [Edge(target_id="b", relationship="blocks")],
                    "related": [Edge(target_id="c", relationship="related")]
                }
            ),
            "b": Node(
                id="b",
                title="Node B",
                edges={
                    "blocked_by": [Edge(target_id="a", relationship="blocked_by")]
                }
            ),
            "c": Node(id="c", title="Node C")
        }

        index = EdgeIndex()
        count = index.rebuild(nodes)

        assert count == 3
        assert len(index) == 3

        # Verify lookups work
        incoming_b = index.get_incoming("b")
        assert len(incoming_b) == 1
        assert incoming_b[0].source_id == "a"

    def test_rebuild_clears_previous(self):
        """Test that rebuild clears previous entries."""
        index = EdgeIndex()
        index.add("x", "y", "old")
        assert len(index) == 1

        nodes = {
            "a": Node(
                id="a",
                title="Node A",
                edges={"blocks": [Edge(target_id="b", relationship="blocks")]}
            ),
            "b": Node(id="b", title="Node B")
        }

        index.rebuild(nodes)
        assert len(index) == 1
        assert index.has_edge("a", "b") is True
        assert index.has_edge("x", "y") is False


class TestEdgeIndexStats:
    """Tests for index statistics."""

    def test_stats(self):
        index = EdgeIndex()
        index.add("a", "b", "blocks")
        index.add("a", "c", "blocks")
        index.add("d", "b", "related")

        stats = index.stats()
        assert stats["edge_count"] == 3
        assert stats["nodes_with_outgoing"] == 2  # a, d
        assert stats["nodes_with_incoming"] == 2  # b, c
        assert set(stats["relationships"]) == {"blocks", "related"}


class TestEdgeIndexIteration:
    """Tests for iterating over edges."""

    def test_iteration(self):
        index = EdgeIndex()
        index.add("a", "b", "blocks")
        index.add("a", "c", "related")

        edges = list(index)
        assert len(edges) == 2

        edge_tuples = {(e.source_id, e.target_id, e.relationship) for e in edges}
        assert edge_tuples == {("a", "b", "blocks"), ("a", "c", "related")}


class TestHtmlGraphEdgeIndex:
    """Tests for EdgeIndex integration with HtmlGraph."""

    @pytest.fixture
    def graph_with_nodes(self):
        """Create a graph with test nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            # Create nodes with edges
            node_a = Node(
                id="feature-a",
                title="Feature A",
                edges={
                    "blocks": [
                        Edge(target_id="feature-b", relationship="blocks"),
                        Edge(target_id="feature-c", relationship="blocks")
                    ]
                }
            )
            node_b = Node(
                id="feature-b",
                title="Feature B",
                edges={
                    "blocked_by": [Edge(target_id="feature-a", relationship="blocked_by")]
                }
            )
            node_c = Node(id="feature-c", title="Feature C")

            graph.add(node_a)
            graph.add(node_b)
            graph.add(node_c)

            yield graph

    def test_index_populated_on_add(self, graph_with_nodes):
        """Test that edge index is populated when nodes are added."""
        graph = graph_with_nodes

        # Check index was populated
        assert len(graph.edge_index) == 3

        # Test lookup
        incoming = graph.get_incoming_edges("feature-b")
        assert len(incoming) == 1
        assert incoming[0].source_id == "feature-a"

    def test_index_updated_on_update(self, graph_with_nodes):
        """Test that edge index is updated when node is updated."""
        graph = graph_with_nodes
        node_a = graph.get("feature-a")

        # Add a new edge
        node_a.edges["blocks"].append(
            Edge(target_id="feature-c", relationship="blocks")
        )
        node_a.edges["related"] = [
            Edge(target_id="feature-d", relationship="related")
        ]

        graph.update(node_a)

        # Old edges should be removed and new ones added
        outgoing = graph.get_outgoing_edges("feature-a")
        target_ids = {ref.target_id for ref in outgoing}
        assert "feature-d" in target_ids

    def test_index_cleared_on_remove(self, graph_with_nodes):
        """Test that edge index is cleared when node is removed."""
        graph = graph_with_nodes

        # Remove node-a
        graph.remove("feature-a")

        # All edges involving feature-a should be gone
        incoming = graph.get_incoming_edges("feature-b", "blocks")
        assert len(incoming) == 0

    def test_dependents_uses_index(self, graph_with_nodes):
        """Test that dependents() uses the O(1) edge index."""
        graph = graph_with_nodes

        # feature-b is blocked_by feature-a
        deps = graph.dependents("feature-a", relationship="blocked_by")
        assert "feature-b" in deps

    def test_get_neighbors(self, graph_with_nodes):
        """Test getting neighbors via graph method."""
        graph = graph_with_nodes

        neighbors = graph.get_neighbors("feature-a", direction="outgoing")
        assert "feature-b" in neighbors
        assert "feature-c" in neighbors

    def test_reload_rebuilds_index(self):
        """Test that reload rebuilds the edge index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            node_a = Node(
                id="node-a",
                title="Node A",
                edges={"blocks": [Edge(target_id="node-b", relationship="blocks")]}
            )
            graph.add(node_a)
            graph.add(Node(id="node-b", title="Node B"))

            # Reload
            graph.reload()

            # Index should be rebuilt
            assert len(graph.edge_index) == 1
            incoming = graph.get_incoming_edges("node-b")
            assert len(incoming) == 1


class TestEdgeIndexPerformance:
    """Performance-related tests for edge index."""

    def test_o1_lookup_vs_linear_scan(self):
        """Verify O(1) lookup is faster than O(V×E) scan for large graphs."""
        # Create a moderately sized graph
        index = EdgeIndex()
        num_nodes = 1000
        edges_per_node = 5

        # Build index
        for i in range(num_nodes):
            for j in range(edges_per_node):
                target = (i + j + 1) % num_nodes
                index.add(f"node-{i}", f"node-{target}", "related")

        # O(1) lookup should be fast
        import time

        start = time.perf_counter()
        for _ in range(1000):
            index.get_incoming("node-500")
        indexed_time = time.perf_counter() - start

        # Should complete in under 100ms for 1000 lookups
        assert indexed_time < 0.1, f"Indexed lookup took {indexed_time:.3f}s, expected < 0.1s"
