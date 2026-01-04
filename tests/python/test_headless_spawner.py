"""
Tests for HeadlessSpawner with mocked CLI calls.

CRITICAL: These tests mock subprocess calls to avoid wasting quota on external AI services.

Unit tests (default): Use mocks, run on every test execution
Integration tests (@pytest.mark.external_api): Call real CLIs, skip by default

For production testing with real CLIs and fallback logic, use the agent scaffolds:
- packages/claude-plugin/agents/gemini-spawner
- packages/claude-plugin/agents/codex-spawner
- packages/claude-plugin/agents/copilot-spawner
"""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest
from htmlgraph.orchestration import AIResult, HeadlessSpawner

# ==============================================================================
# UNIT TESTS - Use mocks, run by default
# ==============================================================================


class TestGeminiSpawnerUnit:
    """Unit tests for spawn_gemini() with mocked CLI calls."""

    def test_spawn_gemini_success(self):
        """Test successful Gemini spawn with mocked response."""
        spawner = HeadlessSpawner()

        # Mock successful JSON response
        mock_output = {
            "response": "2 + 2 = 4",
            "stats": {
                "models": {
                    "gemini-2.0-flash": {"tokens": {"total": 100}}
                }
            },
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_output))

            result = spawner.spawn_gemini(
                prompt="What is 2+2?", output_format="json", timeout=30
            )

            assert result.success is True
            assert result.response == "2 + 2 = 4"
            assert result.tokens_used == 100
            assert result.error is None

            # Verify correct CLI invocation (no --color or --approval flags)
            called_cmd = mock_run.call_args[0][0]
            assert "gemini" in called_cmd
            assert "-p" in called_cmd
            assert "What is 2+2?" in called_cmd
            assert "--output-format" in called_cmd
            assert "json" in called_cmd
            assert "--yolo" in called_cmd  # Critical for headless mode
            assert "--color" not in called_cmd  # Should NOT be present (bug fix)

    def test_spawn_gemini_cli_not_found(self):
        """Test Gemini CLI not installed."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = spawner.spawn_gemini(prompt="Test")

            assert result.success is False
            assert "Gemini CLI not found" in result.error

    def test_spawn_gemini_timeout(self):
        """Test Gemini CLI timeout."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gemini"], timeout=10)

            result = spawner.spawn_gemini(prompt="Test", timeout=10)

            assert result.success is False
            assert "timed out after 10 seconds" in result.error

    def test_spawn_gemini_json_parse_error(self):
        """Test invalid JSON response."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Invalid JSON")

            result = spawner.spawn_gemini(prompt="Test")

            assert result.success is False
            assert "Failed to parse JSON" in result.error

    def test_spawn_gemini_cli_failure(self):
        """Test Gemini CLI non-zero exit code."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="")

            result = spawner.spawn_gemini(prompt="Test")

            assert result.success is False
            assert "exit code 1" in result.error


class TestCodexSpawnerUnit:
    """Unit tests for spawn_codex() with mocked CLI calls."""

    def test_spawn_codex_success(self):
        """Test successful Codex spawn with mocked JSONL response."""
        spawner = HeadlessSpawner()

        # Mock JSONL stream output
        mock_events = [
            {"type": "thread.started", "thread_id": "abc123"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "id": "item_1",
                    "type": "agent_message",
                    "text": "The answer is 4",
                },
            },
            {
                "type": "turn.completed",
                "usage": {"input_tokens": 100, "output_tokens": 20},
            },
        ]
        mock_stdout = "\n".join(json.dumps(e) for e in mock_events)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_stdout)

            result = spawner.spawn_codex(
                prompt="What is 2+2?", output_json=True, full_auto=True, timeout=30
            )

            assert result.success is True
            assert result.response == "The answer is 4"
            assert result.tokens_used == 120  # 100 + 20
            assert result.error is None

            # Verify correct CLI invocation (no --approval or --color flags)
            called_cmd = mock_run.call_args[0][0]
            assert "codex" in called_cmd
            assert "exec" in called_cmd
            assert "--json" in called_cmd
            assert "--full-auto" in called_cmd
            assert "What is 2+2?" in called_cmd
            assert "--approval" not in called_cmd  # Should NOT be present (bug fix)
            assert "--color" not in called_cmd  # Should NOT be present (bug fix)

    def test_spawn_codex_cli_not_found(self):
        """Test Codex CLI not installed."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = spawner.spawn_codex(prompt="Test")

            assert result.success is False
            assert "Codex CLI not found" in result.error

    def test_spawn_codex_timeout(self):
        """Test Codex CLI timeout."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["codex"], timeout=10)

            result = spawner.spawn_codex(prompt="Test", timeout=10)

            assert result.success is False
            assert "Timed out after 10 seconds" in result.error


class TestCopilotSpawnerUnit:
    """Unit tests for spawn_copilot() with mocked CLI calls."""

    def test_spawn_copilot_success(self):
        """Test successful Copilot spawn with mocked response."""
        spawner = HeadlessSpawner()

        mock_stdout = """The answer is 4

Total usage est:       1 Premium requests
Total duration (API):  1.2s
Total duration (wall): 2.5s
Total code changes:    0 lines added, 0 lines removed"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_stdout, stderr="")

            result = spawner.spawn_copilot(
                prompt="What is 2+2?", allow_all_tools=True, timeout=30
            )

            assert result.success is True
            assert "The answer is 4" in result.response
            assert result.error is None

            # Verify correct CLI invocation
            called_cmd = mock_run.call_args[0][0]
            assert "copilot" in called_cmd
            assert "-p" in called_cmd
            assert "What is 2+2?" in called_cmd
            assert "--allow-all-tools" in called_cmd

    def test_spawn_copilot_quota_exceeded(self):
        """Test Copilot quota exceeded (agent scaffold should handle fallback)."""
        spawner = HeadlessSpawner()

        mock_stdout = """Model call failed: {"message":"You have no quota","code":"quota_exceeded"}

Quota exceeded. Upgrade to increase your limit: https://github.com/features/copilot/plans

Total usage est:       0 Premium requests
Total duration (API):  0.0s
Total duration (wall): 1.8s
Total code changes:    0 lines added, 0 lines removed"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,  # Copilot returns 0 even on quota exceeded
                stdout=mock_stdout,
                stderr="",
            )

            result = spawner.spawn_copilot(prompt="Test")

            # HeadlessSpawner returns success=True (exit code 0)
            # Agent scaffold should detect quota error and fallback to Task/Haiku
            assert result.success is True
            assert "quota" in result.response.lower()

    def test_spawn_copilot_cli_not_found(self):
        """Test Copilot CLI not installed."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = spawner.spawn_copilot(prompt="Test")

            assert result.success is False
            assert "Copilot CLI not found" in result.error


class TestAIResult:
    """Test AIResult dataclass structure."""

    def test_air_result_success(self):
        """Test AIResult for success case."""
        result = AIResult(
            success=True,
            response="Test response",
            tokens_used=100,
            error=None,
            raw_output={"test": "data"},
        )

        assert result.success is True
        assert result.response == "Test response"
        assert result.tokens_used == 100
        assert result.error is None
        assert result.raw_output == {"test": "data"}

    def test_air_result_failure(self):
        """Test AIResult for failure case."""
        result = AIResult(
            success=False,
            response="",
            tokens_used=None,
            error="Test error",
            raw_output=None,
        )

        assert result.success is False
        assert result.response == ""
        assert result.tokens_used is None
        assert result.error == "Test error"
        assert result.raw_output is None


class TestFallbackPatterns:
    """
    Document fallback patterns for agent scaffolds.

    NOTE: These are documentation tests, not real integration tests.
    Real fallback testing happens in agent scaffolds via Task tool:
    - Task(subagent_type="gemini-spawner", prompt="...")
    - Task(subagent_type="codex-spawner", prompt="...")
    - Task(subagent_type="copilot-spawner", prompt="...")
    """

    def test_fallback_pattern_gemini_to_haiku(self):
        """Document fallback pattern: Gemini fails → Haiku via Task."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            # Simulate Gemini CLI failure
            mock_run.side_effect = FileNotFoundError()

            result = spawner.spawn_gemini(prompt="Test")

            assert result.success is False
            assert "Gemini CLI not found" in result.error

            # In production, agent scaffold would now call:
            # Task(prompt="Test", subagent_type="haiku")

    def test_fallback_pattern_codex_timeout_to_haiku(self):
        """Document fallback pattern: Codex timeout → Haiku via Task."""
        spawner = HeadlessSpawner()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["codex"], timeout=10)

            result = spawner.spawn_codex(prompt="Test", timeout=10)

            assert result.success is False
            assert "Timed out" in result.error

            # Agent scaffold would fallback to Haiku

    def test_cost_comparison_documentation(self):
        """
        Document cost savings when using Gemini FREE tier.

        Gemini 2.0-Flash: FREE (rate limited)
        Claude Haiku: $0.25/M input, $1.25/M output

        For 100K token task:
        - Gemini: $0 (if within rate limits)
        - Haiku: ~$0.025 input + ~$0.125 output = $0.15

        Real cost tracking happens in agent scaffolds via HtmlGraph SDK.
        """
        pass


# ==============================================================================
# INTEGRATION TESTS - Call real CLIs, skip by default
# ==============================================================================


@pytest.mark.external_api
class TestGeminiSpawnerIntegration:
    """Integration tests for spawn_gemini() with real CLI calls."""

    def test_spawn_gemini_real_cli(self):
        """Test Gemini spawn with real CLI (skipped unless @pytest.mark.external_api enabled)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response
            assert result.tokens_used is not None
            assert result.tokens_used > 0
        else:
            # May fail if CLI not installed or quota exceeded
            pytest.skip(f"Gemini CLI test failed: {result.error}")


@pytest.mark.external_api
class TestCodexSpawnerIntegration:
    """Integration tests for spawn_codex() with real CLI calls."""

    def test_spawn_codex_real_cli(self):
        """Test Codex spawn with real CLI (skipped unless @pytest.mark.external_api enabled)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response
        else:
            pytest.skip(f"Codex CLI test failed: {result.error}")


@pytest.mark.external_api
class TestCopilotSpawnerIntegration:
    """Integration tests for spawn_copilot() with real CLI calls."""

    def test_spawn_copilot_real_cli(self):
        """Test Copilot spawn with real CLI (skipped unless @pytest.mark.external_api enabled)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot(
            "What is 2+2? Brief answer only.", allow_all_tools=True
        )

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response
        else:
            # May fail if quota exceeded
            pytest.skip(f"Copilot CLI test failed: {result.error}")
