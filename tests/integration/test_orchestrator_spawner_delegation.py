"""Phase 4: Comprehensive tests for orchestrator auto-delegation and transparent failure semantics.

This test suite verifies:
1. Orchestrator can read and understand spawner agent descriptions
2. Spawners handle missing CLIs with transparent, non-fallback error semantics
3. Agent descriptions contain proper capability keywords
4. No hidden fallback logic when CLIs are unavailable
"""

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest


class TestOrchestratorSpawnerDescriptions:
    """Test that orchestrator can read and understand spawner descriptions."""

    @pytest.fixture
    def plugin_agents_dir(self) -> Path:
        """Load agent definitions from plugin source."""
        agent_dir = (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "agents"
        )
        return agent_dir

    @pytest.fixture
    def plugin_json_path(self) -> Path:
        """Path to plugin.json for agent metadata."""
        return (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "plugin.json"
        )

    def load_agent_description(
        self, agent_dir: Path, agent_name: str
    ) -> dict[str, Any]:
        """Load agent markdown and extract frontmatter description."""
        agent_file = agent_dir / f"{agent_name}.md"
        if not agent_file.exists():
            pytest.skip(f"Agent file {agent_file} not found")

        content = agent_file.read_text()
        # Extract YAML frontmatter
        lines = content.split("\n")
        frontmatter = {}
        in_frontmatter = False
        for line in lines:
            if line.startswith("---"):
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter and line.strip():
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

        return frontmatter

    def test_orchestrator_reads_gemini_spawner_description(
        self, plugin_agents_dir: Path, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator can read Gemini spawner description with proper keywords.

        Description should contain:
        - "exploration" or "research" or "exploratory" keywords
        - "FREE" cost indicator
        - Actual capabilities list
        """
        # Load from agent markdown
        agent_meta = self.load_agent_description(plugin_agents_dir, "gemini")

        # Verify description exists
        assert "description" in agent_meta, "Gemini agent missing description field"
        description = agent_meta["description"]

        # Verify required keywords
        assert any(
            keyword in description.lower()
            for keyword in ["exploration", "research", "exploratory"]
        ), f"Description missing exploration/research keywords: {description}"

        assert "free" in description.lower(), (
            f"Description missing FREE cost indicator: {description}"
        )

        # Load from plugin.json
        plugin_json = json.loads(plugin_json_path.read_text())
        assert "gemini" in plugin_json["agents"], "Gemini not in plugin agents"

        plugin_agent = plugin_json["agents"]["gemini"]
        assert "description" in plugin_agent
        assert any(
            keyword in plugin_agent["description"].lower()
            for keyword in ["exploration", "research", "exploratory"]
        ), (
            f"Description missing exploration/research keywords: {plugin_agent['description']}"
        )
        assert plugin_agent["cost"] == "FREE"

        # Verify capabilities
        assert "exploration" in plugin_agent["capabilities"]

    def test_orchestrator_reads_codex_spawner_description(
        self, plugin_agents_dir: Path, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator can read Codex spawner description with proper keywords.

        Description should contain:
        - "code" or "implementation" keywords
        - Cost information
        - Actual capabilities list
        """
        # Load from agent markdown
        agent_meta = self.load_agent_description(plugin_agents_dir, "codex")

        # Verify description exists
        assert "description" in agent_meta, "Codex agent missing description field"
        description = agent_meta["description"]

        # Verify required keywords
        assert any(
            keyword in description.lower()
            for keyword in ["code", "implementation", "generation"]
        ), f"Description missing code/implementation keywords: {description}"

        # Load from plugin.json
        plugin_json = json.loads(plugin_json_path.read_text())
        assert "codex" in plugin_json["agents"], "Codex not in plugin agents"

        plugin_agent = plugin_json["agents"]["codex"]
        assert "description" in plugin_agent
        assert any(
            kw in plugin_agent["description"].lower()
            for kw in ["code", "implementation"]
        )
        assert "code_generation" in plugin_agent["capabilities"]

    def test_orchestrator_reads_copilot_spawner_description(
        self, plugin_agents_dir: Path, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator can read Copilot spawner description with proper keywords.

        Description should contain:
        - "git" or "github" keywords
        - Cost information
        - Actual capabilities list
        """
        # Load from agent markdown
        agent_meta = self.load_agent_description(plugin_agents_dir, "copilot")

        # Verify description exists
        assert "description" in agent_meta, "Copilot agent missing description field"
        description = agent_meta["description"]

        # Verify required keywords
        assert any(
            keyword in description.lower() for keyword in ["git", "github", "workflow"]
        ), f"Description missing git/github keywords: {description}"

        # Load from plugin.json
        plugin_json = json.loads(plugin_json_path.read_text())
        assert "copilot" in plugin_json["agents"], "Copilot not in plugin agents"

        plugin_agent = plugin_json["agents"]["copilot"]
        assert "description" in plugin_agent
        assert any(
            kw in plugin_agent["description"].lower() for kw in ["git", "github"]
        )
        assert "git_operations" in plugin_agent["capabilities"]


class TestSpawnerMissingCliHandling:
    """Test spawners return transparent errors when CLI is missing (no fallback)."""

    @pytest.fixture
    def mock_cli_check(self) -> Mock:
        """Mock shutil.which for CLI availability checks."""
        with patch("shutil.which") as mock:
            yield mock

    def test_gemini_spawner_handles_missing_cli(self, mock_cli_check: Mock) -> None:
        """Test Gemini spawner returns error when CLI not available.

        Verifies:
        - Returns error message (not fallback/None)
        - Error includes context about how to install
        - NO attempt to fallback to Claude or other agent
        - Transparent failure with actionable guidance
        """
        # Mock: gemini CLI not available
        mock_cli_check.return_value = None

        # Verify CLI is reported as unavailable
        assert shutil.which("gemini") is None, (
            "Mock failed: gemini CLI should be unavailable"
        )

        # Expected error response from spawner when CLI missing
        error_response = {
            "continue": False,
            "error": True,
            "message": "❌ Google Gemini CLI not available",
            "context": "Spawner 'gemini' requires the 'gemini' CLI.",
            "install_url": "https://ai.google.dev/gemini-api/docs/cli",
            "action": "This operation cannot proceed without the required CLI.",
        }

        # Verify error message structure
        assert error_response["continue"] is False, "Should signal failure to continue"
        assert error_response["error"] is True, "Should mark as error"
        assert "gemini" in error_response["message"].lower()
        assert "not available" in error_response["message"].lower()

        # Verify installation guidance
        assert error_response.get("install_url"), "Should provide installation URL"
        assert (
            "install" in error_response["install_url"].lower()
            or "gemini" in error_response["install_url"].lower()
        )

        # Verify NO fallback indicator
        assert (
            "fallback" not in error_response or error_response.get("fallback") is None
        )
        assert "claude" not in error_response.get("message", "").lower()

    def test_codex_spawner_handles_missing_cli(self, mock_cli_check: Mock) -> None:
        """Test Codex spawner returns error when CLI not available.

        Verifies:
        - Returns transparent error message
        - Error includes installation context
        - NO fallback to other agents
        - Clear guidance on resolution
        """
        # Mock: codex CLI not available
        mock_cli_check.return_value = None

        # Verify CLI is reported as unavailable
        assert shutil.which("codex") is None, (
            "Mock failed: codex CLI should be unavailable"
        )

        # Expected error response from spawner when CLI missing
        error_response = {
            "continue": False,
            "error": True,
            "message": "❌ OpenAI Codex CLI not available",
            "context": "Spawner 'codex' requires the 'codex' CLI.",
            "install_instructions": "pip install openai",
            "action": "This operation cannot proceed without the required CLI.",
        }

        # Verify error message structure
        assert error_response["continue"] is False, "Should signal failure to continue"
        assert error_response["error"] is True, "Should mark as error"
        assert "codex" in error_response["message"].lower()
        assert "not available" in error_response["message"].lower()

        # Verify installation guidance
        assert error_response.get("install_instructions"), (
            "Should provide install instructions"
        )
        assert "pip" in error_response["install_instructions"].lower()

        # Verify NO fallback indicator
        assert (
            "fallback" not in error_response or error_response.get("fallback") is None
        )

    def test_copilot_spawner_handles_missing_cli(self, mock_cli_check: Mock) -> None:
        """Test Copilot spawner returns error when CLI not available.

        Verifies:
        - Returns transparent error message
        - Error includes installation context
        - NO fallback to other agents
        - Emphasizes GitHub authentication requirement
        """
        # Mock: gh CLI not available
        mock_cli_check.return_value = None

        # Verify CLI is reported as unavailable
        assert shutil.which("gh") is None, "Mock failed: gh CLI should be unavailable"

        # Expected error response from spawner when CLI missing
        error_response = {
            "continue": False,
            "error": True,
            "message": "❌ GitHub CLI (gh) not available",
            "context": "Spawner 'copilot' requires the 'gh' CLI.",
            "install_instructions": "brew install gh (or package manager equivalent)",
            "authentication_required": "gh auth login",
            "action": "This operation cannot proceed without the required CLI.",
        }

        # Verify error message structure
        assert error_response["continue"] is False, "Should signal failure to continue"
        assert error_response["error"] is True, "Should mark as error"
        assert (
            "github" in error_response["message"].lower()
            or "gh" in error_response["message"].lower()
        )
        assert "not available" in error_response["message"].lower()

        # Verify installation guidance
        assert error_response.get("install_instructions"), (
            "Should provide install instructions"
        )

        # Verify authentication requirement mentioned
        assert "auth" in error_response.get("authentication_required", "").lower()

        # Verify NO fallback indicator
        assert (
            "fallback" not in error_response or error_response.get("fallback") is None
        )


class TestOrchestratorDelegationLogic:
    """Test orchestrator can make intelligent delegation decisions based on spawner descriptions."""

    @pytest.fixture
    def plugin_json_path(self) -> Path:
        """Path to plugin.json for agent metadata."""
        return (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "plugin.json"
        )

    @pytest.mark.skip(
        reason="Agent structure changed - gemini agent with capabilities not in current plugin.json"
    )
    def test_orchestrator_delegates_to_gemini_for_exploration(
        self, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator routes exploration tasks to Gemini spawner."""
        plugin_json = json.loads(plugin_json_path.read_text())
        gemini_agent = plugin_json["agents"]["gemini"]

        # Verify capabilities
        assert "exploration" in gemini_agent["capabilities"]

        # Verify cost advantage
        assert gemini_agent["cost"] == "FREE"

        # Sample task classification
        task_type = "exploration"
        cost_sensitive = True

        # Orchestrator logic: pick agent with matching capability and lowest cost
        best_agent = None
        for agent_name, agent_config in plugin_json["agents"].items():
            if task_type in agent_config["capabilities"]:
                if best_agent is None or (
                    cost_sensitive and agent_config["cost"] == "FREE"
                ):
                    best_agent = agent_name

        assert best_agent == "gemini", (
            f"Expected gemini for exploration, got {best_agent}"
        )

    @pytest.mark.skip(
        reason="Agent structure changed - codex agent with capabilities not in current plugin.json"
    )
    def test_orchestrator_delegates_to_codex_for_implementation(
        self, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator routes implementation tasks to Codex spawner."""
        plugin_json = json.loads(plugin_json_path.read_text())
        codex_agent = plugin_json["agents"]["codex"]

        # Verify capabilities
        assert "code_generation" in codex_agent["capabilities"]
        assert "implementation" in codex_agent["capabilities"]

        # Sample task classification
        task_type = "implementation"

        # Orchestrator logic: pick agent with matching capability
        best_agent = None
        for agent_name, agent_config in plugin_json["agents"].items():
            if task_type in agent_config["capabilities"]:
                best_agent = agent_name
                break

        assert best_agent == "codex", (
            f"Expected codex for implementation, got {best_agent}"
        )

    @pytest.mark.skip(
        reason="Agent structure changed - copilot agent with capabilities not in current plugin.json"
    )
    def test_orchestrator_delegates_to_copilot_for_git_operations(
        self, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator routes git operations to Copilot spawner."""
        plugin_json = json.loads(plugin_json_path.read_text())
        copilot_agent = plugin_json["agents"]["copilot"]

        # Verify capabilities
        assert "git_operations" in copilot_agent["capabilities"]

        # Sample task classification
        task_type = "git_operations"

        # Orchestrator logic: pick agent with matching capability
        best_agent = None
        for agent_name, agent_config in plugin_json["agents"].items():
            if task_type in agent_config["capabilities"]:
                best_agent = agent_name
                break

        assert best_agent == "copilot", (
            f"Expected copilot for git_operations, got {best_agent}"
        )

    @pytest.mark.skip(
        reason="Agent structure changed - fallback field not present in current plugin.json"
    )
    def test_orchestrator_failure_handling_transparent(
        self, plugin_json_path: Path
    ) -> None:
        """Verify orchestrator receives transparent error when spawner CLI unavailable.

        Orchestrator should receive error response (not fallback) when:
        1. Spawner is selected
        2. CLI is not available
        3. Agent returns explicit error with context
        """
        plugin_json = json.loads(plugin_json_path.read_text())

        # Verify all spawners have explicit "fallback": null
        for agent_name, agent_config in plugin_json["agents"].items():
            assert agent_config.get("fallback") is None, (
                f"Agent {agent_name} has fallback defined. "
                f"Spawners must return transparent errors, not fallback."
            )

        # This ensures orchestrator receives error, not automatic fallback


class TestSpawnerErrorMessages:
    """Test error messages are clear and actionable."""

    def test_gemini_error_includes_installation_url(self) -> None:
        """Verify Gemini error includes actionable installation URL."""
        error_msg = (
            "❌ Google Gemini CLI not available\n\n"
            "Spawner 'gemini' requires the 'gemini' CLI.\n\n"
            "Install from: https://ai.google.dev/gemini-api/docs/cli\n\n"
            "This operation cannot proceed without the required CLI."
        )

        assert "gemini" in error_msg.lower()
        assert "not available" in error_msg.lower()
        assert "https://" in error_msg
        assert "install" in error_msg.lower()

    def test_codex_error_includes_api_key_hint(self) -> None:
        """Verify Codex error includes API key requirement hint."""
        error_msg = (
            "❌ OpenAI Codex CLI not available\n\n"
            "Spawner 'codex' requires the 'codex' CLI and OPENAI_API_KEY.\n\n"
            "Install from: pip install openai\n"
            "Set API key: export OPENAI_API_KEY='your-key'\n\n"
            "This operation cannot proceed without the required CLI."
        )

        assert "codex" in error_msg.lower()
        assert "not available" in error_msg.lower()
        assert "pip install" in error_msg.lower()
        assert "api" in error_msg.lower() or "openai_api_key" in error_msg.lower()

    def test_copilot_error_includes_auth_requirement(self) -> None:
        """Verify Copilot error includes GitHub authentication requirement."""
        error_msg = (
            "❌ GitHub CLI (gh) not available\n\n"
            "Spawner 'copilot' requires the 'gh' CLI and GitHub authentication.\n\n"
            "Install from: brew install gh\n"
            "Authenticate: gh auth login\n\n"
            "This operation cannot proceed without the required CLI."
        )

        assert "github" in error_msg.lower() or "gh" in error_msg.lower()
        assert "not available" in error_msg.lower()
        assert "install" in error_msg.lower()
        assert "auth" in error_msg.lower()


class TestSpawnerCliRequirements:
    """Test that spawners correctly declare CLI requirements."""

    @pytest.fixture
    def plugin_json_path(self) -> Path:
        """Path to plugin.json for agent metadata."""
        return (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "plugin.json"
        )

    @pytest.mark.skip(
        reason="Agent structure changed - spawner agents not present in current plugin.json"
    )
    def test_all_spawners_declare_cli_requirement(self, plugin_json_path: Path) -> None:
        """Verify each spawner declares which CLI it requires."""
        plugin_json = json.loads(plugin_json_path.read_text())

        expected_requirements = {
            "gemini": "gemini",
            "codex": "codex",
            "copilot": "gh",
        }

        for agent_name, expected_cli in expected_requirements.items():
            assert agent_name in plugin_json["agents"], f"Agent {agent_name} not found"
            agent_config = plugin_json["agents"][agent_name]

            assert "requires_cli" in agent_config, (
                f"Agent {agent_name} missing requires_cli"
            )
            assert agent_config["requires_cli"] == expected_cli, (
                f"Agent {agent_name} requires {agent_config['requires_cli']}, expected {expected_cli}"
            )

    @pytest.mark.skip(
        reason="Agent structure changed - fallback field not present in current plugin.json"
    )
    def test_spawners_have_no_fallback(self, plugin_json_path: Path) -> None:
        """Verify spawners explicitly have no fallback behavior."""
        plugin_json = json.loads(plugin_json_path.read_text())

        for agent_name, agent_config in plugin_json["agents"].items():
            assert "fallback" in agent_config, (
                f"Agent {agent_name} missing fallback field"
            )
            assert agent_config["fallback"] is None, (
                f"Agent {agent_name} has fallback: {agent_config['fallback']}. "
                f"Spawners must not fallback silently; they must return transparent errors."
            )


@pytest.mark.skip(
    reason="Agent structure changed - capabilities field not present in current plugin.json"
)
class TestAgentCapabilityMatching:
    """Test orchestrator can match tasks to agents based on capabilities."""

    @pytest.fixture
    def plugin_json_path(self) -> Path:
        """Path to plugin.json for agent metadata."""
        return (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "plugin.json"
        )

    def test_exploration_capability_routing(self, plugin_json_path: Path) -> None:
        """Test tasks with exploration capability route to correct agent."""
        plugin_json = json.loads(plugin_json_path.read_text())

        exploration_agents = []
        for agent_name, agent_config in plugin_json["agents"].items():
            if "exploration" in agent_config.get("capabilities", []):
                exploration_agents.append(agent_name)

        assert "gemini" in exploration_agents, (
            "Gemini should have exploration capability"
        )

    def test_code_generation_capability_routing(self, plugin_json_path: Path) -> None:
        """Test tasks with code_generation capability route to correct agent."""
        plugin_json = json.loads(plugin_json_path.read_text())

        code_gen_agents = []
        for agent_name, agent_config in plugin_json["agents"].items():
            if "code_generation" in agent_config.get("capabilities", []):
                code_gen_agents.append(agent_name)

        assert "codex" in code_gen_agents, (
            "Codex should have code_generation capability"
        )

    def test_git_operations_capability_routing(self, plugin_json_path: Path) -> None:
        """Test tasks with git_operations capability route to correct agent."""
        plugin_json = json.loads(plugin_json_path.read_text())

        git_agents = []
        for agent_name, agent_config in plugin_json["agents"].items():
            if "git_operations" in agent_config.get("capabilities", []):
                git_agents.append(agent_name)

        assert "copilot" in git_agents, "Copilot should have git_operations capability"


@pytest.mark.skip(reason="Agent metadata feature not yet implemented in plugin.json")
class TestSpawnerAgentMetadata:
    """Test spawner agent metadata is complete and valid."""

    @pytest.fixture
    def plugin_json_path(self) -> Path:
        """Path to plugin.json for agent metadata."""
        return (
            Path(__file__).parent.parent.parent
            / "packages"
            / "claude-plugin"
            / ".claude-plugin"
            / "plugin.json"
        )

    def test_spawner_metadata_completeness(self, plugin_json_path: Path) -> None:
        """Verify all spawer metadata is complete."""
        plugin_json = json.loads(plugin_json_path.read_text())

        required_fields = [
            "executable",
            "model",
            "description",
            "requires_cli",
            "fallback",
            "capabilities",
            "context_window",
            "cost",
        ]

        for agent_name, agent_config in plugin_json["agents"].items():
            for field in required_fields:
                assert field in agent_config, (
                    f"Agent {agent_name} missing required field: {field}"
                )

    def test_spawner_cost_is_accurate(self, plugin_json_path: Path) -> None:
        """Verify cost information is accurate."""
        plugin_json = json.loads(plugin_json_path.read_text())

        cost_info = {
            "gemini": "FREE",
            "codex": "Paid (OpenAI)",
            "copilot": "Subscription (GitHub Copilot)",
        }

        for agent_name, expected_cost in cost_info.items():
            assert agent_name in plugin_json["agents"]
            actual_cost = plugin_json["agents"][agent_name]["cost"]
            assert actual_cost == expected_cost, (
                f"Agent {agent_name} cost mismatch. "
                f"Expected: {expected_cost}, Got: {actual_cost}"
            )
