#!/usr/bin/env python3
"""
Demo script to test dependency analytics features.

Tests the newly implemented dependency-aware analytics:
- Bottleneck detection
- Parallelization analysis
- Work recommendations
- Risk assessment
"""

from htmlgraph import HtmlGraph
from htmlgraph.dependency_analytics import DependencyAnalytics
from htmlgraph.models import Node, Edge
import tempfile


def create_sample_project():
    """Create a realistic project graph for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        graph = HtmlGraph(tmpdir)

        # Create a realistic dependency structure:
        # Database -> API -> Frontend
        # Database also blocks Auth and Cache

        # Foundation layer (no dependencies)
        db = Node(
            id="feature-db",
            title="Database Schema",
            type="feature",
            status="in-progress",
            priority="critical",
            properties={"effort": 8.0}
        )

        # Mid layer (depends on DB)
        api = Node(
            id="feature-api",
            title="REST API",
            type="feature",
            status="todo",
            priority="high",
            edges={"depends_on": [Edge(target_id="feature-db", relationship="depends_on")]},
            properties={"effort": 12.0}
        )

        auth = Node(
            id="feature-auth",
            title="Authentication",
            type="feature",
            status="todo",
            priority="high",
            edges={"depends_on": [Edge(target_id="feature-db", relationship="depends_on")]},
            properties={"effort": 6.0}
        )

        cache = Node(
            id="feature-cache",
            title="Redis Cache",
            type="feature",
            status="todo",
            priority="medium",
            edges={"depends_on": [Edge(target_id="feature-db", relationship="depends_on")]},
            properties={"effort": 4.0}
        )

        # Top layer (depends on API and Auth)
        frontend = Node(
            id="feature-frontend",
            title="React Frontend",
            type="feature",
            status="todo",
            priority="high",
            edges={
                "depends_on": [
                    Edge(target_id="feature-api", relationship="depends_on"),
                    Edge(target_id="feature-auth", relationship="depends_on")
                ]
            },
            properties={"effort": 16.0}
        )

        dashboard = Node(
            id="feature-dashboard",
            title="Admin Dashboard",
            type="feature",
            status="todo",
            priority="medium",
            edges={
                "depends_on": [
                    Edge(target_id="feature-api", relationship="depends_on"),
                    Edge(target_id="feature-auth", relationship="depends_on")
                ]
            },
            properties={"effort": 10.0}
        )

        # Independent feature (no dependencies)
        docs = Node(
            id="feature-docs",
            title="Documentation",
            type="feature",
            status="todo",
            priority="low",
            properties={"effort": 5.0}
        )

        # Add all nodes
        for node in [db, api, auth, cache, frontend, dashboard, docs]:
            graph.add(node)

        return graph


def test_bottleneck_detection(dep: DependencyAnalytics):
    """Test bottleneck detection."""
    print("\n" + "="*70)
    print("TEST 1: Bottleneck Detection")
    print("="*70)

    bottlenecks = dep.find_bottlenecks(top_n=5)

    print(f"\nFound {len(bottlenecks)} bottlenecks:")
    for i, bn in enumerate(bottlenecks, 1):
        print(f"\n{i}. {bn.title}")
        print(f"   Status: {bn.status} | Priority: {bn.priority}")
        print(f"   Direct blocking: {bn.direct_blocking} features")
        print(f"   Transitive blocking: {bn.transitive_blocking} features")
        print(f"   Weighted impact: {bn.weighted_impact:.2f}")
        if bn.blocked_nodes:
            print(f"   Blocks: {', '.join(bn.blocked_nodes[:3])}")

    return len(bottlenecks) > 0


def test_parallelization(dep: DependencyAnalytics):
    """Test parallelization analysis."""
    print("\n" + "="*70)
    print("TEST 2: Parallelization Analysis")
    print("="*70)

    report = dep.find_parallelizable_work(status="todo")

    print(f"\nMax parallelism: {report.max_parallelism} features can be worked on simultaneously")
    print(f"\nDependency levels ({len(report.dependency_levels)} levels):")

    for level in report.dependency_levels:
        print(f"\nLevel {level.level} ({level.max_parallel} parallel):")
        for node_id in level.nodes:
            print(f"  - {node_id}")

    if report.suggested_assignments:
        print(f"\nSuggested agent assignments:")
        for agent, tasks in report.suggested_assignments:
            print(f"  {agent}: {', '.join(tasks)}")

    return report.max_parallelism > 0


def test_work_recommendations(dep: DependencyAnalytics):
    """Test work prioritization."""
    print("\n" + "="*70)
    print("TEST 3: Work Recommendations")
    print("="*70)

    recs = dep.recommend_next_tasks(agent_count=3, lookahead=5)

    print(f"\nTop {len(recs.recommendations)} recommended tasks:")
    for i, rec in enumerate(recs.recommendations, 1):
        print(f"\n{i}. {rec.title}")
        print(f"   Priority: {rec.priority} | Score: {rec.score:.2f}")
        print(f"   Estimated effort: {rec.estimated_effort:.1f} hours")
        print(f"   Unlocks: {len(rec.unlocks)} features")
        print(f"   Reasons:")
        for reason in rec.reasons:
            print(f"     - {reason}")

    if recs.parallel_suggestions:
        print(f"\nParallel work suggestions:")
        for suggestion in recs.parallel_suggestions:
            print(f"  - Work on {' and '.join(suggestion)} in parallel")

    return len(recs.recommendations) > 0


def test_risk_assessment(dep: DependencyAnalytics):
    """Test risk assessment."""
    print("\n" + "="*70)
    print("TEST 4: Risk Assessment")
    print("="*70)

    risk = dep.assess_dependency_risk(spof_threshold=2)

    print(f"\nHigh-risk nodes: {len(risk.high_risk)}")
    for node in risk.high_risk:
        print(f"\n  {node.title}")
        print(f"    Risk score: {node.risk_score:.2f}")
        print(f"    Risk factors:")
        for factor in node.risk_factors:
            print(f"      - [{factor.severity}] {factor.description}")
            print(f"        Mitigation: {factor.mitigation}")

    if risk.circular_dependencies:
        print(f"\n⚠️  Circular dependencies detected: {len(risk.circular_dependencies)}")
        for cycle in risk.circular_dependencies:
            print(f"    - {' -> '.join(cycle)}")

    if risk.orphaned_nodes:
        print(f"\n⚠️  Orphaned nodes (no dependents): {len(risk.orphaned_nodes)}")
        for node_id in risk.orphaned_nodes[:5]:
            print(f"    - {node_id}")

    if risk.recommendations:
        print(f"\nRecommendations:")
        for rec in risk.recommendations:
            print(f"  • {rec}")

    return True


def test_impact_analysis(dep: DependencyAnalytics):
    """Test impact analysis."""
    print("\n" + "="*70)
    print("TEST 5: Impact Analysis")
    print("="*70)

    # Analyze impact of database feature
    impact = dep.impact_analysis("feature-db")

    print(f"\nImpact analysis for: feature-db")
    print(f"  Direct dependents: {impact.direct_dependents}")
    print(f"  Transitive dependents: {impact.transitive_dependents}")
    print(f"  Completion impact: {impact.completion_impact:.1f}% of total work")
    print(f"  Affected nodes: {', '.join(impact.affected_nodes[:5])}")

    return impact.transitive_dependents > 0


def run_all_tests():
    """Run all dependency analytics tests."""
    print("\n" + "🔍 "*35)
    print("DEPENDENCY ANALYTICS DEMONSTRATION")
    print("🔍 "*35)

    # Create sample project
    print("\nCreating sample project with realistic dependencies...")
    graph = create_sample_project()
    print(f"✓ Created graph with {len(graph._nodes)} nodes")

    # Initialize dependency analytics
    dep = DependencyAnalytics(graph)
    print(f"✓ Initialized DependencyAnalytics")

    # Run tests
    results = []
    results.append(("Bottleneck Detection", test_bottleneck_detection(dep)))
    results.append(("Parallelization Analysis", test_parallelization(dep)))
    results.append(("Work Recommendations", test_work_recommendations(dep)))
    results.append(("Risk Assessment", test_risk_assessment(dep)))
    results.append(("Impact Analysis", test_impact_analysis(dep)))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All dependency analytics features working!")
    else:
        print("\n⚠️  Some features need attention")

    return all_passed


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
