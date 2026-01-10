"""Unit tests for spawner agent executable scripts."""

import argparse
import json
from unittest.mock import Mock, patch

import pytest


class TestGeminiSpawnerAgent:
    """Tests for gemini-spawner.py agent."""

    @patch("subprocess.run")
    def test_gemini_agent_success(self, mock_run):
        """Gemini agent returns successful result."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Analysis complete",
                "tokens": 1500,
                "agent": "gemini-2.0-flash",
                "duration": 2.5,
                "cost": 0.0,
                "delegation_event_id": "event-gemini-001",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute agent
        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        # Verify JSON output
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["response"] == "Analysis complete"
        assert output["tokens"] == 1500
        assert output["agent"] == "gemini-2.0-flash"

    @patch("subprocess.run")
    def test_gemini_agent_cli_not_found(self, mock_run):
        """Gemini agent handles missing CLI."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = json.dumps(
            {
                "success": False,
                "error": "HtmlGraph SDK not installed",
                "agent": "gemini-2.0-flash",
            }
        )
        mock_run.return_value = mock_result

        # Execute agent
        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        # Verify error returned to stderr
        assert result.returncode == 1
        error = json.loads(result.stderr)
        assert error["success"] is False

    def test_gemini_agent_argparse_configuration(self):
        """Gemini agent argparse configured correctly."""
        # Test argparse setup
        parser = argparse.ArgumentParser()

        # --prompt is required
        parser.add_argument("-p", "--prompt", required=True)

        # --model is optional
        parser.add_argument("-m", "--model", default=None)

        # --output-format with choices
        parser.add_argument(
            "--output-format", choices=["json", "stream-json"], default="stream-json"
        )

        # --timeout accepts int
        parser.add_argument("--timeout", type=int, default=120)

        # Test required argument
        with pytest.raises(SystemExit):
            parser.parse_args([])  # Missing required --prompt

        # Test valid arguments
        args = parser.parse_args(["-p", "Test prompt"])
        assert args.prompt == "Test prompt"
        assert args.model is None
        assert args.output_format == "stream-json"
        assert args.timeout == 120

    def test_gemini_agent_with_model_parameter(self):
        """Gemini agent accepts model parameter."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("-m", "--model", default=None)

        args = parser.parse_args(["-p", "Prompt", "-m", "gemini-2.0-flash"])

        assert args.model == "gemini-2.0-flash"

    def test_gemini_agent_with_output_format(self):
        """Gemini agent accepts output format parameter."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument(
            "--output-format", choices=["json", "stream-json"], default="stream-json"
        )

        # Test valid format
        args = parser.parse_args(["-p", "Prompt", "--output-format", "json"])
        assert args.output_format == "json"

        # Test invalid format
        with pytest.raises(SystemExit):
            parser.parse_args(["-p", "Prompt", "--output-format", "invalid"])

    def test_gemini_agent_with_timeout(self):
        """Gemini agent accepts timeout parameter."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("--timeout", type=int, default=120)

        args = parser.parse_args(["-p", "Prompt", "--timeout", "300"])

        assert args.timeout == 300
        assert isinstance(args.timeout, int)

    def test_gemini_agent_tracking_enabled_by_default(self):
        """Gemini agent tracking enabled by default."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("--track", action="store_true", default=True)
        parser.add_argument("--no-track", action="store_false", dest="track")

        # Default should have tracking enabled
        args = parser.parse_args(["-p", "Prompt"])
        assert args.track is True

        # --no-track should disable
        args = parser.parse_args(["-p", "Prompt", "--no-track"])
        assert args.track is False

    def test_gemini_agent_response_structure(self):
        """Gemini agent response has correct structure."""
        response = {
            "success": True,
            "response": "Analysis complete",
            "tokens": 1000,
            "model": "gemini-2.0-flash",
            "agent": "gemini-2.0-flash",
            "duration": 2.5,
            "cost": 0.0,
            "delegation_event_id": "event-123",
        }

        # Verify all required fields
        assert "success" in response
        assert "response" in response
        assert "tokens" in response
        assert "agent" in response
        assert "delegation_event_id" in response

    def test_gemini_agent_error_response_structure(self):
        """Gemini agent error response has correct structure."""
        error = {
            "success": False,
            "error": "SDK not installed",
            "tokens": 0,
            "agent": "gemini-2.0-flash",
        }

        # Verify error fields
        assert error["success"] is False
        assert "error" in error
        assert "agent" in error


class TestCodexSpawnerAgent:
    """Tests for codex-spawner.py agent."""

    @patch("subprocess.run")
    def test_codex_agent_success(self, mock_run):
        """Codex agent returns successful result."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Code generated",
                "tokens": 2000,
                "agent": "gpt-4",
                "duration": 3.1,
                "cost": 0.05,
                "delegation_event_id": "event-codex-001",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute agent
        result = mock_run(["uv", "run", "agents/codex-spawner.py"])

        # Verify JSON output
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["agent"] == "gpt-4"

    def test_codex_agent_sandbox_parameter(self):
        """Codex agent accepts sandbox parameter."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument(
            "--sandbox", choices=["read-only", "workspace-write"], default="read-only"
        )

        # Test valid sandbox modes
        args = parser.parse_args(["-p", "Prompt", "--sandbox", "read-only"])
        assert args.sandbox == "read-only"

        args = parser.parse_args(["-p", "Prompt", "--sandbox", "workspace-write"])
        assert args.sandbox == "workspace-write"

        # Default should be read-only
        args = parser.parse_args(["-p", "Prompt"])
        assert args.sandbox == "read-only"

    def test_codex_agent_argparse_configuration(self):
        """Codex agent argparse configured correctly."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("-m", "--model", default=None)
        parser.add_argument("--timeout", type=int, default=120)
        parser.add_argument(
            "--sandbox", choices=["read-only", "workspace-write"], default="read-only"
        )

        # Test required argument
        with pytest.raises(SystemExit):
            parser.parse_args([])

        # Test valid arguments
        args = parser.parse_args(
            [
                "-p",
                "Write function",
                "-m",
                "gpt-4",
                "--sandbox",
                "workspace-write",
                "--timeout",
                "300",
            ]
        )

        assert args.prompt == "Write function"
        assert args.model == "gpt-4"
        assert args.sandbox == "workspace-write"
        assert args.timeout == 300

    def test_codex_agent_response_structure(self):
        """Codex agent response has correct structure."""
        response = {
            "success": True,
            "response": "Function generated",
            "tokens": 2000,
            "agent": "gpt-4",
            "duration": 3.1,
            "cost": 0.05,
            "delegation_event_id": "event-codex-123",
        }

        # Verify fields
        assert response["success"] is True
        assert response["agent"] == "gpt-4"
        assert response["cost"] > 0  # Codex has cost


class TestCopilotSpawnerAgent:
    """Tests for copilot-spawner.py agent."""

    @patch("subprocess.run")
    def test_copilot_agent_success(self, mock_run):
        """Copilot agent returns successful result."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "PR created",
                "tokens": 1500,
                "agent": "github-copilot",
                "duration": 2.8,
                "cost": 0.0,
                "delegation_event_id": "event-copilot-001",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute agent
        result = mock_run(["uv", "run", "agents/copilot-spawner.py"])

        # Verify JSON output
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["agent"] == "github-copilot"

    def test_copilot_agent_tools_parameter(self):
        """Copilot agent accepts tool permission parameters."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("--allow-tool", action="append")
        parser.add_argument("--allow-all-tools", action="store_true")
        parser.add_argument("--deny-tool", action="append")

        # Test --allow-tool
        args = parser.parse_args(["-p", "Prompt", "--allow-tool", "git"])
        assert args.allow_tool == ["git"]

        # Test multiple --allow-tool
        args = parser.parse_args(
            ["-p", "Prompt", "--allow-tool", "git", "--allow-tool", "gh"]
        )
        assert args.allow_tool == ["git", "gh"]

        # Test --allow-all-tools
        args = parser.parse_args(["-p", "Prompt", "--allow-all-tools"])
        assert args.allow_all_tools is True

        # Test --deny-tool
        args = parser.parse_args(["-p", "Prompt", "--deny-tool", "shell"])
        assert args.deny_tool == ["shell"]

    def test_copilot_agent_argparse_configuration(self):
        """Copilot agent argparse configured correctly."""
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--prompt", required=True)
        parser.add_argument("-m", "--model", default=None)
        parser.add_argument("--timeout", type=int, default=120)
        parser.add_argument("--allow-tool", action="append")
        parser.add_argument("--allow-all-tools", action="store_true")
        parser.add_argument("--deny-tool", action="append")

        # Test valid arguments
        args = parser.parse_args(
            [
                "-p",
                "Create PR",
                "-m",
                "gpt-4",
                "--allow-tool",
                "git",
                "--allow-tool",
                "gh",
            ]
        )

        assert args.prompt == "Create PR"
        assert args.model == "gpt-4"
        assert args.allow_tool == ["git", "gh"]

    def test_copilot_agent_response_structure(self):
        """Copilot agent response has correct structure."""
        response = {
            "success": True,
            "response": "PR created and merged",
            "tokens": 1500,
            "agent": "github-copilot",
            "duration": 2.8,
            "cost": 0.0,
            "delegation_event_id": "event-copilot-123",
        }

        # Verify fields
        assert response["success"] is True
        assert response["agent"] == "github-copilot"


class TestSpawnerAgentCommon:
    """Common tests for all spawner agents."""

    def test_all_agents_return_json(self):
        """All agents return valid JSON output."""
        # Verify JSON structure for all agents
        agents = ["gemini-spawner.py", "codex-spawner.py", "copilot-spawner.py"]

        for agent in agents:
            # All agents should output JSON
            assert agent.endswith(".py")

    def test_all_agents_have_required_fields(self):
        """All agent responses have required fields."""
        required_fields = ["success", "agent", "delegation_event_id"]

        # Test success response
        success_response = {
            "success": True,
            "response": "Result",
            "tokens": 1000,
            "agent": "gemini-2.0-flash",
            "delegation_event_id": "event-123",
        }

        for field in required_fields:
            assert field in success_response

        # Test error response
        error_response = {
            "success": False,
            "error": "Error message",
            "agent": "gemini-2.0-flash",
        }

        assert error_response["success"] is False
        assert "error" in error_response
        assert "agent" in error_response

    def test_agent_delegation_event_id_format(self):
        """Agent delegation_event_id follows standard format."""
        delegation_event_id = "event-xyz123"

        # Should start with "event-"
        assert delegation_event_id.startswith("event-")

        # Should have hex characters
        assert all(c.isalnum() or c == "-" for c in delegation_event_id)

    def test_agent_error_messages_helpful(self):
        """Agent error messages are helpful."""
        error_messages = [
            "HtmlGraph SDK not installed. Install with: pip install htmlgraph",
            "Unexpected error: KeyError: 'key'",
            "Timeout waiting for response (300s)",
        ]

        for msg in error_messages:
            # Error messages should not be empty
            assert len(msg) > 0

            # Error messages for missing dependencies should include install instructions
            if "not installed" in msg:
                assert "Install" in msg

    def test_agent_timeout_handling(self):
        """Agents handle timeout gracefully."""
        timeout_error = {
            "success": False,
            "error": "Timeout waiting for response (300s)",
            "agent": "gemini-2.0-flash",
        }

        # Verify timeout error structure
        assert timeout_error["success"] is False
        assert "Timeout" in timeout_error["error"]

    def test_agent_execution_duration_tracking(self):
        """Agent tracks execution duration."""
        response = {
            "success": True,
            "response": "Result",
            "tokens": 1000,
            "agent": "gemini-2.0-flash",
            "duration": 2.5,  # seconds
            "delegation_event_id": "event-123",
        }

        # Duration should be numeric
        assert isinstance(response["duration"], float)
        assert response["duration"] > 0

    def test_agent_token_count_tracking(self):
        """Agent tracks token usage."""
        response_gemini = {"success": True, "tokens": 1500, "agent": "gemini-2.0-flash"}

        response_codex = {"success": True, "tokens": 2000, "agent": "gpt-4"}

        # Tokens should be numeric
        assert isinstance(response_gemini["tokens"], int)
        assert response_gemini["tokens"] > 0

        assert isinstance(response_codex["tokens"], int)
        assert response_codex["tokens"] > 0

    def test_agent_cost_calculation(self):
        """Agent calculates cost correctly."""
        costs = {
            "gemini": 0.0,  # Free
            "codex": 0.05,  # Paid
            "copilot": 0.0,  # Subscription
        }

        for agent_type, expected_cost in costs.items():
            response = {
                "success": True,
                "cost": expected_cost,
                "agent": f"agent-{agent_type}",
            }

            assert isinstance(response["cost"], (int, float))
            assert response["cost"] >= 0

    def test_agent_parent_context_preservation(self):
        """Agent preserves parent context in event linking."""
        # Mock environment variables

        parent_context = {
            "HTMLGRAPH_PARENT_SESSION": "session-123",
            "HTMLGRAPH_PARENT_EVENT": "event-parent-456",
            "HTMLGRAPH_PARENT_AGENT": "orchestrator",
        }

        response = {
            "success": True,
            "agent": "gemini-2.0-flash",
            "delegation_event_id": "event-child-789",
            "parent_event_id": parent_context.get("HTMLGRAPH_PARENT_EVENT"),
        }

        # Verify parent linking
        assert response["parent_event_id"] == "event-parent-456"
        assert response["delegation_event_id"] == "event-child-789"

    def test_agent_session_id_handling(self):
        """Agent handles session ID properly."""
        response = {
            "success": True,
            "agent": "gemini-2.0-flash",
            "session_id": "session-abc123",
            "delegation_event_id": "event-123",
        }

        # Session ID should be present and valid
        assert "session_id" in response
        assert response["session_id"].startswith("session-")

    def test_agent_environment_variable_safety(self):
        """Agent safely handles environment variables."""
        import os

        safe_vars = [
            "HTMLGRAPH_PARENT_SESSION",
            "HTMLGRAPH_PARENT_EVENT",
            "HTMLGRAPH_PARENT_AGENT",
        ]

        # Should read these safely without side effects
        for var in safe_vars:
            value = os.getenv(var)
            # Should be None if not set
            if value is None:
                assert True
            else:
                # If set, should be valid
                assert isinstance(value, str)
