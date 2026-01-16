"""
CostOptimizer - Suggests token budgets, parallelization, and model selection.

This module provides cost optimization recommendations:
1. Token budgeting - Automatically suggest token budgets based on task scope
2. Parallelization - Calculate optimal parallelization strategies
3. Model selection - Choose cheapest model that can handle task
4. Caching - Identify caching opportunities to save tokens

Usage:
    from htmlgraph.analytics.strategic import CostOptimizer

    optimizer = CostOptimizer(db_path)

    # Get token budget suggestion
    budget = optimizer.suggest_token_budget(task_description)

    # Get parallelization strategy
    strategy = optimizer.suggest_parallelization(tasks)

    # Get model recommendation
    model = optimizer.choose_model(task, preferences)
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers by capability and cost."""

    HAIKU = "haiku"  # Fast, cheap, simple tasks
    SONNET = "sonnet"  # Balanced, default choice
    OPUS = "opus"  # Complex, expensive, high-quality


@dataclass
class TokenBudget:
    """
    Token budget recommendation for a task.

    Attributes:
        recommended: Recommended token budget
        minimum: Minimum viable budget
        maximum: Maximum reasonable budget
        confidence: Confidence in the recommendation
        reasoning: Explanation for the recommendation
        based_on_history: Whether based on historical data
    """

    recommended: int
    minimum: int
    maximum: int
    confidence: float = 0.7
    reasoning: str = ""
    based_on_history: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recommended": self.recommended,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "based_on_history": self.based_on_history,
        }


@dataclass
class ParallelizationStrategy:
    """
    Parallelization strategy for a set of tasks.

    Attributes:
        groups: List of task groups that can run in parallel
        estimated_speedup: Expected speedup factor
        estimated_cost: Estimated total token cost
        reasoning: Explanation for the strategy
    """

    groups: list[list[str]] = field(default_factory=list)
    estimated_speedup: float = 1.0
    estimated_cost: int = 0
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "groups": self.groups,
            "estimated_speedup": self.estimated_speedup,
            "estimated_cost": self.estimated_cost,
            "reasoning": self.reasoning,
        }


@dataclass
class ModelRecommendation:
    """
    Model selection recommendation.

    Attributes:
        recommended_model: Recommended model tier
        alternative_model: Alternative if budget constrained
        confidence: Confidence in recommendation
        reasoning: Explanation for the choice
        estimated_cost: Estimated token cost with this model
        estimated_quality: Expected quality score (0-1)
    """

    recommended_model: ModelTier
    alternative_model: ModelTier | None = None
    confidence: float = 0.7
    reasoning: str = ""
    estimated_cost: int = 0
    estimated_quality: float = 0.8

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recommended_model": self.recommended_model.value,
            "alternative_model": self.alternative_model.value
            if self.alternative_model
            else None,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "estimated_cost": self.estimated_cost,
            "estimated_quality": self.estimated_quality,
        }


class CostOptimizer:
    """
    Optimizes cost through token budgeting, parallelization, and model selection.

    Uses historical data and heuristics to make intelligent cost decisions.
    """

    # Token cost multipliers (relative to Haiku = 1.0)
    MODEL_COST_MULTIPLIERS = {
        ModelTier.HAIKU: 1.0,
        ModelTier.SONNET: 3.0,
        ModelTier.OPUS: 15.0,
    }

    # Default token budgets by task complexity
    DEFAULT_BUDGETS = {
        "simple": 2000,
        "medium": 5000,
        "complex": 10000,
        "very_complex": 20000,
    }

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize cost optimizer.

        Args:
            db_path: Path to HtmlGraph database. If None, uses default location.
        """
        if db_path is None:
            from htmlgraph.config import get_database_path

            db_path = get_database_path()

        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def suggest_token_budget(
        self,
        task_description: str,
        tool_name: str | None = None,
    ) -> TokenBudget:
        """
        Suggest token budget based on task description and history.

        Args:
            task_description: Description of the task
            tool_name: Specific tool being used (optional)

        Returns:
            TokenBudget recommendation
        """
        # First, try to get historical data for similar tasks
        historical = self._get_historical_token_usage(task_description, tool_name)

        if historical:
            return TokenBudget(
                recommended=int(historical["avg_tokens"] * 1.2),  # 20% buffer
                minimum=int(historical["min_tokens"]),
                maximum=int(historical["max_tokens"] * 1.1),
                confidence=0.8,
                reasoning=f"Based on {historical['count']} similar tasks",
                based_on_history=True,
            )

        # Fall back to heuristics
        complexity = self._estimate_complexity(task_description)
        base_budget = self.DEFAULT_BUDGETS.get(complexity, 5000)

        # Adjust for specific tools
        if tool_name:
            tool_multipliers = {
                "Edit": 1.2,  # Edits often need more context
                "Write": 1.3,  # Writes can be lengthy
                "Bash": 0.8,  # Bash commands typically shorter
                "Read": 0.5,  # Reads are cheap
                "Grep": 0.3,  # Grep is very cheap
                "Task": 2.0,  # Task delegations need more budget
            }
            multiplier = tool_multipliers.get(tool_name, 1.0)
            base_budget = int(base_budget * multiplier)

        return TokenBudget(
            recommended=base_budget,
            minimum=int(base_budget * 0.5),
            maximum=int(base_budget * 2.0),
            confidence=0.6,
            reasoning=f"Estimated {complexity} complexity task",
            based_on_history=False,
        )

    def _get_historical_token_usage(
        self,
        task_description: str,
        tool_name: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get historical token usage for similar tasks.

        Args:
            task_description: Task description to match
            tool_name: Optional tool filter

        Returns:
            Dict with avg, min, max tokens and count, or None if insufficient data
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Build query based on available filters
            if tool_name:
                cursor.execute(
                    """
                    SELECT
                        AVG(cost_tokens) as avg_tokens,
                        MIN(cost_tokens) as min_tokens,
                        MAX(cost_tokens) as max_tokens,
                        COUNT(*) as count
                    FROM agent_events
                    WHERE tool_name = ?
                    AND cost_tokens > 0
                    AND timestamp > datetime('now', '-30 days')
                """,
                    (tool_name,),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        AVG(cost_tokens) as avg_tokens,
                        MIN(cost_tokens) as min_tokens,
                        MAX(cost_tokens) as max_tokens,
                        COUNT(*) as count
                    FROM agent_events
                    WHERE cost_tokens > 0
                    AND timestamp > datetime('now', '-30 days')
                """
                )

            row = cursor.fetchone()
            if row and row["count"] >= 5:  # Need at least 5 samples
                return {
                    "avg_tokens": row["avg_tokens"],
                    "min_tokens": row["min_tokens"],
                    "max_tokens": row["max_tokens"],
                    "count": row["count"],
                }

            return None

        except sqlite3.Error as e:
            logger.warning(f"Error getting historical token usage: {e}")
            return None

    def _estimate_complexity(self, task_description: str) -> str:
        """
        Estimate task complexity from description.

        Args:
            task_description: Task description

        Returns:
            Complexity level: simple, medium, complex, very_complex
        """
        task_lower = task_description.lower()

        # Very complex indicators
        very_complex_indicators = [
            "refactor",
            "architecture",
            "redesign",
            "migrate",
            "rewrite",
            "security audit",
            "performance optimize",
        ]
        if any(ind in task_lower for ind in very_complex_indicators):
            return "very_complex"

        # Complex indicators
        complex_indicators = [
            "implement",
            "create",
            "build",
            "design",
            "integrate",
            "debug",
            "analyze",
            "complex",
        ]
        if any(ind in task_lower for ind in complex_indicators):
            return "complex"

        # Simple indicators
        simple_indicators = [
            "fix typo",
            "rename",
            "format",
            "lint",
            "move",
            "copy",
            "delete",
            "list",
            "show",
            "status",
        ]
        if any(ind in task_lower for ind in simple_indicators):
            return "simple"

        # Default to medium
        return "medium"

    def suggest_parallelization(
        self,
        tasks: list[dict[str, Any]],
    ) -> ParallelizationStrategy:
        """
        Calculate optimal parallelization strategy for a set of tasks.

        Analyzes task dependencies and groups independent tasks for parallel execution.

        Args:
            tasks: List of task dictionaries with 'id', 'description', 'dependencies'

        Returns:
            ParallelizationStrategy with grouped tasks
        """
        if not tasks:
            return ParallelizationStrategy(
                groups=[],
                estimated_speedup=1.0,
                reasoning="No tasks provided",
            )

        # Build dependency graph
        task_ids = {t.get("id", str(i)): t for i, t in enumerate(tasks)}
        dependencies: dict[str, set[str]] = {}

        for task in tasks:
            task_id = task.get("id", str(tasks.index(task)))
            deps = set(task.get("dependencies", []))
            dependencies[task_id] = deps

        # Topological sort into parallel groups
        groups: list[list[str]] = []
        remaining = set(task_ids.keys())
        completed: set[str] = set()

        while remaining:
            # Find tasks with all dependencies satisfied
            ready = []
            for task_id in remaining:
                if dependencies[task_id].issubset(completed):
                    ready.append(task_id)

            if not ready:
                # Circular dependency - just add remaining tasks
                groups.append(list(remaining))
                break

            groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        # Calculate estimated speedup
        sequential_time = len(tasks)
        parallel_time = len(groups)
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0

        # Estimate cost (sum of individual task budgets)
        total_cost = 0
        for task in tasks:
            desc = task.get("description", "")
            budget = self.suggest_token_budget(desc)
            total_cost += budget.recommended

        return ParallelizationStrategy(
            groups=groups,
            estimated_speedup=speedup,
            estimated_cost=total_cost,
            reasoning=f"Grouped {len(tasks)} tasks into {len(groups)} parallel batches",
        )

    def choose_model(
        self,
        task_description: str,
        budget_constraint: int | None = None,
        quality_threshold: float = 0.7,
    ) -> ModelRecommendation:
        """
        Choose the most cost-effective model for a task.

        Balances cost, quality, and task requirements.

        Args:
            task_description: Description of the task
            budget_constraint: Maximum token budget (optional)
            quality_threshold: Minimum acceptable quality (0-1)

        Returns:
            ModelRecommendation with suggested model
        """
        complexity = self._estimate_complexity(task_description)

        # Map complexity to model tier
        complexity_model_map = {
            "simple": (ModelTier.HAIKU, 0.7),
            "medium": (ModelTier.SONNET, 0.85),
            "complex": (ModelTier.SONNET, 0.9),
            "very_complex": (ModelTier.OPUS, 0.95),
        }

        recommended, expected_quality = complexity_model_map.get(
            complexity, (ModelTier.SONNET, 0.85)
        )

        # Check if we can use a cheaper model
        alternative = None
        if recommended == ModelTier.OPUS and quality_threshold <= 0.9:
            alternative = ModelTier.SONNET
        elif recommended == ModelTier.SONNET and quality_threshold <= 0.7:
            alternative = ModelTier.HAIKU

        # Calculate estimated cost
        base_budget = self.DEFAULT_BUDGETS.get(complexity, 5000)
        cost_multiplier = self.MODEL_COST_MULTIPLIERS[recommended]
        estimated_cost = int(base_budget * cost_multiplier)

        # Check budget constraint
        if budget_constraint and estimated_cost > budget_constraint:
            # Try to fit within budget with cheaper model
            if alternative:
                alt_cost = int(base_budget * self.MODEL_COST_MULTIPLIERS[alternative])
                if alt_cost <= budget_constraint:
                    recommended = alternative
                    estimated_cost = alt_cost
                    expected_quality = expected_quality * 0.85

        reasoning = (
            f"{complexity.replace('_', ' ').title()} task - "
            f"{recommended.value} recommended for balance of cost and quality"
        )

        return ModelRecommendation(
            recommended_model=recommended,
            alternative_model=alternative,
            confidence=0.75,
            reasoning=reasoning,
            estimated_cost=estimated_cost,
            estimated_quality=expected_quality,
        )

    def identify_cache_opportunities(
        self,
        recent_tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Identify caching opportunities to save tokens.

        Looks for repeated patterns that could benefit from caching.

        Args:
            recent_tools: List of recent tool calls with input/output

        Returns:
            List of cache opportunity recommendations
        """
        opportunities: list[dict[str, Any]] = []

        if len(recent_tools) < 3:
            return opportunities

        # Track repeated tool+input combinations
        seen: dict[str, list[int]] = {}

        for i, tool in enumerate(recent_tools):
            tool_name = tool.get("tool_name", "")
            # Create a simple key from tool name and input hash
            input_key = str(tool.get("input", {}))[:100]
            key = f"{tool_name}:{hash(input_key)}"

            if key not in seen:
                seen[key] = []
            seen[key].append(i)

        # Find repeated calls
        for key, indices in seen.items():
            if len(indices) >= 2:
                tool_name = key.split(":")[0]
                opportunities.append(
                    {
                        "tool_name": tool_name,
                        "occurrences": len(indices),
                        "suggestion": f"Cache {tool_name} results - called {len(indices)} times with same input",
                        "estimated_savings": len(indices) - 1,  # Could save N-1 calls
                    }
                )

        return opportunities

    def get_cost_summary(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Get cost summary for a session.

        Args:
            session_id: Session to summarize

        Returns:
            Dictionary with cost breakdown
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT
                    tool_name,
                    COUNT(*) as call_count,
                    SUM(cost_tokens) as total_tokens,
                    AVG(cost_tokens) as avg_tokens,
                    model
                FROM agent_events
                WHERE session_id = ?
                AND event_type = 'tool_call'
                GROUP BY tool_name, model
                ORDER BY total_tokens DESC
            """,
                (session_id,),
            )

            breakdown = []
            total_tokens = 0

            for row in cursor.fetchall():
                tokens = row["total_tokens"] or 0
                total_tokens += tokens
                breakdown.append(
                    {
                        "tool_name": row["tool_name"],
                        "model": row["model"] or "unknown",
                        "call_count": row["call_count"],
                        "total_tokens": tokens,
                        "avg_tokens": row["avg_tokens"] or 0,
                    }
                )

            return {
                "session_id": session_id,
                "total_tokens": total_tokens,
                "breakdown": breakdown,
                "most_expensive_tool": breakdown[0]["tool_name"] if breakdown else None,
            }

        except sqlite3.Error as e:
            logger.error(f"Error getting cost summary: {e}")
            return {"session_id": session_id, "total_tokens": 0, "breakdown": []}
