#!/usr/bin/env python3
"""
Demonstrate the edge index corruption bug when updating nodes.

Bug: When a node is updated, all incoming edges are lost from the edge index
even though they still exist in other nodes' edge lists.
"""

import tempfile

from htmlgraph import HtmlGraph


def test_update_preserves_incoming_edges():
    """
    Test that updating a node doesn't lose incoming edges from the index.
    """
    print("\n" + "=" * 70)
    print("TESTING: Edge Index Corruption on Node Update")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir)

        # Create three nodes: A, B, C
        # A depends on B
        # B depends on C
        # So: A -> B -> C (dependency chain)

        print("\n1. Creating nodes A, B, C with dependency chain A->B->C")
        from htmlgraph.models import Edge, Node

        node_c = Node(id="node-c", title="Node C", type="feature")
        node_b = Node(
            id="node-b",
            title="Node B",
            type="feature",
            edges={"depends_on": [Edge(target_id="node-c", relationship="depends_on")]},
        )
        node_a = Node(
            id="node-a",
            title="Node A",
            type="feature",
            edges={"depends_on": [Edge(target_id="node-b", relationship="depends_on")]},
        )

        graph.add(node_c)
        graph.add(node_b)
        graph.add(node_a)

        # Check incoming edges BEFORE update
        print("\n2. Checking incoming edges BEFORE updating node B:")
        incoming_to_b_before = graph.get_incoming_edges("node-b")
        print(f"   Incoming edges to B: {len(incoming_to_b_before)}")
        for edge_ref in incoming_to_b_before:
            print(
                f"     - {edge_ref.source_id} --[{edge_ref.relationship}]--> {edge_ref.target_id}"
            )

        incoming_to_c_before = graph.get_incoming_edges("node-c")
        print(f"   Incoming edges to C: {len(incoming_to_c_before)}")
        for edge_ref in incoming_to_c_before:
            print(
                f"     - {edge_ref.source_id} --[{edge_ref.relationship}]--> {edge_ref.target_id}"
            )

        # Now UPDATE node B (just change the title)
        print("\n3. Updating node B (changing title)...")
        node_b.title = "Node B - Updated"
        graph.update(node_b)

        # Check incoming edges AFTER update
        print("\n4. Checking incoming edges AFTER updating node B:")
        incoming_to_b_after = graph.get_incoming_edges("node-b")
        print(f"   Incoming edges to B: {len(incoming_to_b_after)}")
        for edge_ref in incoming_to_b_after:
            print(
                f"     - {edge_ref.source_id} --[{edge_ref.relationship}]--> {edge_ref.target_id}"
            )

        incoming_to_c_after = graph.get_incoming_edges("node-c")
        print(f"   Incoming edges to C: {len(incoming_to_c_after)}")
        for edge_ref in incoming_to_c_after:
            print(
                f"     - {edge_ref.source_id} --[{edge_ref.relationship}]--> {edge_ref.target_id}"
            )

        # Verify the bug
        print("\n5. VERIFICATION:")
        if len(incoming_to_b_before) == len(incoming_to_b_after):
            print(
                f"   ✅ PASS: Incoming edges to B preserved ({len(incoming_to_b_after)})"
            )
        else:
            print("   ❌ BUG DETECTED: Incoming edges to B lost!")
            print(f"      Before update: {len(incoming_to_b_before)} edges")
            print(f"      After update:  {len(incoming_to_b_after)} edges")
            print(
                f"      Lost: {len(incoming_to_b_before) - len(incoming_to_b_after)} edges"
            )

        # Also check that dependents() is affected
        print("\n6. Checking dependents() method:")
        # Use the correct relationship type
        dependents_result = graph.dependents("node-b", relationship="depends_on")
        print(f"   Dependents of B after update: {dependents_result}")
        print("   Expected: {'node-a'}")

        if "node-a" in dependents_result:
            print("   ✅ PASS: dependents() working correctly")
        else:
            print("   ❌ BUG: dependents() returning incomplete results!")


if __name__ == "__main__":
    test_update_preserves_incoming_edges()
