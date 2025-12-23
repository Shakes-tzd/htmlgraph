"""
Test that updating nodes preserves incoming edges in the edge index.

Regression test for bug where update() would remove all edges (including incoming)
from the edge index via remove_node(), but only re-add outgoing edges, causing
incoming edges to be lost even though they still existed in other nodes' edge lists.
"""

import pytest
from htmlgraph import HtmlGraph
from htmlgraph.models import Node, Edge


def test_update_preserves_incoming_edges(tmp_path):
    """
    Updating a node should preserve incoming edges from other nodes.

    Regression test: Previously, update() called remove_node() which deleted
    both incoming and outgoing edges, then only re-added outgoing edges,
    causing incoming edges to be permanently lost from the index.
    """
    graph = HtmlGraph(tmp_path)

    # Create dependency chain: A -> B -> C
    node_c = Node(id="node-c", title="Node C", type="feature")
    node_b = Node(
        id="node-b",
        title="Node B",
        type="feature",
        edges={"depends_on": [Edge(target_id="node-c", relationship="depends_on")]}
    )
    node_a = Node(
        id="node-a",
        title="Node A",
        type="feature",
        edges={"depends_on": [Edge(target_id="node-b", relationship="depends_on")]}
    )

    graph.add(node_c)
    graph.add(node_b)
    graph.add(node_a)

    # Verify incoming edges exist before update
    incoming_before = graph.get_incoming_edges("node-b")
    assert len(incoming_before) == 1
    assert incoming_before[0].source_id == "node-a"
    assert incoming_before[0].target_id == "node-b"
    assert incoming_before[0].relationship == "depends_on"

    # Update node B (just change title)
    node_b.title = "Node B - Updated"
    graph.update(node_b)

    # Verify incoming edges still exist after update
    incoming_after = graph.get_incoming_edges("node-b")
    assert len(incoming_after) == 1
    assert incoming_after[0].source_id == "node-a"
    assert incoming_after[0].target_id == "node-b"
    assert incoming_after[0].relationship == "depends_on"


def test_update_preserves_incoming_edges_for_dependents(tmp_path):
    """
    Updating a node should keep dependents() working correctly.

    The dependents() method relies on incoming edges in the edge index.
    """
    graph = HtmlGraph(tmp_path)

    # Create nodes where A depends on B
    node_b = Node(id="node-b", title="Node B", type="feature")
    node_a = Node(
        id="node-a",
        title="Node A",
        type="feature",
        edges={"depends_on": [Edge(target_id="node-b", relationship="depends_on")]}
    )

    graph.add(node_b)
    graph.add(node_a)

    # Verify dependents works before update
    deps_before = graph.dependents("node-b", relationship="depends_on")
    assert "node-a" in deps_before

    # Update node B
    node_b.title = "Node B - Updated"
    graph.update(node_b)

    # Verify dependents still works after update
    deps_after = graph.dependents("node-b", relationship="depends_on")
    assert "node-a" in deps_after


def test_update_correctly_modifies_outgoing_edges(tmp_path):
    """
    Updating a node should correctly update its outgoing edges.

    When a node's edges are modified, the edge index should reflect the changes.
    """
    graph = HtmlGraph(tmp_path)

    # Create nodes
    node_a = Node(id="node-a", title="Node A", type="feature")
    node_b = Node(id="node-b", title="Node B", type="feature")
    node_c = Node(id="node-c", title="Node C", type="feature")

    # Node X initially depends on A
    node_x = Node(
        id="node-x",
        title="Node X",
        type="feature",
        edges={"depends_on": [Edge(target_id="node-a", relationship="depends_on")]}
    )

    graph.add(node_a)
    graph.add(node_b)
    graph.add(node_c)
    graph.add(node_x)

    # Verify initial state
    outgoing_before = graph.get_outgoing_edges("node-x")
    assert len(outgoing_before) == 1
    assert outgoing_before[0].target_id == "node-a"

    incoming_to_a = graph.get_incoming_edges("node-a")
    assert len(incoming_to_a) == 1

    incoming_to_b = graph.get_incoming_edges("node-b")
    assert len(incoming_to_b) == 0

    # Update node X to depend on B instead of A
    node_x.edges = {"depends_on": [Edge(target_id="node-b", relationship="depends_on")]}
    graph.update(node_x)

    # Verify outgoing edges were updated
    outgoing_after = graph.get_outgoing_edges("node-x")
    assert len(outgoing_after) == 1
    assert outgoing_after[0].target_id == "node-b"

    # Verify old incoming edge was removed
    incoming_to_a_after = graph.get_incoming_edges("node-a")
    assert len(incoming_to_a_after) == 0

    # Verify new incoming edge was added
    incoming_to_b_after = graph.get_incoming_edges("node-b")
    assert len(incoming_to_b_after) == 1
    assert incoming_to_b_after[0].source_id == "node-x"


def test_update_handles_multiple_edge_types(tmp_path):
    """
    Updating a node with multiple edge types should preserve all incoming edges.
    """
    graph = HtmlGraph(tmp_path)

    # Create nodes with different relationship types
    node_b = Node(id="node-b", title="Node B", type="feature")
    node_a = Node(
        id="node-a",
        title="Node A",
        type="feature",
        edges={
            "depends_on": [Edge(target_id="node-b", relationship="depends_on")],
            "blocks": [Edge(target_id="node-b", relationship="blocks")]
        }
    )

    graph.add(node_b)
    graph.add(node_a)

    # Verify all incoming edges before update
    incoming_before = graph.get_incoming_edges("node-b")
    assert len(incoming_before) == 2

    # Update node B
    node_b.title = "Node B - Updated"
    graph.update(node_b)

    # Verify all incoming edges preserved after update
    incoming_after = graph.get_incoming_edges("node-b")
    assert len(incoming_after) == 2
    relationships = {edge.relationship for edge in incoming_after}
    assert relationships == {"depends_on", "blocks"}
