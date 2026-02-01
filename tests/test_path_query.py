"""
Tests for PathQuery DSL - Declarative Path Expression Language.

Tests parsing, validation, and execution of path expressions against
HtmlGraph instances.
"""

import tempfile

import pytest
from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node
from htmlgraph.path_query import (
    EdgePattern,
    NodePattern,
    PathExpression,
    PathQueryEngine,
    PathQueryError,
    PathQueryParser,
    PathResult,
    WhereClause,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> PathQueryParser:
    """Create a PathQueryParser instance."""
    return PathQueryParser()


@pytest.fixture
def engine() -> PathQueryEngine:
    """Create a PathQueryEngine instance."""
    return PathQueryEngine()


@pytest.fixture
def simple_graph() -> HtmlGraph:
    """Create a simple graph with features and blocked_by edges.

    Graph structure:
        feat-001 --blocked_by--> feat-002
        feat-002 --blocked_by--> feat-003
        feat-003 (no outgoing blocked_by)
        feat-004 --blocked_by--> feat-002
        feat-004 --related--> feat-001
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        feat1 = Node(
            id="feat-001",
            title="User Auth",
            type="feature",
            status="blocked",
            priority="high",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-002", relationship="blocked_by"),
                ],
            },
        )
        feat2 = Node(
            id="feat-002",
            title="Database Schema",
            type="feature",
            status="in-progress",
            priority="high",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-003", relationship="blocked_by"),
                ],
            },
        )
        feat3 = Node(
            id="feat-003",
            title="Infrastructure",
            type="feature",
            status="done",
            priority="medium",
        )
        feat4 = Node(
            id="feat-004",
            title="API Endpoints",
            type="feature",
            status="todo",
            priority="low",
            edges={
                "blocked_by": [
                    Edge(target_id="feat-002", relationship="blocked_by"),
                ],
                "related": [
                    Edge(target_id="feat-001", relationship="related"),
                ],
            },
        )
        session1 = Node(
            id="sess-001",
            title="Dev Session 1",
            type="session",
            status="active",
            priority="medium",
            edges={
                "touches": [
                    Edge(target_id="feat-001", relationship="touches"),
                    Edge(target_id="feat-002", relationship="touches"),
                ],
            },
        )

        graph.add(feat1)
        graph.add(feat2)
        graph.add(feat3)
        graph.add(feat4)
        graph.add(session1)

        yield graph


# =========================================================================
# Parser Tests - Node Patterns
# =========================================================================


class TestParseNodePatterns:
    """Test parsing of node patterns like (Label) and (Label WHERE ...)."""

    def test_parse_simple_label(self, parser: PathQueryParser) -> None:
        """Parsing a node with just a label."""
        expr = parser.parse("(Feature)-[blocked_by]->(Feature)")
        assert len(expr.nodes) == 2
        assert expr.nodes[0].label == "Feature"
        assert expr.nodes[1].label == "Feature"
        assert expr.nodes[0].filters == []

    def test_parse_no_label(self, parser: PathQueryParser) -> None:
        """Parsing a node pattern with no label (matches any type)."""
        expr = parser.parse("()-[blocked_by]->()")
        assert len(expr.nodes) == 2
        assert expr.nodes[0].label == ""
        assert expr.nodes[1].label == ""

    def test_parse_where_single(self, parser: PathQueryParser) -> None:
        """Parsing a node with a single WHERE condition."""
        expr = parser.parse("(Feature WHERE status='blocked')-[blocked_by]->(Feature)")
        assert len(expr.nodes[0].filters) == 1
        assert expr.nodes[0].filters[0].attribute == "status"
        assert expr.nodes[0].filters[0].value == "blocked"

    def test_parse_where_multiple(self, parser: PathQueryParser) -> None:
        """Parsing a node with multiple AND-separated WHERE conditions."""
        expr = parser.parse(
            "(Feature WHERE status='blocked' AND priority='high')"
            "-[blocked_by]->"
            "(Feature)"
        )
        assert len(expr.nodes[0].filters) == 2
        assert expr.nodes[0].filters[0].attribute == "status"
        assert expr.nodes[0].filters[0].value == "blocked"
        assert expr.nodes[0].filters[1].attribute == "priority"
        assert expr.nodes[0].filters[1].value == "high"

    def test_parse_where_on_target(self, parser: PathQueryParser) -> None:
        """WHERE clause on the target node."""
        expr = parser.parse("(Feature)-[blocked_by]->(Feature WHERE priority='high')")
        assert expr.nodes[0].filters == []
        assert len(expr.nodes[1].filters) == 1
        assert expr.nodes[1].filters[0].attribute == "priority"
        assert expr.nodes[1].filters[0].value == "high"


# =========================================================================
# Parser Tests - Edge Patterns
# =========================================================================


class TestParseEdgePatterns:
    """Test parsing of edge patterns like -[rel]-> and <-[rel]-."""

    def test_parse_outgoing(self, parser: PathQueryParser) -> None:
        """Parse a simple outgoing edge."""
        expr = parser.parse("(Feature)-[blocked_by]->(Feature)")
        assert len(expr.edges) == 1
        assert expr.edges[0].relationship == "blocked_by"
        assert expr.edges[0].direction == "outgoing"
        assert expr.edges[0].quantifier is None

    def test_parse_incoming(self, parser: PathQueryParser) -> None:
        """Parse a simple incoming (reverse) edge."""
        expr = parser.parse("(Feature)<-[blocks]-(Feature)")
        assert len(expr.edges) == 1
        assert expr.edges[0].relationship == "blocks"
        assert expr.edges[0].direction == "incoming"
        assert expr.edges[0].quantifier is None

    def test_parse_quantifier_plus(self, parser: PathQueryParser) -> None:
        """Parse an edge with + quantifier (transitive / one-or-more)."""
        expr = parser.parse("(Feature)-[blocked_by]->+(Feature)")
        assert expr.edges[0].quantifier == "+"

    def test_parse_quantifier_star(self, parser: PathQueryParser) -> None:
        """Parse an edge with * quantifier (shortest / zero-or-more)."""
        expr = parser.parse("(Feature)-[blocked_by]->*(Feature)")
        assert expr.edges[0].quantifier == "*"

    def test_parse_quantifier_question(self, parser: PathQueryParser) -> None:
        """Parse an edge with ? quantifier (optional / zero-or-one)."""
        expr = parser.parse("(Feature)-[blocked_by]->?(Feature)")
        assert expr.edges[0].quantifier == "?"


# =========================================================================
# Parser Tests - Multi-Hop & Structure
# =========================================================================


class TestParseMultiHop:
    """Test multi-hop patterns and overall structure validation."""

    def test_parse_two_hop(self, parser: PathQueryParser) -> None:
        """Parse a two-hop pattern: node-edge-node-edge-node."""
        expr = parser.parse("(Session)-[touches]->(Feature)<-[blocked_by]-(Feature)")
        assert len(expr.nodes) == 3
        assert len(expr.edges) == 2
        assert expr.nodes[0].label == "Session"
        assert expr.nodes[1].label == "Feature"
        assert expr.nodes[2].label == "Feature"
        assert expr.edges[0].relationship == "touches"
        assert expr.edges[0].direction == "outgoing"
        assert expr.edges[1].relationship == "blocked_by"
        assert expr.edges[1].direction == "incoming"

    def test_raw_preserved(self, parser: PathQueryParser) -> None:
        """The raw expression string is preserved."""
        raw = "(Feature)-[blocked_by]->(Feature)"
        expr = parser.parse(raw)
        assert expr.raw == raw


# =========================================================================
# Parser Tests - Error Handling
# =========================================================================


class TestParseErrors:
    """Test error handling for malformed expressions."""

    def test_empty_expression(self, parser: PathQueryParser) -> None:
        """Empty string raises PathQueryError."""
        with pytest.raises(PathQueryError, match="Empty"):
            parser.parse("")

    def test_single_node(self, parser: PathQueryParser) -> None:
        """Single node without edge raises error."""
        with pytest.raises(PathQueryError, match="at least two"):
            parser.parse("(Feature)")

    def test_missing_closing_paren(self, parser: PathQueryParser) -> None:
        """Missing closing parenthesis raises error."""
        with pytest.raises(PathQueryError):
            parser.parse("(Feature-[blocked_by]->(Feature)")

    def test_invalid_where_format(self, parser: PathQueryParser) -> None:
        """Invalid WHERE clause format raises error."""
        with pytest.raises(PathQueryError, match="Invalid WHERE"):
            parser.parse("(Feature WHERE status blocked)-[x]->(Feature)")

    def test_missing_edge_between_nodes(self, parser: PathQueryParser) -> None:
        """Two consecutive nodes without edge raises error."""
        with pytest.raises(PathQueryError):
            parser.parse("(Feature)(Feature)")


# =========================================================================
# Dataclass Tests
# =========================================================================


class TestDataclasses:
    """Test PathQuery dataclass construction and defaults."""

    def test_node_pattern_defaults(self) -> None:
        """NodePattern has sensible defaults."""
        np = NodePattern()
        assert np.label == ""
        assert np.filters == []

    def test_edge_pattern_defaults(self) -> None:
        """EdgePattern has sensible defaults."""
        ep = EdgePattern(relationship="blocked_by")
        assert ep.direction == "outgoing"
        assert ep.quantifier is None

    def test_path_expression_defaults(self) -> None:
        """PathExpression has sensible defaults."""
        pe = PathExpression()
        assert pe.nodes == []
        assert pe.edges == []
        assert pe.raw == ""

    def test_path_result_defaults(self) -> None:
        """PathResult has sensible defaults."""
        pr = PathResult()
        assert pr.nodes == []
        assert pr.path_length == 0
        assert pr.bindings == {}

    def test_where_clause(self) -> None:
        """WhereClause stores attribute and value."""
        wc = WhereClause(attribute="status", value="blocked")
        assert wc.attribute == "status"
        assert wc.value == "blocked"


# =========================================================================
# Engine Tests - Single-Hop Queries
# =========================================================================


class TestEngineSingleHop:
    """Test single-hop query execution."""

    def test_single_hop_outgoing(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Single outgoing hop: feat-001 -blocked_by-> feat-002."""
        results = engine.execute(simple_graph, "(Feature)-[blocked_by]->(Feature)")
        # feat-001 -> feat-002, feat-002 -> feat-003, feat-004 -> feat-002
        assert len(results) == 3
        paths = [tuple(r.nodes) for r in results]
        assert ("feat-001", "feat-002") in paths
        assert ("feat-002", "feat-003") in paths
        assert ("feat-004", "feat-002") in paths

    def test_single_hop_with_source_filter(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Single hop with WHERE filter on source node."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->(Feature)",
        )
        # Only feat-001 has status='blocked'
        assert len(results) == 1
        assert results[0].nodes == ["feat-001", "feat-002"]

    def test_single_hop_with_target_filter(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Single hop with WHERE filter on target node."""
        results = engine.execute(
            simple_graph,
            "(Feature)-[blocked_by]->(Feature WHERE status='done')",
        )
        # Only feat-002 -> feat-003 ends at a 'done' feature
        assert len(results) == 1
        assert results[0].nodes == ["feat-002", "feat-003"]

    def test_single_hop_incoming(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Single incoming (reverse) hop."""
        results = engine.execute(
            simple_graph,
            "(Feature)<-[blocked_by]-(Feature)",
        )
        # feat-002 <-blocked_by- feat-001
        # feat-002 <-blocked_by- feat-004
        # feat-003 <-blocked_by- feat-002
        assert len(results) == 3
        paths = [tuple(r.nodes) for r in results]
        assert ("feat-002", "feat-001") in paths
        assert ("feat-002", "feat-004") in paths
        assert ("feat-003", "feat-002") in paths

    def test_different_relationship(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Query using a different relationship type."""
        results = engine.execute(simple_graph, "(Feature)-[related]->(Feature)")
        assert len(results) == 1
        assert results[0].nodes == ["feat-004", "feat-001"]

    def test_cross_type_hop(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Query spanning different node types (Session -> Feature)."""
        results = engine.execute(simple_graph, "(Session)-[touches]->(Feature)")
        assert len(results) == 2
        targets = {tuple(r.nodes) for r in results}
        assert ("sess-001", "feat-001") in targets
        assert ("sess-001", "feat-002") in targets

    def test_no_label_matches_any(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Empty label matches any node type."""
        results = engine.execute(simple_graph, "()-[touches]->()")
        assert len(results) == 2

    def test_path_length(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """path_length is 1 for single-hop results."""
        results = engine.execute(simple_graph, "(Feature)-[blocked_by]->(Feature)")
        for r in results:
            assert r.path_length == 1

    def test_no_matches(self, engine: PathQueryEngine, simple_graph: HtmlGraph) -> None:
        """Query that matches nothing returns empty list."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='nonexistent')-[blocked_by]->(Feature)",
        )
        assert results == []


# =========================================================================
# Engine Tests - Variable-Length Queries
# =========================================================================


class TestEngineVariableLength:
    """Test variable-length (transitive) query execution."""

    def test_transitive_outgoing(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Transitive (->+) follows blocked_by chains.

        feat-001 -> feat-002 -> feat-003 transitively.
        """
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->+(Feature)",
        )
        # From feat-001: transitively reaches feat-002 and feat-003
        assert len(results) == 2
        target_ids = {r.nodes[-1] for r in results}
        assert target_ids == {"feat-002", "feat-003"}

    def test_transitive_reaches_deep(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Transitive from feat-004 reaches feat-002 and feat-003."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='todo')-[blocked_by]->+(Feature)",
        )
        target_ids = {r.nodes[-1] for r in results}
        assert "feat-002" in target_ids
        assert "feat-003" in target_ids

    def test_transitive_with_target_filter(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Transitive with WHERE on target only returns matching."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->+(Feature WHERE status='done')",
        )
        # Only feat-003 is 'done' and reachable from feat-001
        assert len(results) == 1
        assert results[0].nodes[-1] == "feat-003"


# =========================================================================
# Engine Tests - Shortest Path Queries
# =========================================================================


class TestEngineShortestPath:
    """Test shortest path (*) query execution."""

    def test_shortest_path(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Shortest path (*) between two features."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->*(Feature WHERE status='done')",
        )
        # feat-001 -> feat-002 -> feat-003 (shortest is length 2)
        assert len(results) >= 1
        # Find the result ending at feat-003
        paths_to_done = [r for r in results if r.nodes[-1] == "feat-003"]
        assert len(paths_to_done) == 1
        assert paths_to_done[0].nodes == ["feat-001", "feat-002", "feat-003"]
        assert paths_to_done[0].path_length == 2

    def test_shortest_path_self(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Shortest path (*) can return zero-length path (self-match)."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->*(Feature WHERE status='blocked')",
        )
        # feat-001 with * can match itself (zero-length)
        self_matches = [
            r for r in results if len(r.nodes) == 2 and r.nodes[0] == r.nodes[1]
        ]
        assert len(self_matches) == 1
        assert self_matches[0].nodes == ["feat-001", "feat-001"]


# =========================================================================
# Engine Tests - Optional Queries
# =========================================================================


class TestEngineOptional:
    """Test optional (?) query execution."""

    def test_optional_with_match(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Optional (?) returns direct hop if it exists."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='blocked')-[blocked_by]->?(Feature)",
        )
        # feat-001 has one blocked_by edge to feat-002 (direct hop)
        # Plus feat-001 itself matches Feature (zero-hop)
        assert len(results) >= 1
        nodes_lists = [r.nodes for r in results]
        assert ["feat-001", "feat-002"] in nodes_lists

    def test_optional_zero_hop(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Optional (?) returns self if it matches target pattern."""
        results = engine.execute(
            simple_graph,
            "(Feature WHERE status='done')-[blocked_by]->?(Feature WHERE status='done')",
        )
        # feat-003 has no blocked_by edges, but matches target (zero-hop)
        self_matches = [
            r for r in results if len(r.nodes) == 2 and r.nodes[0] == r.nodes[1]
        ]
        assert len(self_matches) == 1
        assert self_matches[0].nodes == ["feat-003", "feat-003"]


# =========================================================================
# Engine Tests - Multi-Hop
# =========================================================================


class TestEngineMultiHop:
    """Test multi-hop query execution."""

    def test_two_hop(self, engine: PathQueryEngine, simple_graph: HtmlGraph) -> None:
        """Two-hop: Session -touches-> Feature <-blocked_by- Feature."""
        results = engine.execute(
            simple_graph,
            "(Session)-[touches]->(Feature)<-[blocked_by]-(Feature)",
        )
        # sess-001 touches feat-001 and feat-002
        # feat-001 <-blocked_by- (nobody has blocked_by pointing to feat-001)
        # Wait: blocked_by incoming to feat-002: feat-001 and feat-004
        # blocked_by incoming to feat-001: nobody
        # So: sess-001 -> feat-002 <- feat-001, sess-001 -> feat-002 <- feat-004
        assert len(results) == 2
        paths = [tuple(r.nodes) for r in results]
        assert ("sess-001", "feat-002", "feat-001") in paths
        assert ("sess-001", "feat-002", "feat-004") in paths


# =========================================================================
# Engine Tests - String Input vs PathExpression Input
# =========================================================================


class TestEngineInputTypes:
    """Test that engine accepts both strings and PathExpression objects."""

    def test_string_input(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Engine accepts a string expression."""
        results = engine.execute(simple_graph, "(Feature)-[blocked_by]->(Feature)")
        assert len(results) > 0

    def test_path_expression_input(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Engine accepts a pre-parsed PathExpression."""
        parser = PathQueryParser()
        expr = parser.parse("(Feature)-[blocked_by]->(Feature)")
        results = engine.execute(simple_graph, expr)
        assert len(results) > 0

    def test_both_give_same_results(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """String and PathExpression produce identical results."""
        query = "(Feature)-[blocked_by]->(Feature)"
        parser = PathQueryParser()
        expr = parser.parse(query)

        results_str = engine.execute(simple_graph, query)
        results_expr = engine.execute(simple_graph, expr)

        str_paths = sorted([tuple(r.nodes) for r in results_str])
        expr_paths = sorted([tuple(r.nodes) for r in results_expr])
        assert str_paths == expr_paths


# =========================================================================
# Engine Tests - Bindings
# =========================================================================


class TestEngineBindings:
    """Test that PathResult bindings are correctly populated."""

    def test_bindings_populated(
        self, engine: PathQueryEngine, simple_graph: HtmlGraph
    ) -> None:
        """Bindings map pattern index to matched node IDs."""
        results = engine.execute(simple_graph, "(Feature)-[blocked_by]->(Feature)")
        for r in results:
            assert 0 in r.bindings
            assert 1 in r.bindings
            assert r.bindings[0] == [r.nodes[0]]
            assert r.bindings[1] == [r.nodes[1]]
