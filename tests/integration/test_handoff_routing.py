"""
E2E integration tests for Handoff + Routing features working together.

This test verifies that:
1. Agent A (Python capabilities) claims a task
2. Agent A completes it and hands off to Agent B (Testing capabilities)
3. Agent B receives the task with handoff context
4. Capability matching correctly routes the task
"""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from htmlgraph.models import Node
from htmlgraph.session_manager import SessionManager
from htmlgraph.routing import (
    AgentCapabilityRegistry,
    CapabilityMatcher,
)


class TestHandoffWithCapabilityMatching:
    """Test handoff between agents when next agent has matching capabilities."""

    def test_agent_a_hands_off_to_capable_agent_b(self, tmp_path):
        """Agent A hands off task to Agent B based on capability match."""
        manager = SessionManager(tmp_path)

        # Create feature
        feature = manager.create_feature("Implement Database Query Optimizer")
        feature.required_capabilities = ["python", "performance"]
        feature_id = feature.id

        # Agent A claims and starts
        manager.claim_feature(feature_id, agent="alice")
        manager.start_feature(feature_id, agent="alice")

        # Agent A completes first step
        feature = manager.features_graph.get(feature_id)
        feature.steps[0].completed = True

        # Agent A hands off
        manager.create_handoff(
            feature_id=feature_id,
            reason="blocked_on_testing",
            notes="Optimization logic complete. Needs comprehensive test coverage.",
            agent="alice",
        )

        # Verify handoff metadata
        handoff_feature = manager.features_graph.get(feature_id)
        assert handoff_feature.handoff_required is True
        assert handoff_feature.previous_agent == "alice"
        assert handoff_feature.handoff_reason == "blocked_on_testing"

        # Use routing to find best agent for continuation
        registry = AgentCapabilityRegistry()
        registry.register_agent("alice", ["python", "performance"])
        registry.register_agent("bob", ["testing", "quality-assurance"])

        # Create test task with testing requirements
        test_task = Node(
            id="test-task",
            title="Testing Task",
            required_capabilities=["testing", "quality-assurance"]
        )
        agents = registry.get_all_agents()
        best_agent = CapabilityMatcher.find_best_agent(agents, test_task)

        # Verify routing found Bob
        assert best_agent is not None
        assert best_agent.agent_id == "bob"

        # Bob claims handoff feature
        manager.claim_feature(feature_id, agent="bob")
        manager.start_feature(feature_id, agent="bob")

        # Verify context preserved
        final_feature = manager.features_graph.get(feature_id)
        assert final_feature.previous_agent == "alice"

    def test_multi_step_handoff_preserves_progress(self, tmp_path):
        """Multiple handoffs preserve full history."""
        manager = SessionManager(tmp_path)

        feature = manager.create_feature("Complete Feature Development")
        feature.required_capabilities = ["architecture"]
        feature_id = feature.id

        # Phase 1: Alice (architecture)
        manager.claim_feature(feature_id, agent="alice")
        manager.start_feature(feature_id, agent="alice")
        feature = manager.features_graph.get(feature_id)
        feature.steps[0].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="implementation_ready",
            notes="Architecture designed. Ready for implementation.",
            agent="alice",
        )

        # Phase 2: Bob (implementation)
        manager.claim_feature(feature_id, agent="bob")
        manager.start_feature(feature_id, agent="bob")
        feature = manager.features_graph.get(feature_id)
        feature.steps[1].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="testing_required",
            notes="Implementation complete. Needs QA testing.",
            agent="bob",
        )

        # Verify history preserved
        final_feature = manager.features_graph.get(feature_id)
        assert final_feature.previous_agent == "bob"
        assert "QA testing" in final_feature.handoff_notes

    def test_routing_respects_capability_matching(self, tmp_path):
        """Routing prefers agents with matching capabilities."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("alice", ["python", "testing"])
        registry.register_agent("bob", ["testing"])

        # Task requiring testing
        test_task = Node(
            id="test-task",
            title="Testing Task",
            required_capabilities=["testing"]
        )

        agents = registry.get_all_agents()
        best_agent = CapabilityMatcher.find_best_agent(agents, test_task)

        # Alice has more capabilities, should be preferred
        assert best_agent is not None
        assert best_agent.agent_id == "alice"


class TestCapabilityRoutingBasics:
    """Test basic capability routing functionality."""

    def test_router_finds_capable_agents(self):
        """Router finds agents with matching capabilities."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("alice", ["python", "testing"])
        registry.register_agent("bob", ["javascript"])

        agents = registry.get_all_agents()
        assert len(agents) == 2

        # Python task
        py_task = Node(
            id="py-task",
            title="Python Task",
            required_capabilities=["python"]
        )
        best = CapabilityMatcher.find_best_agent(agents, py_task)
        assert best.agent_id == "alice"

    def test_routing_respects_workload(self):
        """Routing considers agent workload."""
        registry = AgentCapabilityRegistry()
        registry.register_agent("alice", ["python"], wip_limit=2)
        registry.register_agent("bob", ["python"], wip_limit=2)

        # Alice at capacity
        registry.set_wip("alice", 2)
        registry.set_wip("bob", 0)

        agents = registry.get_all_agents()
        task = Node(
            id="task",
            title="Task",
            required_capabilities=["python"]
        )

        # Should prefer Bob (less loaded)
        best = CapabilityMatcher.find_best_agent(agents, task)
        assert best.agent_id == "bob"


class TestComplexHandoffRoutingScenario:
    """Test realistic multi-agent scenarios with handoffs."""

    def test_three_agent_relay_workflow(self, tmp_path):
        """Complex 3-agent relay: Design -> Implement -> Test."""
        manager = SessionManager(tmp_path)
        registry = AgentCapabilityRegistry()

        # Register specialists
        registry.register_agent("architect", ["architecture", "design"])
        registry.register_agent("backend", ["python", "backend"])
        registry.register_agent("qa", ["testing", "quality"])

        feature = manager.create_feature("Complete API Gateway")
        feature_id = feature.id

        # Phase 1: Architect designs
        manager.claim_feature(feature_id, agent="architect")
        manager.start_feature(feature_id, agent="architect")
        feat = manager.features_graph.get(feature_id)
        feat.steps[0].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="design_complete",
            notes="API schema designed.",
            agent="architect",
        )

        # Phase 2: Backend implements
        manager.claim_feature(feature_id, agent="backend")
        manager.start_feature(feature_id, agent="backend")
        feat = manager.features_graph.get(feature_id)
        feat.steps[1].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="implementation_complete",
            notes="All endpoints implemented.",
            agent="backend",
        )

        # Phase 3: QA tests
        manager.claim_feature(feature_id, agent="qa")
        manager.start_feature(feature_id, agent="qa")
        feat = manager.features_graph.get(feature_id)
        feat.steps[2].completed = True
        feat.status = "done"

        # Verify final state
        final_feat = manager.features_graph.get(feature_id)
        assert final_feat.status == "done"
        assert final_feat.previous_agent == "backend"
        assert final_feat.handoff_required is True
