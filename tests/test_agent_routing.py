"""
Tests for agent capabilities and smart routing.
"""

import pytest
from pathlib import Path
from htmlgraph.models import Node
from htmlgraph.agent_registry import AgentRegistry, AgentProfile
from htmlgraph.agents import AgentInterface
from htmlgraph.graph import HtmlGraph


def test_agent_profile_capability_matching():
    """Test that agent profiles correctly match capabilities."""
    agent = AgentProfile(
        id="test-agent",
        name="Test Agent",
        capabilities=["python", "javascript", "testing"],
        max_parallel_tasks=3,
        preferred_complexity=["low", "medium", "high"]
    )

    # Should match
    assert agent.can_handle(["python"])
    assert agent.can_handle(["python", "javascript"])
    assert agent.can_handle([])  # No requirements

    # Should not match
    assert not agent.can_handle(["rust"])
    assert not agent.can_handle(["python", "rust"])


def test_agent_profile_complexity_matching():
    """Test that agent profiles correctly match complexity levels."""
    agent = AgentProfile(
        id="test-agent",
        name="Test Agent",
        capabilities=["python"],
        preferred_complexity=["low", "medium"]
    )

    # Should match
    assert agent.can_handle_complexity("low")
    assert agent.can_handle_complexity("medium")
    assert agent.can_handle_complexity(None)  # No complexity specified

    # Should not match
    assert not agent.can_handle_complexity("high")
    assert not agent.can_handle_complexity("very-high")


def test_agent_registry_creation(tmp_path):
    """Test that agent registry creates default agents."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir()

    registry = AgentRegistry(htmlgraph_dir)

    # Should have default agents
    agents = registry.list_agents()
    assert len(agents) > 0

    # Should have claude by default
    claude = registry.get("claude")
    assert claude is not None
    assert claude.id == "claude"
    assert "python" in claude.capabilities


def test_agent_registry_find_capable_agents(tmp_path):
    """Test finding agents by capabilities."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    htmlgraph_dir.mkdir()

    registry = AgentRegistry(htmlgraph_dir)

    # Register test agents
    registry.register(AgentProfile(
        id="python-expert",
        name="Python Expert",
        capabilities=["python", "testing", "debugging"],
        preferred_complexity=["high", "very-high"]
    ))

    registry.register(AgentProfile(
        id="js-expert",
        name="JS Expert",
        capabilities=["javascript", "typescript", "testing"],
        preferred_complexity=["medium", "high"]
    ))

    # Find python agents
    python_agents = registry.find_capable_agents(["python"])
    assert len(python_agents) > 0
    assert any(a.id == "python-expert" for a in python_agents)

    # Find testing agents (should match both)
    testing_agents = registry.find_capable_agents(["testing"])
    assert len(testing_agents) >= 2

    # Find with complexity
    complex_python = registry.find_capable_agents(["python"], complexity="high")
    assert any(a.id == "python-expert" for a in complex_python)


def test_task_scoring(tmp_path):
    """Test task scoring algorithm."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    features_dir = htmlgraph_dir / "features"
    features_dir.mkdir(parents=True)

    # Create a test task
    task = Node(
        id="test-task",
        title="Python Feature",
        type="feature",
        priority="high",
        required_capabilities=["python", "testing"],
        complexity="medium",
        estimated_effort=4.0
    )

    # Save task
    graph = HtmlGraph(features_dir)
    graph.add(task)

    # Create agent interface
    agent_interface = AgentInterface(features_dir, agent_id="claude")

    # Create test agent
    agent = AgentProfile(
        id="test-agent",
        name="Test Agent",
        capabilities=["python", "testing", "debugging"],
        preferred_complexity=["low", "medium", "high"]
    )

    # Calculate score
    score = agent_interface.calculate_task_score(task, agent, current_workload=0)

    # High priority + capability match + complexity match should score well
    assert score > 50.0


def test_work_queue_generation(tmp_path):
    """Test work queue generation with smart routing."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    features_dir = htmlgraph_dir / "features"
    features_dir.mkdir(parents=True)

    # Register test agent
    registry = AgentRegistry(htmlgraph_dir)
    registry.register(AgentProfile(
        id="test-agent",
        name="Test Agent",
        capabilities=["python", "testing"],
        preferred_complexity=["low", "medium"]
    ))

    # Create test tasks
    tasks = [
        Node(
            id="task-1",
            title="Python Task",
            type="feature",
            status="todo",
            priority="high",
            required_capabilities=["python"],
            complexity="medium"
        ),
        Node(
            id="task-2",
            title="JS Task",
            type="feature",
            status="todo",
            priority="medium",
            required_capabilities=["javascript"],  # Agent can't do this
            complexity="low"
        ),
        Node(
            id="task-3",
            title="Testing Task",
            type="feature",
            status="todo",
            priority="critical",
            required_capabilities=["testing"],
            complexity="low"
        ),
    ]

    graph = HtmlGraph(features_dir)
    for task in tasks:
        graph.add(task)

    # Create agent interface
    agent_interface = AgentInterface(features_dir, agent_id="test-agent")

    # Get work queue
    queue = agent_interface.get_work_queue(agent_id="test-agent", limit=10, min_score=0.0)

    # Should have python and testing tasks, not JS
    assert len(queue) >= 2

    # Critical priority testing task should be first
    assert queue[0]["task_id"] == "task-3"

    # JS task should not be in queue or have low score
    js_task = next((q for q in queue if q["task_id"] == "task-2"), None)
    if js_task:
        # If it's there, score should be very low
        assert js_task["score"] <= 20.0


def test_find_best_match(tmp_path):
    """Test finding the best agent for a task."""
    htmlgraph_dir = tmp_path / ".htmlgraph"
    features_dir = htmlgraph_dir / "features"
    features_dir.mkdir(parents=True)

    # Register test agents with different capabilities
    registry = AgentRegistry(htmlgraph_dir)

    # Deactivate default agents to test our specific agents
    for agent_id in ["claude", "gemini", "codex"]:
        agent = registry.get(agent_id)
        if agent:
            registry.deactivate(agent_id)

    registry.register(AgentProfile(
        id="python-specialist",
        name="Python Specialist",
        capabilities=["python", "testing"],
        preferred_complexity=["high", "very-high"]
    ))
    registry.register(AgentProfile(
        id="generalist",
        name="Generalist",
        capabilities=["python", "javascript", "testing", "documentation"],
        preferred_complexity=["low", "medium"]
    ))

    # Create a high-complexity Python task
    task = Node(
        id="complex-python",
        title="Complex Python Feature",
        type="feature",
        priority="high",
        required_capabilities=["python"],
        complexity="high"
    )

    graph = HtmlGraph(features_dir)
    graph.add(task)

    agent_interface = AgentInterface(features_dir)

    # Find best match
    match = agent_interface.find_best_match(task)

    assert match is not None
    agent_id, score = match

    # Python specialist should be best match for high complexity
    assert agent_id == "python-specialist"
    assert score > 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
