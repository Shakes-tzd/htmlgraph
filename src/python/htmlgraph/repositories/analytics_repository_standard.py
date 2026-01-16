"""
StandardAnalyticsRepository - Unified analytics using Feature/Track repositories.

Composes FeatureRepository and TrackRepository to provide:
- Work recommendations with multi-criteria scoring
- Dependency analysis and critical path detection
- Project health metrics and completion estimates
- Blocked/blocking item detection

NO direct data access - all data through repositories.
"""

from collections import defaultdict, deque
from typing import Any

from .analytics_repository import (
    AnalysisError,
    AnalyticsRepository,
    DependencyAnalysis,
    InvalidItemError,
    WorkRecommendation,
)
from .feature_repository import FeatureRepository
from .shared_cache import SharedCache
from .track_repository import TrackRepository

# Priority scoring weights
PRIORITY_WEIGHTS = {
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "critical": 1.0,
}


class StandardAnalyticsRepository(AnalyticsRepository):
    """
    Standard implementation of AnalyticsRepository.

    Features:
    - Composes Feature and Track repositories
    - Multi-criteria work recommendations
    - Transitive dependency analysis
    - Critical path detection
    - Comprehensive caching with invalidation

    Performance:
    - recommend_next_work(): O(n) with caching
    - analyze_dependencies(): O(n) graph traversal, cached
    - calculate_priority(): O(1) if cached, O(n) if not
    - get_critical_path(): O(n) computed once, cached
    """

    def __init__(
        self,
        feature_repo: FeatureRepository,
        track_repo: TrackRepository,
        cache: SharedCache,
    ):
        """Initialize analytics repository with dependencies."""
        self.feature_repo = feature_repo
        self.track_repo = track_repo
        self.cache = cache

    # ===== RECOMMENDATION OPERATIONS =====

    def recommend_next_work(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        min_priority: float = 0.0,
    ) -> list[WorkRecommendation]:
        """Get prioritized recommendations for next work items."""
        try:
            # Get all work items
            items = self.get_work_items(
                status=filters.get("status") if filters else None, include_tracks=True
            )

            # Apply additional filters
            if filters:
                items = self._apply_filters(items, filters)

            # Score each item
            recommendations = []
            for item in items:
                item_id = getattr(item, "id", str(item))

                # Calculate priority score
                try:
                    priority_score = self.calculate_priority(item_id)
                except (InvalidItemError, AnalysisError):
                    continue

                # Skip if below threshold
                if priority_score < min_priority:
                    continue

                # Get dependency analysis
                try:
                    analysis = self.analyze_dependencies(item_id)
                except (InvalidItemError, AnalysisError):
                    analysis = DependencyAnalysis(
                        item_id=item_id,
                        dependencies=[],
                        blocking=[],
                        blocked_by=[],
                        critical_path=False,
                        blocked_count=0,
                        dependency_count=0,
                    )

                # Build recommendation
                title = getattr(item, "title", item_id)
                rationale = self._build_rationale(item, analysis, priority_score)

                recommendation = WorkRecommendation(
                    item_id=item_id,
                    title=title,
                    priority_score=priority_score,
                    rationale=rationale,
                    estimated_impact=self._estimate_impact(item, analysis),
                    blocking_count=analysis.blocked_count,
                    dependency_count=analysis.dependency_count,
                )

                recommendations.append(recommendation)

            # Sort by priority score (descending)
            recommendations.sort(key=lambda r: r.priority_score, reverse=True)

            # Return top N
            return recommendations[:limit]

        except Exception as e:
            raise AnalysisError(f"Failed to generate recommendations: {e}")

    def analyze_dependencies(self, item_id: str) -> DependencyAnalysis:
        """Compute complete dependency analysis for a work item."""
        # Check cache
        cache_key = f"dependency:{item_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            result: DependencyAnalysis = cached
            return result

        try:
            # Get item
            item = self._get_item(item_id)
            if item is None:
                raise InvalidItemError(item_id)

            # Build dependency graph
            all_deps = self._get_transitive_dependencies(item_id)
            blocking = self._get_blocking_items(item_id)

            # Get items blocking this one (dependencies that are incomplete)
            blocked_by = []
            direct_deps = self._get_direct_dependencies(item_id)
            for dep_id in direct_deps:
                dep_item = self._get_item(dep_id)
                if dep_item and self._is_incomplete(dep_item):
                    blocked_by.append(dep_id)

            # Check if on critical path
            critical_path = self.is_on_critical_path(item_id)

            analysis = DependencyAnalysis(
                item_id=item_id,
                dependencies=all_deps,
                blocking=blocking,
                blocked_by=blocked_by,
                critical_path=critical_path,
                blocked_count=len(blocking),
                dependency_count=len(all_deps),
            )

            # Cache result
            self.cache.set(cache_key, analysis, ttl=3600)

            return analysis

        except InvalidItemError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to analyze dependencies for {item_id}: {e}")

    def calculate_priority(self, item_id: str) -> float:
        """Calculate normalized priority score for item."""
        # Check cache
        cache_key = f"priority:{item_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            result: float = cached
            return result

        try:
            # Get item
            item = self._get_item(item_id)
            if item is None:
                raise InvalidItemError(item_id)

            # Base priority from item
            priority_str = getattr(item, "priority", "medium").lower()
            base_score = PRIORITY_WEIGHTS.get(priority_str, 0.5)

            # Get dependency analysis
            analysis = self.analyze_dependencies(item_id)

            # Boost if blocking many items
            blocking_boost = min(analysis.blocked_count * 0.1, 0.3)

            # Boost if on critical path
            critical_boost = 0.2 if analysis.critical_path else 0.0

            # Penalty if blocked
            blocked_penalty = -0.2 if analysis.is_blocked else 0.0

            # Calculate final score (clamped to 0-1)
            score = base_score + blocking_boost + critical_boost + blocked_penalty
            score = max(0.0, min(1.0, score))

            # Cache result
            self.cache.set(cache_key, score, ttl=3600)

            return score

        except InvalidItemError:
            raise
        except Exception as e:
            raise AnalysisError(f"Failed to calculate priority for {item_id}: {e}")

    # ===== WORK ITEM QUERIES =====

    def get_work_items(
        self, status: str | None = None, include_tracks: bool = True
    ) -> list[Any]:
        """Get all work items (features and optionally tracks)."""
        items = []

        # Get features
        try:
            features = self.feature_repo.list()
            if status:
                features = [f for f in features if getattr(f, "status", None) == status]
            items.extend(features)
        except Exception:
            pass

        # Get tracks
        if include_tracks:
            try:
                tracks = self.track_repo.list()
                if status:
                    tracks = [t for t in tracks if getattr(t, "status", None) == status]
                items.extend(tracks)
            except Exception:
                pass

        return items

    def find_blocked_items(self) -> list[str]:
        """Find all work items currently blocked by incomplete dependencies."""
        # Check cache
        cache_key = "blocking:all_blocked"
        cached = self.cache.get(cache_key)
        if cached is not None:
            result: list[str] = cached
            return result

        blocked = []
        all_items = self.get_work_items(include_tracks=True)

        for item in all_items:
            item_id = getattr(item, "id", str(item))
            try:
                analysis = self.analyze_dependencies(item_id)
                if analysis.is_blocked:
                    blocked.append(item_id)
            except (InvalidItemError, AnalysisError):
                continue

        # Cache result
        self.cache.set(cache_key, blocked, ttl=1800)

        return list(blocked)

    def find_blocking_items(self, item_id: str) -> list[str]:
        """Find what items are blocked by the given item."""
        try:
            analysis = self.analyze_dependencies(item_id)
            return analysis.blocking
        except (InvalidItemError, AnalysisError):
            raise InvalidItemError(item_id)

    # ===== CRITICAL PATH ANALYSIS =====

    def get_critical_path(self) -> list[str]:
        """Get items on the critical path to project completion."""
        # Check cache
        cache_key = "critical_path:path"
        cached = self.cache.get(cache_key)
        if cached is not None:
            result: list[str] = cached
            return result

        try:
            # Build full dependency graph
            all_items = self.get_work_items(include_tracks=True)
            graph = self._build_dependency_graph(all_items)

            # Find longest path (critical path)
            critical_path = self._compute_critical_path(graph)

            # Cache result
            self.cache.set(cache_key, critical_path, ttl=3600)

            return list(critical_path)

        except Exception as e:
            raise AnalysisError(f"Failed to compute critical path: {e}")

    def is_on_critical_path(self, item_id: str) -> bool:
        """Check if item is on critical path."""
        try:
            path = self.get_critical_path()
            return item_id in path
        except (InvalidItemError, AnalysisError):
            return False

    # ===== METRICS & HEALTH =====

    def cache_metrics(self) -> dict[str, Any]:
        """Get cache performance metrics."""
        return self.cache.stats()

    def invalidate_analytics_cache(self, item_id: str | None = None) -> None:
        """Invalidate cached analytics for item or all items."""
        if item_id:
            self.cache.delete(f"dependency:{item_id}")
            self.cache.delete(f"priority:{item_id}")
            self.cache.delete_pattern(f"dependency:*:blocking_for_{item_id}")
        else:
            self.cache.invalidate_analytics()

    # ===== ADVANCED QUERIES =====

    def find_dependency_cycles(self) -> list[list[str]]:
        """Find any circular dependencies in the project graph."""
        all_items = self.get_work_items(include_tracks=True)
        graph = self._build_dependency_graph(all_items)

        cycles = []
        visited = set()
        rec_stack = set()

        def dfs_cycle(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs_cycle(neighbor, path[:])
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            rec_stack.remove(node)

        for item_id in graph:
            if item_id not in visited:
                dfs_cycle(item_id, [])

        return cycles

    def suggest_parallelizable_work(self) -> list[list[str]]:
        """Suggest groups of work that can be done in parallel."""
        all_items = self.get_work_items(status="todo", include_tracks=True)
        graph = self._build_dependency_graph(all_items)

        # Topological sort to find waves of parallel work
        waves = []
        remaining = set(getattr(item, "id", str(item)) for item in all_items)

        while remaining:
            # Find items with no incomplete dependencies
            wave = []
            for item_id in list(remaining):
                deps = graph.get(item_id, [])
                if all(dep not in remaining for dep in deps):
                    wave.append(item_id)

            if not wave:
                break  # Cycle or blocked

            waves.append(wave)
            remaining -= set(wave)

        return waves

    def project_completion_estimate(self) -> dict[str, Any]:
        """Estimate project completion time based on current state."""
        all_items = self.get_work_items(include_tracks=True)

        # Count by status
        status_counts: dict[str, int] = defaultdict(int)
        for item in all_items:
            status = getattr(item, "status", "unknown")
            status_counts[status] += 1

        # Get critical path length
        try:
            critical_path = self.get_critical_path()
            critical_path_length = len(critical_path)
        except AnalysisError:
            critical_path_length = 0

        # Get blocked items
        blocked = self.find_blocked_items()

        # Incomplete items
        incomplete = [
            item
            for item in all_items
            if getattr(item, "status", "") not in ["done", "completed"]
        ]

        # Estimate (simplified: assume 1 day per critical path item)
        estimated_days = critical_path_length
        worst_case_days = len(incomplete)  # If all serial

        return {
            "items_remaining": len(incomplete),
            "critical_path_length": critical_path_length,
            "estimated_days": estimated_days,
            "blocking_items": len(blocked),
            "worst_case_days": worst_case_days,
            "status_breakdown": dict(status_counts),
        }

    # ===== HELPER METHODS =====

    def _get_item(self, item_id: str) -> Any | None:
        """Get item by ID from either repository."""
        # Try feature first
        item = self.feature_repo.get(item_id)
        if item:
            return item

        # Try track
        item = self.track_repo.get(item_id)
        return item

    def _get_direct_dependencies(self, item_id: str) -> list[str]:
        """Get direct dependencies of an item."""
        item = self._get_item(item_id)
        if not item:
            return []

        deps = getattr(item, "dependencies", [])
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(",") if d.strip()]

        return deps

    def _get_transitive_dependencies(self, item_id: str) -> list[str]:
        """Get all transitive dependencies (BFS)."""
        visited = set()
        queue = deque([item_id])
        all_deps = []

        while queue:
            current = queue.popleft()
            if current in visited:
                continue

            visited.add(current)
            deps = self._get_direct_dependencies(current)

            for dep in deps:
                if dep not in visited and dep != item_id:
                    all_deps.append(dep)
                    queue.append(dep)

        return all_deps

    def _get_blocking_items(self, item_id: str) -> list[str]:
        """Get items that depend on this item."""
        all_items = self.get_work_items(include_tracks=True)
        blocking = []

        for item in all_items:
            current_id = getattr(item, "id", str(item))
            if current_id == item_id:
                continue

            deps = self._get_direct_dependencies(current_id)
            if item_id in deps:
                blocking.append(current_id)

        return blocking

    def _is_incomplete(self, item: Any) -> bool:
        """Check if item is incomplete."""
        status = getattr(item, "status", "").lower()
        return status not in ["done", "completed"]

    def _build_dependency_graph(self, items: list[Any]) -> dict[str, list[str]]:
        """Build adjacency list for dependency graph."""
        graph = {}

        for item in items:
            item_id = getattr(item, "id", str(item))
            deps = self._get_direct_dependencies(item_id)
            graph[item_id] = deps

        return graph

    def _compute_critical_path(self, graph: dict[str, list[str]]) -> list[str]:
        """Compute critical path using longest path algorithm."""
        # Topological sort
        in_degree: dict[str, int] = defaultdict(int)
        for node in graph:
            for dep in graph[node]:
                in_degree[dep] += 1

        # Find starting nodes (no dependencies)
        queue = deque([node for node in graph if in_degree[node] == 0])

        # Compute longest path
        distances: dict[str, int] = defaultdict(int)
        predecessors: dict[str, str] = {}

        while queue:
            node = queue.popleft()

            for neighbor in graph.get(node, []):
                # Update distance if longer path found
                if distances[node] + 1 > distances[neighbor]:
                    distances[neighbor] = distances[node] + 1
                    predecessors[neighbor] = node

                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Find end node (max distance)
        if not distances:
            return []

        end_node = max(distances, key=lambda k: distances[k])

        # Reconstruct path
        path: list[str] = []
        current: str | None = end_node
        while current is not None:
            path.append(current)
            current = predecessors.get(current)

        path.reverse()
        return path

    def _apply_filters(self, items: list[Any], filters: dict[str, Any]) -> list[Any]:
        """Apply additional filters to items."""
        filtered = items

        for key, value in filters.items():
            if key == "status":
                continue  # Already handled

            filtered = [item for item in filtered if getattr(item, key, None) == value]

        return filtered

    def _build_rationale(
        self, item: Any, analysis: DependencyAnalysis, priority_score: float
    ) -> str:
        """Build human-readable rationale for recommendation."""
        reasons = []

        # Priority
        if priority_score > 0.8:
            reasons.append("Critical priority")
        elif priority_score > 0.6:
            reasons.append("High priority")

        # Blocking
        if analysis.blocked_count > 0:
            reasons.append(f"Unblocks {analysis.blocked_count} item(s)")

        # Critical path
        if analysis.critical_path:
            reasons.append("On critical path")

        # Dependencies
        if not analysis.is_blocked:
            reasons.append("No blockers")

        if not reasons:
            return "Ready to work"

        return "; ".join(reasons)

    def _estimate_impact(self, item: Any, analysis: DependencyAnalysis) -> float:
        """Estimate impact of completing this item (0-1)."""
        # Impact based on:
        # - How many items it unblocks
        # - Whether it's on critical path
        # - Base priority

        impact = 0.0

        # Blocking impact
        if analysis.blocked_count > 0:
            impact += min(analysis.blocked_count * 0.2, 0.6)

        # Critical path impact
        if analysis.critical_path:
            impact += 0.3

        # Base impact
        impact += 0.1

        return min(impact, 1.0)
