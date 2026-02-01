"""
Tests for graph pattern matching engine.

Tests the GraphPattern builder, PatternMatcher engine, and MatchResult
dataclass for structural pattern matching across HtmlGraph instances.
"""

import tempfile

import pytest
from htmlgraph.edge_index import EdgeRef
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node
from htmlgraph.pattern_matcher import (
    EdgePattern,
    GraphPattern,
    MatchResult,
    NodePattern,
)


@pytest.fixture
def graph_with_edges():
    """
    Create a temporary graph with nodes and edges for pattern matching tests.

    Graph structure:
        feat-001 (feature, blocked, high)
            --blocked_by--> feat-002 (feature, in-progress, high)
            --related--> feat-003 (task, todo, medium)

        feat-002 (feature, in-progress, high)
            --blocked_by--> feat-004 (feature, done, critical)

        feat-003 (task, todo, medium)
            --related--> feat-001 (feature, blocked, high)

        feat-005 (feature, todo, low)
            (no edges)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        node1 = Node(
            id="feat-001",
            title="Auth Feature",
            type="feature",
            status="blocked",
            priority="high",
            properties={"effort": 8, "team": "backend"},
            edges={
                "blocked_by": [
                    Edge(target_id="feat-002", relationship="blocked_by"),
                ],
                "related": [
                    Edge(target_id="feat-003", relationship="related"),
                ],
            },
        )
        node2 = Node(
            id="feat-002",
            title="Database Migration",
            type="feature",
            status="in-progress",
            priority="high",
            properties={"effort": 5, "team": "backend"},
            edges={
                "blocked_by": [
                    Edge(target_id="feat-004", relationship="blocked_by"),
                ],
            },
        )
        node3 = Node(
            id="feat-003",
            title="Write Tests",
            type="task",
            status="todo",
            priority="medium",
            properties={"effort": 3, "team": "qa"},
            edges={
                "related": [
                    Edge(target_id="feat-001", relationship="related"),
                ],
            },
        )
        node4 = Node(
            id="feat-004",
            title="Infrastructure Setup",
            type="feature",
            status="done",
            priority="critical",
            properties={"effort": 13, "team": "infra"},
        )
        node5 = Node(
            id="feat-005",
            title="Nice To Have",
            type="feature",
            status="todo",
            priority="low",
            properties={"effort": 1},
        )

        graph.add(node1)
        graph.add(node2)
        graph.add(node3)
        graph.add(node4)
        graph.add(node5)

        yield graph


class TestNodePattern:
    """Tests for the NodePattern dataclass."""

    def test_matches_any_node(self, graph_with_edges: HtmlGraph):
        """A pattern with no label or filters matches any node."""
        np = NodePattern(variable="x")
        node = graph_with_edges.get("feat-001")
        assert node is not None
        assert np.matches(node) is True

    def test_matches_label(self, graph_with_edges: HtmlGraph):
        """A pattern with a label filters by node type."""
        np = NodePattern(variable="x", label="feature")
        feature = graph_with_edges.get("feat-001")
        task = graph_with_edges.get("feat-003")
        assert feature is not None
        assert task is not None
        assert np.matches(feature) is True
        assert np.matches(task) is False

    def test_matches_filters(self, graph_with_edges: HtmlGraph):
        """A pattern with filters checks attribute values."""
        np = NodePattern(variable="x", filters={"status": "blocked"})
        blocked = graph_with_edges.get("feat-001")
        not_blocked = graph_with_edges.get("feat-002")
        assert blocked is not None
        assert not_blocked is not None
        assert np.matches(blocked) is True
        assert np.matches(not_blocked) is False

    def test_matches_nested_filter(self, graph_with_edges: HtmlGraph):
        """A pattern can filter on nested attributes via dot notation."""
        np = NodePattern(variable="x", filters={"properties.team": "backend"})
        backend_node = graph_with_edges.get("feat-001")
        qa_node = graph_with_edges.get("feat-003")
        assert backend_node is not None
        assert qa_node is not None
        assert np.matches(backend_node) is True
        assert np.matches(qa_node) is False

    def test_matches_label_and_filters(self, graph_with_edges: HtmlGraph):
        """A pattern with both label and filters checks both."""
        np = NodePattern(variable="x", label="feature", filters={"priority": "high"})
        high_feature = graph_with_edges.get("feat-001")
        low_feature = graph_with_edges.get("feat-005")
        task = graph_with_edges.get("feat-003")
        assert high_feature is not None
        assert low_feature is not None
        assert task is not None
        assert np.matches(high_feature) is True
        assert np.matches(low_feature) is False  # wrong priority
        assert np.matches(task) is False  # wrong type


class TestEdgePattern:
    """Tests for the EdgePattern dataclass."""

    def test_defaults(self):
        """EdgePattern has sensible defaults."""
        ep = EdgePattern(variable="e", source="a", target="b")
        assert ep.direction == "outgoing"
        assert ep.quantifier == "one"
        assert ep.relationship is None


class TestMatchResult:
    """Tests for the MatchResult dataclass."""

    def test_get_node(self, graph_with_edges: HtmlGraph):
        """get_node returns the correct Node from bindings."""
        node = graph_with_edges.get("feat-001")
        assert node is not None
        result = MatchResult(bindings={"f1": node}, path_length=0)
        assert result.get_node("f1") is node

    def test_get_node_raises_on_missing(self):
        """get_node raises KeyError for missing variable."""
        result = MatchResult(bindings={}, path_length=0)
        with pytest.raises(KeyError):
            result.get_node("missing")

    def test_get_node_raises_on_wrong_type(self):
        """get_node raises TypeError when binding is an EdgeRef."""
        ref = EdgeRef(source_id="a", target_id="b", relationship="related")
        result = MatchResult(bindings={"e": ref}, path_length=0)
        with pytest.raises(TypeError):
            result.get_node("e")

    def test_get_edge(self):
        """get_edge returns the correct EdgeRef from bindings."""
        ref = EdgeRef(source_id="a", target_id="b", relationship="related")
        result = MatchResult(bindings={"e": ref}, path_length=0)
        assert result.get_edge("e") is ref

    def test_get_edge_raises_on_missing(self):
        """get_edge raises KeyError for missing variable."""
        result = MatchResult(bindings={}, path_length=0)
        with pytest.raises(KeyError):
            result.get_edge("missing")

    def test_get_edge_raises_on_wrong_type(self, graph_with_edges: HtmlGraph):
        """get_edge raises TypeError when binding is a Node."""
        node = graph_with_edges.get("feat-001")
        assert node is not None
        result = MatchResult(bindings={"n": node}, path_length=0)
        with pytest.raises(TypeError):
            result.get_edge("n")


class TestGraphPatternBuilder:
    """Tests for the GraphPattern fluent builder."""

    def test_add_node_pattern(self):
        """Node patterns can be added fluently."""
        pattern = GraphPattern()
        result = pattern.node("f1", label="feature", filters={"status": "blocked"})
        assert result is pattern  # Returns self for chaining
        assert len(pattern._node_patterns) == 1
        assert pattern._node_patterns[0].variable == "f1"
        assert pattern._node_patterns[0].label == "feature"

    def test_add_edge_pattern(self):
        """Edge patterns can be added fluently."""
        pattern = GraphPattern()
        pattern.node("a")
        pattern.node("b")
        result = pattern.edge("e", source="a", target="b", relationship="blocked_by")
        assert result is pattern
        assert len(pattern._edge_patterns) == 1
        assert pattern._edge_patterns[0].relationship == "blocked_by"

    def test_duplicate_node_variable_raises(self):
        """Adding a node with duplicate variable raises ValueError."""
        pattern = GraphPattern()
        pattern.node("f1")
        with pytest.raises(ValueError, match="Duplicate node variable"):
            pattern.node("f1")

    def test_columns_projection(self):
        """columns() sets which bindings to project in results."""
        pattern = GraphPattern()
        result = pattern.columns("f1", "f2")
        assert result is pattern
        assert pattern._columns == ["f1", "f2"]


class TestSimpleTwoNodePattern:
    """Tests for simple two-node, one-edge pattern matching."""

    def test_basic_match(self, graph_with_edges: HtmlGraph):
        """Find a blocked feature connected to another feature via blocked_by."""
        pattern = GraphPattern()
        pattern.node("f1", label="feature", filters={"status": "blocked"})
        pattern.edge("e", source="f1", target="f2", relationship="blocked_by")
        pattern.node("f2", label="feature")

        results = pattern.match(graph_with_edges)

        assert len(results) == 1
        result = results[0]
        assert result.get_node("f1").id == "feat-001"
        assert result.get_node("f2").id == "feat-002"
        assert result.path_length == 1

        # Check edge binding
        edge = result.get_edge("e")
        assert edge.source_id == "feat-001"
        assert edge.target_id == "feat-002"
        assert edge.relationship == "blocked_by"

    def test_match_with_relationship_filter(self, graph_with_edges: HtmlGraph):
        """Edge relationship filter restricts matching edges."""
        pattern = GraphPattern()
        pattern.node("a")
        pattern.edge("e", source="a", target="b", relationship="related")
        pattern.node("b")

        results = pattern.match(graph_with_edges)

        # feat-001 --related--> feat-003 and feat-003 --related--> feat-001
        assert len(results) == 2

        result_ids = {(r.get_node("a").id, r.get_node("b").id) for r in results}
        assert ("feat-001", "feat-003") in result_ids
        assert ("feat-003", "feat-001") in result_ids

    def test_match_with_target_attribute_filter(self, graph_with_edges: HtmlGraph):
        """Target node filters further restrict matches."""
        pattern = GraphPattern()
        pattern.node("src", label="feature")
        pattern.edge("e", source="src", target="dst", relationship="blocked_by")
        pattern.node("dst", label="feature", filters={"priority": "critical"})

        results = pattern.match(graph_with_edges)

        # Only feat-002 --blocked_by--> feat-004 matches (feat-004 is critical)
        assert len(results) == 1
        assert results[0].get_node("src").id == "feat-002"
        assert results[0].get_node("dst").id == "feat-004"


class TestMultiNodeChainPattern:
    """Tests for multi-node chain patterns (3+ nodes)."""

    def test_three_node_chain(self, graph_with_edges: HtmlGraph):
        """Find chain: feat blocked_by another feat blocked_by a third."""
        pattern = GraphPattern()
        pattern.node("a", label="feature", filters={"status": "blocked"})
        pattern.edge("e1", source="a", target="b", relationship="blocked_by")
        pattern.node("b", label="feature")
        pattern.edge("e2", source="b", target="c", relationship="blocked_by")
        pattern.node("c", label="feature")

        results = pattern.match(graph_with_edges)

        # feat-001 --blocked_by--> feat-002 --blocked_by--> feat-004
        assert len(results) == 1
        result = results[0]
        assert result.get_node("a").id == "feat-001"
        assert result.get_node("b").id == "feat-002"
        assert result.get_node("c").id == "feat-004"
        assert result.path_length == 2

    def test_chain_with_mixed_relationships(self, graph_with_edges: HtmlGraph):
        """Find chain using different relationship types."""
        pattern = GraphPattern()
        pattern.node("a", label="feature")
        pattern.edge("e1", source="a", target="b", relationship="related")
        pattern.node("b", label="task")
        pattern.edge("e2", source="b", target="c", relationship="related")
        pattern.node("c", label="feature")

        results = pattern.match(graph_with_edges)

        # feat-001 --related--> feat-003(task) --related--> feat-001
        # But c cannot be the same as a (no explicit uniqueness constraint
        # in the base matcher, but let's check what we get)
        assert len(results) >= 1

        # At least one result should be: feat-001 -> feat-003 -> feat-001
        found = False
        for r in results:
            if (
                r.get_node("a").id == "feat-001"
                and r.get_node("b").id == "feat-003"
                and r.get_node("c").id == "feat-001"
            ):
                found = True
                break
        assert found


class TestEmptyResults:
    """Tests for patterns that produce no matches."""

    def test_no_matching_nodes(self, graph_with_edges: HtmlGraph):
        """No results when node label doesn't exist in graph."""
        pattern = GraphPattern()
        pattern.node("x", label="nonexistent_type")

        results = pattern.match(graph_with_edges)
        assert results == []

    def test_no_matching_edges(self, graph_with_edges: HtmlGraph):
        """No results when relationship doesn't exist."""
        pattern = GraphPattern()
        pattern.node("a", label="feature")
        pattern.edge("e", source="a", target="b", relationship="nonexistent_rel")
        pattern.node("b", label="feature")

        results = pattern.match(graph_with_edges)
        assert results == []

    def test_no_matching_filter_combination(self, graph_with_edges: HtmlGraph):
        """No results when filter combination matches nothing."""
        pattern = GraphPattern()
        pattern.node(
            "a", label="feature", filters={"status": "blocked", "priority": "low"}
        )

        results = pattern.match(graph_with_edges)
        assert results == []

    def test_empty_graph(self):
        """No results on an empty graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = HtmlGraph(tmpdir, auto_load=False)

            pattern = GraphPattern()
            pattern.node("a")

            results = pattern.match(graph)
            assert results == []


class TestColumnProjection:
    """Tests for column projection in results."""

    def test_project_specific_columns(self, graph_with_edges: HtmlGraph):
        """Only specified bindings appear in results when columns are set."""
        pattern = GraphPattern()
        pattern.node("f1", label="feature", filters={"status": "blocked"})
        pattern.edge("e", source="f1", target="f2", relationship="blocked_by")
        pattern.node("f2", label="feature")
        pattern.columns("f1", "f2")

        results = pattern.match(graph_with_edges)
        assert len(results) == 1

        # Only f1 and f2 should be in bindings, not "e"
        assert "f1" in results[0].bindings
        assert "f2" in results[0].bindings
        assert "e" not in results[0].bindings

    def test_project_single_column(self, graph_with_edges: HtmlGraph):
        """Projection can select a single binding."""
        pattern = GraphPattern()
        pattern.node("f1", label="feature", filters={"status": "blocked"})
        pattern.edge("e", source="f1", target="f2", relationship="blocked_by")
        pattern.node("f2", label="feature")
        pattern.columns("f2")

        results = pattern.match(graph_with_edges)
        assert len(results) == 1
        assert set(results[0].bindings.keys()) == {"f2"}


class TestEdgeDirection:
    """Tests for edge direction (incoming vs outgoing)."""

    def test_outgoing_direction(self, graph_with_edges: HtmlGraph):
        """Outgoing direction follows edges from source to target."""
        pattern = GraphPattern()
        pattern.node("a", filters={"id": "feat-001"})
        pattern.edge(
            "e", source="a", target="b", relationship="blocked_by", direction="outgoing"
        )
        pattern.node("b")

        results = pattern.match(graph_with_edges)
        assert len(results) == 1
        assert results[0].get_node("b").id == "feat-002"

    def test_incoming_direction(self, graph_with_edges: HtmlGraph):
        """Incoming direction follows edges pointing to the source node."""
        pattern = GraphPattern()
        pattern.node("a", filters={"id": "feat-002"})
        pattern.edge(
            "e", source="a", target="b", relationship="blocked_by", direction="incoming"
        )
        pattern.node("b")

        results = pattern.match(graph_with_edges)

        # feat-001 --blocked_by--> feat-002, so incoming to feat-002 is feat-001
        assert len(results) == 1
        assert results[0].get_node("b").id == "feat-001"

    def test_both_direction(self, graph_with_edges: HtmlGraph):
        """Both direction matches edges in either direction."""
        pattern = GraphPattern()
        pattern.node("a", filters={"id": "feat-002"})
        pattern.edge(
            "e", source="a", target="b", relationship="blocked_by", direction="both"
        )
        pattern.node("b")

        results = pattern.match(graph_with_edges)

        # Outgoing: feat-002 --blocked_by--> feat-004
        # Incoming: feat-001 --blocked_by--> feat-002 (so feat-001 is neighbor)
        result_ids = {r.get_node("b").id for r in results}
        assert "feat-004" in result_ids
        assert "feat-001" in result_ids
        assert len(results) == 2


class TestNodeOnlyPatterns:
    """Tests for patterns with only node patterns and no edges."""

    def test_single_node_pattern(self, graph_with_edges: HtmlGraph):
        """A single node pattern returns all matching nodes."""
        pattern = GraphPattern()
        pattern.node("f", label="feature")

        results = pattern.match(graph_with_edges)

        # feat-001, feat-002, feat-004, feat-005 are features
        assert len(results) == 4
        result_ids = {r.get_node("f").id for r in results}
        assert result_ids == {"feat-001", "feat-002", "feat-004", "feat-005"}

    def test_single_node_with_filters(self, graph_with_edges: HtmlGraph):
        """A single node pattern with filters narrows results."""
        pattern = GraphPattern()
        pattern.node("f", label="feature", filters={"priority": "high"})

        results = pattern.match(graph_with_edges)

        # feat-001 and feat-002 are high-priority features
        assert len(results) == 2
        result_ids = {r.get_node("f").id for r in results}
        assert result_ids == {"feat-001", "feat-002"}


class TestPatternMatcherEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_pattern_with_no_patterns(self, graph_with_edges: HtmlGraph):
        """An empty pattern returns no results."""
        pattern = GraphPattern()
        results = pattern.match(graph_with_edges)
        assert results == []

    def test_all_edges_any_relationship(self, graph_with_edges: HtmlGraph):
        """Edge pattern with no relationship filter matches all relationships."""
        pattern = GraphPattern()
        pattern.node("a", filters={"id": "feat-001"})
        pattern.edge("e", source="a", target="b")
        pattern.node("b")

        results = pattern.match(graph_with_edges)

        # feat-001 has edges: blocked_by->feat-002, related->feat-003
        assert len(results) == 2
        result_ids = {r.get_node("b").id for r in results}
        assert result_ids == {"feat-002", "feat-003"}

    def test_match_result_path_length(self, graph_with_edges: HtmlGraph):
        """Path length is correctly computed for multi-edge patterns."""
        pattern = GraphPattern()
        pattern.node("a", label="feature", filters={"status": "blocked"})
        pattern.edge("e1", source="a", target="b", relationship="blocked_by")
        pattern.node("b", label="feature")
        pattern.edge("e2", source="b", target="c", relationship="blocked_by")
        pattern.node("c", label="feature")

        results = pattern.match(graph_with_edges)
        assert len(results) == 1
        assert results[0].path_length == 2

    def test_fluent_chaining(self, graph_with_edges: HtmlGraph):
        """GraphPattern supports full fluent chaining."""
        results = (
            GraphPattern()
            .node("f1", label="feature", filters={"status": "blocked"})
            .edge("e", source="f1", target="f2", relationship="blocked_by")
            .node("f2", label="feature")
            .columns("f1", "f2")
            .match(graph_with_edges)
        )

        assert len(results) == 1
        assert "f1" in results[0].bindings
        assert "f2" in results[0].bindings
        assert "e" not in results[0].bindings
