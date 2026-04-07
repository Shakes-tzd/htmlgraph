"""
Integration tests for Cross-Agent Presence Tracking (Phase 1).

Tests:
- AgentPresence data model
- PresenceManager state management
- Database persistence
- Idle detection
- Event integration
"""

import time
from datetime import datetime, timedelta

from htmlgraph.api.presence import AgentPresence, PresenceManager, PresenceStatus


class TestAgentPresence:
    """Test AgentPresence data model."""

    def test_create_presence(self):
        """Test creating an AgentPresence instance."""
        presence = AgentPresence(agent_id="test-agent")

        assert presence.agent_id == "test-agent"
        assert presence.status == PresenceStatus.OFFLINE
        assert presence.current_feature_id is None
        assert presence.last_tool_name is None
        assert presence.total_tools_executed == 0
        assert presence.total_cost_tokens == 0

    def test_presence_to_dict(self):
        """Test converting AgentPresence to dictionary."""
        presence = AgentPresence(
            agent_id="test-agent",
            status=PresenceStatus.ACTIVE,
            current_feature_id="feat-123",
            last_tool_name="Read",
            total_tools_executed=5,
            total_cost_tokens=1000,
        )

        data = presence.to_dict()

        assert data["agent_id"] == "test-agent"
        assert data["status"] == "active"
        assert data["current_feature_id"] == "feat-123"
        assert data["last_tool_name"] == "Read"
        assert data["total_tools_executed"] == 5
        assert data["total_cost_tokens"] == 1000

    def test_presence_from_dict(self):
        """Test creating AgentPresence from dictionary."""
        data = {
            "agent_id": "test-agent",
            "status": "active",
            "current_feature_id": "feat-123",
            "last_tool_name": "Read",
            "last_activity": datetime.now().isoformat(),
            "total_tools_executed": 5,
            "total_cost_tokens": 1000,
        }

        presence = AgentPresence.from_dict(data)

        assert presence.agent_id == "test-agent"
        assert presence.status == PresenceStatus.ACTIVE
        assert presence.current_feature_id == "feat-123"
        assert presence.last_tool_name == "Read"


class TestPresenceManager:
    """Test PresenceManager functionality."""

    def test_update_presence(self, tmp_path):
        """Test updating agent presence."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        event = {
            "tool_name": "Read",
            "session_id": "sess-123",
            "feature_id": "feat-456",
            "cost_tokens": 100,
        }

        presence = manager.update_presence("agent-1", event)

        assert presence.agent_id == "agent-1"
        assert presence.status == PresenceStatus.ACTIVE
        assert presence.last_tool_name == "Read"
        assert presence.current_feature_id == "feat-456"
        assert presence.total_tools_executed == 1
        assert presence.total_cost_tokens == 100

    def test_multiple_updates(self, tmp_path):
        """Test multiple updates to same agent."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        # First update
        manager.update_presence(
            "agent-1", {"tool_name": "Read", "session_id": "sess-1", "cost_tokens": 50}
        )

        # Second update
        presence = manager.update_presence(
            "agent-1", {"tool_name": "Write", "session_id": "sess-1", "cost_tokens": 75}
        )

        assert presence.total_tools_executed == 2
        assert presence.total_cost_tokens == 125
        assert presence.last_tool_name == "Write"

    def test_get_all_presence(self, tmp_path):
        """Test getting all agent presence."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        # Add multiple agents
        manager.update_presence(
            "agent-1", {"tool_name": "Read", "session_id": "sess-1"}
        )
        manager.update_presence(
            "agent-2", {"tool_name": "Write", "session_id": "sess-2"}
        )
        manager.update_presence(
            "agent-3", {"tool_name": "Bash", "session_id": "sess-3"}
        )

        all_presence = manager.get_all_presence()

        assert len(all_presence) == 3
        agent_ids = {p.agent_id for p in all_presence}
        assert agent_ids == {"agent-1", "agent-2", "agent-3"}

    def test_get_agent_presence(self, tmp_path):
        """Test getting specific agent presence."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        manager.update_presence(
            "agent-1", {"tool_name": "Read", "session_id": "sess-1"}
        )

        presence = manager.get_agent_presence("agent-1")

        assert presence is not None
        assert presence.agent_id == "agent-1"
        assert presence.last_tool_name == "Read"

        # Non-existent agent
        missing = manager.get_agent_presence("agent-999")
        assert missing is None

    def test_mark_idle(self, tmp_path):
        """Test marking agents as idle after timeout."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path), idle_timeout_seconds=1)

        # Create active agent
        manager.update_presence(
            "agent-1", {"tool_name": "Read", "session_id": "sess-1"}
        )

        # Should be active
        presence = manager.get_agent_presence("agent-1")
        assert presence.status == PresenceStatus.ACTIVE

        # Wait for idle timeout
        time.sleep(1.5)

        # Mark idle
        marked_idle = manager.mark_idle()

        assert "agent-1" in marked_idle

        # Verify status changed
        presence = manager.get_agent_presence("agent-1")
        assert presence.status == PresenceStatus.IDLE

    def test_mark_offline(self, tmp_path):
        """Test marking agent as offline."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        manager.update_presence(
            "agent-1", {"tool_name": "Read", "session_id": "sess-1"}
        )

        # Mark offline
        success = manager.mark_offline("agent-1")
        assert success is True

        # Verify status
        presence = manager.get_agent_presence("agent-1")
        assert presence.status == PresenceStatus.OFFLINE

        # Non-existent agent
        success = manager.mark_offline("agent-999")
        assert success is False

    def test_cleanup_stale_agents(self, tmp_path):
        """Test cleanup of stale agents."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        # Create agent with old activity
        manager.update_presence(
            "agent-old", {"tool_name": "Read", "session_id": "sess-1"}
        )

        # Manually set old timestamp
        manager.agents["agent-old"].last_activity = datetime.now() - timedelta(hours=25)

        # Create recent agent
        manager.update_presence(
            "agent-new", {"tool_name": "Write", "session_id": "sess-2"}
        )

        # Cleanup
        removed = manager.cleanup_stale_agents(max_age_hours=24)

        assert "agent-old" in removed
        assert "agent-new" not in removed
        assert "agent-old" not in manager.agents
        assert "agent-new" in manager.agents


class TestPresencePersistence:
    """Test database persistence."""

    def test_save_and_load(self, tmp_path):
        """Test saving to database and loading on restart."""
        db_path = tmp_path / "test.db"

        # First manager - add agents
        manager1 = PresenceManager(db_path=str(db_path))
        manager1.update_presence(
            "agent-1",
            {
                "tool_name": "Read",
                "session_id": "sess-1",
                "feature_id": "feat-123",
                "cost_tokens": 100,
            },
        )
        manager1.update_presence(
            "agent-2", {"tool_name": "Write", "session_id": "sess-2", "cost_tokens": 50}
        )

        # Second manager - should load from database
        manager2 = PresenceManager(db_path=str(db_path))

        assert len(manager2.agents) == 2
        assert "agent-1" in manager2.agents
        assert "agent-2" in manager2.agents

        presence = manager2.get_agent_presence("agent-1")
        assert presence.last_tool_name == "Read"
        assert presence.current_feature_id == "feat-123"
        assert presence.total_cost_tokens == 100


class TestPresenceLatency:
    """Test latency requirements (<500ms)."""

    def test_update_latency(self, tmp_path):
        """Test that presence updates complete in <500ms."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        event = {"tool_name": "Read", "session_id": "sess-1", "cost_tokens": 100}

        start = time.time()
        manager.update_presence("agent-1", event)
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, f"Update took {elapsed_ms:.2f}ms (exceeds 500ms)"

    def test_get_all_latency(self, tmp_path):
        """Test that get_all_presence completes in <500ms."""
        db_path = tmp_path / "test.db"
        manager = PresenceManager(db_path=str(db_path))

        # Add multiple agents
        for i in range(10):
            manager.update_presence(
                f"agent-{i}", {"tool_name": "Read", "session_id": f"sess-{i}"}
            )

        start = time.time()
        manager.get_all_presence()
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 500, (
            f"get_all_presence took {elapsed_ms:.2f}ms (exceeds 500ms)"
        )
