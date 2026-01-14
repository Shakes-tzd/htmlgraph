"""Parallel work detection and orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


def get_parallel_work(sdk: Any, max_agents: int = 5) -> dict[str, Any]:
    """
    Find tasks that can be worked on simultaneously.

    Note: Prefer using sdk.dep_analytics.find_parallelizable_work() directly.
    This method exists for backward compatibility.

    Args:
        sdk: SDK instance
        max_agents: Maximum number of parallel agents to plan for

    Returns:
        Dict with parallelization opportunities

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # Preferred approach
        >>> report = sdk.dep_analytics.find_parallelizable_work(status="todo")
        >>> # Or via SDK (backward compatibility)
        >>> parallel = sdk.get_parallel_work(max_agents=3)
        >>> logger.info(f"Can work on {parallel['max_parallelism']} tasks at once")
        >>> logger.info(f"Ready now: {parallel['ready_now']}")
    """
    report = sdk.dep_analytics.find_parallelizable_work(status="todo")

    ready_now = report.dependency_levels[0].nodes if report.dependency_levels else []

    return {
        "max_parallelism": report.max_parallelism,
        "ready_now": ready_now[:max_agents],
        "total_ready": len(ready_now),
        "level_count": len(report.dependency_levels),
        "next_level": report.dependency_levels[1].nodes
        if len(report.dependency_levels) > 1
        else [],
    }


def plan_parallel_work(
    sdk: Any,
    max_agents: int = 5,
    shared_files: list[str] | None = None,
) -> dict[str, Any]:
    """
    Plan and prepare parallel work execution.

    This integrates with smart_plan to enable parallel agent dispatch.
    Uses the 6-phase ParallelWorkflow:
    1. Pre-flight analysis (dependencies, risks)
    2. Context preparation (shared file caching)
    3. Prompt generation (for Task tool)

    Args:
        sdk: SDK instance
        max_agents: Maximum parallel agents (default: 5)
        shared_files: Files to pre-cache for all agents

    Returns:
        Dict with parallel execution plan:
            - can_parallelize: Whether parallelization is recommended
            - analysis: Pre-flight analysis results
            - prompts: Ready-to-use Task tool prompts
            - recommendations: Optimization suggestions

    Example:
        >>> sdk = SDK(agent="orchestrator")
        >>> plan = sdk.plan_parallel_work(max_agents=3)
        >>> if plan["can_parallelize"]:
        ...     # Use prompts with Task tool
        ...     for p in plan["prompts"]:
        ...         Task(prompt=p["prompt"], description=p["description"])
    """
    from htmlgraph.parallel import ParallelWorkflow

    workflow = ParallelWorkflow(sdk)

    # Phase 1: Pre-flight analysis
    analysis = workflow.analyze(max_agents=max_agents)

    result = {
        "can_parallelize": analysis.can_parallelize,
        "max_parallelism": analysis.max_parallelism,
        "ready_tasks": analysis.ready_tasks,
        "blocked_tasks": analysis.blocked_tasks,
        "speedup_factor": analysis.speedup_factor,
        "recommendation": analysis.recommendation,
        "warnings": analysis.warnings,
        "prompts": [],
    }

    if not analysis.can_parallelize:
        result["reason"] = analysis.recommendation
        return result

    # Phase 2 & 3: Prepare tasks and generate prompts
    tasks = workflow.prepare_tasks(
        analysis.ready_tasks[:max_agents],
        shared_files=shared_files,
    )
    prompts = workflow.generate_prompts(tasks)

    result["prompts"] = prompts
    result["task_count"] = len(prompts)

    # Add efficiency guidelines
    result["guidelines"] = {
        "dispatch": "Send ALL Task calls in a SINGLE message for true parallelism",
        "patterns": [
            "Grep → Read (search before reading)",
            "Read → Edit → Bash (read, modify, test)",
            "Glob → Read (find files first)",
        ],
        "avoid": [
            "Sequential Task calls (loses parallelism)",
            "Read → Read → Read (cache instead)",
            "Edit → Edit → Edit (batch edits)",
        ],
    }

    return result


def aggregate_parallel_results(
    sdk: Any,
    agent_ids: list[str],
) -> dict[str, Any]:
    """
    Aggregate results from parallel agent execution.

    Call this after parallel agents complete to:
    - Collect health metrics
    - Detect anti-patterns
    - Identify conflicts
    - Generate recommendations

    Args:
        sdk: SDK instance
        agent_ids: List of agent/transcript IDs to analyze

    Returns:
        Dict with aggregated results and validation

    Example:
        >>> # After parallel work completes
        >>> results = sdk.aggregate_parallel_results([
        ...     "agent-abc123",
        ...     "agent-def456",
        ...     "agent-ghi789",
        ... ])
        >>> logger.info(f"Health: {results['avg_health_score']:.0%}")
        >>> logger.info(f"Conflicts: {results['conflicts']}")
    """
    from htmlgraph.parallel import ParallelWorkflow

    workflow = ParallelWorkflow(sdk)

    # Phase 5: Aggregate
    aggregate = workflow.aggregate(agent_ids)

    # Phase 6: Validate
    validation = workflow.validate(aggregate)

    return {
        "total_agents": aggregate.total_agents,
        "successful": aggregate.successful,
        "failed": aggregate.failed,
        "total_duration_seconds": aggregate.total_duration_seconds,
        "parallel_speedup": aggregate.parallel_speedup,
        "avg_health_score": aggregate.avg_health_score,
        "total_anti_patterns": aggregate.total_anti_patterns,
        "files_modified": aggregate.files_modified,
        "conflicts": aggregate.conflicts,
        "recommendations": aggregate.recommendations,
        "validation": validation,
        "all_passed": all(validation.values()),
    }
