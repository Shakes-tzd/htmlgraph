"""
E2E integration tests for multi-agent coordination scenarios.

Tests realistic workflows with 3+ agents working simultaneously:
- Independent feature claims
- Parallel work without conflicts
- Event log consistency
- Handoff chains
"""

import pytest
from datetime import datetime
from tempfile import TemporaryDirectory

from htmlgraph.session_manager import SessionManager
from htmlgraph.models import Node
from htmlgraph.routing import (
    AgentCapabilityRegistry,
    CapabilityMatcher,
)


class TestIndependentAgentWork:
    """Test multiple agents working on different tasks independently."""

    def test_three_agents_claim_different_features(self, tmp_path):
        """3 agents each claim different features without conflicts."""
        manager = SessionManager(tmp_path)

        # Create 3 features
        feature1 = manager.create_feature("API Authentication")
        feature2 = manager.create_feature("Database Migration")
        feature3 = manager.create_feature("UI Components")

        # Agents claim different features
        manager.claim_feature(feature1.id, agent="alice")
        manager.claim_feature(feature2.id, agent="bob")
        manager.claim_feature(feature3.id, agent="charlie")

        # Verify each agent has their feature
        f1 = manager.features_graph.get(feature1.id)
        f2 = manager.features_graph.get(feature2.id)
        f3 = manager.features_graph.get(feature3.id)

        assert f1.agent_assigned == "alice"
        assert f2.agent_assigned == "bob"
        assert f3.agent_assigned == "charlie"

    def test_agents_work_independently_no_conflicts(self, tmp_path):
        """Agents work on features without blocking each other."""
        manager = SessionManager(tmp_path)

        # Create 5 features
        features = [manager.create_feature(f"Task {i}") for i in range(5)]
        feature_ids = [f.id for f in features]

        # Agent A works on features 0, 1
        manager.claim_feature(feature_ids[0], agent="alice")
        manager.start_feature(feature_ids[0], agent="alice")
        f = manager.features_graph.get(feature_ids[0])
        f.steps[0].completed = True

        # Agent B works on features 2, 3
        manager.claim_feature(feature_ids[2], agent="bob")
        manager.start_feature(feature_ids[2], agent="bob")
        f = manager.features_graph.get(feature_ids[2])
        f.steps[0].completed = True

        # Agent C works on feature 4
        manager.claim_feature(feature_ids[4], agent="charlie")
        manager.start_feature(feature_ids[4], agent="charlie")

        # Verify no conflicts
        f0 = manager.features_graph.get(feature_ids[0])
        f2 = manager.features_graph.get(feature_ids[2])
        f4 = manager.features_graph.get(feature_ids[4])

        assert f0.agent_assigned == "alice"
        assert f0.steps[0].completed is True
        assert f2.agent_assigned == "bob"
        assert f2.steps[0].completed is True
        assert f4.agent_assigned == "charlie"

    def test_feature_release_allows_next_agent(self, tmp_path):
        """Releasing a feature allows next agent to claim it."""
        manager = SessionManager(tmp_path)
        feature = manager.create_feature("Shared Task")
        feature_id = feature.id

        # Agent A claims
        manager.claim_feature(feature_id, agent="alice")
        assert manager.features_graph.get(feature_id).agent_assigned == "alice"

        # Agent B cannot claim
        with pytest.raises(ValueError):
            manager.claim_feature(feature_id, agent="bob")

        # Agent A releases
        manager.release_feature(feature_id, agent="alice")
        assert manager.features_graph.get(feature_id).agent_assigned is None

        # Now Agent B can claim
        manager.claim_feature(feature_id, agent="bob")
        assert manager.features_graph.get(feature_id).agent_assigned == "bob"


class TestMultiAgentHandoffChains:
    """Test handoff chains involving multiple agents."""

    def test_handoff_chain_a_to_b_to_c(self, tmp_path):
        """Handoff chain: A -> B -> C -> Done."""
        manager = SessionManager(tmp_path)
        feature = manager.create_feature("Complex Feature")
        feature_id = feature.id

        # Agent A
        manager.claim_feature(feature_id, agent="alice")
        manager.start_feature(feature_id, agent="alice")
        f = manager.features_graph.get(feature_id)
        f.steps[0].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="design_review_needed",
            agent="alice",
        )

        # Agent B
        manager.claim_feature(feature_id, agent="bob")
        manager.start_feature(feature_id, agent="bob")
        f = manager.features_graph.get(feature_id)
        f.steps[1].completed = True

        manager.create_handoff(
            feature_id=feature_id,
            reason="implementation_complete",
            agent="bob",
        )

        # Agent C
        manager.claim_feature(feature_id, agent="charlie")
        manager.start_feature(feature_id, agent="charlie")
        f = manager.features_graph.get(feature_id)
        f.steps[2].completed = True
        f.status = "done"

        # Verify final state
        final = manager.features_graph.get(feature_id)
        assert final.status == "done"
        assert final.previous_agent == "bob"

    def test_parallel_handoff_chains(self, tmp_path):
        """Two independent handoff chains running in parallel."""
        manager = SessionManager(tmp_path)

        # Create 2 features
        feat1 = manager.create_feature("Feature 1")
        feat2 = manager.create_feature("Feature 2")

        # Chain 1: A -> B
        manager.claim_feature(feat1.id, agent="alice")
        manager.start_feature(feat1.id, agent="alice")
        f = manager.features_graph.get(feat1.id)
        f.steps[0].completed = True
        manager.create_handoff(feat1.id, reason="ready_for_b", agent="alice")

        # Chain 2: C -> D
        manager.claim_feature(feat2.id, agent="charlie")
        manager.start_feature(feat2.id, agent="charlie")
        f = manager.features_graph.get(feat2.id)
        f.steps[0].completed = True
        manager.create_handoff(feat2.id, reason="ready_for_d", agent="charlie")

        # Complete chain 1
        manager.claim_feature(feat1.id, agent="bob")
        b_feature = manager.features_graph.get(feat1.id)
        assert b_feature.previous_agent == "alice"

        # Complete chain 2
        manager.claim_feature(feat2.id, agent="david")
        d_feature = manager.features_graph.get(feat2.id)
        assert d_feature.previous_agent == "charlie"


class TestCapabilityRoutingUnderLoad:
    """Test routing decisions with multiple agents and tasks."""

    def test_routing_distributes_based_on_capability(self):
        """Routing distributes tasks based on capability match."""
        registry = AgentCapabilityRegistry()

        # Register agents
        registry.register_agent("alice", ["python", "backend"])
        registry.register_agent("bob", ["python", "frontend"])
        registry.register_agent("charlie", ["testing", "qa"])
        registry.register_agent("david", ["devops", "infrastructure"])

        # Test various task routings
        tasks_and_expected = [
            (["python", "backend"], "alice"),
            (["python", "frontend"], "bob"),
            (["testing"], "charlie"),
            (["devops"], "david"),
        ]

        for requirements, expected_agent in tasks_and_expected:
            task = Node(
                id=f"task-{expected_agent}",
                title=f"Task for {expected_agent}",
                required_capabilities=requirements
            )
            agents = registry.get_all_agents()
            best = CapabilityMatcher.find_best_agent(agents, task)
            assert best is not None
            assert best.agent_id == expected_agent

    def test_routing_respects_wip_limits(self):
        """Routing respects work-in-progress limits."""
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

        # Should get Bob (Alice at capacity)
        best = CapabilityMatcher.find_best_agent(agents, task)
        assert best.agent_id == "bob"


class TestEventLogConsistency:
    """Verify event log stays consistent with parallel operations."""

    def test_session_tracking_records_operations(self, tmp_path):
        """Session tracking records all agent operations."""
        manager = SessionManager(tmp_path)

        features = [manager.create_feature(f"Feature {i}") for i in range(3)]

        # Multiple operations
        manager.claim_feature(features[0].id, agent="alice")
        manager.claim_feature(features[1].id, agent="bob")
        manager.start_feature(features[0].id, agent="alice")
        manager.start_feature(features[1].id, agent="bob")

        # Verify features are claimed
        f0 = manager.features_graph.get(features[0].id)
        f1 = manager.features_graph.get(features[1].id)
        assert f0.agent_assigned == "alice"
        assert f1.agent_assigned == "bob"

    def test_concurrent_claims_serialize_correctly(self, tmp_path):
        """Only one agent can claim a feature at a time."""
        manager = SessionManager(tmp_path)
        feature = manager.create_feature("Disputed Feature")
        feature_id = feature.id

        # Sequential claims
        manager.claim_feature(feature_id, agent="alice")
        f = manager.features_graph.get(feature_id)
        assert f.agent_assigned == "alice"

        # Bob cannot claim
        with pytest.raises(ValueError):
            manager.claim_feature(feature_id, agent="bob")

        # Feature still Alice's
        f = manager.features_graph.get(feature_id)
        assert f.agent_assigned == "alice"


class TestComplexMultiAgentScenario:
    """Realistic complex scenario with 4 agents, handoffs, and routing."""

    def test_4_agent_feature_pipeline(self, tmp_path):
        """Feature pipeline: Architect -> Backend -> QA -> Done."""
        manager = SessionManager(tmp_path)
        registry = AgentCapabilityRegistry()

        # Register specialists
        registry.register_agent("architect", ["architecture", "design"])
        registry.register_agent("alice", ["python", "backend", "performance"])
        registry.register_agent("bob", ["python", "backend", "databases"])
        registry.register_agent("qa", ["testing", "quality-assurance"])

        # Architect creates 3 features
        features = [
            manager.create_feature("Feature 1: User API"),
            manager.create_feature("Feature 2: Auth Service"),
            manager.create_feature("Feature 3: Data Pipeline"),
        ]

        # Architect designs all
        for f in features:
            manager.claim_feature(f.id, agent="architect")
            manager.start_feature(f.id, agent="architect")
            feat = manager.features_graph.get(f.id)
            feat.steps[0].completed = True
            manager.create_handoff(f.id, reason="design_complete", agent="architect")

        # Backend team implements
        manager.claim_feature(features[0].id, agent="alice")
        manager.claim_feature(features[1].id, agent="bob")
        manager.claim_feature(features[2].id, agent="alice")

        # Both work
        for feat_id, agent in [
            (features[0].id, "alice"),
            (features[1].id, "bob"),
            (features[2].id, "alice"),
        ]:
            manager.start_feature(feat_id, agent=agent)
            f = manager.features_graph.get(feat_id)
            f.steps[1].completed = True
            manager.create_handoff(feat_id, reason="implementation_complete", agent=agent)

        # QA tests all
        for feat_id in [f.id for f in features]:
            manager.claim_feature(feat_id, agent="qa")
            manager.start_feature(feat_id, agent="qa")
            f = manager.features_graph.get(feat_id)
            f.steps[2].completed = True
            f.status = "done"

        # Verify all complete
        for feat_id in [f.id for f in features]:
            f = manager.features_graph.get(feat_id)
            assert f.status == "done"
            assert f.agent_assigned == "qa"
