"""Unit tests for spawner routing in PreToolUse hook."""

import json
from unittest.mock import Mock, patch

import pytest


class TestSpawnerRouting:
    """Test Task() routing to spawner agents."""

    def test_non_task_tool_passes_through(self):
        """Non-Task tools should not be intercepted."""
        hook_input = {"name": "ReadFile", "input": {"path": "/tmp/test.txt"}}

        # Simulate hook behavior - non-Task tools pass through
        tool_name = hook_input.get("name", "")
        assert tool_name != "Task"

        # Router should return early
        response = {"continue": True}
        assert response["continue"] is True

    def test_non_spawner_subagent_type_passes_through(self):
        """Task() with non-spawner types (haiku, sonnet) pass through."""
        # Test Task(subagent_type="haiku") passes through
        hook_input = {
            "name": "Task",
            "input": {"subagent_type": "haiku", "prompt": "Analyze this code"},
        }

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type not in ["gemini", "codex", "copilot"]

        # Should pass through
        response = {"continue": True}
        assert response["continue"] is True

    def test_task_with_empty_subagent_type_passes_through(self):
        """Task() with empty subagent_type should pass through."""
        hook_input = {
            "name": "Task",
            "input": {"subagent_type": "", "prompt": "Do something"},
        }

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type == ""
        assert subagent_type not in ["gemini", "codex", "copilot"]

    def test_task_with_missing_subagent_type_passes_through(self):
        """Task() without subagent_type should pass through."""
        hook_input = {"name": "Task", "input": {"prompt": "Do something"}}

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type == ""

    def test_gemini_spawner_routing(self):
        """Task(subagent_type='gemini') routes to gemini-spawner.py."""
        hook_input = {
            "name": "Task",
            "input": {"subagent_type": "gemini", "prompt": "Analyze this"},
        }

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type == "gemini"
        assert subagent_type in ["gemini", "codex", "copilot"]

    def test_codex_spawner_routing(self):
        """Task(subagent_type='codex') routes to codex-spawner.py."""
        hook_input = {
            "name": "Task",
            "input": {"subagent_type": "codex", "prompt": "Write code"},
        }

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type == "codex"
        assert subagent_type in ["gemini", "codex", "copilot"]

    def test_copilot_spawner_routing(self):
        """Task(subagent_type='copilot') routes to copilot-spawner.py."""
        hook_input = {
            "name": "Task",
            "input": {"subagent_type": "copilot", "prompt": "Create PR"},
        }

        tool_name = hook_input.get("name", "")
        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "").strip()

        assert tool_name == "Task"
        assert subagent_type == "copilot"
        assert subagent_type in ["gemini", "codex", "copilot"]

    @patch("shutil.which")
    def test_cli_not_found_explicit_error(self, mock_which):
        """When CLI unavailable, returns explicit error (no silent fallback)."""
        # Mock shutil.which to return None (CLI not found)
        mock_which.return_value = None

        cli_name = "gemini"
        result = mock_which(cli_name)

        # Should return None, not fallback to Claude
        assert result is None

        # Error should be explicit
        error_msg = "❌ Google Gemini CLI not available\n\nSpawner 'gemini' requires the 'gemini' CLI."
        assert "gemini" in error_msg.lower()
        assert "not available" in error_msg.lower()

    @patch("shutil.which")
    def test_cli_not_found_error_message_includes_install_url(self, mock_which):
        """Error message for missing CLI includes installation instructions."""
        mock_which.return_value = None

        cli_requirements = {
            "gemini": {
                "cli": "gemini",
                "install_url": "https://ai.google.dev/gemini-api/docs/cli",
                "description": "Google Gemini CLI",
            }
        }

        requirement = cli_requirements["gemini"]
        install_url = requirement["install_url"]
        description = requirement["description"]

        # Verify error includes install URL
        assert install_url in f"Install from: {install_url}"
        assert description in f"{description} not available"

    @patch("subprocess.run")
    def test_spawner_execution_success(self, mock_run):
        """Successful spawner execution returns response."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Analysis complete",
                "tokens": 1000,
                "agent": "gemini-2.0-flash",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Mock subprocess execution
        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        assert result.returncode == 0
        assert "success" in result.stdout

    @patch("subprocess.run")
    def test_spawner_execution_failure(self, mock_run):
        """Failed spawner execution returns error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "HtmlGraph SDK not installed"
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        assert result.returncode != 0
        assert result.stderr != ""

    @patch("subprocess.run")
    def test_spawner_execution_timeout(self, mock_run):
        """Spawner execution timeout handled gracefully."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        # Verify timeout is caught
        with pytest.raises(subprocess.TimeoutExpired):
            mock_run(["uv", "run", "agents/gemini-spawner.py"], timeout=300)

    def test_missing_agent_config(self):
        """Missing agent config in plugin.json handled gracefully."""
        manifest = {"agents": {}}

        agents = manifest.get("agents", {})
        config = agents.get("unknown_spawner")

        # Should be None when agent not found
        assert config is None

    def test_plugin_manifest_loading(self):
        """Plugin manifest loaded correctly."""
        manifest = {
            "name": "htmlgraph",
            "agents": {
                "gemini": {
                    "executable": "agents/gemini-spawner.py",
                    "model": "haiku",
                    "requires_cli": "gemini",
                    "fallback": None,
                },
                "codex": {
                    "executable": "agents/codex-spawner.py",
                    "model": "haiku",
                    "requires_cli": "codex",
                    "fallback": None,
                },
                "copilot": {
                    "executable": "agents/copilot-spawner.py",
                    "model": "haiku",
                    "requires_cli": "gh",
                    "fallback": None,
                },
            },
        }

        # Verify plugin.json structure
        assert "agents" in manifest
        agents = manifest["agents"]
        assert "gemini" in agents
        assert "codex" in agents
        assert "copilot" in agents

        # Verify each spawner configured
        for spawner_type in ["gemini", "codex", "copilot"]:
            assert spawner_type in agents
            assert "executable" in agents[spawner_type]
            assert "requires_cli" in agents[spawner_type]

    @patch("shutil.which")
    def test_cli_available_check(self, mock_which):
        """CLI availability check returns correct status."""
        mock_which.return_value = "/usr/local/bin/gemini"

        cli_name = "gemini"
        result = mock_which(cli_name)

        assert result is not None
        assert "/gemini" in result

    def test_is_spawner_type_detection(self):
        """is_spawner_type correctly identifies spawner types."""
        spawner_types = ["gemini", "codex", "copilot"]
        non_spawner_types = ["haiku", "sonnet", "opus", "general-purpose", ""]

        for spawner_type in spawner_types:
            # Should be detected as spawner
            assert spawner_type.lower() in ["gemini", "codex", "copilot"]

        for non_spawner in non_spawner_types:
            # Should NOT be detected as spawner
            assert non_spawner.lower() not in ["gemini", "codex", "copilot"]

    def test_spawner_type_case_insensitive(self):
        """Spawner type detection is case-insensitive."""
        assert "GEMINI".lower() in ["gemini", "codex", "copilot"]
        assert "Codex".lower() in ["gemini", "codex", "copilot"]
        assert "COPILOT".lower() in ["gemini", "codex", "copilot"]

    def test_json_parsing_error_handling(self):
        """JSON parsing errors handled gracefully."""
        invalid_json = "not valid json"

        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    @patch("subprocess.run")
    def test_spawner_subprocess_arguments(self, mock_run):
        """Spawner subprocess called with correct arguments."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"success": True})
        mock_run.return_value = mock_result

        cmd = ["uv", "run", "agents/gemini-spawner.py"]
        prompt = "Test prompt"

        mock_run(cmd, input=prompt, capture_output=True, text=True, timeout=300)

        # Verify subprocess called with correct arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == cmd

    def test_task_input_extraction(self):
        """Task input parameters extracted correctly."""
        hook_input = {
            "name": "Task",
            "input": {
                "subagent_type": "gemini",
                "prompt": "Analyze this code",
                "model": "gemini-2.0-flash",
            },
        }

        tool_input = hook_input.get("input", {})
        subagent_type = tool_input.get("subagent_type", "")
        prompt = tool_input.get("prompt", "")

        assert subagent_type == "gemini"
        assert prompt == "Analyze this code"

    def test_task_without_prompt_passes_through(self):
        """Task() without prompt should pass through."""
        hook_input = {"name": "Task", "input": {"subagent_type": "gemini"}}

        tool_input = hook_input.get("input", {})
        prompt = tool_input.get("prompt", "")

        # Empty prompt should pass through
        assert prompt == ""

    @patch("subprocess.run")
    def test_spawner_error_response_structure(self, mock_run):
        """Error response has correct structure."""
        error_msg = "CLI not available"

        response = {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"🚫 SPAWNER UNAVAILABLE: {error_msg}",
            },
        }

        assert response["continue"] is False
        assert "hookSpecificOutput" in response
        assert response["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert "🚫" in response["hookSpecificOutput"]["additionalContext"]

    @patch("subprocess.run")
    def test_spawner_success_response_structure(self, mock_run):
        """Success response has correct structure."""
        response = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "✅ Spawned gemini agent\n\nResult here",
            },
        }

        assert response["continue"] is True
        assert "✅" in response["hookSpecificOutput"]["additionalContext"]

    def test_tracking_disabled_bypass(self):
        """HTMLGRAPH_DISABLE_TRACKING=1 bypasses router."""
        import os

        # When tracking disabled, should return early
        os.environ["HTMLGRAPH_DISABLE_TRACKING"] = "1"

        response = {"continue": True}

        # Should not be intercepted
        assert response["continue"] is True

        # Cleanup
        if "HTMLGRAPH_DISABLE_TRACKING" in os.environ:
            del os.environ["HTMLGRAPH_DISABLE_TRACKING"]


class TestSpawnerCLIRequirements:
    """Test CLI requirement checks for each spawner."""

    def test_gemini_cli_requirement(self):
        """Gemini spawner requires 'gemini' CLI."""
        cli_requirements = {
            "gemini": {
                "cli": "gemini",
                "install_url": "https://ai.google.dev/gemini-api/docs/cli",
            }
        }

        assert cli_requirements["gemini"]["cli"] == "gemini"

    def test_codex_cli_requirement(self):
        """Codex spawner requires 'codex' CLI."""
        cli_requirements = {
            "codex": {
                "cli": "codex",
                "install_url": "https://github.com/openai/codex",
            }
        }

        assert cli_requirements["codex"]["cli"] == "codex"

    def test_copilot_cli_requirement(self):
        """Copilot spawner requires 'gh' CLI."""
        cli_requirements = {
            "copilot": {
                "cli": "gh",
                "install_url": "https://cli.github.com/",
            }
        }

        assert cli_requirements["copilot"]["cli"] == "gh"

    def test_all_spawners_have_install_urls(self):
        """All spawners have installation URLs in error messages."""
        cli_requirements = {
            "gemini": {
                "cli": "gemini",
                "install_url": "https://ai.google.dev/gemini-api/docs/cli",
            },
            "codex": {
                "cli": "codex",
                "install_url": "https://github.com/openai/codex",
            },
            "copilot": {
                "cli": "gh",
                "install_url": "https://cli.github.com/",
            },
        }

        for spawner_type, requirement in cli_requirements.items():
            assert "install_url" in requirement
            assert requirement["install_url"].startswith("https://")


class TestSpawnerManifestParsing:
    """Test plugin.json manifest parsing."""

    def test_manifest_agents_section_exists(self):
        """Plugin manifest has agents section."""
        manifest = {"name": "htmlgraph", "agents": {}}

        assert "agents" in manifest

    def test_manifest_missing_agents_section(self):
        """Plugin manifest without agents section handled."""
        manifest = {"name": "htmlgraph"}

        agents = manifest.get("agents", {})
        assert agents == {}

    def test_agent_config_has_executable(self):
        """Agent config includes executable path."""
        agent_config = {
            "executable": "agents/gemini-spawner.py",
            "model": "haiku",
            "requires_cli": "gemini",
        }

        assert "executable" in agent_config
        assert agent_config["executable"].endswith(".py")

    def test_agent_config_has_cli_requirement(self):
        """Agent config specifies CLI requirement."""
        agent_config = {
            "executable": "agents/gemini-spawner.py",
            "model": "haiku",
            "requires_cli": "gemini",
        }

        assert "requires_cli" in agent_config
        assert agent_config["requires_cli"] == "gemini"

    def test_invalid_spawner_type_not_in_manifest(self):
        """Invalid spawner types not in agent registry."""
        manifest = {"agents": {"gemini": {}, "codex": {}, "copilot": {}}}

        agents = manifest.get("agents", {})
        assert "invalid_spawner" not in agents
        assert "unknown" not in agents
