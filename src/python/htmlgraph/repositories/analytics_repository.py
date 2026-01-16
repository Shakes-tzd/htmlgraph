"""
AnalyticsRepository - Abstract interface for analytics and work recommendations.

Unifies all analytics patterns across HtmlGraph:
- Work item recommendations and prioritization
- Dependency analysis and critical path detection
- Feature/track health metrics
- Blocked item detection and resolution tracking

Implementations handle:
- Feature and Track repository integration (no direct data access)
- Multi-criteria recommendation scoring
- Transitive dependency analysis
- Centralized metrics caching
- Concurrent query safety

All implementations MUST pass AnalyticsRepositoryComplianceTests.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class DependencyAnalysis:
    """
    Complete dependency analysis for a single work item.

    Contains transitive closure of dependencies, blocking items,
    and critical path information.
    """

    item_id: str
    dependencies: list[str]  # All transitive dependencies
    blocking: list[str]  # Items blocked by this one
    blocked_by: list[str]  # Items blocking this one
    critical_path: bool  # Whether on critical path
    blocked_count: int  # Count of items blocked by this
    dependency_count: int  # Count of dependencies

    @property
    def is_blocked(self) -> bool:
        """True if any dependencies are incomplete."""
        return len(self.blocked_by) > 0

    @property
    def is_blocking_others(self) -> bool:
        """True if any items depend on this one."""
        return len(self.blocking) > 0


@dataclass
class WorkRecommendation:
    """
    Recommended work item with priority and reasoning.
    """

    item_id: str
    title: str
    priority_score: float  # 0-1 normalized score
    rationale: str  # Human-readable explanation
    estimated_impact: float  # Expected impact on project (0-1)
    blocking_count: int  # How many items it unblocks
    dependency_count: int  # How many deps must complete first


class AnalyticsRepositoryError(Exception):
    """Base exception for analytics operations."""

    pass


class AnalysisError(AnalyticsRepositoryError):
    """Raised when analysis cannot be computed."""

    pass


class InvalidItemError(AnalyticsRepositoryError):
    """Raised when item is not found or invalid."""

    def __init__(self, item_id: str):
        self.item_id = item_id
        super().__init__(f"Invalid or not found: {item_id}")


class AnalyticsRepository(ABC):
    """
    Abstract interface for work item analytics and recommendations.

    Uses Feature and Track repositories internally to build unified
    analytics view across all work items. No direct data access.

    CONTRACT:
    1. **Data Consistency**: All recommendations based on current repo state
    2. **Accuracy**: Dependency analysis correctly computes transitive closure
    3. **Performance**: Heavy computations cached, invalidated on data changes
    4. **Isolation**: Multiple concurrent recommendations don't interfere
    5. **Error Handling**: Analysis failures include full context

    CACHING BEHAVIOR:
    - Recommendations cached by item_id
    - Dependencies cached and invalidated on feature/track changes
    - Metrics cached with optional TTL
    - Cache statistics available for monitoring

    PERFORMANCE:
    - recommend_next_work(filters): O(n) with caching
    - analyze_dependencies(item_id): O(n) graph traversal, cached
    - calculate_priority(item_id): O(1) if cached, O(n) if not
    - get_work_items(status): O(n) with early termination
    - get_critical_path(): O(n) computed once per session
    - find_blocked_items(): O(n) with caching
    - find_blocking_items(item_id): O(1) lookup

    THREAD SAFETY:
    - Implementations should be thread-safe
    - Concurrent reads allowed
    - Concurrent analytics queries serialized if needed
    """

    # ===== RECOMMENDATION OPERATIONS =====

    @abstractmethod
    def recommend_next_work(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        min_priority: float = 0.0,
    ) -> list[WorkRecommendation]:
        """
        Get prioritized recommendations for next work items.

        Uses multi-criteria scoring:
        - Item dependencies (prefer unblocking others)
        - Priority level
        - Impact on project timeline
        - Team capacity
        - Business value

        Args:
            filters: Optional filters (status, priority, assigned_to, etc.)
            limit: Max recommendations to return (default 10)
            min_priority: Minimum priority score threshold (0-1)

        Returns:
            List of WorkRecommendation objects sorted by priority

        Raises:
            AnalysisError: If scoring computation fails

        Performance: O(n) with caching

        Examples:
            >>> recs = repo.recommend_next_work(filters={"status": "todo"})
            >>> assert len(recs) <= 10
            >>> assert all(r.priority_score >= 0.0 for r in recs)
            >>> best = recs[0]
            >>> print(f"Do {best.item_id}: {best.rationale}")
        """
        ...

    @abstractmethod
    def analyze_dependencies(self, item_id: str) -> DependencyAnalysis:
        """
        Compute complete dependency analysis for a work item.

        Analyzes:
        - All transitive dependencies (things this must wait for)
        - All blocking items (things waiting on this)
        - Critical path status
        - Blocked/blocking counts

        Args:
            item_id: Item to analyze (feature or track)

        Returns:
            DependencyAnalysis with complete graph information

        Raises:
            InvalidItemError: If item not found
            AnalysisError: If graph traversal fails

        Performance: O(n) graph traversal, cached

        Examples:
            >>> analysis = repo.analyze_dependencies("feat-auth")
            >>> if analysis.is_blocked:
            ...     print(f"Blocked by: {analysis.blocked_by}")
            >>> print(f"Unblocks {analysis.blocking_count} items")
            >>> if analysis.critical_path:
            ...     print("On critical path!")
        """
        ...

    @abstractmethod
    def calculate_priority(self, item_id: str) -> float:
        """
        Calculate normalized priority score for item.

        Score 0-1 based on:
        - Item's explicit priority level
        - How many other items depend on it
        - Position on critical path
        - Business value weight

        Args:
            item_id: Item to score

        Returns:
            Priority score 0.0-1.0 (higher = more important)

        Raises:
            InvalidItemError: If item not found
            AnalysisError: If scoring fails

        Performance: O(1) if cached, O(n) if not

        Examples:
            >>> score = repo.calculate_priority("feat-001")
            >>> assert 0.0 <= score <= 1.0
            >>> if score > 0.8:
            ...     print("This is critical!")
        """
        ...

    # ===== WORK ITEM QUERIES =====

    @abstractmethod
    def get_work_items(
        self, status: str | None = None, include_tracks: bool = True
    ) -> list[Any]:
        """
        Get all work items (features and optionally tracks).

        Args:
            status: Filter by status (e.g., 'todo', 'in-progress', 'done')
            include_tracks: If True, include both features and tracks

        Returns:
            List of work item objects (Features or Tracks)

        Raises:
            ValueError: If status is invalid

        Performance: O(n) with early termination

        Examples:
            >>> todo_items = repo.get_work_items(status="todo")
            >>> all_items = repo.get_work_items()
            >>> assert len(all_items) > 0
        """
        ...

    @abstractmethod
    def find_blocked_items(self) -> list[str]:
        """
        Find all work items currently blocked by incomplete dependencies.

        Returns item IDs that cannot proceed until dependencies complete.

        Returns:
            List of blocked item IDs

        Performance: O(n) with caching

        Examples:
            >>> blocked = repo.find_blocked_items()
            >>> for item_id in blocked:
            ...     analysis = repo.analyze_dependencies(item_id)
            ...     print(f"{item_id} blocked by {analysis.blocked_by}")
        """
        ...

    @abstractmethod
    def find_blocking_items(self, item_id: str) -> list[str]:
        """
        Find what items are blocked by the given item.

        Inverse of dependencies: returns items that depend ON this item.

        Args:
            item_id: Item to find blockers for

        Returns:
            List of item IDs blocked by given item

        Raises:
            InvalidItemError: If item not found

        Performance: O(1) lookup

        Examples:
            >>> blocking = repo.find_blocking_items("feat-database")
            >>> print(f"Completing this unblocks {len(blocking)} items")
        """
        ...

    # ===== CRITICAL PATH ANALYSIS =====

    @abstractmethod
    def get_critical_path(self) -> list[str]:
        """
        Get items on the critical path to project completion.

        Critical path = longest chain of dependent items that determines
        minimum time to complete project.

        Returns:
            List of item IDs on critical path (in dependency order)

        Raises:
            AnalysisError: If critical path cannot be computed

        Performance: O(n) computed once per session

        Examples:
            >>> path = repo.get_critical_path()
            >>> print(f"Critical path has {len(path)} items")
            >>> for item_id in path:
            ...     item = repo.get_item(item_id)
            ...     print(f"  {item.title}")
        """
        ...

    @abstractmethod
    def is_on_critical_path(self, item_id: str) -> bool:
        """
        Check if item is on critical path.

        Args:
            item_id: Item to check

        Returns:
            True if on critical path, False otherwise

        Raises:
            InvalidItemError: If item not found

        Performance: O(1) with cached critical path

        Examples:
            >>> if repo.is_on_critical_path("feat-auth"):
            ...     print("This is blocking project completion!")
        """
        ...

    # ===== METRICS & HEALTH =====

    @abstractmethod
    def cache_metrics(self) -> dict[str, Any]:
        """
        Get cache performance metrics.

        Returns statistics about cache efficiency:
        - Hit count and rate
        - Miss count
        - Eviction count
        - Average load time
        - Memory usage

        Returns:
            Dict with metrics (keys: hits, misses, rate, memory_kb, etc.)

        Examples:
            >>> metrics = repo.cache_metrics()
            >>> print(f"Cache hit rate: {metrics['hit_rate']:.1%}")
            >>> print(f"Memory: {metrics['memory_kb']} KB")
        """
        ...

    @abstractmethod
    def invalidate_analytics_cache(self, item_id: str | None = None) -> None:
        """
        Invalidate cached analytics for item or all items.

        Called when underlying data changes:
        - When feature/track status changes
        - When dependencies added/removed
        - When explicit refresh needed

        Args:
            item_id: Specific item to invalidate, or None for all

        Examples:
            >>> repo.invalidate_analytics_cache("feat-001")  # Single item
            >>> repo.invalidate_analytics_cache()  # Clear all analytics cache
        """
        ...

    # ===== ADVANCED QUERIES =====

    @abstractmethod
    def find_dependency_cycles(self) -> list[list[str]]:
        """
        Find any circular dependencies in the project graph.

        Returns:
            List of cycles, each cycle is list of item IDs forming loop

        Returns empty list if no cycles found.

        Performance: O(n) graph traversal

        Examples:
            >>> cycles = repo.find_dependency_cycles()
            >>> if cycles:
            ...     for cycle in cycles:
            ...         print(f"Cycle detected: {' -> '.join(cycle)}")
            >>> else:
            ...     print("No circular dependencies!")
        """
        ...

    @abstractmethod
    def suggest_parallelizable_work(self) -> list[list[str]]:
        """
        Suggest groups of work that can be done in parallel.

        Returns:
            List of groups, each group is list of item IDs with no dependencies

        Useful for team coordination and optimal scheduling.

        Performance: O(n)

        Examples:
            >>> groups = repo.suggest_parallelizable_work()
            >>> for i, group in enumerate(groups):
            ...     print(f"Parallel wave {i+1}: {group}")
        """
        ...

    @abstractmethod
    def project_completion_estimate(self) -> dict[str, Any]:
        """
        Estimate project completion time based on current state.

        Returns:
            Dict with estimates:
            - items_remaining: count of incomplete items
            - critical_path_length: items on critical path
            - estimated_days: days to completion (based on team velocity)
            - blocking_items: count of items blocking others
            - worst_case_days: pessimistic estimate

        Performance: O(n)

        Examples:
            >>> estimate = repo.project_completion_estimate()
            >>> print(f"Estimated completion: {estimate['estimated_days']} days")
            >>> print(f"Critical path: {estimate['critical_path_length']} items")
        """
        ...
