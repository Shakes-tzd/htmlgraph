"""
Tests for GraphQueryComposer - relationship composition with attribute filtering.

Tests cover:
- Simple attribute filtering (equivalent to QueryBuilder)
- Single-hop traverse via relationship
- Traverse + filter combinations
- Filter + traverse combinations
- traverse_recursive with depth limit
- reachable_from starting at specific node
- blocked_by_chain convenience method
- dependency_chain convenience method
- count(), first(), ids() execution methods
- Empty results
- Chaining multiple traverse + filter stages
"""

import tempfile

import pytest
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node
from htmlgraph.query_composer import GraphQueryComposer, QueryStage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def graph_dir():
    """Provide a temporary directory for graph files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def simple_graph(graph_dir: str) -> HtmlGraph:
    """Create a simple graph with various statuses and priorities."""
    graph = HtmlGraph(graph_dir, auto_load=False)

    graph.add(
        Node(
            id="feat-001",
            title="Auth System",
            type="feature",
            status="todo",
            priority="high",
        )
    )
    graph.add(
        Node(
            id="feat-002",
            title="Database Layer",
            type="feature",
            status="in-progress",
            priority="high",
        )
    )
    graph.add(
        Node(
            id="feat-003",
            title="UI Dashboard",
            type="feature",
            status="blocked",
            priority="medium",
        )
    )
    graph.add(
        Node(
            id="feat-004",
            title="Logging",
            type="feature",
            status="done",
            priority="low",
        )
    )
    graph.add(
        Node(
            id="feat-005",
            title="Search Engine",
            type="feature",
            status="todo",
            priority="critical",
        )
    )

    return graph


@pytest.fixture
def linked_graph(graph_dir: str) -> HtmlGraph:
    """Create a graph with edge relationships for traversal tests.

    Graph structure (blocked_by edges point from blocker to blocked):
        feat-A --blocked_by--> feat-B --blocked_by--> feat-C
        feat-A --blocked_by--> feat-D
        feat-D --blocked_by--> feat-E

    So feat-A is blocked by B and D.
    feat-B is blocked by C.
    feat-D is blocked by E.
    """
    graph = HtmlGraph(graph_dir, auto_load=False)

    graph.add(
        Node(
            id="feat-A",
            title="Feature A",
            type="feature",
            status="blocked",
            priority="high",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-B", relationship="blocked_by"),
                    Edge(target_id="feat-D", relationship="blocked_by"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="feat-B",
            title="Feature B",
            type="feature",
            status="in-progress",
            priority="high",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-C", relationship="blocked_by"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="feat-C",
            title="Feature C",
            type="feature",
            status="todo",
            priority="medium",
        )
    )
    graph.add(
        Node(
            id="feat-D",
            title="Feature D",
            type="feature",
            status="todo",
            priority="low",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-E", relationship="blocked_by"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="feat-E",
            title="Feature E",
            type="feature",
            status="done",
            priority="critical",
        )
    )

    return graph


@pytest.fixture
def depends_graph(graph_dir: str) -> HtmlGraph:
    """Create a graph with depends_on relationships.

    Graph structure:
        root --depends_on--> mid-1 --depends_on--> leaf-1
        root --depends_on--> mid-2 --depends_on--> leaf-2
        mid-1 --depends_on--> leaf-2   (shared dependency)
    """
    graph = HtmlGraph(graph_dir, auto_load=False)

    graph.add(
        Node(
            id="root",
            title="Root Feature",
            type="feature",
            status="todo",
            priority="high",
            edges={
                "depends_on": [
                    Edge(target_id="mid-1", relationship="depends_on"),
                    Edge(target_id="mid-2", relationship="depends_on"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="mid-1",
            title="Mid Feature 1",
            type="feature",
            status="in-progress",
            priority="medium",
            edges={
                "depends_on": [
                    Edge(target_id="leaf-1", relationship="depends_on"),
                    Edge(target_id="leaf-2", relationship="depends_on"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="mid-2",
            title="Mid Feature 2",
            type="feature",
            status="blocked",
            priority="high",
            edges={
                "depends_on": [
                    Edge(target_id="leaf-2", relationship="depends_on"),
                ]
            },
        )
    )
    graph.add(
        Node(
            id="leaf-1",
            title="Leaf Feature 1",
            type="feature",
            status="done",
            priority="low",
        )
    )
    graph.add(
        Node(
            id="leaf-2",
            title="Leaf Feature 2",
            type="feature",
            status="done",
            priority="medium",
        )
    )

    return graph


# ---------------------------------------------------------------------------
# QueryStage dataclass tests
# ---------------------------------------------------------------------------


class TestQueryStage:
    """Tests for the QueryStage dataclass."""

    def test_stage_creation_filter(self):
        stage = QueryStage(stage_type="filter", params={"conditions": []})
        assert stage.stage_type == "filter"
        assert stage.params == {"conditions": []}

    def test_stage_creation_traverse(self):
        stage = QueryStage(
            stage_type="traverse",
            params={"relationship": "blocked_by", "direction": "outgoing"},
        )
        assert stage.stage_type == "traverse"
        assert stage.params["relationship"] == "blocked_by"

    def test_stage_default_params(self):
        stage = QueryStage(stage_type="filter")
        assert stage.params == {}


# ---------------------------------------------------------------------------
# Simple attribute filter tests
# ---------------------------------------------------------------------------


class TestSimpleAttributeFilter:
    """Test attribute filtering (equivalent to QueryBuilder)."""

    def test_where_equality(self, simple_graph: HtmlGraph):
        """Filter by exact attribute value."""
        composer = GraphQueryComposer(simple_graph)
        results = composer.where("status", "todo").execute()

        ids = {n.id for n in results}
        assert ids == {"feat-001", "feat-005"}

    def test_where_and_combination(self, simple_graph: HtmlGraph):
        """Filter with AND condition."""
        composer = GraphQueryComposer(simple_graph)
        results = composer.where("status", "todo").and_("priority", "high").execute()

        assert len(results) == 1
        assert results[0].id == "feat-001"

    def test_where_or_combination(self, simple_graph: HtmlGraph):
        """Filter with OR condition."""
        composer = GraphQueryComposer(simple_graph)
        results = composer.where("status", "todo").or_("status", "blocked").execute()

        ids = {n.id for n in results}
        assert ids == {"feat-001", "feat-003", "feat-005"}

    def test_no_conditions_returns_all(self, simple_graph: HtmlGraph):
        """With no stages, all nodes are returned."""
        composer = GraphQueryComposer(simple_graph)
        results = composer.execute()
        assert len(results) == 5

    def test_filter_no_matches(self, simple_graph: HtmlGraph):
        """Filter that matches nothing returns empty list."""
        composer = GraphQueryComposer(simple_graph)
        results = composer.where("status", "nonexistent").execute()
        assert results == []


# ---------------------------------------------------------------------------
# Traverse single hop tests
# ---------------------------------------------------------------------------


class TestTraverseSingleHop:
    """Test single-hop edge traversal."""

    def test_traverse_outgoing(self, linked_graph: HtmlGraph):
        """Traverse outgoing blocked_by edges from feat-A."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        ids = {n.id for n in results}
        assert ids == {"feat-B", "feat-D"}

    def test_traverse_incoming(self, linked_graph: HtmlGraph):
        """Traverse incoming blocked_by edges to feat-B (who is blocked by feat-B?)."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-B")
            .traverse("blocked_by", direction="incoming")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A has an outgoing blocked_by edge to feat-B,
        # so incoming to feat-B means feat-A
        assert ids == {"feat-A"}

    def test_traverse_both_directions(self, linked_graph: HtmlGraph):
        """Traverse both directions from feat-B."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-B")
            .traverse("blocked_by", direction="both")
            .execute()
        )

        ids = {n.id for n in results}
        # outgoing: feat-C, incoming: feat-A
        assert ids == {"feat-A", "feat-C"}

    def test_traverse_no_edges(self, linked_graph: HtmlGraph):
        """Traverse from a node with no edges of that type."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-E")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        assert results == []


# ---------------------------------------------------------------------------
# Traverse + filter combination tests
# ---------------------------------------------------------------------------


class TestTraverseThenFilter:
    """Test traversing then filtering the result."""

    def test_traverse_then_filter_status(self, linked_graph: HtmlGraph):
        """Traverse from feat-A, then filter by status."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse("blocked_by", direction="outgoing")
            .where("status", "todo")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-B is in-progress, feat-D is todo
        assert ids == {"feat-D"}

    def test_traverse_then_filter_priority(self, linked_graph: HtmlGraph):
        """Traverse from feat-A, then filter by priority."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse("blocked_by", direction="outgoing")
            .where("priority", "high")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-B is high priority, feat-D is low
        assert ids == {"feat-B"}


# ---------------------------------------------------------------------------
# Filter + traverse combination tests
# ---------------------------------------------------------------------------


class TestFilterThenTraverse:
    """Test filtering first then traversing from matches."""

    def test_filter_then_traverse(self, linked_graph: HtmlGraph):
        """Filter to blocked nodes, then traverse their blocked_by edges."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("status", "blocked")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        ids = {n.id for n in results}
        # Only feat-A is blocked. Its blocked_by targets are feat-B and feat-D.
        assert ids == {"feat-B", "feat-D"}

    def test_filter_multiple_then_traverse(self, linked_graph: HtmlGraph):
        """Filter to multiple nodes, then traverse."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("status", "in-progress")
            .or_("status", "blocked")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A (blocked) -> blocked_by -> feat-B, feat-D
        # feat-B (in-progress) -> blocked_by -> feat-C
        assert ids == {"feat-B", "feat-C", "feat-D"}


# ---------------------------------------------------------------------------
# traverse_recursive tests
# ---------------------------------------------------------------------------


class TestTraverseRecursive:
    """Test recursive edge traversal."""

    def test_recursive_from_single_node(self, linked_graph: HtmlGraph):
        """Recursively traverse blocked_by from feat-A."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse_recursive("blocked_by", direction="outgoing", max_depth=10)
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A -> B, D; B -> C; D -> E
        assert ids == {"feat-B", "feat-C", "feat-D", "feat-E"}

    def test_recursive_with_depth_limit(self, linked_graph: HtmlGraph):
        """Recursive traversal respects depth limit."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse_recursive("blocked_by", direction="outgoing", max_depth=1)
            .execute()
        )

        ids = {n.id for n in results}
        # depth=1: only direct neighbors of feat-A
        assert ids == {"feat-B", "feat-D"}

    def test_recursive_with_depth_two(self, linked_graph: HtmlGraph):
        """Recursive traversal at depth 2."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse_recursive("blocked_by", direction="outgoing", max_depth=2)
            .execute()
        )

        ids = {n.id for n in results}
        # depth 1: B, D; depth 2: C (from B), E (from D)
        assert ids == {"feat-B", "feat-C", "feat-D", "feat-E"}

    def test_recursive_no_cycles(self, graph_dir: str):
        """Recursive traversal handles cycles correctly."""
        graph = HtmlGraph(graph_dir, auto_load=False)

        # Create a cycle: A -> B -> C -> A
        graph.add(
            Node(
                id="cyc-A",
                title="Cycle A",
                status="todo",
                priority="high",
                edges={
                    "depends_on": [
                        Edge(target_id="cyc-B", relationship="depends_on"),
                    ]
                },
            )
        )
        graph.add(
            Node(
                id="cyc-B",
                title="Cycle B",
                status="todo",
                priority="medium",
                edges={
                    "depends_on": [
                        Edge(target_id="cyc-C", relationship="depends_on"),
                    ]
                },
            )
        )
        graph.add(
            Node(
                id="cyc-C",
                title="Cycle C",
                status="todo",
                priority="low",
                edges={
                    "depends_on": [
                        Edge(target_id="cyc-A", relationship="depends_on"),
                    ]
                },
            )
        )

        composer = GraphQueryComposer(graph)
        results = (
            composer.where("id", "cyc-A")
            .traverse_recursive("depends_on", direction="outgoing", max_depth=10)
            .execute()
        )

        ids = {n.id for n in results}
        # Should find B and C but not re-visit A (it was in working set)
        assert ids == {"cyc-B", "cyc-C"}


# ---------------------------------------------------------------------------
# reachable_from tests
# ---------------------------------------------------------------------------


class TestReachableFrom:
    """Test reachable_from starting at specific node."""

    def test_reachable_from_root(self, depends_graph: HtmlGraph):
        """Find all nodes reachable from root via depends_on."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from("root", "depends_on").execute()

        ids = {n.id for n in results}
        # root -> mid-1, mid-2; mid-1 -> leaf-1, leaf-2; mid-2 -> leaf-2
        assert ids == {"mid-1", "mid-2", "leaf-1", "leaf-2"}

    def test_reachable_from_mid(self, depends_graph: HtmlGraph):
        """Reachable from mid-1."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from("mid-1", "depends_on").execute()

        ids = {n.id for n in results}
        # mid-1 -> leaf-1, leaf-2
        assert ids == {"leaf-1", "leaf-2"}

    def test_reachable_from_leaf(self, depends_graph: HtmlGraph):
        """Reachable from leaf node (no outgoing edges)."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from("leaf-1", "depends_on").execute()

        assert results == []

    def test_reachable_from_nonexistent(self, depends_graph: HtmlGraph):
        """Reachable from nonexistent node returns empty."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from("nonexistent", "depends_on").execute()

        assert results == []

    def test_reachable_from_with_filter(self, depends_graph: HtmlGraph):
        """Reachable from root, then filter by status."""
        composer = GraphQueryComposer(depends_graph)
        results = (
            composer.reachable_from("root", "depends_on")
            .where("status", "done")
            .execute()
        )

        ids = {n.id for n in results}
        # leaf-1 and leaf-2 are done, mid-1 is in-progress, mid-2 is blocked
        assert ids == {"leaf-1", "leaf-2"}

    def test_reachable_from_with_depth_limit(self, depends_graph: HtmlGraph):
        """Reachable from root with depth limit."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from("root", "depends_on", max_depth=1).execute()

        ids = {n.id for n in results}
        # Only direct dependencies: mid-1, mid-2
        assert ids == {"mid-1", "mid-2"}

    def test_reachable_from_incoming(self, depends_graph: HtmlGraph):
        """Reachable via incoming edges (who depends on leaf-2?)."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.reachable_from(
            "leaf-2", "depends_on", direction="incoming"
        ).execute()

        ids = {n.id for n in results}
        # leaf-2 is depended on by mid-1 and mid-2.
        # mid-1 is depended on by root. mid-2 is depended on by root.
        assert ids == {"mid-1", "mid-2", "root"}


# ---------------------------------------------------------------------------
# Convenience method tests
# ---------------------------------------------------------------------------


class TestConvenienceMethods:
    """Test blocked_by_chain and dependency_chain."""

    def test_blocked_by_chain(self, linked_graph: HtmlGraph):
        """Find the full blocked_by chain from feat-A."""
        composer = GraphQueryComposer(linked_graph)
        results = composer.blocked_by_chain("feat-A").execute()

        ids = {n.id for n in results}
        # feat-A -> B, D; B -> C; D -> E
        assert ids == {"feat-B", "feat-C", "feat-D", "feat-E"}

    def test_blocked_by_chain_leaf(self, linked_graph: HtmlGraph):
        """Blocked-by chain from a leaf node."""
        composer = GraphQueryComposer(linked_graph)
        results = composer.blocked_by_chain("feat-E").execute()

        assert results == []

    def test_dependency_chain(self, depends_graph: HtmlGraph):
        """Find the full dependency chain from root."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.dependency_chain("root").execute()

        ids = {n.id for n in results}
        assert ids == {"mid-1", "mid-2", "leaf-1", "leaf-2"}

    def test_dependency_chain_with_filter(self, depends_graph: HtmlGraph):
        """Dependency chain from root, filtered to done items."""
        composer = GraphQueryComposer(depends_graph)
        results = composer.dependency_chain("root").where("status", "done").execute()

        ids = {n.id for n in results}
        assert ids == {"leaf-1", "leaf-2"}


# ---------------------------------------------------------------------------
# Execution method tests
# ---------------------------------------------------------------------------


class TestExecutionMethods:
    """Test count(), first(), ids()."""

    def test_count(self, simple_graph: HtmlGraph):
        """Count matching nodes."""
        composer = GraphQueryComposer(simple_graph)
        assert composer.where("status", "todo").count() == 2

    def test_count_zero(self, simple_graph: HtmlGraph):
        """Count with no matches."""
        composer = GraphQueryComposer(simple_graph)
        assert composer.where("status", "nonexistent").count() == 0

    def test_first_returns_node(self, simple_graph: HtmlGraph):
        """first() returns a Node."""
        composer = GraphQueryComposer(simple_graph)
        result = composer.where("status", "done").first()

        assert result is not None
        assert result.id == "feat-004"
        assert result.status == "done"

    def test_first_returns_none(self, simple_graph: HtmlGraph):
        """first() returns None when no matches."""
        composer = GraphQueryComposer(simple_graph)
        result = composer.where("status", "nonexistent").first()

        assert result is None

    def test_ids(self, simple_graph: HtmlGraph):
        """ids() returns list of node IDs."""
        composer = GraphQueryComposer(simple_graph)
        result = composer.where("status", "todo").ids()

        assert set(result) == {"feat-001", "feat-005"}

    def test_ids_empty(self, simple_graph: HtmlGraph):
        """ids() returns empty list when no matches."""
        composer = GraphQueryComposer(simple_graph)
        result = composer.where("status", "nonexistent").ids()

        assert result == []


# ---------------------------------------------------------------------------
# Empty results tests
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Test edge cases with empty results."""

    def test_empty_graph(self, graph_dir: str):
        """Composer on empty graph returns empty results."""
        graph = HtmlGraph(graph_dir, auto_load=False)
        composer = GraphQueryComposer(graph)
        results = composer.where("status", "todo").execute()

        assert results == []

    def test_traverse_empty_set(self, linked_graph: HtmlGraph):
        """Traverse from empty working set returns empty."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("status", "nonexistent").traverse("blocked_by").execute()
        )

        assert results == []

    def test_recursive_empty_set(self, linked_graph: HtmlGraph):
        """Recursive traverse from empty set returns empty."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("status", "nonexistent")
            .traverse_recursive("blocked_by")
            .execute()
        )

        assert results == []


# ---------------------------------------------------------------------------
# Chaining multiple traverse + filter stages
# ---------------------------------------------------------------------------


class TestMultipleStageChaining:
    """Test chaining multiple traverse and filter stages."""

    def test_filter_traverse_filter(self, linked_graph: HtmlGraph):
        """Filter -> traverse -> filter pipeline."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("status", "blocked")
            .traverse("blocked_by", direction="outgoing")
            .where("priority", "high")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A (blocked) -> B (high), D (low). Filter high -> B only.
        assert ids == {"feat-B"}

    def test_traverse_traverse(self, linked_graph: HtmlGraph):
        """Two consecutive traversals."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse("blocked_by", direction="outgoing")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A -> (B, D) -> B's blocked_by -> C; D's blocked_by -> E
        assert ids == {"feat-C", "feat-E"}

    def test_traverse_filter_traverse(self, linked_graph: HtmlGraph):
        """Traverse -> filter -> traverse pipeline."""
        composer = GraphQueryComposer(linked_graph)
        results = (
            composer.where("id", "feat-A")
            .traverse("blocked_by", direction="outgoing")
            .where("status", "todo")
            .traverse("blocked_by", direction="outgoing")
            .execute()
        )

        ids = {n.id for n in results}
        # feat-A -> (B in-progress, D todo)
        # filter todo -> D
        # D -> blocked_by -> E
        assert ids == {"feat-E"}

    def test_reachable_then_filter(self, depends_graph: HtmlGraph):
        """Reachable from + filter pipeline."""
        composer = GraphQueryComposer(depends_graph)
        results = (
            composer.reachable_from("root", "depends_on")
            .where("priority", "medium")
            .execute()
        )

        ids = {n.id for n in results}
        # Reachable: mid-1(medium), mid-2(high), leaf-1(low), leaf-2(medium)
        # Filter medium: mid-1, leaf-2
        assert ids == {"mid-1", "leaf-2"}

    def test_complex_chain(self, depends_graph: HtmlGraph):
        """Complex multi-stage pipeline."""
        composer = GraphQueryComposer(depends_graph)
        results = (
            composer.reachable_from("root", "depends_on")
            .where("status", "done")
            .and_("priority", "medium")
            .execute()
        )

        ids = {n.id for n in results}
        # Reachable from root: mid-1, mid-2, leaf-1, leaf-2
        # status=done AND priority=medium -> leaf-2
        assert ids == {"leaf-2"}
