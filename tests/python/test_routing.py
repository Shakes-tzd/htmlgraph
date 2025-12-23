"""
Tests for capability-based agent routing.

Tests cover:
- AgentCapabilityRegistry: Agent registration and capability tracking
- CapabilityMatcher: Scoring algorithm for agent-task fit
- Routing functions: Task assignment and batch routing
"""

import pytest
from datetime import datetime
from pathlib import Path

from htmlgraph.models import Node, Step
from htmlgraph.routing import (
    AgentCapabilityRegistry,
    AgentProfile,
    CapabilityMatcher,
    route_task_to_agent,
    route_tasks_to_agents,
)


class TestAgentCapabilityRegistry:
    """Test agent registration and capability tracking."""

    def test_register_agent(self):
        """Test registering an agent with capabilities."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "documentation", "testing"])

        agent = registry.get_agent("claude")
        assert agent is not None
        assert agent.agent_id == "claude"
        assert agent.capabilities == ["python", "documentation", "testing"]
        assert agent.wip_limit == 5
        assert agent.current_wip == 0

    def test_register_multiple_agents(self):
        """Test registering multiple agents."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "testing"])
        registry.register_agent("haiku", ["python", "refactoring"])
        registry.register_agent("opus", ["python", "architecture"])

        agents = registry.get_all_agents()
        assert len(agents) == 3
        assert any(a.agent_id == "claude" for a in agents)
        assert any(a.agent_id == "haiku" for a in agents)
        assert any(a.agent_id == "opus" for a in agents)

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])

        assert registry.unregister_agent("claude") is True
        assert registry.get_agent("claude") is None

    def test_unregister_nonexistent_agent(self):
        """Test unregistering an agent that doesn't exist."""
        registry = AgentCapabilityRegistry()
        assert registry.unregister_agent("nonexistent") is False

    def test_set_wip(self):
        """Test setting WIP count for an agent."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])

        assert registry.set_wip("claude", 3) is True
        agent = registry.get_agent("claude")
        assert agent.current_wip == 3

    def test_set_wip_nonexistent_agent(self):
        """Test setting WIP for nonexistent agent."""
        registry = AgentCapabilityRegistry()
        assert registry.set_wip("nonexistent", 1) is False

    def test_increment_wip(self):
        """Test incrementing WIP count."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.increment_wip("claude")
        registry.increment_wip("claude")

        agent = registry.get_agent("claude")
        assert agent.current_wip == 2

    def test_decrement_wip(self):
        """Test decrementing WIP count."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.set_wip("claude", 3)
        registry.decrement_wip("claude")

        agent = registry.get_agent("claude")
        assert agent.current_wip == 2

    def test_decrement_wip_below_zero(self):
        """Test decrementing WIP doesn't go below 0."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])

        registry.decrement_wip("claude")
        agent = registry.get_agent("claude")
        assert agent.current_wip == 0  # Should not go negative

    def test_get_capable_agents_exact_match(self):
        """Test finding agents with exact capability match."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "testing"])
        registry.register_agent("haiku", ["javascript"])
        registry.register_agent("opus", ["python", "architecture"])

        capable = registry.get_capable_agents(["python"])
        assert len(capable) == 2
        assert any(a.agent_id == "claude" for a in capable)
        assert any(a.agent_id == "opus" for a in capable)

    def test_get_capable_agents_empty_requirements(self):
        """Test that empty requirements return all agents."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.register_agent("haiku", ["javascript"])

        capable = registry.get_capable_agents([])
        assert len(capable) == 2

    def test_get_capable_agents_sorted_by_availability(self):
        """Test that capable agents are sorted by WIP (availability)."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.register_agent("haiku", ["python"])
        registry.register_agent("opus", ["python"])

        # Set different WIP levels
        registry.set_wip("claude", 3)
        registry.set_wip("haiku", 0)
        registry.set_wip("opus", 1)

        capable = registry.get_capable_agents(["python"])
        assert capable[0].agent_id == "haiku"  # Lowest WIP
        assert capable[1].agent_id == "opus"
        assert capable[2].agent_id == "claude"


class TestCapabilityMatcher:
    """Test capability matching and scoring."""

    def test_score_exact_match(self):
        """Test scoring when agent has all required capabilities."""
        agent = AgentProfile("claude", ["python", "testing", "documentation"])
        task = Node(
            id="task-1",
            title="Write Python Tests",
            required_capabilities=["python", "testing"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=False)
        # 2 exact matches * 100 = 200
        # 1 extra capability * 10 = 10
        # Total: 210
        assert score == 210

    def test_score_partial_match(self):
        """Test scoring with partial capability match."""
        agent = AgentProfile("claude", ["python", "documentation"])
        task = Node(
            id="task-1",
            title="Full Stack Dev",
            required_capabilities=["python", "javascript", "testing"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=False)
        # 1 exact match (python): 100
        # 2 missing (javascript, testing): -100
        # 1 extra capability (documentation): 10
        # Total: 10
        assert score == 10

    def test_score_no_match(self):
        """Test scoring when agent has no required capabilities."""
        agent = AgentProfile("claude", ["javascript"])
        task = Node(
            id="task-1",
            title="Python Backend",
            required_capabilities=["python", "databases"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=False)
        # 2 missing: -100
        # 1 extra capability (javascript): 10
        # Total: -90
        assert score == -90

    def test_score_no_required_capabilities(self):
        """Test scoring task with no required capabilities."""
        agent = AgentProfile("claude", ["python"])
        task = Node(id="task-1", title="Unspecified Task")

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=False)
        # Unspecified tasks get baseline score
        assert score == 50.0

    def test_score_with_workload_penalty(self):
        """Test that workload penalizes score."""
        agent = AgentProfile("claude", ["python"])
        agent.current_wip = 3

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=True)
        # 1 exact match: 100
        # WIP penalty: -15 (3 * 5)
        # Expected: 85
        assert score == 85

    def test_score_at_capacity(self):
        """Test severe penalty when agent is at WIP capacity."""
        agent = AgentProfile("claude", ["python"], wip_limit=5)
        agent.current_wip = 5  # At capacity

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=True)
        # 1 exact match: 100
        # WIP penalty: -25 (5 * 5)
        # At capacity penalty: -100
        # Expected: -25
        assert score == -25

    def test_score_extra_capabilities_bonus(self):
        """Test bonus for having extra capabilities."""
        agent = AgentProfile("claude", ["python", "testing", "documentation", "refactoring"])
        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        score = CapabilityMatcher.score_agent_task_fit(agent, task, include_workload=False)
        # 1 exact match: 100
        # 3 extra capabilities: 30 (3 * 10)
        # Expected: 130
        assert score == 130

    def test_find_best_agent_exact_match(self):
        """Test finding best agent with exact match."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "testing"])
        registry.register_agent("haiku", ["javascript"])

        task = Node(
            id="task-1",
            title="Python Tests",
            required_capabilities=["python", "testing"]
        )

        agents = registry.get_all_agents()
        best = CapabilityMatcher.find_best_agent(agents, task)

        assert best is not None
        assert best.agent_id == "claude"

    def test_find_best_agent_no_match(self):
        """Test finding best agent when none match well."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.register_agent("haiku", ["javascript"])

        task = Node(
            id="task-1",
            title="Rust Backend",
            required_capabilities=["rust"]
        )

        agents = registry.get_all_agents()
        best = CapabilityMatcher.find_best_agent(agents, task, min_score=0.0)

        # No agent meets minimum score
        assert best is None

    def test_find_best_agent_by_availability(self):
        """Test that best agent selection considers workload."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.register_agent("haiku", ["python"])

        registry.set_wip("claude", 4)
        registry.set_wip("haiku", 1)

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        agents = registry.get_all_agents()
        best = CapabilityMatcher.find_best_agent(agents, task)

        # Both match, but haiku has lower WIP
        assert best is not None
        assert best.agent_id == "haiku"


class TestRoutingFunctions:
    """Test routing task assignment functions."""

    def test_route_task_to_agent(self):
        """Test routing a single task."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "testing"])

        task = Node(
            id="task-1",
            title="Python Tests",
            required_capabilities=["python"]
        )

        agent, score = route_task_to_agent(task, registry)
        assert agent is not None
        assert agent.agent_id == "claude"
        assert score >= 100

    def test_route_task_no_capable_agent(self):
        """Test routing when no agent is capable."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["javascript"])

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        agent, score = route_task_to_agent(task, registry, allow_unmatched=False)
        assert agent is None
        assert score == -100.0

    def test_route_task_allow_unmatched(self):
        """Test routing with allow_unmatched=True."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["javascript"])

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        agent, score = route_task_to_agent(task, registry, allow_unmatched=True)
        assert agent is not None
        assert agent.agent_id == "claude"
        # Score will be negative due to missing capability
        assert score < 0

    def test_route_multiple_tasks(self):
        """Test routing multiple tasks."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python", "testing"])
        registry.register_agent("haiku", ["documentation", "refactoring"])

        tasks = [
            Node(
                id="task-1",
                title="Python Tests",
                required_capabilities=["python", "testing"]
            ),
            Node(
                id="task-2",
                title="Refactor Code",
                required_capabilities=["refactoring"]
            ),
        ]

        routing = route_tasks_to_agents(tasks, registry)
        assert len(routing) == 2

        # task-1 should route to claude
        agent1, score1 = routing["task-1"]
        assert agent1.agent_id == "claude"

        # task-2 should route to haiku
        agent2, score2 = routing["task-2"]
        assert agent2.agent_id == "haiku"

    def test_route_unspecified_task_to_available_agent(self):
        """Test that tasks with no required capabilities go to available agents."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("claude", ["python"])
        registry.register_agent("haiku", ["javascript"])

        task = Node(id="task-1", title="General Task")  # No required_capabilities

        agent, score = route_task_to_agent(task, registry)
        # Should route to either agent (both have same baseline score)
        assert agent is not None

    def test_empty_registry(self):
        """Test routing with empty registry."""
        registry = AgentCapabilityRegistry()

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        agent, score = route_task_to_agent(task, registry)
        assert agent is None


class TestCapabilityIntegration:
    """Integration tests for capability-based routing."""

    def test_agent_capability_workflow(self):
        """Test complete workflow: register agents, create tasks, route."""
        registry = AgentCapabilityRegistry()

        # Register agents with different specialties
        registry.register_agent("claude-py", ["python", "testing", "documentation"])
        registry.register_agent("claude-js", ["javascript", "react"])
        registry.register_agent("claude-generalist", ["python", "javascript", "documentation"])

        # Create diverse tasks
        tasks = [
            Node(
                id="task-py-test",
                title="Unit Tests",
                required_capabilities=["python", "testing"]
            ),
            Node(
                id="task-react",
                title="React Component",
                required_capabilities=["javascript", "react"]
            ),
            Node(
                id="task-docs",
                title="Documentation",
                required_capabilities=["documentation"]
            ),
        ]

        # Route tasks
        routing = route_tasks_to_agents(tasks, registry)

        # Verify routing
        assert routing["task-py-test"][0] is not None
        assert routing["task-react"][0] is not None
        assert routing["task-docs"][0] is not None

        # Specialized task should go to specialist
        assert routing["task-react"][0].agent_id == "claude-js"

    def test_workload_balancing(self):
        """Test that routing balances workload across agents."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("agent1", ["python"])
        registry.register_agent("agent2", ["python"])

        # Set agent1 as busy
        registry.set_wip("agent1", 5)
        registry.set_wip("agent2", 1)

        task = Node(
            id="task-1",
            title="Python Task",
            required_capabilities=["python"]
        )

        agent, score = route_task_to_agent(task, registry)
        # Should prefer agent2 due to lower workload
        assert agent.agent_id == "agent2"

    def test_performance_many_agents_many_tasks(self):
        """Test routing performance with realistic scale."""
        import time

        registry = AgentCapabilityRegistry()

        # Register 20 agents with various capabilities
        for i in range(20):
            caps = ["python", "testing"] if i % 3 == 0 else ["javascript", "react"]
            registry.register_agent(f"agent-{i}", caps)

        # Create 100 tasks
        tasks = []
        for i in range(100):
            caps = ["python"] if i % 2 == 0 else ["javascript"]
            tasks.append(
                Node(
                    id=f"task-{i}",
                    title=f"Task {i}",
                    required_capabilities=caps
                )
            )

        # Measure routing time
        start = time.time()
        routing = route_tasks_to_agents(tasks, registry)
        elapsed = time.time() - start

        # Should complete in under 100ms
        assert elapsed < 0.1
        assert len(routing) == 100
