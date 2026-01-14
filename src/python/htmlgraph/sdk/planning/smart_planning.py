"""Smart planning workflow integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from htmlgraph.models import Node


def start_planning_spike(
    sdk: Any,
    title: str,
    context: str = "",
    timebox_hours: float = 4.0,
    auto_start: bool = True,
) -> Node:
    """
    Create a planning spike to research and design before implementation.

    This is for timeboxed investigation before creating a full track.

    Args:
        sdk: SDK instance
        title: Spike title (e.g., "Plan User Authentication System")
        context: Background information
        timebox_hours: Time limit for spike (default: 4 hours)
        auto_start: Automatically start the spike (default: True)

    Returns:
        Created spike Node

    Example:
        >>> sdk = SDK(agent="claude")
        >>> spike = sdk.start_planning_spike(
        ...     "Plan Real-time Notifications",
        ...     context="Users need live updates. Research options.",
        ...     timebox_hours=3.0
        ... )
    """
    from htmlgraph.ids import generate_id
    from htmlgraph.models import Spike, SpikeType, Step

    # Create spike directly (SpikeBuilder doesn't exist yet)
    spike_id = generate_id(node_type="spike", title=title)
    spike = Spike(
        id=spike_id,
        title=title,
        type="spike",
        status="in-progress" if auto_start and sdk._agent_id else "todo",
        spike_type=SpikeType.ARCHITECTURAL,
        timebox_hours=int(timebox_hours),
        agent_assigned=sdk._agent_id if auto_start and sdk._agent_id else None,
        steps=[
            Step(description="Research existing solutions and patterns"),
            Step(description="Define requirements and constraints"),
            Step(description="Design high-level architecture"),
            Step(description="Identify dependencies and risks"),
            Step(description="Create implementation plan"),
        ],
        content=f"<p>{context}</p>" if context else "",
        edges={},
        properties={},
    )

    sdk._graph.add(spike)
    return spike


def create_track_from_plan(
    sdk: Any,
    title: str,
    description: str,
    spike_id: str | None = None,
    priority: str = "high",
    requirements: list[str | tuple[str, str]] | None = None,
    phases: list[tuple[str, list[str]]] | None = None,
) -> dict[str, Any]:
    """
    Create a track with spec and plan from planning results.

    Args:
        sdk: SDK instance
        title: Track title
        description: Track description
        spike_id: Optional spike ID that led to this track
        priority: Track priority (default: "high")
        requirements: List of requirements (strings or (req, priority) tuples)
        phases: List of (phase_name, tasks) tuples for the plan

    Returns:
        Dict with track, spec, and plan details

    Example:
        >>> sdk = SDK(agent="claude")
        >>> track_info = sdk.create_track_from_plan(
        ...     title="User Authentication System",
        ...     description="OAuth 2.0 with JWT tokens",
        ...     requirements=[
        ...         ("OAuth 2.0 integration", "must-have"),
        ...         ("JWT token management", "must-have"),
        ...         "Password reset flow"
        ...     ],
        ...     phases=[
        ...         ("Phase 1: OAuth", ["Setup providers (2h)", "Callback (2h)"]),
        ...         ("Phase 2: JWT", ["Token signing (2h)", "Refresh (1.5h)"])
        ...     ]
        ... )
    """

    builder = (
        sdk.tracks.builder().title(title).description(description).priority(priority)
    )

    # Add reference to planning spike if provided
    if spike_id:
        # Access internal data for track builder
        data: dict[str, Any] = builder._data  # type: ignore[attr-defined]
        data["properties"]["planning_spike"] = spike_id

    # Add spec if requirements provided
    if requirements:
        # Convert simple strings to (requirement, "must-have") tuples
        req_list = []
        for req in requirements:
            if isinstance(req, str):
                req_list.append((req, "must-have"))
            else:
                req_list.append(req)

        builder.with_spec(
            overview=description,
            context=f"Track created from planning spike: {spike_id}"
            if spike_id
            else "",
            requirements=req_list,
            acceptance_criteria=[],
        )

    # Add plan if phases provided
    if phases:
        builder.with_plan_phases(phases)

    track = builder.create()

    return {
        "track_id": track.id,
        "title": track.title,
        "has_spec": bool(requirements),
        "has_plan": bool(phases),
        "spike_id": spike_id,
        "priority": priority,
    }


def smart_plan(
    sdk: Any,
    description: str,
    create_spike: bool = True,
    timebox_hours: float = 4.0,
    research_completed: bool = False,
    research_findings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Smart planning workflow: analyzes project context and creates spike or track.

    This is the main entry point for planning new work. It:
    1. Checks current project state
    2. Provides context from strategic analytics
    3. Creates a planning spike or track as appropriate

    **IMPORTANT: Research Phase Required**
    For complex features, you should complete research BEFORE planning:
    1. Use /htmlgraph:research or WebSearch to gather best practices
    2. Document findings (libraries, patterns, anti-patterns)
    3. Pass research_completed=True and research_findings to this method
    4. This ensures planning is informed by industry best practices

    Research-first workflow:
        1. /htmlgraph:research "{topic}" → Gather external knowledge
        2. sdk.smart_plan(..., research_completed=True) → Plan with context
        3. Complete spike steps → Design solution
        4. Create track from plan → Structure implementation

    Args:
        sdk: SDK instance
        description: What you want to plan (e.g., "User authentication system")
        create_spike: Create a spike for research (default: True)
        timebox_hours: If creating spike, time limit (default: 4 hours)
        research_completed: Whether research was performed (default: False)
        research_findings: Structured research findings (optional)

    Returns:
        Dict with planning context and created spike/track info

    Example:
        >>> sdk = SDK(agent="claude")
        >>> # WITH research (recommended for complex work)
        >>> research = {
        ...     "topic": "OAuth 2.0 best practices",
        ...     "sources_count": 5,
        ...     "recommended_library": "authlib",
        ...     "key_insights": ["Use PKCE", "Implement token rotation"]
        ... }
        >>> plan = sdk.smart_plan(
        ...     "User authentication system",
        ...     create_spike=True,
        ...     research_completed=True,
        ...     research_findings=research
        ... )
        >>> logger.info(f"Created: {plan['spike_id']}")
        >>> logger.info(f"Research informed: {plan['research_informed']}")
    """
    # Get project context from strategic analytics
    from htmlgraph.sdk.planning.bottlenecks import assess_risks, find_bottlenecks
    from htmlgraph.sdk.planning.parallel import get_parallel_work

    bottlenecks = find_bottlenecks(sdk, top_n=3)
    risks = assess_risks(sdk)
    parallel = get_parallel_work(sdk, max_agents=5)

    context = {
        "bottlenecks_count": len(bottlenecks),
        "high_risk_count": risks["high_risk_count"],
        "parallel_capacity": parallel["max_parallelism"],
        "description": description,
    }

    # Build context string with research info
    context_str = f"Project context:\n- {len(bottlenecks)} bottlenecks\n- {risks['high_risk_count']} high-risk items\n- {parallel['max_parallelism']} parallel capacity"

    if research_completed and research_findings:
        context_str += f"\n\nResearch completed:\n- Topic: {research_findings.get('topic', description)}"
        if "sources_count" in research_findings:
            context_str += f"\n- Sources: {research_findings['sources_count']}"
        if "recommended_library" in research_findings:
            context_str += (
                f"\n- Recommended: {research_findings['recommended_library']}"
            )

    # Validation: warn if complex work planned without research
    is_complex = any(
        [
            "auth" in description.lower(),
            "security" in description.lower(),
            "real-time" in description.lower(),
            "websocket" in description.lower(),
            "oauth" in description.lower(),
            "performance" in description.lower(),
            "integration" in description.lower(),
        ]
    )

    warnings = []
    if is_complex and not research_completed:
        warnings.append(
            "⚠️  Complex feature detected without research. "
            "Consider using /htmlgraph:research first to gather best practices."
        )

    if create_spike:
        spike = start_planning_spike(
            sdk,
            title=f"Plan: {description}",
            context=context_str,
            timebox_hours=timebox_hours,
        )

        # Store research metadata in spike properties if provided
        if research_completed and research_findings:
            spike.properties["research_completed"] = True
            spike.properties["research_findings"] = research_findings
            sdk._graph.update(spike)

        result = {
            "type": "spike",
            "spike_id": spike.id,
            "title": spike.title,
            "status": spike.status,
            "timebox_hours": timebox_hours,
            "project_context": context,
            "research_informed": research_completed,
            "next_steps": [
                "Research and design the solution"
                if not research_completed
                else "Design solution using research findings",
                "Complete spike steps",
                "Use SDK.create_track_from_plan() to create track",
            ],
        }

        if warnings:
            result["warnings"] = warnings

        return result
    else:
        # Direct track creation (for when you already know what to do)
        track_info = create_track_from_plan(
            sdk,
            title=description,
            description=f"Planned with context: {context}",
        )

        result = {
            "type": "track",
            **track_info,
            "project_context": context,
            "research_informed": research_completed,
            "next_steps": [
                "Create features from track plan",
                "Link features to track",
                "Start implementation",
            ],
        }

        if warnings:
            result["warnings"] = warnings

        return result
