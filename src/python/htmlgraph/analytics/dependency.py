from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

"""
Dependency-aware analytics for HtmlGraph.

Provides advanced graph analysis for project management:
- Critical path detection
- Bottleneck identification
- Parallelization opportunities
- Risk assessment
- Work prioritization
"""

from collections import deque
from typing import TYPE_CHECKING

from htmlgraph.dependency_models import (
    BottleneckNode,
    ImpactAnalysis,
    ParallelizationReport,
    ParallelLevel,
    RiskAssessment,
    RiskFactor,
    RiskNode,
    TaskRecommendation,
    TaskRecommendations,
)

if TYPE_CHECKING:
    from htmlgraph.graph import HtmlGraph
    from htmlgraph.models import Node


class DependencyAnalytics:
    """
    Dependency-aware analytics for project management insights.

    Analyzes the dependency graph to provide actionable insights:
    - What's blocking the most work? (bottlenecks)
    - What's the critical path? (longest dependency chain)
    - What can be worked on in parallel?
    - What should we prioritize next?
    - What are the high-risk dependencies?

    Performance: Uses internal caching to optimize transitive dependency calculations.
    Multiple calls to bottleneck detection or task recommendations reuse cached results.
    Call invalidate_cache() after graph structure changes to refresh the cache.

    Example:
        from htmlgraph import SDK

        sdk = SDK(agent="claude")
        dep = sdk.dep_analytics

        # Find bottlenecks (cached internally for performance)
        bottlenecks = dep.find_bottlenecks(top_n=5)
        for bn in bottlenecks:
            logger.info(f"{bn.title} blocks {bn.transitive_blocking} features")

        # Get work recommendations (reuses cached data)
        recs = dep.recommend_next_tasks(agent_count=3)
        for rec in recs.recommendations:
            logger.info(f"Work on: {rec.title} (unlocks {len(rec.unlocks)} features)")

        # After making graph changes, invalidate cache
        sdk.features.update(feature_id, status="done")
        dep.invalidate_cache()  # Refresh for accurate results
    """

    def __init__(self, graph: HtmlGraph):
        """
        Initialize dependency analytics with a graph.

        Args:
            graph: HtmlGraph instance to analyze
        """
        self.graph = graph
        self._edge_index = graph.edge_index
        self._transitive_cache: dict[str, set[str]] = {}

    # === Bottleneck Detection ===

    def find_bottlenecks(
        self,
        status_filter: list[str] | None = None,
        top_n: int = 10,
        min_impact: int = 1,
    ) -> list[BottleneckNode]:
        """
        Identify nodes that are blocking the most work.

        A bottleneck is a node that many other nodes depend on (high fan-in).
        The impact is measured by both direct and transitive blocking.

        Args:
            status_filter: Only consider nodes with these statuses
            top_n: Return top N bottlenecks
            min_impact: Minimum transitive blocking count to include

        Returns:
            List of BottleneckNode sorted by weighted impact (highest first)

        Example:
            bottlenecks = dep.find_bottlenecks(
                status_filter=["in-progress", "blocked"],
                top_n=5
            )
        """
        if status_filter is None:
            status_filter = ["todo", "in-progress", "blocked"]

        bottlenecks = []

        for node in self.graph.nodes.values():
            if node.status not in status_filter:
                continue

            # Count direct dependents (nodes that depend on this one)
            direct = self._count_direct_dependents(node.id)

            if direct < min_impact:
                continue

            # Count transitive dependents (all downstream nodes)
            transitive = self._count_transitive_dependents(node.id)

            # Calculate weighted impact
            priority_weight = {
                "critical": 3.0,
                "high": 2.0,
                "medium": 1.0,
                "low": 0.5,
            }.get(node.priority, 1.0)
            completion_pct = self._calculate_completion(node)
            incompletion_factor = (100.0 - completion_pct) / 100.0
            weighted_impact = transitive * priority_weight * incompletion_factor

            # Get list of blocked nodes
            blocked_nodes = self._get_direct_dependents(node.id)

            bottlenecks.append(
                BottleneckNode(
                    id=node.id,
                    title=node.title,
                    status=node.status,
                    priority=node.priority,
                    completion_pct=completion_pct,
                    direct_blocking=direct,
                    transitive_blocking=transitive,
                    weighted_impact=weighted_impact,
                    blocked_nodes=blocked_nodes,
                )
            )

        # Sort by weighted impact descending
        bottlenecks.sort(key=lambda x: x.weighted_impact, reverse=True)

        return bottlenecks[:top_n]

    def bottleneck_score(self, node_id: str) -> float:
        """
        Calculate bottleneck impact score for a single node.

        Args:
            node_id: Node to score

        Returns:
            Weighted impact score
        """
        node = self.graph.get(node_id)
        if not node:
            return 0.0

        self._count_direct_dependents(node_id)
        transitive = self._count_transitive_dependents(node_id)
        priority_weight = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}.get(
            node.priority, 1.0
        )
        completion_pct = self._calculate_completion(node)
        incompletion_factor = (100.0 - completion_pct) / 100.0

        return transitive * priority_weight * incompletion_factor

    # === Parallelization Analysis ===

    def find_parallelizable_work(
        self, status: str = "todo", max_levels: int | None = None
    ) -> ParallelizationReport:
        """
        Identify work that can be done in parallel.

        Groups nodes by dependency level (topological layers) and identifies
        which nodes can be worked on simultaneously without conflicts.

        Args:
            status: Only consider nodes with this status
            max_levels: Maximum number of dependency levels to analyze

        Returns:
            ParallelizationReport with levels and suggestions

        Example:
            report = dep.find_parallelizable_work(status="todo")
            logger.info(f"Can work on {report.max_parallelism} features in parallel")
        """
        # Get dependency levels (topological layers)
        levels = self.dependency_levels(status_filter=[status])

        if max_levels:
            levels = levels[:max_levels]

        parallel_levels = []
        max_parallelism = 0

        for level_idx, node_ids in enumerate(levels):
            if not node_ids:
                continue

            # Find independent groups within this level
            independent_groups = self._find_independent_groups(list(node_ids))

            max_parallel = len(node_ids)
            max_parallelism = max(max_parallelism, max_parallel)

            parallel_levels.append(
                ParallelLevel(
                    level=level_idx,
                    nodes=list(node_ids),
                    max_parallel=max_parallel,
                    independent_groups=independent_groups,
                )
            )

        # Suggest assignments (round-robin for now)
        suggestions = []
        if parallel_levels and parallel_levels[0].nodes:
            for i, node_id in enumerate(parallel_levels[0].nodes[:3]):  # Top 3
                agent_name = f"agent-{i + 1}"
                suggestions.append((agent_name, [node_id]))

        return ParallelizationReport(
            max_parallelism=max_parallelism,
            dependency_levels=parallel_levels,
            suggested_assignments=suggestions,
        )

    def dependency_levels(
        self, status_filter: list[str] | None = None
    ) -> list[set[str]]:
        """
        Group nodes by dependency level (topological layers).

        Level 0 = nodes with no dependencies
        Level 1 = nodes that only depend on level 0
        Level 2 = nodes that depend on level 0 or 1
        etc.

        Args:
            status_filter: Only include nodes with these statuses

        Returns:
            List of sets, where each set contains node IDs at that level
        """
        # Get all nodes matching filter
        if status_filter:
            nodes_to_process = [
                n for n in self.graph.nodes.values() if n.status in status_filter
            ]
        else:
            nodes_to_process = list(self.graph.nodes.values())

        node_ids = {n.id for n in nodes_to_process}

        # Calculate in-degree for each node (only counting edges within our filtered set)
        in_degree = {}
        for node in nodes_to_process:
            count = 0
            for edge_ref in self._edge_index.get_incoming(node.id):
                if edge_ref.source_id in node_ids:
                    count += 1
            in_degree[node.id] = count

        levels = []
        processed: set[str] = set()

        while len(processed) < len(node_ids):
            # Find all nodes with in-degree 0 (no unprocessed dependencies)
            current_level = set()
            for node_id in node_ids:
                if node_id in processed:
                    continue
                if in_degree[node_id] == 0:
                    current_level.add(node_id)

            if not current_level:
                # Circular dependency or disconnected - add remaining nodes
                remaining = node_ids - processed
                if remaining:
                    levels.append(remaining)
                break

            levels.append(current_level)
            processed.update(current_level)

            # Decrease in-degree for neighbors
            for node_id in current_level:
                for edge_ref in self._edge_index.get_outgoing(node_id):
                    if (
                        edge_ref.target_id in in_degree
                        and edge_ref.target_id not in processed
                    ):
                        in_degree[edge_ref.target_id] -= 1

        return levels

    def max_parallelism(self, status: str = "todo") -> int:
        """
        Calculate maximum number of features that can be worked on simultaneously.

        Args:
            status: Status filter for nodes

        Returns:
            Maximum number of parallel tasks
        """
        levels = self.dependency_levels(status_filter=[status])
        if not levels:
            return 0
        return max(len(level) for level in levels)

    # === Risk Assessment ===

    def assess_dependency_risk(self, spof_threshold: int = 3) -> RiskAssessment:
        """
        Assess risk based on dependency structure.

        Identifies:
        - Single points of failure (high fan-in)
        - Nodes on deep dependency chains
        - Circular dependencies
        - Orphaned nodes (no dependents)

        Args:
            spof_threshold: Minimum dependents to consider SPOF

        Returns:
            RiskAssessment with identified risks
        """
        high_risk = []

        # Find single points of failure
        spofs = self.single_points_of_failure(min_dependents=spof_threshold)
        for node_id in spofs:
            node = self.graph.get(node_id)
            if not node:
                continue

            dependents_count = self._count_transitive_dependents(node_id)
            risk_factors = [
                RiskFactor(
                    type="spof",
                    severity="high" if dependents_count > 10 else "medium",
                    description=f"Blocks {dependents_count} features with no alternative paths",
                    mitigation="Consider breaking into smaller independent features",
                )
            ]

            risk_score = min(dependents_count / 20.0, 1.0)  # Cap at 1.0

            high_risk.append(
                RiskNode(
                    id=node_id,
                    title=node.title,
                    risk_score=risk_score,
                    risk_factors=risk_factors,
                )
            )

        # Find circular dependencies
        cycles = self.graph.find_cycles()

        # Find orphaned nodes
        orphaned = []
        for node in self.graph.nodes.values():
            if node.status == "done":
                continue
            dependents = self._count_direct_dependents(node.id)
            if dependents == 0:
                orphaned.append(node.id)

        # Generate recommendations
        recommendations = []
        for risk_node in high_risk[:3]:
            recommendations.append(
                f"Break {risk_node.title} into smaller features to reduce SPOF risk"
            )
        if cycles:
            recommendations.append(
                f"Resolve {len(cycles)} circular dependencies detected"
            )
        if orphaned:
            recommendations.append(
                f"Review {len(orphaned)} orphaned nodes with no dependents"
            )

        return RiskAssessment(
            high_risk=high_risk,
            circular_dependencies=cycles,
            orphaned_nodes=orphaned,
            recommendations=recommendations,
        )

    def single_points_of_failure(self, min_dependents: int = 3) -> list[str]:
        """
        Identify nodes with high fan-in (many dependents).

        Args:
            min_dependents: Minimum number of dependents to consider SPOF

        Returns:
            List of node IDs that are SPOFs
        """
        spofs = []
        for node in self.graph.nodes.values():
            if node.status == "done":
                continue

            dependents = self._count_direct_dependents(node.id)
            if dependents >= min_dependents:
                spofs.append(node.id)

        return spofs

    # === Work Prioritization ===

    def recommend_next_tasks(
        self, agent_count: int = 1, status: str = "todo", lookahead: int = 3
    ) -> TaskRecommendations:
        """
        Recommend which tasks to work on next.

        Prioritization considers:
        - How many features this unlocks (transitive blocking)
        - User-assigned priority
        - Whether dependencies are complete
        - Whether it's on the critical path

        Args:
            agent_count: Number of agents/developers available
            status: Status filter for candidate tasks
            lookahead: How many tasks to recommend

        Returns:
            TaskRecommendations with prioritized suggestions

        Example:
            recs = dep.recommend_next_tasks(agent_count=3)
            for rec in recs.recommendations:
                logger.info(f"Work on: {rec.title}")
        """
        # Get all nodes with target status
        candidates = [n for n in self.graph.nodes.values() if n.status == status]

        # Filter to only nodes with all dependencies complete
        ready_nodes = []
        for node in candidates:
            if self._all_dependencies_complete(node.id):
                ready_nodes.append(node)

        # Score each node
        scored = []
        for node in ready_nodes:
            score = self.prioritization_score(node.id)

            # Calculate what this unlocks
            unlocks = self._get_direct_dependents(node.id)
            effort = self._get_effort(node)

            # Build reasons
            reasons = []
            transitive = self._count_transitive_dependents(node.id)
            if transitive > 5:
                reasons.append(f"Unlocks {transitive} downstream features")
            if node.priority in ["high", "critical"]:
                reasons.append(f"{node.priority.title()} priority")
            if self._is_on_critical_path(node.id):
                reasons.append("On critical path")
            if len(unlocks) > 0:
                reasons.append(f"Directly unblocks {len(unlocks)} features")
            if not reasons:
                reasons.append("Ready to start (all dependencies complete)")

            scored.append(
                (
                    score,
                    TaskRecommendation(
                        id=node.id,
                        title=node.title,
                        priority=node.priority,
                        score=score,
                        reasons=reasons,
                        estimated_effort=effort,
                        unlocks=unlocks,
                    ),
                )
            )

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Take top recommendations
        recommendations = [rec for _, rec in scored[: lookahead * agent_count]]

        # Find parallel suggestions
        parallel_suggestions = []
        if len(recommendations) >= 2:
            # Simple approach: suggest non-overlapping dependency chains
            for i in range(0, min(len(recommendations), agent_count * 2), 2):
                if i + 1 < len(recommendations):
                    parallel_suggestions.append(
                        [recommendations[i].id, recommendations[i + 1].id]
                    )

        return TaskRecommendations(
            recommendations=recommendations, parallel_suggestions=parallel_suggestions
        )

    def prioritization_score(
        self, node_id: str, weights: dict[str, float] | None = None
    ) -> float:
        """
        Calculate priority score for a node.

        Score formula:
        (transitive_blocking * 2) +
        (priority_weight * 1.5) +
        (-dependency_count * 0.5) +
        (is_on_critical_path * 3)

        Args:
            node_id: Node to score
            weights: Optional custom weights

        Returns:
            Prioritization score (higher = more urgent)
        """
        if weights is None:
            weights = {
                "transitive_blocking": 2.0,
                "priority": 1.5,
                "dependency_penalty": -0.5,
                "critical_path": 3.0,
            }

        node = self.graph.get(node_id)
        if not node:
            return 0.0

        score = 0.0

        # Transitive blocking (how much work this unlocks)
        transitive = self._count_transitive_dependents(node_id)
        score += transitive * weights["transitive_blocking"]

        # User priority
        priority_values = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        priority_value = priority_values.get(node.priority, 2)
        score += priority_value * weights["priority"]

        # Dependency count (fewer dependencies = easier to start)
        dep_count = len(self._edge_index.get_outgoing(node_id))
        score += dep_count * weights["dependency_penalty"]

        # Critical path bonus
        if self._is_on_critical_path(node_id):
            score += weights["critical_path"]

        return score

    # === Utility Methods ===

    def fan_in_fan_out(self, node_id: str) -> tuple[int, int]:
        """
        Get fan-in and fan-out counts for a node.

        Args:
            node_id: Node to analyze

        Returns:
            (fan_in, fan_out) tuple
        """
        fan_in = len(self._edge_index.get_incoming(node_id))
        fan_out = len(self._edge_index.get_outgoing(node_id))
        return (fan_in, fan_out)

    def impact_analysis(
        self, node_id: str, include_done: bool = False
    ) -> ImpactAnalysis:
        """
        Analyze the downstream impact of a node.

        Args:
            node_id: Node to analyze
            include_done: Include completed nodes in analysis

        Returns:
            ImpactAnalysis with dependency impact
        """
        direct = self._count_direct_dependents(node_id)
        transitive = self._count_transitive_dependents(
            node_id, include_done=include_done
        )
        affected = self._get_all_transitive_dependents(
            node_id, include_done=include_done
        )

        # Calculate what % of total work this represents
        total_nodes = len(
            [n for n in self.graph.nodes.values() if include_done or n.status != "done"]
        )
        completion_impact = (
            (transitive / total_nodes * 100.0) if total_nodes > 0 else 0.0
        )

        return ImpactAnalysis(
            node_id=node_id,
            direct_dependents=direct,
            transitive_dependents=transitive,
            affected_nodes=affected,
            completion_impact=completion_impact,
        )

    # === Private Helper Methods ===

    def _count_direct_dependents(self, node_id: str) -> int:
        """Count nodes that directly depend on this node."""
        return len(self._edge_index.get_incoming(node_id))

    def _get_direct_dependents(self, node_id: str) -> list[str]:
        """Get list of node IDs that directly depend on this node."""
        return [
            edge_ref.source_id for edge_ref in self._edge_index.get_incoming(node_id)
        ]

    def _count_transitive_dependents(
        self, node_id: str, include_done: bool = False
    ) -> int:
        """
        Count all downstream nodes that transitively depend on this node.

        Uses cached results when available to improve performance from O(V²+VE) to O(V+E)
        for repeated calls.
        """
        transitive_set = self._get_or_compute_transitive(node_id, include_done)
        return len(transitive_set)

    def _get_all_transitive_dependents(
        self, node_id: str, include_done: bool = False
    ) -> list[str]:
        """Get all downstream nodes (BFS traversal of dependents)."""
        visited = set()
        queue = deque([node_id])
        visited.add(node_id)

        while queue:
            current = queue.popleft()
            for edge_ref in self._edge_index.get_incoming(current):
                if edge_ref.source_id not in visited:
                    # Check if we should include based on status
                    source_node = self.graph.get(edge_ref.source_id)
                    if source_node and (include_done or source_node.status != "done"):
                        visited.add(edge_ref.source_id)
                        queue.append(edge_ref.source_id)

        # Remove the original node from results
        visited.discard(node_id)
        return list(visited)

    def _calculate_completion(self, node: Node) -> float:
        """Calculate completion percentage for a node."""
        if node.status == "done":
            return 100.0
        if not node.steps:
            return 0.0

        completed = sum(1 for step in node.steps if step.completed)
        return (completed / len(node.steps)) * 100.0

    def _get_effort(self, node: Node) -> float:
        """Get effort estimate from node properties."""
        return float(node.properties.get("effort", 0.0))

    def _all_dependencies_complete(self, node_id: str) -> bool:
        """Check if all dependencies of a node are complete."""
        for edge_ref in self._edge_index.get_outgoing(node_id):
            dep_node = self.graph.get(edge_ref.target_id)
            if dep_node and dep_node.status != "done":
                return False
        return True

    def _is_on_critical_path(self, node_id: str) -> bool:
        """Check if node is on the critical path (simplified heuristic)."""
        # Simplified: node is on critical path if it has high transitive impact
        # A full implementation would compute actual critical path
        transitive = self._count_transitive_dependents(node_id)
        return transitive > 5

    def _find_independent_groups(self, node_ids: list[str]) -> list[list[str]]:
        """
        Find groups of nodes that don't share dependencies.

        Args:
            node_ids: Nodes to group

        Returns:
            List of independent groups
        """
        # Simple implementation: return individual nodes for now
        # A more sophisticated version would use graph coloring
        return [[nid] for nid in node_ids]

    def _get_or_compute_transitive(
        self, node_id: str, include_done: bool = False
    ) -> set[str]:
        """
        Get or compute transitive dependents with caching.

        Uses a cache to avoid redundant BFS traversals. The cache key combines
        node_id and include_done flag to ensure correct results for both cases.

        Args:
            node_id: Node to analyze
            include_done: Whether to include completed nodes

        Returns:
            Set of node IDs that transitively depend on this node
        """
        cache_key = f"{node_id}:{include_done}"

        if cache_key in self._transitive_cache:
            return self._transitive_cache[cache_key]

        # Compute transitive dependents via BFS
        dependents = self._get_all_transitive_dependents(
            node_id, include_done=include_done
        )
        dependents_set = set(dependents)

        # Cache the result
        self._transitive_cache[cache_key] = dependents_set

        return dependents_set

    def invalidate_cache(self) -> None:
        """
        Clear the transitive dependency cache.

        Call this method after making structural changes to the graph
        (adding/removing nodes or edges) to ensure cached results remain accurate.

        Example:
            analytics = sdk.dep_analytics
            analytics.invalidate_cache()  # After graph updates
            bottlenecks = analytics.find_bottlenecks()  # Fresh calculation
        """
        self._transitive_cache.clear()
