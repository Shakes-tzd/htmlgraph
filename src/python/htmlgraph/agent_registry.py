from __future__ import annotations

"""
Agent Registry - Manages agent capabilities and routing.

Provides:
- Agent capability declarations
- Agent registry management
- Capability matching for task routing
"""


import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


@dataclass
class AgentProfile:
    """
    Profile for an AI agent with capabilities and preferences.

    Attributes:
        id: Unique agent identifier
        name: Human-readable name
        capabilities: List of skills/tools the agent can use
        max_parallel_tasks: Maximum concurrent tasks
        preferred_complexity: Complexity levels the agent prefers
        active: Whether the agent is currently available
        metadata: Additional agent information
    """

    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)
    max_parallel_tasks: int = 3
    preferred_complexity: list[Literal["low", "medium", "high", "very-high"]] = field(
        default_factory=lambda: ["low", "medium", "high"]
    )
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_handle(self, required_capabilities: list[str]) -> bool:
        """Check if agent has all required capabilities."""
        if not required_capabilities:
            return True  # No requirements, any agent can handle
        return all(cap in self.capabilities for cap in required_capabilities)

    def can_handle_complexity(self, complexity: str | None) -> bool:
        """Check if agent can handle the task complexity."""
        if not complexity:
            return True  # No complexity specified, assume ok
        return complexity in self.preferred_complexity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "capabilities": self.capabilities,
            "max_parallel_tasks": self.max_parallel_tasks,
            "preferred_complexity": self.preferred_complexity,
            "active": self.active,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProfile:
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            capabilities=data.get("capabilities", []),
            max_parallel_tasks=data.get("max_parallel_tasks", 3),
            preferred_complexity=data.get(
                "preferred_complexity", ["low", "medium", "high"]
            ),
            active=data.get("active", True),
            metadata=data.get("metadata", {}),
        )


class AgentRegistry:
    """
    Registry for managing agent profiles and capabilities.

    Stores agent information in .htmlgraph/agents.json
    """

    def __init__(self, htmlgraph_dir: Path | str):
        """
        Initialize agent registry.

        Args:
            htmlgraph_dir: Path to .htmlgraph directory
        """
        self.htmlgraph_dir = Path(htmlgraph_dir)
        self.registry_file = self.htmlgraph_dir / "agents.json"
        self._agents: dict[str, AgentProfile] = {}
        self._load()

    def _load(self) -> None:
        """Load agents from registry file."""
        if not self.registry_file.exists():
            # Create default registry with common agents
            self._create_default_registry()
            return

        try:
            with open(self.registry_file) as f:
                data = json.load(f)

            # Load agents from the registry
            agents_data = data.get("agents", {})
            self._agents = {
                agent_id: AgentProfile.from_dict(agent_data)
                for agent_id, agent_data in agents_data.items()
            }
        except (json.JSONDecodeError, KeyError) as e:
            # Invalid registry, create default
            print(f"Warning: Invalid agents.json, creating default: {e}")
            self._create_default_registry()

    def _create_default_registry(self) -> None:
        """Create default agent registry with common agents."""
        self._agents = {
            "claude": AgentProfile(
                id="claude",
                name="Claude",
                capabilities=[
                    "python",
                    "javascript",
                    "typescript",
                    "html",
                    "css",
                    "code-review",
                    "testing",
                    "documentation",
                    "debugging",
                    "refactoring",
                    "architecture",
                    "api-design",
                ],
                max_parallel_tasks=3,
                preferred_complexity=["low", "medium", "high", "very-high"],
                active=True,
            ),
            "gemini": AgentProfile(
                id="gemini",
                name="Gemini",
                capabilities=[
                    "python",
                    "data-analysis",
                    "documentation",
                    "testing",
                    "code-review",
                    "javascript",
                ],
                max_parallel_tasks=2,
                preferred_complexity=["low", "medium", "high"],
                active=True,
            ),
            "codex": AgentProfile(
                id="codex",
                name="Codex",
                capabilities=[
                    "python",
                    "javascript",
                    "debugging",
                    "testing",
                    "code-generation",
                    "documentation",
                ],
                max_parallel_tasks=2,
                preferred_complexity=["low", "medium"],
                active=True,
            ),
        }
        self._save()

    def _save(self) -> None:
        """Save agents to registry file."""
        # Ensure directory exists
        self.htmlgraph_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "updated": datetime.now().isoformat(),
            "agents": {
                agent_id: agent.to_dict() for agent_id, agent in self._agents.items()
            },
        }

        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

    def register(self, agent: AgentProfile) -> None:
        """Register a new agent or update existing one."""
        self._agents[agent.id] = agent
        self._save()

    def get(self, agent_id: str) -> AgentProfile | None:
        """Get agent profile by ID."""
        return self._agents.get(agent_id)

    def list_agents(self, active_only: bool = False) -> list[AgentProfile]:
        """
        List all agents.

        Args:
            active_only: If True, only return active agents

        Returns:
            List of agent profiles
        """
        agents = list(self._agents.values())
        if active_only:
            agents = [a for a in agents if a.active]
        return agents

    def find_capable_agents(
        self, required_capabilities: list[str], complexity: str | None = None
    ) -> list[AgentProfile]:
        """
        Find agents that can handle the given requirements.

        Args:
            required_capabilities: Required capabilities
            complexity: Task complexity

        Returns:
            List of capable agents, sorted by relevance
        """
        capable = []

        for agent in self._agents.values():
            if not agent.active:
                continue

            if agent.can_handle(required_capabilities):
                if agent.can_handle_complexity(complexity):
                    capable.append(agent)

        # Sort by number of matching capabilities (more specific first)
        def match_score(agent: AgentProfile) -> int:
            if not required_capabilities:
                return 0
            return sum(1 for cap in required_capabilities if cap in agent.capabilities)

        capable.sort(key=match_score, reverse=True)
        return capable

    def update_agent(self, agent_id: str, **updates: Any) -> AgentProfile | None:
        """
        Update agent profile.

        Args:
            agent_id: Agent to update
            **updates: Fields to update

        Returns:
            Updated agent profile or None if not found
        """
        agent = self.get(agent_id)
        if not agent:
            return None

        # Update allowed fields
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        self._save()
        return agent

    def deactivate(self, agent_id: str) -> bool:
        """Deactivate an agent."""
        return self.update_agent(agent_id, active=False) is not None

    def activate(self, agent_id: str) -> bool:
        """Activate an agent."""
        return self.update_agent(agent_id, active=True) is not None

    def delete(self, agent_id: str) -> bool:
        """
        Delete an agent from the registry.

        Args:
            agent_id: Agent to delete

        Returns:
            True if deleted, False if not found
        """
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._save()
            return True
        return False
