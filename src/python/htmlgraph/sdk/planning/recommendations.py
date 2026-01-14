"""Smart work recommendations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def recommend_next_work(sdk: Any, agent_count: int = 1) -> list[dict[str, Any]]:
    """
    Get smart recommendations for what to work on next.

    Note: Prefer using sdk.dep_analytics.recommend_next_tasks() directly.
    This method exists for backward compatibility.

    Considers priority, dependencies, and transitive impact.

    Args:
        sdk: SDK instance
        agent_count: Number of agents/tasks to recommend

    Returns:
        List of recommended tasks with reasoning

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # Preferred approach
        >>> recs = sdk.dep_analytics.recommend_next_tasks(agent_count=3)
        >>> # Or via SDK (backward compatibility)
        >>> recs = sdk.recommend_next_work(agent_count=3)
        >>> for rec in recs:
        ...     logger.info(f"{rec['title']} (score: {rec['score']})")
        ...     logger.info(f"  Reasons: {rec['reasons']}")
    """
    recommendations = sdk.dep_analytics.recommend_next_tasks(
        agent_count=agent_count, lookahead=5
    )

    return [
        {
            "id": rec.id,
            "title": rec.title,
            "priority": rec.priority,
            "score": rec.score,
            "reasons": rec.reasons,
            "estimated_hours": rec.estimated_effort,
            "unlocks_count": len(rec.unlocks),
            "unlocks": rec.unlocks[:3],
        }
        for rec in recommendations.recommendations
    ]


def analyze_impact(sdk: Any, node_id: str) -> dict[str, Any]:
    """
    Analyze the impact of completing a specific task.

    Note: Prefer using sdk.dep_analytics.impact_analysis() directly.
    This method exists for backward compatibility.

    Args:
        sdk: SDK instance
        node_id: Task to analyze

    Returns:
        Dict with impact analysis

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # Preferred approach
        >>> impact = sdk.dep_analytics.impact_analysis("feature-001")
        >>> # Or via SDK (backward compatibility)
        >>> impact = sdk.analyze_impact("feature-001")
        >>> logger.info(f"Completing this unlocks {impact['unlocks_count']} tasks")
    """
    impact = sdk.dep_analytics.impact_analysis(node_id)

    return {
        "node_id": node_id,
        "direct_dependents": impact.direct_dependents,
        "total_impact": impact.transitive_dependents,
        "completion_impact": impact.completion_impact,
        "unlocks_count": len(impact.affected_nodes),
        "affected_tasks": impact.affected_nodes[:10],
    }
