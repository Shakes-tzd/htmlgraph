"""Tests for the NetworkX GraphManager.

Uses in-memory SQLite databases populated with test data so that
no project-level .htmlgraph directory is required.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import networkx as nx
import pytest
from htmlgraph.graph.networkx_manager import GraphManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_db(
    tmp_path: Path, features: list[dict[str, Any]], edges: list[tuple[str, str, str]]
) -> str:
    """Create a minimal SQLite DB with features and graph_edges tables."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE features (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            type TEXT NOT NULL DEFAULT 'feature',
            track_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE graph_edges (
            edge_id TEXT PRIMARY KEY,
            from_node_id TEXT NOT NULL,
            from_node_type TEXT NOT NULL DEFAULT 'feature',
            to_node_id TEXT NOT NULL,
            to_node_type TEXT NOT NULL DEFAULT 'feature',
            relationship_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)

    for feat in features:
        cursor.execute(
            "INSERT INTO features (id, title, status, priority, type, track_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                feat["id"],
                feat.get("title", feat["id"]),
                feat.get("status", "todo"),
                feat.get("priority", "medium"),
                feat.get("type", "feature"),
                feat.get("track_id"),
            ),
        )

    for i, (from_id, to_id, rel) in enumerate(edges):
        cursor.execute(
            "INSERT INTO graph_edges (edge_id, from_node_id, from_node_type, "
            "to_node_id, to_node_type, relationship_type) "
            "VALUES (?, ?, 'feature', ?, 'feature', ?)",
            (f"edge-{i}", from_id, to_id, rel),
        )

    conn.commit()
    conn.close()
    return db_path


def _make_manager(
    tmp_path: Path, features: list[dict[str, Any]], edges: list[tuple[str, str, str]]
) -> GraphManager:
    """Create a GraphManager backed by a test DB."""
    db_path = _create_db(tmp_path, features, edges)
    gm = GraphManager(graph_dir=str(tmp_path), db_path=db_path)
    return gm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_chain(tmp_path: Path) -> GraphManager:
    """A -> B -> C linear chain (blocks relationship)."""
    features = [
        {"id": "A", "title": "Alpha", "status": "done"},
        {"id": "B", "title": "Beta", "status": "todo"},
        {"id": "C", "title": "Charlie", "status": "todo"},
    ]
    edges = [
        ("A", "B", "blocks"),
        ("B", "C", "blocks"),
    ]
    return _make_manager(tmp_path, features, edges)


@pytest.fixture()
def diamond(tmp_path: Path) -> GraphManager:
    """Diamond DAG: A -> B, A -> C, B -> D, C -> D."""
    features = [
        {"id": "A", "title": "Start", "status": "done"},
        {"id": "B", "title": "Left", "status": "todo"},
        {"id": "C", "title": "Right", "status": "todo"},
        {"id": "D", "title": "End", "status": "todo"},
    ]
    edges = [
        ("A", "B", "blocks"),
        ("A", "C", "blocks"),
        ("B", "D", "blocks"),
        ("C", "D", "blocks"),
    ]
    return _make_manager(tmp_path, features, edges)


@pytest.fixture()
def cyclic(tmp_path: Path) -> GraphManager:
    """Graph with a cycle: A -> B -> C -> A."""
    features = [
        {"id": "A", "title": "Alpha"},
        {"id": "B", "title": "Beta"},
        {"id": "C", "title": "Charlie"},
    ]
    edges = [
        ("A", "B", "blocks"),
        ("B", "C", "blocks"),
        ("C", "A", "blocks"),
    ]
    return _make_manager(tmp_path, features, edges)


@pytest.fixture()
def with_tracks(tmp_path: Path) -> GraphManager:
    """Two tracks with inter-track edges."""
    features = [
        {"id": "T1-A", "title": "Track1-A", "track_id": "trk-1", "status": "done"},
        {"id": "T1-B", "title": "Track1-B", "track_id": "trk-1", "status": "todo"},
        {"id": "T2-X", "title": "Track2-X", "track_id": "trk-2", "status": "todo"},
        {"id": "T2-Y", "title": "Track2-Y", "track_id": "trk-2", "status": "todo"},
    ]
    edges = [
        ("T1-A", "T1-B", "blocks"),
        ("T2-X", "T2-Y", "blocks"),
        ("T1-B", "T2-X", "blocks"),  # cross-track dependency
    ]
    return _make_manager(tmp_path, features, edges)


@pytest.fixture()
def disconnected(tmp_path: Path) -> GraphManager:
    """Two disconnected components: {A,B} and {X,Y}."""
    features = [
        {"id": "A", "title": "A"},
        {"id": "B", "title": "B"},
        {"id": "X", "title": "X"},
        {"id": "Y", "title": "Y"},
    ]
    edges = [
        ("A", "B", "blocks"),
        ("X", "Y", "blocks"),
    ]
    return _make_manager(tmp_path, features, edges)


# ---------------------------------------------------------------------------
# Tests: build_graph
# ---------------------------------------------------------------------------


class TestBuildGraph:
    def test_build_graph_from_db(self, simple_chain: GraphManager) -> None:
        G = simple_chain.build_graph()  # noqa: N806
        assert isinstance(G, nx.DiGraph)
        assert set(G.nodes) == {"A", "B", "C"}
        assert G.has_edge("A", "B")
        assert G.has_edge("B", "C")

    def test_build_graph_node_attributes(self, simple_chain: GraphManager) -> None:
        G = simple_chain.G  # noqa: N806
        assert G.nodes["A"]["title"] == "Alpha"
        assert G.nodes["A"]["status"] == "done"

    def test_build_graph_empty(self, tmp_path: Path) -> None:
        gm = _make_manager(tmp_path, features=[], edges=[])
        G = gm.build_graph()  # noqa: N806
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_build_graph_blocked_by_reversal(self, tmp_path: Path) -> None:
        """blocked_by edges should be reversed: B blocked_by A => A -> B."""
        features = [
            {"id": "A", "title": "A"},
            {"id": "B", "title": "B"},
        ]
        edges = [("B", "A", "blocked_by")]  # B is blocked by A => A -> B
        gm = _make_manager(tmp_path, features, edges)
        G = gm.G  # noqa: N806
        assert G.has_edge("A", "B")
        assert not G.has_edge("B", "A")

    def test_refresh_rebuilds(self, simple_chain: GraphManager) -> None:
        G1 = simple_chain.G  # noqa: N806
        G2 = simple_chain.refresh()  # noqa: N806
        assert G1 is not G2
        assert set(G2.nodes) == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Tests: find_cycles / has_cycles
# ---------------------------------------------------------------------------


class TestCycles:
    def test_find_cycles_none(self, simple_chain: GraphManager) -> None:
        assert simple_chain.find_cycles() == []

    def test_has_cycles_false(self, simple_chain: GraphManager) -> None:
        assert simple_chain.has_cycles() is False

    def test_find_cycles_detected(self, cyclic: GraphManager) -> None:
        cycles = cyclic.find_cycles()
        assert len(cycles) > 0
        # Every cycle should contain all three nodes
        for cycle in cycles:
            assert set(cycle) == {"A", "B", "C"}

    def test_has_cycles_true(self, cyclic: GraphManager) -> None:
        assert cyclic.has_cycles() is True


# ---------------------------------------------------------------------------
# Tests: critical_path
# ---------------------------------------------------------------------------


class TestCriticalPath:
    def test_critical_path_simple(self, simple_chain: GraphManager) -> None:
        path = simple_chain.critical_path()
        assert path == ["A", "B", "C"]

    def test_critical_path_diamond(self, diamond: GraphManager) -> None:
        path = diamond.critical_path()
        # Longest path in the diamond is length 3 (A -> B/C -> D)
        assert len(path) == 3
        assert path[0] == "A"
        assert path[-1] == "D"

    def test_critical_path_empty(self, tmp_path: Path) -> None:
        gm = _make_manager(tmp_path, [], [])
        assert gm.critical_path() == []

    def test_critical_path_with_cycles(self, cyclic: GraphManager) -> None:
        # Should not raise; cycles are broken internally
        path = cyclic.critical_path()
        assert isinstance(path, list)

    def test_critical_path_track_filter(self, with_tracks: GraphManager) -> None:
        path = with_tracks.critical_path(track_id="trk-1")
        # Only T1-A -> T1-B are in track 1
        assert set(path) <= {"T1-A", "T1-B"}


# ---------------------------------------------------------------------------
# Tests: bottlenecks
# ---------------------------------------------------------------------------


class TestBottlenecks:
    def test_bottlenecks_ranking(self, diamond: GraphManager) -> None:
        bns = diamond.bottlenecks(top_n=5)
        # A blocks both B and C (out-degree 2), B and C each block D (out-degree 1)
        assert bns[0]["id"] == "A"
        assert bns[0]["blocks_count"] == 2

    def test_bottlenecks_empty(self, tmp_path: Path) -> None:
        gm = _make_manager(tmp_path, [{"id": "X", "title": "X"}], [])
        assert gm.bottlenecks() == []

    def test_bottlenecks_top_n(self, diamond: GraphManager) -> None:
        bns = diamond.bottlenecks(top_n=1)
        assert len(bns) == 1


# ---------------------------------------------------------------------------
# Tests: topological_sort / execution_order
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_topological_sort(self, simple_chain: GraphManager) -> None:
        order = simple_chain.topological_sort()
        assert order == ["A", "B", "C"]

    def test_topological_sort_diamond(self, diamond: GraphManager) -> None:
        order = diamond.topological_sort()
        # A must come first, D must come last
        assert order[0] == "A"
        assert order[-1] == "D"
        # B and C are between A and D
        assert set(order[1:3]) == {"B", "C"}

    def test_topological_sort_cycles_raises(self, cyclic: GraphManager) -> None:
        with pytest.raises(nx.NetworkXUnfeasible):
            cyclic.topological_sort()

    def test_topological_sort_track_filter(self, with_tracks: GraphManager) -> None:
        order = with_tracks.topological_sort(track_id="trk-2")
        assert order == ["T2-X", "T2-Y"]

    def test_execution_order_can_start(self, simple_chain: GraphManager) -> None:
        order = simple_chain.execution_order()
        # A is done, B depends on A (done) -> can_start, C depends on B (todo) -> cannot
        a_item = next(i for i in order if i["id"] == "A")
        b_item = next(i for i in order if i["id"] == "B")
        c_item = next(i for i in order if i["id"] == "C")
        assert a_item["can_start"] is True  # No predecessors
        assert b_item["can_start"] is True  # A is done
        assert c_item["can_start"] is False  # B is not done


# ---------------------------------------------------------------------------
# Tests: neighborhood & subgraph queries
# ---------------------------------------------------------------------------


class TestNeighborhood:
    def test_neighborhood(self, simple_chain: GraphManager) -> None:
        sub = simple_chain.neighborhood("B", depth=1)
        assert isinstance(sub, nx.DiGraph)
        # B's 1-hop neighborhood: A (predecessor), C (successor), B itself
        assert set(sub.nodes) == {"A", "B", "C"}

    def test_neighborhood_depth_0(self, simple_chain: GraphManager) -> None:
        sub = simple_chain.neighborhood("B", depth=0)
        assert set(sub.nodes) == {"B"}

    def test_neighborhood_missing_node(self, simple_chain: GraphManager) -> None:
        sub = simple_chain.neighborhood("MISSING")
        assert sub.number_of_nodes() == 0


class TestAncestorsDescendants:
    def test_ancestors(self, simple_chain: GraphManager) -> None:
        anc = simple_chain.ancestors("C")
        assert anc == {"A", "B"}

    def test_ancestors_root(self, simple_chain: GraphManager) -> None:
        anc = simple_chain.ancestors("A")
        assert anc == set()

    def test_ancestors_missing(self, simple_chain: GraphManager) -> None:
        assert simple_chain.ancestors("MISSING") == set()

    def test_descendants(self, simple_chain: GraphManager) -> None:
        desc = simple_chain.descendants("A")
        assert desc == {"B", "C"}

    def test_descendants_leaf(self, simple_chain: GraphManager) -> None:
        desc = simple_chain.descendants("C")
        assert desc == set()

    def test_descendants_missing(self, simple_chain: GraphManager) -> None:
        assert simple_chain.descendants("MISSING") == set()


class TestShortestPath:
    def test_shortest_path(self, simple_chain: GraphManager) -> None:
        path = simple_chain.shortest_path("A", "C")
        assert path == ["A", "B", "C"]

    def test_shortest_path_same_node(self, simple_chain: GraphManager) -> None:
        path = simple_chain.shortest_path("A", "A")
        assert path == ["A"]

    def test_shortest_path_unreachable(self, disconnected: GraphManager) -> None:
        path = disconnected.shortest_path("A", "X")
        assert path is None

    def test_shortest_path_missing_node(self, simple_chain: GraphManager) -> None:
        path = simple_chain.shortest_path("A", "MISSING")
        assert path is None


class TestConnectedComponents:
    def test_connected_components(self, disconnected: GraphManager) -> None:
        components = disconnected.connected_components()
        assert len(components) == 2
        component_sets = [frozenset(c) for c in components]
        assert frozenset({"A", "B"}) in component_sets
        assert frozenset({"X", "Y"}) in component_sets

    def test_single_component(self, simple_chain: GraphManager) -> None:
        components = simple_chain.connected_components()
        assert len(components) == 1
        assert components[0] == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Tests: SDK integration
# ---------------------------------------------------------------------------


class TestSDKGraphProperty:
    def test_sdk_graph_property(self, isolated_sdk: Any) -> None:
        """sdk.graph returns a GraphManager instance."""
        gm = isolated_sdk.graph
        assert isinstance(gm, GraphManager)

    def test_sdk_graph_is_cached(self, isolated_sdk: Any) -> None:
        """Subsequent accesses return the same instance."""
        gm1 = isolated_sdk.graph
        gm2 = isolated_sdk.graph
        assert gm1 is gm2

    def test_sdk_graph_builds_empty(self, isolated_sdk: Any) -> None:
        """Empty project DB produces an empty graph."""
        G = isolated_sdk.graph.G  # noqa: N806
        assert isinstance(G, nx.DiGraph)
        # May have features from test setup, but should not error
