"""
Capability-based agent routing for intelligent task assignment.

Provides:
- AgentCapabilityRegistry: Track agent capabilities
- CapabilityMatcher: Score agent-task fit
- Routing algorithms: Smart task assignment based on skills and workload
"""

from dataclasses import dataclass, field

from htmlgraph.models import Node


@dataclass
class AgentProfile:
    """Profile of an agent with capabilities and workload info."""

    agent_id: str
    capabilities: list[str] = field(default_factory=list)
    wip_limit: int = 5  # Work in progress limit
    current_wip: int = 0  # Current tasks in progress


class AgentCapabilityRegistry:
    """
    Registry for tracking agent capabilities and workload.

    Maintains in-memory registry of:
    - Agent capabilities (declared skills)
    - Current workload (WIP count)
    - Availability status

    Example:
        registry = AgentCapabilityRegistry()
        registry.register_agent('claude', ['python', 'documentation', 'testing'])
        registry.register_agent('haiku', ['python', 'refactoring'])
        registry.set_wip('claude', 3)  # claude has 3 tasks in progress

        capable = registry.get_capable_agents(['python', 'testing'])
        # Returns: [AgentProfile(agent_id='claude', ...)]
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self.agents: dict[str, AgentProfile] = {}

    def register_agent(
        self, agent_id: str, capabilities: list[str], wip_limit: int = 5
    ) -> None:
        """
        Register an agent with capabilities.

        Args:
            agent_id: Unique identifier for the agent
            capabilities: List of capability strings
            wip_limit: Maximum tasks this agent can work on simultaneously
        """
        self.agents[agent_id] = AgentProfile(
            agent_id=agent_id,
            capabilities=capabilities,
            wip_limit=wip_limit,
            current_wip=0,
        )

    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.

        Args:
            agent_id: Agent to remove

        Returns:
            True if agent was registered, False otherwise
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False

    def set_wip(self, agent_id: str, wip_count: int) -> bool:
        """
        Set current work-in-progress count for an agent.

        Args:
            agent_id: Agent identifier
            wip_count: Number of tasks currently in progress

        Returns:
            True if successful, False if agent not found
        """
        if agent_id not in self.agents:
            return False
        self.agents[agent_id].current_wip = wip_count
        return True

    def increment_wip(self, agent_id: str) -> bool:
        """Increment WIP count (called when agent claims task)."""
        if agent_id not in self.agents:
            return False
        self.agents[agent_id].current_wip += 1
        return True

    def decrement_wip(self, agent_id: str) -> bool:
        """Decrement WIP count (called when agent completes task)."""
        if agent_id not in self.agents:
            return False
        if self.agents[agent_id].current_wip > 0:
            self.agents[agent_id].current_wip -= 1
        return True

    def get_capable_agents(
        self, required_capabilities: list[str]
    ) -> list[AgentProfile]:
        """
        Get all agents capable of handling required capabilities.

        Args:
            required_capabilities: List of required capabilities

        Returns:
            List of capable agents, sorted by availability
        """
        if not required_capabilities:
            return list(self.agents.values())

        capable = []
        for agent in self.agents.values():
            if any(cap in agent.capabilities for cap in required_capabilities):
                capable.append(agent)

        # Sort by availability (lower WIP first)
        capable.sort(key=lambda a: (a.current_wip, a.agent_id))
        return capable

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Get agent profile by ID."""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> list[AgentProfile]:
        """Get all registered agents."""
        return list(self.agents.values())


class CapabilityMatcher:
    """
    Score agent-task fit based on capabilities and workload.

    Scoring algorithm:
    1. Exact match (required capability in agent capabilities): +100
    2. Partial match (related capability): +50
    3. No match: -50
    4. Workload penalty (higher WIP = lower score): -5 per task
    """

    @staticmethod
    def score_agent_task_fit(
        agent_profile: AgentProfile, task: Node, include_workload: bool = True
    ) -> float:
        """
        Calculate fit score for agent-task pair.

        Higher score = better fit.

        Args:
            agent_profile: Agent to evaluate
            task: Task to evaluate
            include_workload: Whether to penalize based on WIP

        Returns:
            Fit score (can be negative)
        """
        score = 0.0

        # No required capabilities = available to all agents
        if not task.required_capabilities:
            score = 50.0  # Baseline for unspecified tasks
        else:
            # Score capability matches
            required = set(task.required_capabilities)
            agent_caps = set(agent_profile.capabilities)

            exact_matches = len(required & agent_caps)
            missing = len(required - agent_caps)

            # Exact match scoring
            score += exact_matches * 100

            # Penalty for missing capabilities
            score -= missing * 50

            # Bonus for having more capabilities than required
            extra = len(agent_caps - required)
            score += extra * 10

        # Workload penalty
        if include_workload:
            wip_penalty = agent_profile.current_wip * 5
            score -= wip_penalty

            # Additional penalty if at capacity
            if agent_profile.current_wip >= agent_profile.wip_limit:
                score -= 100

        return score

    @staticmethod
    def find_best_agent(
        agents: list[AgentProfile], task: Node, min_score: float = 0.0
    ) -> AgentProfile | None:
        """
        Find the best agent for a task.

        Args:
            agents: List of candidate agents
            task: Task to assign
            min_score: Minimum acceptable score

        Returns:
            Best agent, or None if no agent meets minimum score
        """
        if not agents:
            return None

        best_agent = None
        best_score = min_score - 1

        for agent in agents:
            score = CapabilityMatcher.score_agent_task_fit(agent, task)
            if score > best_score:
                best_score = score
                best_agent = agent

        return best_agent


def route_task_to_agent(
    task: Node, registry: AgentCapabilityRegistry, allow_unmatched: bool = False
) -> tuple[AgentProfile | None, float]:
    """
    Route a single task to the best capable agent.

    Args:
        task: Task to route
        registry: Agent capability registry
        allow_unmatched: If True, return best match even if < 0 score

    Returns:
        Tuple of (best_agent, score) or (None, score) if no match
    """
    agents = registry.get_all_agents()

    if not agents:
        return None, -100.0

    # Get capable agents
    capable = registry.get_capable_agents(task.required_capabilities)

    if capable:
        agents_to_consider = capable
    elif allow_unmatched:
        agents_to_consider = agents
    else:
        return None, -100.0

    # Find best fit
    best_agent = CapabilityMatcher.find_best_agent(
        agents_to_consider,
        task,
        min_score=0.0 if not allow_unmatched else -float("inf"),
    )

    if best_agent:
        score = CapabilityMatcher.score_agent_task_fit(best_agent, task)
        return best_agent, score
    else:
        return None, -100.0


def route_tasks_to_agents(
    tasks: list[Node], registry: AgentCapabilityRegistry, allow_unmatched: bool = False
) -> dict[str, tuple[AgentProfile | None, float]]:
    """
    Route multiple tasks to best agents.

    Args:
        tasks: List of tasks to route
        registry: Agent capability registry
        allow_unmatched: If True, assign even without capability match

    Returns:
        Dict mapping task_id to (agent_profile, score) tuple
    """
    routing = {}

    for task in tasks:
        agent, score = route_task_to_agent(task, registry, allow_unmatched)
        routing[task.id] = (agent, score)

    return routing
