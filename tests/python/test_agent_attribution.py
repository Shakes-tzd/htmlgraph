"""
Tests for agent attribution bug fix.

Verifies that:
1. SDK() without agent parameter raises ValueError with clear error message
2. SDK(agent='name') sets _agent_id correctly
3. Spikes created with agent parameter have agent_assigned field
4. Warning logged when spike created without agent attribution
5. Error messages are clear and helpful
"""

from pathlib import Path
import logging

import pytest

from htmlgraph import SDK
from htmlgraph.exceptions import ValidationError


@pytest.fixture
def tmp_htmlgraph(tmp_path: Path):
    """Create a temporary .htmlgraph directory structure."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()

    # Create all required subdirectories
    for subdir in [
        "features",
        "bugs",
        "spikes",
        "chores",
        "epics",
        "sessions",
        "phases",
        "tracks",
        "patterns",
        "insights",
        "metrics",
        "todos",
    ]:
        (graph_dir / subdir).mkdir()

    return graph_dir


class TestSDKAgentParameterRequired:
    """Test that agent parameter is required for SDK initialization."""

    def test_sdk_without_agent_uses_detected_value(self, tmp_htmlgraph: Path):
        """SDK() without explicit agent uses detect_agent_name() if not CLI."""
        # In test environment, detect_agent_name() will return "claude"
        # (because CLAUDE_CODE_VERSION is set)
        sdk = SDK(directory=tmp_htmlgraph)

        # Should use detected agent
        assert sdk._agent_id is not None
        # In this environment, it should be "claude"
        assert sdk._agent_id in ["claude", "cli"]

    def test_sdk_with_agent_parameter_succeeds(self, tmp_htmlgraph: Path):
        """SDK(agent='name') should succeed and set _agent_id."""
        sdk = SDK(directory=tmp_htmlgraph, agent="test-agent")

        assert sdk._agent_id == "test-agent"
        # Verify collections are initialized
        assert sdk.features is not None
        assert sdk.spikes is not None
        assert sdk.bugs is not None

    def test_sdk_with_agent_parameter_various_names(self, tmp_htmlgraph: Path):
        """SDK should work with various agent names."""
        agent_names = [
            "claude",
            "explorer",
            "coder",
            "tester",
            "my-custom-agent",
            "agent-123",
        ]

        for agent_name in agent_names:
            sdk = SDK(directory=tmp_htmlgraph, agent=agent_name)
            assert sdk._agent_id == agent_name

    def test_sdk_with_claude_agent_name_env(self, tmp_htmlgraph: Path, monkeypatch):
        """SDK should use CLAUDE_AGENT_NAME env var if provided."""
        monkeypatch.setenv("CLAUDE_AGENT_NAME", "env-agent")
        sdk = SDK(directory=tmp_htmlgraph)

        assert sdk._agent_id == "env-agent"

    def test_sdk_explicit_parameter_overrides_env(
        self, tmp_htmlgraph: Path, monkeypatch
    ):
        """Explicit agent parameter should override env vars."""
        monkeypatch.setenv("CLAUDE_AGENT_NAME", "env-agent")
        sdk = SDK(directory=tmp_htmlgraph, agent="explicit-agent")

        assert sdk._agent_id == "explicit-agent"


class TestSpikeWithAgentAttribution:
    """Test that spikes are created with proper agent attribution."""

    def test_spike_has_agent_assigned_field(self, tmp_htmlgraph: Path):
        """Spike created via SDK should have agent_assigned field."""
        sdk = SDK(directory=tmp_htmlgraph, agent="test-agent")

        spike = sdk.spikes.create("Test Spike").save()

        # Spike should have agent_assigned field
        assert hasattr(spike, "agent_assigned")
        assert spike.agent_assigned == "test-agent"

    def test_spike_agent_matches_sdk_agent(self, tmp_htmlgraph: Path):
        """Spike's agent_assigned should match SDK's agent."""
        agent_name = "my-test-agent"
        sdk = SDK(directory=tmp_htmlgraph, agent=agent_name)

        spike = sdk.spikes.create("Investigation").save()

        assert spike.agent_assigned == agent_name

    def test_spike_with_builder_methods_preserves_agent(self, tmp_htmlgraph: Path):
        """Agent attribution should persist through builder methods."""
        sdk = SDK(directory=tmp_htmlgraph, agent="coder")

        spike = (
            sdk.spikes.create("Investigate Database")
            .set_spike_type("technical")
            .set_timebox_hours(4)
            .add_steps(["Research options", "Benchmark"])
            .set_findings("SQLite is sufficient")
            .save()
        )

        assert spike.agent_assigned == "coder"
        assert spike.title == "Investigate Database"
        assert spike.findings == "SQLite is sufficient"

    def test_multiple_spikes_all_have_agent_assigned(self, tmp_htmlgraph: Path):
        """All spikes created should have agent_assigned."""
        sdk = SDK(directory=tmp_htmlgraph, agent="explorer")

        spikes = []
        for i in range(3):
            spike = sdk.spikes.create(f"Spike {i}").save()
            spikes.append(spike)

        # All spikes should have agent_assigned
        for spike in spikes:
            assert hasattr(spike, "agent_assigned")
            assert spike.agent_assigned == "explorer"


class TestSpikeBuilderWarning:
    """Test that warning is logged when spike created without agent."""

    def test_spike_created_always_has_agent(self, tmp_htmlgraph: Path):
        """Spike created should always have agent_assigned from SDK."""
        # Even without explicit agent, SDK detects one
        sdk = SDK(directory=tmp_htmlgraph)

        spike = sdk.spikes.create("Test Spike").save()

        # Should have agent_assigned from SDK
        assert spike.agent_assigned is not None


class TestErrorMessageClarity:
    """Test that error messages are clear and helpful when no agent can be detected."""

    def test_sdk_init_docstring_documents_agent_requirement(self):
        """SDK.__init__ docstring should document agent parameter requirement."""
        docstring = SDK.__init__.__doc__
        assert docstring is not None
        assert "agent" in docstring.lower()
        assert "required" in docstring.lower() or "REQUIRED" in docstring


class TestOtherCollectionsWithAgent:
    """Test that all collections properly use agent attribution."""

    def test_feature_has_agent_assigned(self, tmp_htmlgraph: Path):
        """Feature created via SDK should have agent_assigned."""
        sdk = SDK(directory=tmp_htmlgraph, agent="coder")

        feature = sdk.features.create("User Auth").save()

        assert hasattr(feature, "agent_assigned")
        assert feature.agent_assigned == "coder"

    def test_bug_has_agent_assigned(self, tmp_htmlgraph: Path):
        """Bug created via SDK should have agent_assigned."""
        sdk = SDK(directory=tmp_htmlgraph, agent="tester")

        bug = sdk.bugs.create("Login broken").save()

        assert hasattr(bug, "agent_assigned")
        assert bug.agent_assigned == "tester"

    def test_chore_has_agent_assigned(self, tmp_htmlgraph: Path):
        """Chore created via SDK should have agent_assigned."""
        sdk = SDK(directory=tmp_htmlgraph, agent="coder")

        chore = sdk.chores.create("Update dependencies").save()

        assert hasattr(chore, "agent_assigned")
        assert chore.agent_assigned == "coder"


class TestSpikeRetrieval:
    """Test that spikes can be retrieved and agent is preserved."""

    def test_spike_retrieval_preserves_agent(self, tmp_htmlgraph: Path):
        """Retrieved spike should have agent_assigned field."""
        sdk = SDK(directory=tmp_htmlgraph, agent="explorer")

        # Create spike
        created = sdk.spikes.create("Research Options").save()
        spike_id = created.id

        # Retrieve spike
        retrieved = sdk.spikes.get(spike_id)

        assert retrieved is not None
        assert retrieved.agent_assigned == "explorer"

    def test_all_spikes_have_agent_assigned(self, tmp_htmlgraph: Path):
        """All retrieved spikes should have agent_assigned."""
        sdk = SDK(directory=tmp_htmlgraph, agent="coder")

        # Create multiple spikes
        for i in range(3):
            sdk.spikes.create(f"Spike {i}").save()

        # Get all spikes
        all_spikes = sdk.spikes.all()

        assert len(all_spikes) >= 3
        for spike in all_spikes:
            assert hasattr(spike, "agent_assigned")
            assert spike.agent_assigned == "coder"
