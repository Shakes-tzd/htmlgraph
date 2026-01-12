#!/usr/bin/env python3
"""
Test HtmlGraph operations on the features/ directory.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src" / "python"))

from htmlgraph import AgentInterface, HtmlGraph


def test_queries():
    """Test CSS selector queries."""
    print("=" * 50)
    print("Testing HtmlGraph Queries")
    print("=" * 50)

    graph = HtmlGraph("features/")

    # Test 1: Query by status
    print("\n1. Query: [data-status='todo']")
    todo_nodes = graph.query("[data-status='todo']")
    for node in todo_nodes:
        print(f"   - {node.id}: {node.title}")

    # Test 2: Query by type
    print("\n2. Query: [data-type='phase']")
    phases = graph.query("[data-type='phase']")
    for node in phases:
        print(f"   - {node.id}: {node.title} [{node.status}]")

    # Test 3: Query high priority in-progress
    print("\n3. Query: [data-priority='high'][data-status='in-progress']")
    active_high = graph.query("[data-priority='high'][data-status='in-progress']")
    for node in active_high:
        print(f"   - {node.id}: {node.title}")

    # Test 4: Shortest path
    print("\n4. Shortest path: feature-self-tracking -> phase6-launch")
    path = graph.shortest_path(
        "feature-self-tracking", "phase6-launch", relationship="related"
    )
    if path:
        print(f"   Path: {' -> '.join(path)}")
    else:
        print("   No direct path via 'related' edges")

    # Test 5: Transitive dependencies
    print("\n5. Transitive dependencies of phase6-launch:")
    deps = graph.transitive_deps("phase6-launch", relationship="blocked_by")
    for dep_id in deps:
        dep = graph.get(dep_id)
        if dep:
            print(f"   - {dep.id}: {dep.title}")

    # Test 6: Mermaid diagram
    print("\n6. Mermaid Diagram (blocked_by edges):")
    mermaid = graph.to_mermaid(relationship="blocked_by")
    print(mermaid)


def test_agent_interface():
    """Test agent interface."""
    print("\n" + "=" * 50)
    print("Testing AgentInterface")
    print("=" * 50)

    agent = AgentInterface("features/", agent_id="claude")

    # Get summary
    print("\n1. Project Summary:")
    print(agent.get_summary())

    # Get context for a specific node
    print("\n2. Context for feature-self-tracking:")
    print(agent.get_context("feature-self-tracking"))

    # Get next available task
    print("\n3. Next available task:")
    task = agent.get_next_task()
    if task:
        print(f"   {task.id}: {task.title} [{task.priority}]")

    # Get workload
    print("\n4. Workload for claude:")
    workload = agent.get_workload("claude")
    print(f"   In progress: {workload['in_progress']}")
    print(f"   Tasks: {workload['tasks']}")


if __name__ == "__main__":
    test_queries()
    test_agent_interface()
    print("\n✅ All tests passed!")
