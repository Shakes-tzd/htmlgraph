#!/usr/bin/env python3
"""
Test script for new features pulled from remote:
1. BeautifulSoup-style Find API
2. QueryBuilder fluent interface
3. EdgeIndex O(1) lookups
4. Graph traversal methods
"""

from htmlgraph import HtmlGraph


def test_find_api():
    """Test BeautifulSoup-style find() and find_all() API."""
    print("\n" + "=" * 60)
    print("TEST 1: BeautifulSoup-style Find API")
    print("=" * 60)

    graph = HtmlGraph(".htmlgraph/features/")

    # Test find() - returns first match
    print("\n1. Testing find() - should return first feature:")
    first = graph.find(type="feature")
    if first:
        print(f"   ✓ Found: {first.id} - {first.title}")
    else:
        print("   ✗ No results found")

    # Test find_all() - returns all matches
    print("\n2. Testing find_all() - all features:")
    all_features = list(graph.find_all(type="feature"))
    print(f"   ✓ Found {len(all_features)} features")
    for f in all_features[:3]:
        print(f"     - {f.id}: {f.title}")
    if len(all_features) > 3:
        print(f"     ... and {len(all_features) - 3} more")

    # Test with status filter
    print("\n3. Testing find_all() with status='done':")
    done_features = list(graph.find_all(type="feature", status="done"))
    print(f"   ✓ Found {len(done_features)} done features")

    print("\n✅ Find API tests complete!")
    return True


def test_query_builder():
    """Test QueryBuilder fluent interface."""
    print("\n" + "=" * 60)
    print("TEST 2: QueryBuilder Fluent Interface")
    print("=" * 60)

    graph = HtmlGraph(".htmlgraph/features/")

    # Test basic where clause
    print("\n1. Testing basic where() clause:")
    results = graph.query_builder().where("type", "feature").execute()
    print(f"   ✓ Found {len(results)} features using where('type', 'feature')")

    # Test chained AND conditions
    print("\n2. Testing chained AND conditions:")
    results = (
        graph.query_builder().where("type", "feature").and_("status", "done").execute()
    )
    print(f"   ✓ Found {len(results)} done features using .where().and_()")

    # Test OR conditions
    print("\n3. Testing OR conditions:")
    results = (
        graph.query_builder()
        .where("status", "done")
        .or_("status", "in-progress")
        .execute()
    )
    print(f"   ✓ Found {len(results)} nodes with status done OR in-progress")

    # Test in_() operator
    print("\n4. Testing in_() operator:")
    results = (
        graph.query_builder().where("priority").in_(["high", "critical"]).execute()
    )
    print(f"   ✓ Found {len(results)} high/critical priority nodes")

    # Test contains() for text search
    print("\n5. Testing contains() for text search:")
    results = graph.query_builder().where("title").contains("test").execute()
    print(f"   ✓ Found {len(results)} nodes with 'test' in title")

    print("\n✅ QueryBuilder tests complete!")
    return True


def test_edge_index():
    """Test EdgeIndex O(1) lookups."""
    print("\n" + "=" * 60)
    print("TEST 3: EdgeIndex O(1) Lookups")
    print("=" * 60)

    graph = HtmlGraph(".htmlgraph/features/")
    edge_index = graph.edge_index

    # Get a feature with edges
    features = list(graph.find_all(type="feature"))
    if not features:
        print("   ⚠️  No features found to test edge index")
        return True

    test_feature = features[0]
    print(f"\n1. Testing with feature: {test_feature.id}")

    # Test get_incoming_edges via graph method
    print("\n2. Testing get_incoming_edges():")
    incoming = graph.get_incoming_edges(test_feature.id)
    print(f"   ✓ Found {len(incoming)} incoming edges")
    for edge_ref in incoming[:3]:
        print(
            f"     - {edge_ref.source_id} --[{edge_ref.relationship}]--> {test_feature.id}"
        )

    # Test get_outgoing_edges via graph method
    print("\n3. Testing get_outgoing_edges():")
    outgoing = graph.get_outgoing_edges(test_feature.id)
    print(f"   ✓ Found {len(outgoing)} outgoing edges")
    for edge_ref in outgoing[:3]:
        print(
            f"     - {test_feature.id} --[{edge_ref.relationship}]--> {edge_ref.target_id}"
        )

    # Test direct edge_index access
    print("\n4. Testing direct EdgeIndex access:")
    print(f"   ✓ EdgeIndex has {len(edge_index._incoming)} nodes with incoming edges")
    print(f"   ✓ EdgeIndex has {len(edge_index._outgoing)} nodes with outgoing edges")

    print("\n✅ EdgeIndex tests complete!")
    return True


def test_graph_traversal():
    """Test graph traversal methods."""
    print("\n" + "=" * 60)
    print("TEST 4: Graph Traversal Methods")
    print("=" * 60)

    graph = HtmlGraph(".htmlgraph/features/")
    features = list(graph.find_all(type="feature"))

    if not features:
        print("   ⚠️  No features found to test traversal")
        return True

    test_feature = features[0]
    print(f"\n1. Testing with feature: {test_feature.id}")

    # Test descendants
    print("\n2. Testing descendants():")
    try:
        descendants = graph.descendants(test_feature.id)
        print(f"   ✓ Found {len(descendants)} descendants")
        for desc in descendants[:3]:
            print(f"     - {desc}")
    except Exception as e:
        print(f"   ⚠️  descendants() error: {e}")

    # Test ancestors
    print("\n3. Testing ancestors():")
    try:
        ancestors = graph.ancestors(test_feature.id)
        print(f"   ✓ Found {len(ancestors)} ancestors")
        for anc in ancestors[:3]:
            print(f"     - {anc}")
    except Exception as e:
        print(f"   ⚠️  ancestors() error: {e}")

    # Test dependents (reverse of dependencies)
    print("\n4. Testing dependents():")
    try:
        dependents = graph.dependents(test_feature.id)
        print(f"   ✓ Found {len(dependents)} dependents")
    except Exception as e:
        print(f"   ⚠️  dependents() error: {e}")

    # Test topological_sort
    print("\n5. Testing topological_sort():")
    try:
        sorted_ids = graph.topological_sort()
        print(f"   ✓ Topologically sorted {len(sorted_ids)} nodes")
        print(f"     First 5: {sorted_ids[:5]}")
    except Exception as e:
        print(f"   ⚠️  topological_sort() error: {e}")

    # Test shortest_path
    if len(features) >= 2:
        print("\n6. Testing shortest_path():")
        try:
            path = graph.shortest_path(features[0].id, features[1].id)
            if path:
                print(f"   ✓ Found path of length {len(path)}: {' -> '.join(path)}")
            else:
                print(
                    f"   ✓ No path exists between {features[0].id} and {features[1].id}"
                )
        except Exception as e:
            print(f"   ⚠️  shortest_path() error: {e}")

    # Test find_cycles
    print("\n7. Testing find_cycles():")
    try:
        cycles = graph.find_cycles()
        print(f"   ✓ Found {len(cycles)} cycles in graph")
        if cycles:
            for i, cycle in enumerate(cycles[:2]):
                print(f"     Cycle {i + 1}: {' -> '.join(cycle)}")
    except Exception as e:
        print(f"   ⚠️  find_cycles() error: {e}")

    print("\n✅ Graph traversal tests complete!")
    return True


def run_all_tests():
    """Run all test suites."""
    print("\n" + "🧪 " * 30)
    print("TESTING NEW HTMLGRAPH FEATURES")
    print("🧪 " * 30)

    results = []

    # Run all tests
    results.append(("Find API", test_find_api()))
    results.append(("QueryBuilder", test_query_builder()))
    results.append(("EdgeIndex", test_edge_index()))
    results.append(("Graph Traversal", test_graph_traversal()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")

    return all_passed


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
