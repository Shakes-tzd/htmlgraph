"""Bottleneck identification for planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.types import BottleneckDict


def find_bottlenecks(sdk: Any, top_n: int = 5) -> list[BottleneckDict]:
    """
    Identify tasks blocking the most downstream work.

    Note: Prefer using sdk.dep_analytics.find_bottlenecks() directly.
    This method exists for backward compatibility.

    Args:
        sdk: SDK instance
        top_n: Maximum number of bottlenecks to return

    Returns:
        List of bottleneck tasks with impact metrics

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # Preferred approach
        >>> bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=3)
        >>> # Or via SDK (backward compatibility)
        >>> bottlenecks = sdk.find_bottlenecks(top_n=3)
        >>> for bn in bottlenecks:
        ...     logger.info(f"{bn['title']} blocks {bn['blocks_count']} tasks")
    """
    bottlenecks = sdk.dep_analytics.find_bottlenecks(top_n=top_n)

    # Convert to agent-friendly dict format for backward compatibility
    return [
        {
            "id": bn.id,
            "title": bn.title,
            "status": bn.status,
            "priority": bn.priority,
            "blocks_count": bn.transitive_blocking,
            "impact_score": bn.weighted_impact,
            "blocked_tasks": bn.blocked_nodes[:5],
        }
        for bn in bottlenecks
    ]


def assess_risks(sdk: Any) -> dict[str, Any]:
    """
    Assess dependency-related risks in the project.

    Note: Prefer using sdk.dep_analytics.assess_dependency_risk() directly.
    This method exists for backward compatibility.

    Identifies single points of failure, circular dependencies,
    and orphaned tasks.

    Args:
        sdk: SDK instance

    Returns:
        Dict with risk assessment results

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # Preferred approach
        >>> risk = sdk.dep_analytics.assess_dependency_risk()
        >>> # Or via SDK (backward compatibility)
        >>> risks = sdk.assess_risks()
        >>> if risks['high_risk_count'] > 0:
        ...     logger.info(f"Warning: {risks['high_risk_count']} high-risk tasks")
    """
    risk = sdk.dep_analytics.assess_dependency_risk()

    return {
        "high_risk_count": len(risk.high_risk),
        "high_risk_tasks": [
            {
                "id": node.id,
                "title": node.title,
                "risk_score": node.risk_score,
                "risk_factors": [f.description for f in node.risk_factors],
            }
            for node in risk.high_risk
        ],
        "circular_dependencies": risk.circular_dependencies,
        "orphaned_count": len(risk.orphaned_nodes),
        "orphaned_tasks": risk.orphaned_nodes[:5],
        "recommendations": risk.recommendations,
    }
