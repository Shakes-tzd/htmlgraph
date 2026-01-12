#!/usr/bin/env python3
"""
Bootstrap HtmlGraph development tracking using HtmlGraph itself.

This script creates feature nodes based on the project roadmap.
Run from project root: python setup_features.py
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from htmlgraph import Edge, HtmlGraph, Node
from htmlgraph.models import Step


def create_features():
    """Create feature nodes for HtmlGraph development."""

    # Initialize graph in features/ directory
    graph = HtmlGraph("features/", stylesheet_path="styles.css", auto_load=False)

    # Phase 1: Core Library (DONE)
    phase1_core = Node(
        id="phase1-core-library",
        title="Phase 1: Core Python Library",
        type="phase",
        status="done",
        priority="critical",
        content="<p>Build the core Python library with HTML parsing, Pydantic models, and graph algorithms.</p>",
        steps=[
            Step(
                description="Python package structure", completed=True, agent="claude"
            ),
            Step(
                description="HTML parser using justhtml", completed=True, agent="claude"
            ),
            Step(
                description="Pydantic models for Node/Edge",
                completed=True,
                agent="claude",
            ),
            Step(
                description="Basic graph operations (add, query, traverse)",
                completed=True,
                agent="claude",
            ),
            Step(
                description="HTML ↔ Pydantic converters", completed=True, agent="claude"
            ),
            Step(description="Unit tests", completed=True, agent="claude"),
        ],
        properties={
            "completion": 100,
            "test_count": 23,
        },
    )

    # Phase 2: JavaScript Library (TODO)
    phase2_js = Node(
        id="phase2-js-library",
        title="Phase 2: JavaScript Library",
        type="phase",
        status="todo",
        priority="high",
        content="<p>Build vanilla JavaScript library for browser-based graph operations and dashboard rendering.</p>",
        steps=[
            Step(description="Vanilla JS implementation with DOMParser"),
            Step(description="CSS selector queries"),
            Step(description="Graph algorithms (BFS, DFS, shortest path)"),
            Step(description="Basic dashboard rendering"),
            Step(description="Unit tests"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase1-core-library",
                    relationship="blocked_by",
                    title="Core Python Library",
                )
            ],
        },
    )

    # Phase 3: Examples (TODO)
    phase3_examples = Node(
        id="phase3-examples",
        title="Phase 3: Examples",
        type="phase",
        status="in-progress",
        priority="high",
        content="<p>Create example projects demonstrating HtmlGraph use cases.</p>",
        steps=[
            Step(description="Todo list example", completed=True, agent="claude"),
            Step(description="Agent coordination example (Ijoka pattern)"),
            Step(description="Knowledge base example"),
            Step(description="Documentation site example"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase1-core-library",
                    relationship="blocked_by",
                    title="Core Python Library",
                )
            ],
        },
        properties={
            "completion": 25,
        },
    )

    # Phase 4: Documentation (TODO)
    phase4_docs = Node(
        id="phase4-documentation",
        title="Phase 4: Documentation",
        type="phase",
        status="todo",
        priority="medium",
        content="<p>Write comprehensive documentation including philosophy, comparisons, and guides.</p>",
        steps=[
            Step(description="README.md with manifesto"),
            Step(description="Philosophy.md - Why HTML?"),
            Step(description="Comparison.md - vs alternatives"),
            Step(description="Quickstart guide"),
            Step(description="API reference"),
            Step(description="Cookbook with recipes"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase3-examples",
                    relationship="blocked_by",
                    title="Examples",
                )
            ],
        },
    )

    # Phase 5: Polish (TODO)
    phase5_polish = Node(
        id="phase5-polish",
        title="Phase 5: Polish",
        type="phase",
        status="todo",
        priority="medium",
        content="<p>Optimize performance, add advanced features, prepare for release.</p>",
        steps=[
            Step(description="Dashboard improvements"),
            Step(description="Performance optimization"),
            Step(description="Optional SQLite indexer"),
            Step(description="TypeScript definitions"),
            Step(description="CI/CD pipeline"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase2-js-library",
                    relationship="blocked_by",
                    title="JS Library",
                ),
                Edge(
                    target_id="phase4-documentation",
                    relationship="blocked_by",
                    title="Documentation",
                ),
            ],
        },
    )

    # Phase 6: Launch (TODO)
    phase6_launch = Node(
        id="phase6-launch",
        title="Phase 6: Launch",
        type="phase",
        status="todo",
        priority="low",
        content="<p>Public release and community building.</p>",
        steps=[
            Step(description="GitHub repo public"),
            Step(description="PyPI package"),
            Step(description="npm package (optional)"),
            Step(description="Blog post"),
            Step(description="Social media (HN, Reddit, Twitter)"),
            Step(description="Documentation site"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase5-polish", relationship="blocked_by", title="Polish"
                )
            ],
        },
    )

    # Feature: Self-tracking (THIS!)
    feature_self_tracking = Node(
        id="feature-self-tracking",
        title="Use HtmlGraph to Track HtmlGraph Development",
        type="feature",
        status="in-progress",
        priority="high",
        content="<p>Dogfood the library by using it to track its own development.</p>",
        steps=[
            Step(
                description="Create features/ directory", completed=True, agent="claude"
            ),
            Step(
                description="Create feature nodes from roadmap",
                completed=True,
                agent="claude",
            ),
            Step(description="Add dashboard for viewing progress"),
            Step(description="Test query and traversal operations"),
        ],
        edges={
            "related": [
                Edge(
                    target_id="phase3-examples",
                    relationship="related",
                    title="Examples Phase",
                )
            ],
        },
        agent_assigned="claude",
    )

    # Feature: JS Dashboard
    feature_dashboard = Node(
        id="feature-js-dashboard",
        title="Vanilla JS Dashboard for Feature Tracking",
        type="feature",
        status="todo",
        priority="high",
        content="<p>Build interactive dashboard showing project status, dependency graph, and progress.</p>",
        steps=[
            Step(description="Create dashboard HTML scaffold"),
            Step(description="Implement node loading via fetch"),
            Step(description="Add status/priority filtering"),
            Step(description="Render dependency graph visualization"),
            Step(description="Add progress statistics"),
        ],
        edges={
            "blocked_by": [
                Edge(
                    target_id="phase2-js-library",
                    relationship="blocked_by",
                    title="JS Library",
                )
            ],
            "related": [
                Edge(
                    target_id="feature-self-tracking",
                    relationship="related",
                    title="Self-Tracking Feature",
                )
            ],
        },
    )

    # Add all nodes
    nodes = [
        phase1_core,
        phase2_js,
        phase3_examples,
        phase4_docs,
        phase5_polish,
        phase6_launch,
        feature_self_tracking,
        feature_dashboard,
    ]

    for node in nodes:
        graph.add(node, overwrite=True)
        print(f"✓ Created: {node.id} [{node.status}]")

    # Print summary
    print("\n" + "=" * 50)
    print("HtmlGraph Development Tracking Initialized")
    print("=" * 50)

    # Reload and show stats
    graph.reload()
    stats = graph.stats()

    print(f"\nTotal nodes: {stats['total']}")
    print(f"Completion: {stats['completion_rate']}%")
    print("\nBy Status:")
    for status, count in stats["by_status"].items():
        print(f"  {status}: {count}")

    print("\nBy Type:")
    for node_type, count in stats["by_type"].items():
        print(f"  {node_type}: {count}")

    # Show dependency order
    print("\nDependency Order (what to work on first):")
    order = graph.topological_sort()
    if order:
        for i, node_id in enumerate(order, 1):
            node = graph.get(node_id)
            if node and node.status != "done":
                print(f"  {i}. {node.title} [{node.status}]")

    # Show bottlenecks
    print("\nBottlenecks (most things depend on these):")
    bottlenecks = graph.find_bottlenecks(top_n=3)
    for node_id, count in bottlenecks:
        node = graph.get(node_id)
        if node:
            print(f"  {node.title}: blocks {count} items")

    return graph


if __name__ == "__main__":
    create_features()
