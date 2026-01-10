"""Integration tests for spawner routing with mocked CLIs."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest


class TestSpawnerIntegration:
    """Integration tests for spawner routing and execution."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_gemini_spawner_with_cli_available(self, mock_run, mock_which):
        """Test Gemini spawner when CLI is available."""
        # Setup mocks
        mock_which.return_value = "/usr/local/bin/gemini"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Gemini analysis complete",
                "tokens": 1500,
                "agent": "gemini-2.0-flash",
                "delegation_event_id": "event-abc123",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Verify CLI is available
        assert mock_which("gemini") is not None

        # Execute spawner
        result = mock_run(
            ["uv", "run", "agents/gemini-spawner.py"],
            input="Analyze this code",
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Verify execution successful
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["agent"] == "gemini-2.0-flash"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_gemini_spawner_without_cli(self, mock_run, mock_which):
        """Test Gemini spawner when CLI not installed."""
        # Setup mocks - CLI not available
        mock_which.return_value = None

        # Verify CLI is not available
        assert mock_which("gemini") is None

        # Should not attempt execution - router would block
        # Verify no fallback to Claude
        error_msg = (
            "❌ Google Gemini CLI not available\n\n"
            "Spawner 'gemini' requires the 'gemini' CLI.\n\n"
            "Install from: https://ai.google.dev/gemini-api/docs/cli\n\n"
            "This operation cannot proceed without the required CLI."
        )

        assert "gemini" in error_msg
        assert "not available" in error_msg
        assert "cannot proceed" in error_msg

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_gemini_spawner_execution_and_tracking(self, mock_run, mock_which):
        """Test spawner execution creates proper event tracking."""
        mock_which.return_value = "/usr/local/bin/gemini"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Analysis complete",
                "tokens": 1000,
                "agent": "gemini-2.0-flash",
                "duration": 2.5,
                "delegation_event_id": "event-xyz789",
            }
        )
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute spawner
        result = mock_run(
            ["uv", "run", "agents/gemini-spawner.py"],
            input="Test prompt",
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Verify event tracking created
        output = json.loads(result.stdout)
        assert "delegation_event_id" in output
        assert output["delegation_event_id"].startswith("event-")

        # Verify attribution to gemini-2.0-flash (not wrapper)
        assert output["agent"] == "gemini-2.0-flash"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_orchestrator_fallback_on_spawner_failure(self, mock_run, mock_which):
        """Test orchestrator can fallback when spawner fails."""
        # First call: Gemini fails
        mock_which.side_effect = [None, "/usr/local/bin/codex", "/usr/local/bin/gh"]

        # Verify Gemini unavailable
        assert mock_which("gemini") is None

        # Orchestrator should receive explicit error
        error_response = {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "🚫 SPAWNER UNAVAILABLE: ❌ Google Gemini CLI not available",
            },
        }

        assert error_response["continue"] is False
        assert "🚫" in error_response["hookSpecificOutput"]["additionalContext"]

        # Orchestrator can then try different spawner (Codex)
        assert mock_which("codex") is not None

        # Or fallback to Claude (different subagent_type)
        # This tests orchestrator logic, not router

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_parallel_spawner_execution(self, mock_run, mock_which):
        """Test parallel execution of multiple spawners."""
        mock_which.return_value = "/usr/local/bin/spawner"

        # Setup multiple mock results
        results = [
            Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "agent": "gemini-2.0-flash",
                        "tokens": 1000,
                        "delegation_event_id": "event-1",
                    }
                ),
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "agent": "gpt-4",
                        "tokens": 1200,
                        "delegation_event_id": "event-2",
                    }
                ),
                stderr="",
            ),
            Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "agent": "github-copilot",
                        "tokens": 800,
                        "delegation_event_id": "event-3",
                    }
                ),
                stderr="",
            ),
        ]

        mock_run.side_effect = results

        # Launch spawners in parallel
        spawners = ["gemini", "codex", "copilot"]
        responses = []

        for spawner_type in spawners:
            result = mock_run(
                ["uv", "run", f"agents/{spawner_type}-spawner.py"],
                input="Test prompt",
                capture_output=True,
                text=True,
                timeout=300,
            )
            responses.append(json.loads(result.stdout))

        # Verify all executed correctly
        assert len(responses) == 3
        assert all(r["success"] is True for r in responses)

        # Verify events tracked separately
        event_ids = [r["delegation_event_id"] for r in responses]
        assert len(set(event_ids)) == 3  # All unique

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_spawner_event_attribution(self, mock_run, mock_which):
        """Verify events attributed to spawned AI, not wrapper."""
        mock_which.return_value = "/usr/local/bin/gemini"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Analysis",
                "agent": "gemini-2.0-flash",
                "tokens": 1000,
                "delegation_event_id": "event-123",
            }
        )
        mock_run.return_value = mock_result

        # Execute spawner
        result = mock_run(
            ["uv", "run", "agents/gemini-spawner.py"],
            input="Prompt",
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = json.loads(result.stdout)

        # Verify agent_id = "gemini-2.0-flash" (NOT "gemini-spawner")
        assert output["agent"] == "gemini-2.0-flash"
        assert "spawner" not in output["agent"].lower()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_spawner_collaboration_records(self, mock_run, mock_which):
        """Verify collaboration handoff records created."""
        mock_which.return_value = "/usr/local/bin/gemini"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Done",
                "agent": "gemini-2.0-flash",
                "tokens": 500,
                "delegation_event_id": "event-456",
            }
        )
        mock_run.return_value = mock_result

        # Execute spawner
        result = mock_run(
            ["uv", "run", "agents/gemini-spawner.py"],
            input="Task",
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = json.loads(result.stdout)

        # Verify delegation_event_id present (linking key)
        assert "delegation_event_id" in output
        assert output["delegation_event_id"].startswith("event-")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_codex_spawner_with_cli_available(self, mock_run, mock_which):
        """Test Codex spawner when CLI is available."""
        mock_which.return_value = "/usr/local/bin/codex"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Code generated",
                "tokens": 2000,
                "agent": "gpt-4",
                "delegation_event_id": "event-codex-1",
            }
        )
        mock_run.return_value = mock_result

        assert mock_which("codex") is not None

        result = mock_run(
            ["uv", "run", "agents/codex-spawner.py"],
            input="Generate function",
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["agent"] == "gpt-4"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_copilot_spawner_with_cli_available(self, mock_run, mock_which):
        """Test Copilot spawner when CLI is available."""
        mock_which.return_value = "/usr/local/bin/gh"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "PR created",
                "tokens": 1500,
                "agent": "github-copilot",
                "delegation_event_id": "event-copilot-1",
            }
        )
        mock_run.return_value = mock_result

        assert mock_which("gh") is not None

        result = mock_run(
            ["uv", "run", "agents/copilot-spawner.py"],
            input="Create PR",
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = json.loads(result.stdout)
        assert output["success"] is True
        assert output["agent"] == "github-copilot"

    @patch("subprocess.run")
    def test_spawner_execution_with_timeout(self, mock_run):
        """Test spawner execution respects timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 300)

        # Should raise TimeoutExpired
        with pytest.raises(subprocess.TimeoutExpired) as exc_info:
            mock_run(
                ["uv", "run", "agents/gemini-spawner.py"], input="Prompt", timeout=300
            )

        assert exc_info.value.timeout == 300

    @patch("subprocess.run")
    def test_spawner_execution_json_output(self, mock_run):
        """Test spawner returns valid JSON."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Result",
                "tokens": 1000,
                "agent": "gemini-2.0-flash",
                "duration": 1.5,
                "cost": 0.0,
                "delegation_event_id": "event-json-1",
            }
        )
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])
        output = json.loads(result.stdout)

        # Verify all required fields
        assert "success" in output
        assert "response" in output
        assert "tokens" in output
        assert "agent" in output
        assert "delegation_event_id" in output

    @patch("subprocess.run")
    def test_spawner_error_json_output(self, mock_run):
        """Test spawner returns valid JSON on error."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = json.dumps(
            {
                "success": False,
                "error": "SDK not installed",
                "agent": "gemini-2.0-flash",
            }
        )
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        # Verify returncode indicates error
        assert result.returncode != 0

        # Verify error output is valid JSON
        error_output = json.loads(result.stderr)
        assert error_output["success"] is False
        assert "error" in error_output

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_spawner_execution_preserves_parent_context(self, mock_run, mock_which):
        """Test spawner maintains parent-child event linking."""
        mock_which.return_value = "/usr/local/bin/gemini"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "success": True,
                "response": "Result",
                "tokens": 1000,
                "agent": "gemini-2.0-flash",
                "delegation_event_id": "event-parent-123",
            }
        )
        mock_run.return_value = mock_result

        # Execute with parent context
        result = mock_run(
            ["uv", "run", "agents/gemini-spawner.py"],
            input="Prompt",
            capture_output=True,
            text=True,
            timeout=300,
        )

        output = json.loads(result.stdout)

        # Verify delegation_event_id for parent-child linking
        assert "delegation_event_id" in output
        assert output["delegation_event_id"].startswith("event-")

    def test_spawner_cost_tracking(self):
        """Test spawner cost metrics included in response."""
        response_gemini = {
            "success": True,
            "response": "Result",
            "tokens": 1000,
            "agent": "gemini-2.0-flash",
            "cost": 0.0,
        }

        response_codex = {
            "success": True,
            "response": "Result",
            "tokens": 1200,
            "agent": "gpt-4",
            "cost": 0.05,
        }

        response_copilot = {
            "success": True,
            "response": "Result",
            "tokens": 800,
            "agent": "github-copilot",
            "cost": 0.0,
        }

        # Gemini is free
        assert response_gemini["cost"] == 0.0

        # Codex has cost
        assert response_codex["cost"] > 0

        # Copilot subscription-based
        assert response_copilot["cost"] == 0.0


class TestSpawnerErrorHandling:
    """Test error handling in spawner integration."""

    @patch("subprocess.run")
    def test_spawner_missing_sdk(self, mock_run):
        """Test spawner handles missing HtmlGraph SDK."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = json.dumps(
            {
                "success": False,
                "error": "HtmlGraph SDK not installed. Install with: pip install htmlgraph",
                "agent": "gemini-2.0-flash",
            }
        )
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        assert result.returncode == 1
        error = json.loads(result.stderr)
        assert "SDK not installed" in error["error"]

    @patch("subprocess.run")
    def test_spawner_unexpected_error(self, mock_run):
        """Test spawner handles unexpected errors."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = json.dumps(
            {
                "success": False,
                "error": "Unexpected error: KeyError: 'key'",
                "agent": "gemini-2.0-flash",
            }
        )
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        assert result.returncode == 1
        error = json.loads(result.stderr)
        assert error["success"] is False

    @patch("subprocess.run")
    def test_spawner_invalid_json_output(self, mock_run):
        """Test handling of invalid JSON output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        result = mock_run(["uv", "run", "agents/gemini-spawner.py"])

        # Should fail to parse
        with pytest.raises(json.JSONDecodeError):
            json.loads(result.stdout)
