"""
Tests for bounded path-finding and cycle detection.

Covers:
- any_shortest: BFS shortest path
- all_shortest: all equal-length shortest paths
- bounded_paths: depth-limited DFS path enumeration
- find_cycles: cycle detection with depth bounds
- reachable_set: bounded reachability analysis
- Edge type filtering on all methods
- Empty / disconnected graph edge cases
- Performance: bounded_paths terminates quickly on dense graphs
"""

import tempfile
import time

import pytest
from htmlgraph.bounded_paths import BoundedPathFinder, CycleResult, PathResult
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_graph():
    """An empty HtmlGraph in a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield HtmlGraph(tmpdir, auto_load=False)


@pytest.fixture
def linear_graph():
    """A -> B -> C -> D (all 'depends_on' edges)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        g = HtmlGraph(tmpdir, auto_load=False)
        g.add(
            Node(
                id="A",
                title="A",
                edges={"depends_on": [Edge(target_id="B", relationship="depends_on")]},
            )
        )
        g.add(
            Node(
                id="B",
                title="B",
                edges={"depends_on": [Edge(target_id="C", relationship="depends_on")]},
            )
        )
        g.add(
            Node(
                id="C",
                title="C",
                edges={"depends_on": [Edge(target_id="D", relationship="depends_on")]},
            )
        )
        g.add(Node(id="D", title="D"))
        yield g


@pytest.fixture
def diamond_graph():
    """
    Diamond-shaped graph:
        A
       / \\
      B   C
       \\ /
        D

    All edges use 'related' relationship.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        g = HtmlGraph(tmpdir, auto_load=False)
        g.add(
            Node(
                id="A",
                title="A",
                edges={
                    "related": [
                        Edge(target_id="B", relationship="related"),
                        Edge(target_id="C", relationship="related"),
                    ]
                },
            )
        )
        g.add(
            Node(
                id="B",
                title="B",
                edges={"related": [Edge(target_id="D", relationship="related")]},
            )
        )
        g.add(
            Node(
                id="C",
                title="C",
                edges={"related": [Edge(target_id="D", relationship="related")]},
            )
        )
        g.add(Node(id="D", title="D"))
        yield g


@pytest.fixture
def cycle_graph():
    """
    Graph with a simple cycle: A -> B -> C -> A
    Plus a tail: C -> D (no cycle).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        g = HtmlGraph(tmpdir, auto_load=False)
        g.add(
            Node(
                id="A",
                title="A",
                edges={"blocks": [Edge(target_id="B", relationship="blocks")]},
            )
        )
        g.add(
            Node(
                id="B",
                title="B",
                edges={"blocks": [Edge(target_id="C", relationship="blocks")]},
            )
        )
        g.add(
            Node(
                id="C",
                title="C",
                edges={
                    "blocks": [
                        Edge(target_id="A", relationship="blocks"),
                        Edge(target_id="D", relationship="blocks"),
                    ]
                },
            )
        )
        g.add(Node(id="D", title="D"))
        yield g


@pytest.fixture
def multi_edge_graph():
    """
    Graph with multiple edge types:
    A --owns--> B --owns--> C
    A --uses--> C
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        g = HtmlGraph(tmpdir, auto_load=False)
        g.add(
            Node(
                id="A",
                title="A",
                edges={
                    "owns": [Edge(target_id="B", relationship="owns")],
                    "uses": [Edge(target_id="C", relationship="uses")],
                },
            )
        )
        g.add(
            Node(
                id="B",
                title="B",
                edges={"owns": [Edge(target_id="C", relationship="owns")]},
            )
        )
        g.add(Node(id="C", title="C"))
        yield g


@pytest.fixture
def disconnected_graph():
    """Two disconnected components: {A, B} and {C, D}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        g = HtmlGraph(tmpdir, auto_load=False)
        g.add(
            Node(
                id="A",
                title="A",
                edges={"related": [Edge(target_id="B", relationship="related")]},
            )
        )
        g.add(Node(id="B", title="B"))
        g.add(
            Node(
                id="C",
                title="C",
                edges={"related": [Edge(target_id="D", relationship="related")]},
            )
        )
        g.add(Node(id="D", title="D"))
        yield g


# ---------------------------------------------------------------------------
# any_shortest tests
# ---------------------------------------------------------------------------


class TestAnyShortest:
    """Tests for BoundedPathFinder.any_shortest."""

    def test_finds_shortest_path_linear(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("A", "D")

        assert result is not None
        assert result.nodes == ["A", "B", "C", "D"]
        assert result.length == 3
        assert result.relationship_types == ["depends_on"]

    def test_finds_shortest_path_diamond(self, diamond_graph):
        finder = BoundedPathFinder(diamond_graph)
        result = finder.any_shortest("A", "D")

        assert result is not None
        assert result.length == 2
        # Should be either [A, B, D] or [A, C, D]
        assert result.nodes[0] == "A"
        assert result.nodes[-1] == "D"
        assert len(result.nodes) == 3

    def test_same_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("A", "A")

        assert result is not None
        assert result.nodes == ["A"]
        assert result.length == 0
        assert result.edges == []

    def test_no_path_disconnected(self, disconnected_graph):
        finder = BoundedPathFinder(disconnected_graph)
        result = finder.any_shortest("A", "C")

        assert result is None

    def test_nonexistent_source(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("MISSING", "D")

        assert result is None

    def test_nonexistent_target(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("A", "MISSING")

        assert result is None

    def test_no_reverse_path(self, linear_graph):
        """Linear graph A->B->C->D has no path D->A."""
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("D", "A")

        assert result is None

    def test_edge_type_filtering(self, multi_edge_graph):
        finder = BoundedPathFinder(multi_edge_graph)

        # Using only 'owns' edges: A -> B -> C (length 2)
        result_owns = finder.any_shortest("A", "C", edge_types=["owns"])
        assert result_owns is not None
        assert result_owns.length == 2
        assert result_owns.nodes == ["A", "B", "C"]

        # Using only 'uses' edges: A -> C (length 1)
        result_uses = finder.any_shortest("A", "C", edge_types=["uses"])
        assert result_uses is not None
        assert result_uses.length == 1
        assert result_uses.nodes == ["A", "C"]

        # Using all edges: shortest is A -> C via 'uses' (length 1)
        result_all = finder.any_shortest("A", "C")
        assert result_all is not None
        assert result_all.length == 1

    def test_edge_refs_populated(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("A", "C")

        assert result is not None
        assert len(result.edges) == 2
        assert result.edges[0].source_id == "A"
        assert result.edges[0].target_id == "B"
        assert result.edges[1].source_id == "B"
        assert result.edges[1].target_id == "C"

    def test_path_result_is_dataclass(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        result = finder.any_shortest("A", "B")

        assert isinstance(result, PathResult)
        assert result.nodes == ["A", "B"]
        assert result.length == 1


# ---------------------------------------------------------------------------
# all_shortest tests
# ---------------------------------------------------------------------------


class TestAllShortest:
    """Tests for BoundedPathFinder.all_shortest."""

    def test_single_shortest_path(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.all_shortest("A", "D")

        assert len(results) == 1
        assert results[0].nodes == ["A", "B", "C", "D"]
        assert results[0].length == 3

    def test_two_shortest_paths_diamond(self, diamond_graph):
        finder = BoundedPathFinder(diamond_graph)
        results = finder.all_shortest("A", "D")

        assert len(results) == 2
        paths = [r.nodes for r in results]
        assert ["A", "B", "D"] in paths
        assert ["A", "C", "D"] in paths
        for r in results:
            assert r.length == 2

    def test_same_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.all_shortest("A", "A")

        assert len(results) == 1
        assert results[0].nodes == ["A"]
        assert results[0].length == 0

    def test_no_path(self, disconnected_graph):
        finder = BoundedPathFinder(disconnected_graph)
        results = finder.all_shortest("A", "C")

        assert results == []

    def test_nonexistent_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        assert finder.all_shortest("MISSING", "D") == []
        assert finder.all_shortest("A", "MISSING") == []

    def test_edge_type_filtering(self, multi_edge_graph):
        finder = BoundedPathFinder(multi_edge_graph)

        # Only 'owns': A -> B -> C
        results_owns = finder.all_shortest("A", "C", edge_types=["owns"])
        assert len(results_owns) == 1
        assert results_owns[0].nodes == ["A", "B", "C"]

        # Only 'uses': A -> C
        results_uses = finder.all_shortest("A", "C", edge_types=["uses"])
        assert len(results_uses) == 1
        assert results_uses[0].nodes == ["A", "C"]

        # All types: shortest is length 1 (uses), so only 1 result
        results_all = finder.all_shortest("A", "C")
        assert len(results_all) == 1
        assert results_all[0].length == 1


# ---------------------------------------------------------------------------
# bounded_paths tests
# ---------------------------------------------------------------------------


class TestBoundedPaths:
    """Tests for BoundedPathFinder.bounded_paths."""

    def test_finds_all_paths_within_depth(self, diamond_graph):
        finder = BoundedPathFinder(diamond_graph)
        results = finder.bounded_paths("A", "D", max_depth=5)

        paths = [r.nodes for r in results]
        assert ["A", "B", "D"] in paths
        assert ["A", "C", "D"] in paths
        assert len(results) == 2

    def test_respects_depth_limit(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)

        # Depth 2 should NOT find A -> B -> C -> D (length 3)
        results = finder.bounded_paths("A", "D", max_depth=2)
        assert len(results) == 0

        # Depth 3 should find it
        results = finder.bounded_paths("A", "D", max_depth=3)
        assert len(results) == 1
        assert results[0].nodes == ["A", "B", "C", "D"]

    def test_avoids_cycles_within_path(self, cycle_graph):
        """Cycle graph A->B->C->A should not produce infinite paths."""
        finder = BoundedPathFinder(cycle_graph)
        results = finder.bounded_paths("A", "D", max_depth=10)

        # Should find A -> B -> C -> D
        assert len(results) >= 1
        for r in results:
            # No duplicates within a single path (cycle avoidance)
            assert len(r.nodes) == len(set(r.nodes))

    def test_max_results_limit(self, diamond_graph):
        finder = BoundedPathFinder(diamond_graph)
        results = finder.bounded_paths("A", "D", max_results=1)

        assert len(results) == 1

    def test_same_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.bounded_paths("A", "A")

        assert len(results) == 1
        assert results[0].nodes == ["A"]
        assert results[0].length == 0

    def test_no_path_disconnected(self, disconnected_graph):
        finder = BoundedPathFinder(disconnected_graph)
        results = finder.bounded_paths("A", "C")

        assert results == []

    def test_nonexistent_nodes(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        assert finder.bounded_paths("MISSING", "D") == []
        assert finder.bounded_paths("A", "MISSING") == []

    def test_edge_type_filtering(self, multi_edge_graph):
        finder = BoundedPathFinder(multi_edge_graph)

        # Only 'owns' edges: A -> B -> C
        results = finder.bounded_paths("A", "C", edge_types=["owns"])
        assert len(results) == 1
        assert results[0].nodes == ["A", "B", "C"]

        # All edges: two paths (A->C via uses, A->B->C via owns)
        results_all = finder.bounded_paths("A", "C")
        assert len(results_all) == 2

    def test_uses_instance_max_depth(self):
        """When max_depth is not passed, uses the finder's max_depth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={"r": [Edge(target_id="B", relationship="r")]},
                )
            )
            g.add(
                Node(
                    id="B",
                    title="B",
                    edges={"r": [Edge(target_id="C", relationship="r")]},
                )
            )
            g.add(Node(id="C", title="C"))

            # max_depth=1 on finder: should NOT find A->B->C
            finder = BoundedPathFinder(g, max_depth=1)
            results = finder.bounded_paths("A", "C")
            assert len(results) == 0

            # max_depth=2 on finder: should find A->B->C
            finder2 = BoundedPathFinder(g, max_depth=2)
            results2 = finder2.bounded_paths("A", "C")
            assert len(results2) == 1

    def test_path_results_have_edges(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.bounded_paths("A", "D", max_depth=5)

        assert len(results) == 1
        r = results[0]
        assert len(r.edges) == 3
        assert r.edges[0].source_id == "A"
        assert r.edges[0].target_id == "B"
        assert r.edges[2].source_id == "C"
        assert r.edges[2].target_id == "D"


# ---------------------------------------------------------------------------
# find_cycles tests
# ---------------------------------------------------------------------------


class TestFindCycles:
    """Tests for BoundedPathFinder.find_cycles."""

    def test_simple_cycle_a_b_c_a(self, cycle_graph):
        finder = BoundedPathFinder(cycle_graph)
        results = finder.find_cycles(node_id="A", edge_types=["blocks"])

        assert len(results) >= 1
        # Should find cycle A -> B -> C -> A
        cycle_nodes = None
        for r in results:
            if r.cycle == ["A", "B", "C", "A"]:
                cycle_nodes = r.cycle
                break
        assert cycle_nodes is not None, (
            f"Expected [A,B,C,A] in {[r.cycle for r in results]}"
        )

    def test_simple_two_node_cycle(self):
        """A -> B -> A (length 2 cycle)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={"blocks": [Edge(target_id="B", relationship="blocks")]},
                )
            )
            g.add(
                Node(
                    id="B",
                    title="B",
                    edges={"blocks": [Edge(target_id="A", relationship="blocks")]},
                )
            )

            finder = BoundedPathFinder(g)
            results = finder.find_cycles(node_id="A", edge_types=["blocks"])

            assert len(results) == 1
            assert results[0].cycle == ["A", "B", "A"]
            assert results[0].length == 2
            assert results[0].involves_node == "A"

    def test_longer_cycle(self):
        """A -> B -> C -> D -> A (length 4 cycle)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={"r": [Edge(target_id="B", relationship="r")]},
                )
            )
            g.add(
                Node(
                    id="B",
                    title="B",
                    edges={"r": [Edge(target_id="C", relationship="r")]},
                )
            )
            g.add(
                Node(
                    id="C",
                    title="C",
                    edges={"r": [Edge(target_id="D", relationship="r")]},
                )
            )
            g.add(
                Node(
                    id="D",
                    title="D",
                    edges={"r": [Edge(target_id="A", relationship="r")]},
                )
            )

            finder = BoundedPathFinder(g)
            results = finder.find_cycles(node_id="A", edge_types=["r"])

            assert len(results) == 1
            assert results[0].cycle == ["A", "B", "C", "D", "A"]
            assert results[0].length == 4

    def test_max_cycle_length(self, cycle_graph):
        finder = BoundedPathFinder(cycle_graph)

        # max_cycle_length=2 should NOT find the 3-edge cycle A->B->C->A
        results = finder.find_cycles(
            node_id="A", edge_types=["blocks"], max_cycle_length=2
        )
        assert len(results) == 0

        # max_cycle_length=3 should find it
        results = finder.find_cycles(
            node_id="A", edge_types=["blocks"], max_cycle_length=3
        )
        assert len(results) == 1

    def test_no_cycles_in_dag(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.find_cycles(node_id="A")

        assert results == []

    def test_find_all_cycles_in_graph(self, cycle_graph):
        """find_cycles without node_id finds all cycles."""
        finder = BoundedPathFinder(cycle_graph)
        results = finder.find_cycles(edge_types=["blocks"])

        # Should find at least one cycle (A->B->C->A)
        assert len(results) >= 1
        cycle_sets = [tuple(r.cycle) for r in results]
        # The cycle A->B->C->A should be present (possibly normalized differently)
        found_abc = False
        for cs in cycle_sets:
            nodes_in_cycle = set(cs)
            if {"A", "B", "C"} <= nodes_in_cycle:
                found_abc = True
                break
        assert found_abc

    def test_nonexistent_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        results = finder.find_cycles(node_id="MISSING")

        assert results == []

    def test_cycle_result_dataclass(self, cycle_graph):
        finder = BoundedPathFinder(cycle_graph)
        results = finder.find_cycles(
            node_id="A", edge_types=["blocks"], max_cycle_length=5
        )

        assert len(results) >= 1
        r = results[0]
        assert isinstance(r, CycleResult)
        assert r.involves_node == "A"
        assert r.edge_types == ["blocks"]
        assert r.length > 0

    def test_edge_type_filtering_no_match(self, cycle_graph):
        """No cycles when filtering by a non-existent edge type."""
        finder = BoundedPathFinder(cycle_graph)
        results = finder.find_cycles(node_id="A", edge_types=["nonexistent"])

        assert results == []


# ---------------------------------------------------------------------------
# reachable_set tests
# ---------------------------------------------------------------------------


class TestReachableSet:
    """Tests for BoundedPathFinder.reachable_set."""

    def test_all_reachable_linear(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        reachable = finder.reachable_set("A")

        assert reachable == {"B", "C", "D"}

    def test_depth_bound(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)

        r1 = finder.reachable_set("A", max_depth=1)
        assert r1 == {"B"}

        r2 = finder.reachable_set("A", max_depth=2)
        assert r2 == {"B", "C"}

        r3 = finder.reachable_set("A", max_depth=3)
        assert r3 == {"B", "C", "D"}

    def test_incoming_direction(self, linear_graph):
        """Incoming from D should find C, B, A."""
        finder = BoundedPathFinder(linear_graph)
        reachable = finder.reachable_set("D", direction="incoming")

        assert reachable == {"A", "B", "C"}

    def test_incoming_depth_bound(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)

        r1 = finder.reachable_set("D", direction="incoming", max_depth=1)
        assert r1 == {"C"}

    def test_disconnected(self, disconnected_graph):
        finder = BoundedPathFinder(disconnected_graph)

        reachable_a = finder.reachable_set("A")
        assert reachable_a == {"B"}

        reachable_c = finder.reachable_set("C")
        assert reachable_c == {"D"}

    def test_leaf_node(self, linear_graph):
        """D has no outgoing edges."""
        finder = BoundedPathFinder(linear_graph)
        reachable = finder.reachable_set("D")

        assert reachable == set()

    def test_nonexistent_node(self, linear_graph):
        finder = BoundedPathFinder(linear_graph)
        reachable = finder.reachable_set("MISSING")

        assert reachable == set()

    def test_edge_type_filtering(self, multi_edge_graph):
        finder = BoundedPathFinder(multi_edge_graph)

        # Only 'owns': A -> B -> C
        r_owns = finder.reachable_set("A", edge_types=["owns"])
        assert r_owns == {"B", "C"}

        # Only 'uses': A -> C
        r_uses = finder.reachable_set("A", edge_types=["uses"])
        assert r_uses == {"C"}

    def test_excludes_start_node(self, linear_graph):
        """reachable_set should not include the start node."""
        finder = BoundedPathFinder(linear_graph)
        reachable = finder.reachable_set("A")

        assert "A" not in reachable

    def test_handles_cycles(self, cycle_graph):
        """Cycles should not cause infinite loops."""
        finder = BoundedPathFinder(cycle_graph)
        reachable = finder.reachable_set("A")

        # A -> B -> C -> A (cycle, already visited), C -> D
        assert reachable == {"B", "C", "D"}

    def test_uses_instance_max_depth(self):
        """When max_depth is not passed, uses the finder's max_depth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={"r": [Edge(target_id="B", relationship="r")]},
                )
            )
            g.add(
                Node(
                    id="B",
                    title="B",
                    edges={"r": [Edge(target_id="C", relationship="r")]},
                )
            )
            g.add(Node(id="C", title="C"))

            finder = BoundedPathFinder(g, max_depth=1)
            assert finder.reachable_set("A") == {"B"}

            finder2 = BoundedPathFinder(g, max_depth=10)
            assert finder2.reachable_set("A") == {"B", "C"}


# ---------------------------------------------------------------------------
# Performance tests
# ---------------------------------------------------------------------------


class TestPerformance:
    """Verify bounded algorithms terminate quickly on dense graphs."""

    def test_bounded_paths_on_dense_graph(self):
        """
        Create a fully connected graph with 20 nodes.
        bounded_paths must terminate quickly without timeouts.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            n = 20
            node_ids = [f"n{i}" for i in range(n)]

            for i, nid in enumerate(node_ids):
                edges_list = []
                for j, tid in enumerate(node_ids):
                    if i != j:
                        edges_list.append(Edge(target_id=tid, relationship="connected"))
                g.add(
                    Node(
                        id=nid,
                        title=nid,
                        edges={"connected": edges_list},
                    )
                )

            finder = BoundedPathFinder(g, max_depth=3)

            start = time.monotonic()
            results = finder.bounded_paths(
                "n0", f"n{n - 1}", max_depth=3, max_results=50
            )
            elapsed = time.monotonic() - start

            assert len(results) > 0
            assert elapsed < 5.0, f"bounded_paths took {elapsed:.2f}s (expected < 5s)"

    def test_reachable_set_on_dense_graph(self):
        """reachable_set should handle dense graphs efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            n = 50
            node_ids = [f"n{i}" for i in range(n)]

            for i, nid in enumerate(node_ids):
                # Each node connects to next 5 nodes (circular)
                edges_list = []
                for offset in range(1, 6):
                    tid = node_ids[(i + offset) % n]
                    edges_list.append(Edge(target_id=tid, relationship="next"))
                g.add(
                    Node(
                        id=nid,
                        title=nid,
                        edges={"next": edges_list},
                    )
                )

            finder = BoundedPathFinder(g)

            start = time.monotonic()
            reachable = finder.reachable_set("n0", max_depth=10)
            elapsed = time.monotonic() - start

            # All 49 other nodes should be reachable
            assert len(reachable) == n - 1
            assert elapsed < 2.0, f"reachable_set took {elapsed:.2f}s (expected < 2s)"

    def test_find_cycles_bounded_on_dense(self):
        """find_cycles should terminate quickly with max_cycle_length bound."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            # Small ring: 0 -> 1 -> 2 -> ... -> 9 -> 0
            n = 10
            for i in range(n):
                nid = f"n{i}"
                tid = f"n{(i + 1) % n}"
                g.add(
                    Node(
                        id=nid,
                        title=nid,
                        edges={"next": [Edge(target_id=tid, relationship="next")]},
                    )
                )

            finder = BoundedPathFinder(g)

            start = time.monotonic()
            results = finder.find_cycles(
                node_id="n0", edge_types=["next"], max_cycle_length=10
            )
            elapsed = time.monotonic() - start

            # Should find the full ring cycle
            assert len(results) == 1
            assert results[0].length == 10
            assert elapsed < 2.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Additional edge case coverage."""

    def test_empty_graph(self, empty_graph):
        finder = BoundedPathFinder(empty_graph)

        assert finder.any_shortest("A", "B") is None
        assert finder.all_shortest("A", "B") == []
        assert finder.bounded_paths("A", "B") == []
        assert finder.find_cycles() == []
        assert finder.reachable_set("A") == set()

    def test_single_node_no_edges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(Node(id="solo", title="Solo Node"))

            finder = BoundedPathFinder(g)

            assert finder.any_shortest("solo", "solo") is not None
            assert finder.any_shortest("solo", "solo").length == 0  # type: ignore[union-attr]
            assert finder.reachable_set("solo") == set()
            assert finder.find_cycles(node_id="solo") == []

    def test_self_loop(self):
        """A node pointing to itself: A -> A."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={"self": [Edge(target_id="A", relationship="self")]},
                )
            )

            finder = BoundedPathFinder(g)

            # find_cycles should detect the self-loop
            results = finder.find_cycles(node_id="A", edge_types=["self"])
            assert len(results) == 1
            assert results[0].cycle == ["A", "A"]
            assert results[0].length == 1

    def test_multiple_edges_same_pair(self):
        """Multiple edge types between same nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            g = HtmlGraph(tmpdir, auto_load=False)
            g.add(
                Node(
                    id="A",
                    title="A",
                    edges={
                        "owns": [Edge(target_id="B", relationship="owns")],
                        "uses": [Edge(target_id="B", relationship="uses")],
                    },
                )
            )
            g.add(Node(id="B", title="B"))

            finder = BoundedPathFinder(g)

            # any_shortest without filter should find a path
            result = finder.any_shortest("A", "B")
            assert result is not None
            assert result.length == 1

            # bounded_paths with all edges might find two paths
            # (one via 'owns', one via 'uses')
            results = finder.bounded_paths("A", "B")
            assert len(results) >= 1
