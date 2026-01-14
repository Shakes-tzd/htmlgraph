"""Work queue management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import Node


def get_work_queue(
    sdk: Any, agent_id: str | None = None, limit: int = 10, min_score: float = 0.0
) -> list[dict[str, Any]]:
    """
    Get prioritized work queue showing recommended work, active work, and dependencies.

    This method provides a comprehensive view of:
    1. Recommended next work (using smart analytics)
    2. Active work by all agents
    3. Blocked items and what's blocking them
    4. Priority-based scoring

    Args:
        sdk: SDK instance
        agent_id: Agent to get queue for (defaults to SDK agent)
        limit: Maximum number of items to return (default: 10)
        min_score: Minimum score threshold (default: 0.0)

    Returns:
        List of work queue items with scoring and metadata:
            - task_id: Work item ID
            - title: Work item title
            - status: Current status
            - priority: Priority level
            - score: Routing score
            - complexity: Complexity level (if set)
            - effort: Estimated effort (if set)
            - blocks_count: Number of tasks this blocks (if any)
            - blocked_by: List of blocking task IDs (if blocked)
            - agent_assigned: Current assignee (if any)
            - type: Work item type (feature, bug, spike, etc.)

    Example:
        >>> sdk = SDK(agent="claude")
        >>> queue = sdk.get_work_queue(limit=5)
        >>> for item in queue:
        ...     logger.info(f"{item['score']:.1f} - {item['title']}")
        ...     if item.get('blocked_by'):
        ...         logger.info(f"  ⚠️  Blocked by: {', '.join(item['blocked_by'])}")
    """
    from htmlgraph.routing import AgentCapabilityRegistry, CapabilityMatcher

    agent = agent_id or sdk._agent_id or "cli"

    # Get all work item types
    all_work = []
    for collection_name in ["features", "bugs", "spikes", "chores", "epics"]:
        collection = getattr(sdk, collection_name, None)
        if collection:
            # Get todo and blocked items
            for item in collection.where(status="todo"):
                all_work.append(item)
            for item in collection.where(status="blocked"):
                all_work.append(item)

    if not all_work:
        return []

    # Get recommendations from analytics (uses strategic scoring)
    from htmlgraph.sdk.planning.recommendations import recommend_next_work

    recommendations = recommend_next_work(sdk, agent_count=limit * 2)
    rec_scores = {rec["id"]: rec["score"] for rec in recommendations}

    # Build routing registry
    registry = AgentCapabilityRegistry()

    # Register current agent
    registry.register_agent(agent, capabilities=[], wip_limit=5)

    # Get current WIP count for agent
    wip_count = len(sdk.features.where(status="in-progress", agent_assigned=agent))
    registry.set_wip(agent, wip_count)

    # Score each work item
    queue_items = []
    for item in all_work:
        # Use strategic score if available, otherwise use routing score
        if item.id in rec_scores:
            score = rec_scores[item.id]
        else:
            # Fallback to routing score
            agent_profile = registry.get_agent(agent)
            if agent_profile:
                score = CapabilityMatcher.score_agent_task_fit(agent_profile, item)
            else:
                score = 0.0

        # Apply minimum score filter
        if score < min_score:
            continue

        # Build queue item
        queue_item = {
            "task_id": item.id,
            "title": item.title,
            "status": item.status,
            "priority": item.priority,
            "score": score,
            "type": item.type,
            "complexity": getattr(item, "complexity", None),
            "effort": getattr(item, "estimated_effort", None),
            "agent_assigned": getattr(item, "agent_assigned", None),
            "blocks_count": 0,
            "blocked_by": [],
        }

        # Add dependency information
        if hasattr(item, "edges"):
            # Check if this item blocks others
            blocks = item.edges.get("blocks", [])
            queue_item["blocks_count"] = len(blocks)

            # Check if this item is blocked
            blocked_by = item.edges.get("blocked_by", [])
            queue_item["blocked_by"] = blocked_by

        queue_items.append(queue_item)

    # Sort by score (descending)
    queue_items.sort(key=lambda x: x["score"], reverse=True)

    # Limit results
    return queue_items[:limit]


def work_next(
    sdk: Any,
    agent_id: str | None = None,
    auto_claim: bool = False,
    min_score: float = 0.0,
) -> Node | None:
    """
    Get the next best task for an agent using smart routing.

    Uses both strategic analytics and capability-based routing to find
    the optimal next task.

    Args:
        sdk: SDK instance
        agent_id: Agent to get task for (defaults to SDK agent)
        auto_claim: Automatically claim the task (default: False)
        min_score: Minimum score threshold (default: 0.0)

    Returns:
        Next best Node or None if no suitable task found

    Example:
        >>> sdk = SDK(agent="claude")
        >>> task = sdk.work_next(auto_claim=True)
        >>> if task:
        ...     logger.info(f"Working on: {task.title}")
        ...     # Task is automatically claimed and assigned
    """
    agent = agent_id or sdk._agent_id or "cli"

    # Get work queue - get more items since we filter for actionable (todo) only
    queue = get_work_queue(sdk, agent_id=agent, limit=20, min_score=min_score)

    if not queue:
        return None

    # Find the first actionable (todo) task - blocked tasks are not actionable
    top_item = None
    for item in queue:
        if item["status"] == "todo":
            top_item = item
            break

    if top_item is None:
        return None

    # Fetch the actual node
    task = None
    for collection_name in ["features", "bugs", "spikes", "chores", "epics"]:
        collection = getattr(sdk, collection_name, None)
        if collection:
            try:
                task = collection.get(top_item["task_id"])
                if task:
                    break
            except (ValueError, FileNotFoundError):
                continue

    if not task:
        return None

    # Auto-claim if requested
    if auto_claim and task.status == "todo" and collection is not None:
        # Claim the task
        # collection.edit returns context manager or None
        task_editor: Any = collection.edit(task.id)
        if task_editor is not None:
            # collection.edit returns context manager
            with task_editor as t:
                t.status = "in-progress"
                t.agent_assigned = agent

    result: Node | None = task
    return result
