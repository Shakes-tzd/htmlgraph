"""
Benchmark fixtures for performance testing.

Provides pre-populated graphs of various sizes for benchmarking.
"""

import tempfile
from pathlib import Path

import pytest

from htmlgraph.graph import HtmlGraph
from htmlgraph.models import Edge, Node


@pytest.fixture
def small_graph():
    """Create a small graph with 10 nodes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        for i in range(10):
            node = Node(
                id=f"node-{i:03d}",
                title=f"Node {i}",
                type="feature",
                status="todo" if i % 3 == 0 else "in-progress" if i % 3 == 1 else "done",
                priority="high" if i % 2 == 0 else "medium",
            )
            graph.add(node)

        yield graph


@pytest.fixture
def medium_graph():
    """Create a medium graph with 100 nodes and some edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Create 100 nodes with edges
        for i in range(100):
            edges = {}
            # Create some dependencies
            if i > 0 and i % 5 == 0:
                edges["blocked_by"] = [
                    Edge(target_id=f"node-{i-1:03d}", relationship="blocked_by")
                ]
            if i > 1 and i % 7 == 0:
                edges["related"] = [
                    Edge(target_id=f"node-{i-2:03d}", relationship="related")
                ]

            node = Node(
                id=f"node-{i:03d}",
                title=f"Node {i}",
                type="feature",
                status="todo" if i % 3 == 0 else "in-progress" if i % 3 == 1 else "done",
                priority="high" if i % 2 == 0 else "medium",
                edges=edges,
            )
            graph.add(node)

        yield graph


@pytest.fixture
def large_graph():
    """Create a large graph with 500 nodes and complex edges."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir, auto_load=False)

        # Create 500 nodes with more complex edge patterns
        for i in range(500):
            edges = {}

            # Create dependency chains
            if i > 0 and i % 10 == 0:
                edges["blocked_by"] = [
                    Edge(target_id=f"node-{i-1:03d}", relationship="blocked_by")
                ]

            # Create related links
            related = []
            if i > 5 and i % 7 == 0:
                related.append(Edge(target_id=f"node-{i-5:03d}", relationship="related"))
            if i > 10 and i % 11 == 0:
                related.append(Edge(target_id=f"node-{i-10:03d}", relationship="related"))
            if related:
                edges["related"] = related

            node = Node(
                id=f"node-{i:03d}",
                title=f"Node {i}",
                type="feature" if i % 3 != 0 else "task",
                status="todo" if i % 4 == 0 else "in-progress" if i % 4 == 1 else "done" if i % 4 == 2 else "blocked",
                priority="high" if i % 3 == 0 else "medium" if i % 3 == 1 else "low",
                edges=edges,
                properties={
                    "effort": i % 20 + 1,
                    "completion": (i * 13) % 100,
                },
            )
            graph.add(node)

        yield graph


@pytest.fixture
def benchmark_baseline(tmp_path):
    """Load baseline benchmark results if available."""
    baseline_file = Path("tests/benchmarks/baseline.json")
    if baseline_file.exists():
        import json
        with open(baseline_file) as f:
            return json.load(f)
    return None
