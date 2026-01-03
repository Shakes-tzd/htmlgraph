"""Tests for HeadlessSpawner."""

import pytest
from htmlgraph.orchestration import AIResult, HeadlessSpawner


class TestHeadlessSpawner:
    """Test HeadlessSpawner class."""

    def test_init(self):
        """Test HeadlessSpawner initialization."""
        spawner = HeadlessSpawner()
        assert spawner is not None

    @pytest.mark.external_api
    def test_spawn_gemini_basic(self):
        """Test basic Gemini spawn."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        assert result.success, f"Expected success, got error: {result.error}"
        assert result.response, "Expected non-empty response"
        assert "4" in result.response, f"Expected '4' in response: {result.response}"
        assert result.tokens_used is not None, "Expected token count"
        assert result.tokens_used > 0, "Expected positive token count"
        assert result.error is None, f"Expected no error, got: {result.error}"
        assert result.raw_output is not None, "Expected raw output"

    @pytest.mark.external_api
    def test_spawn_gemini_with_json_format(self):
        """Test Gemini spawn with explicit JSON format."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini(
            "List 3 colors in JSON array format.", output_format="json"
        )

        assert result.success
        assert result.response
        # Response should contain some color-related content
        assert any(
            color in result.response.lower()
            for color in ["red", "blue", "green", "yellow", "orange", "purple"]
        )

    @pytest.mark.external_api
    def test_spawn_gemini_empty_prompt(self):
        """Test Gemini spawn with empty prompt."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini("")

        # Gemini may handle empty prompts gracefully or return an error
        # We just verify we get a result and don't crash
        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_gemini_timeout(self):
        """Test timeout handling with very short timeout."""
        spawner = HeadlessSpawner()
        # Use very short timeout to trigger timeout error
        result = spawner.spawn_gemini(
            "Write a very long essay about the history of computing.", timeout=1
        )

        # Should either succeed quickly or timeout
        assert isinstance(result, AIResult)
        if not result.success:
            assert (
                "timeout" in result.error.lower() or "timed out" in result.error.lower()
            )

    @pytest.mark.external_api
    def test_spawn_gemini_complex_prompt(self):
        """Test Gemini spawn with complex multi-line prompt."""
        prompt = """
        Analyze the following:
        1. What is the capital of France?
        2. What is 10 * 5?

        Provide brief answers only.
        """
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini(prompt)

        assert result.success
        assert result.response
        # Should mention Paris and 50
        response_lower = result.response.lower()
        assert "paris" in response_lower
        assert "50" in result.response

    @pytest.mark.external_api
    def test_spawn_gemini_with_model(self):
        """Test Gemini with specific model selection."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini(
            "What is 2+2? Brief answer only.", model="gemini-2.0-flash"
        )

        assert isinstance(result, AIResult)
        # May fail if specific model not available
        if result.success:
            assert "4" in result.response

    @pytest.mark.external_api
    def test_spawn_gemini_with_include_directories(self):
        """Test Gemini with include directories for context."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini(
            "Summarize the structure.", include_directories=["src/", "tests/"]
        )

        assert isinstance(result, AIResult)
        # Just verify it doesn't crash with the option

    @pytest.mark.external_api
    def test_spawn_gemini_color_control(self):
        """Test Gemini with color output control."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini("What is 2+2? Brief answer only.", color="off")

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response

    @pytest.mark.external_api
    def test_spawn_gemini_multiple_options(self):
        """Test Gemini with multiple options combined."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_gemini(
            "What is 2+2?",
            model="gemini-2.0-flash",
            include_directories=["src/"],
            color="auto",
        )

        assert isinstance(result, AIResult)

    def test_air_result_structure(self):
        """Test AIResult dataclass structure."""
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

    @pytest.mark.external_api
    def test_spawn_codex_basic(self):
        """Test basic Codex spawn with JSONL output."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        # May fail if Codex CLI not installed
        if result.success:
            assert "4" in result.response
            # Tokens may or may not be available
            if result.tokens_used:
                assert result.tokens_used > 0
        else:
            assert result.error is not None

    @pytest.mark.external_api
    def test_spawn_codex_error_handling(self):
        """Test Codex error handling."""
        spawner = HeadlessSpawner()
        # Test with very short timeout
        result = spawner.spawn_codex("What is 2+2?", timeout=0.001)

        assert isinstance(result, AIResult)
        assert not result.success
        assert "Timed out" in result.error or "not found" in result.error

    @pytest.mark.external_api
    def test_spawn_codex_plain_text(self):
        """Test Codex with plain text output (no JSON)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2?", output_json=False)

        assert isinstance(result, AIResult)
        # May fail if Codex CLI not installed
        if result.success:
            assert result.response
            assert isinstance(result.raw_output, str)

    @pytest.mark.external_api
    def test_spawn_codex_with_model(self):
        """Test Codex with specific model selection."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            "What is 2+2? Brief answer only.", model="gpt-4-turbo"
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_with_sandbox_mode(self):
        """Test Codex with sandbox mode."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            "List files in current directory.", sandbox="read-only"
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_full_auto_mode(self):
        """Test Codex with full auto mode enabled."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2? Brief answer only.", full_auto=True)

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_with_images(self):
        """Test Codex with image inputs."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            "Describe this image.", images=["test.png", "image.jpg"]
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_color_output(self):
        """Test Codex with color output control."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2?", color="off")

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_output_last_message(self):
        """Test Codex with output last message file."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            "What is 2+2?", output_last_message="/tmp/last_message.txt"
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_output_schema(self):
        """Test Codex with output schema validation."""
        spawner = HeadlessSpawner()
        schema = '{"type": "object", "properties": {"answer": {"type": "string"}}}'
        result = spawner.spawn_codex("What is 2+2?", output_schema=schema)

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_skip_git_check(self):
        """Test Codex with git check skipped."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2?", skip_git_check=True)

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_working_directory(self):
        """Test Codex with working directory option."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("List files.", working_directory="/tmp")

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_use_oss(self):
        """Test Codex with OSS flag for local Ollama."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2?", use_oss=True)

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_bypass_approvals(self):
        """Test Codex with dangerous bypass approvals flag."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex("What is 2+2?", bypass_approvals=True)

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_codex_multiple_options(self):
        """Test Codex with multiple options combined."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_codex(
            "What is 2+2?",
            model="gpt-4-turbo",
            sandbox="read-only",
            full_auto=True,
            color="auto",
            skip_git_check=True,
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_copilot_basic(self):
        """Test basic Copilot spawn."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        # May fail if Copilot CLI not installed
        if result.success:
            assert "4" in result.response
        else:
            assert result.error is not None

    @pytest.mark.external_api
    def test_spawn_copilot_with_tools(self):
        """Test Copilot with tool permissions."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot(
            "List Python files in current directory", allow_tools=["shell(ls)"]
        )

        assert isinstance(result, AIResult)
        # May fail if Copilot CLI not installed
        if not result.success:
            assert result.error is not None

    @pytest.mark.external_api
    def test_spawn_copilot_error_handling(self):
        """Test Copilot error handling."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot("Test", timeout=0.001)

        assert isinstance(result, AIResult)
        assert not result.success
        assert "Timed out" in result.error or "not found" in result.error

    @pytest.mark.external_api
    def test_spawn_copilot_allow_all_tools(self):
        """Test Copilot with allow all tools flag."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot(
            "What is 2+2? Brief answer only.", allow_all_tools=True
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_copilot_deny_tools(self):
        """Test Copilot with denied tools."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot(
            "What is 2+2?", deny_tools=["shell(rm)", "write(*)"]
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_copilot_combined_tool_options(self):
        """Test Copilot with combined allow and deny tool options."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_copilot(
            "What is 2+2?",
            allow_tools=["shell(ls)", "write(*.py)"],
            deny_tools=["shell(rm)"],
        )

        assert isinstance(result, AIResult)

    @pytest.mark.external_api
    def test_spawn_claude_basic(self):
        """Test basic Claude spawn with JSON output."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude("What is 2+2? Brief answer only.")

        assert isinstance(result, AIResult)
        # May fail if Claude CLI not installed or not authenticated
        if result.success:
            assert "4" in result.response
            assert result.tokens_used is not None
            assert result.tokens_used > 0
            # Check raw_output has cost info
            assert isinstance(result.raw_output, dict)
            assert "total_cost_usd" in result.raw_output
        else:
            assert result.error is not None

    @pytest.mark.external_api
    def test_spawn_claude_text_mode(self):
        """Test Claude with plain text output."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(
            "What is 2+2? Brief answer.", output_format="text"
        )

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response
            assert isinstance(result.raw_output, str)

    @pytest.mark.external_api
    def test_spawn_claude_permission_mode_bypass(self):
        """Test Claude with bypassPermissions mode (default)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(
            "What is 2+2?", permission_mode="bypassPermissions"
        )

        assert isinstance(result, AIResult)
        # Should work with bypass permissions
        if result.success:
            assert result.response

    @pytest.mark.external_api
    def test_spawn_claude_permission_mode_plan(self):
        """Test Claude with plan mode (no execution)."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(
            "List files in current directory", permission_mode="plan"
        )

        assert isinstance(result, AIResult)
        # Plan mode should succeed but not execute
        if result.success:
            # Should describe plan, not actually list files
            assert result.response

    @pytest.mark.external_api
    def test_spawn_claude_error_handling(self):
        """Test Claude error handling."""
        spawner = HeadlessSpawner()

        # Test with very short timeout
        result = spawner.spawn_claude("What is 2+2?", timeout=0.001)

        assert isinstance(result, AIResult)
        assert not result.success
        assert "Timed out" in result.error or "not found" in result.error

    @pytest.mark.external_api
    def test_spawn_claude_cost_tracking(self):
        """Test that cost information is captured."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude("What is 2+2?")

        assert isinstance(result, AIResult)
        if result.success:
            assert isinstance(result.raw_output, dict)
            assert "total_cost_usd" in result.raw_output
            assert result.raw_output["total_cost_usd"] >= 0
            assert "usage" in result.raw_output

    @pytest.mark.external_api
    def test_spawn_claude_complex_prompt(self):
        """Test Claude with complex multi-line prompt."""
        prompt = """
        Analyze the following:
        1. What is the capital of France?
        2. What is 10 * 5?

        Provide brief answers only.
        """
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(prompt)

        assert isinstance(result, AIResult)
        if result.success:
            response_lower = result.response.lower()
            assert "paris" in response_lower
            assert "50" in result.response

    @pytest.mark.external_api
    def test_spawn_claude_json_parse_error(self):
        """Test Claude handles JSON parse errors gracefully."""
        # This test verifies error handling, actual error conditions
        # may vary based on Claude CLI implementation
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude("")

        assert isinstance(result, AIResult)
        # Empty prompt may succeed or fail, just verify we handle it
        if not result.success and result.error:
            # Should have meaningful error message
            assert len(result.error) > 0

    @pytest.mark.external_api
    def test_spawn_claude_with_resume(self):
        """Test Claude with session resume option."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(
            "Continue working on the previous task.", resume="session-abc-123"
        )

        assert isinstance(result, AIResult)
        # Resume may fail if session doesn't exist, just verify we handle it

    @pytest.mark.external_api
    def test_spawn_claude_verbose_mode(self):
        """Test Claude with verbose output."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude("What is 2+2? Brief answer only.", verbose=True)

        assert isinstance(result, AIResult)
        if result.success:
            assert "4" in result.response

    @pytest.mark.external_api
    def test_spawn_claude_resume_and_verbose(self):
        """Test Claude with both resume and verbose options."""
        spawner = HeadlessSpawner()
        result = spawner.spawn_claude(
            "Continue the task.",
            resume="session-abc-123",
            verbose=True,
            permission_mode="plan",
        )

        assert isinstance(result, AIResult)


# Conditional tests that require Gemini CLI to be installed
@pytest.mark.skipif(
    not pytest.importorskip("subprocess")
    .run(
        ["which", "gemini"],
        capture_output=True,
        text=True,
    )
    .returncode
    == 0,
    reason="Gemini CLI not installed",
)
class TestHeadlessSpawnerIntegration:
    """Integration tests requiring Gemini CLI."""

    def test_gemini_cli_available(self):
        """Verify Gemini CLI is available for integration tests."""
        import subprocess

        result = subprocess.run(["which", "gemini"], capture_output=True, text=True)
        assert result.returncode == 0, "Gemini CLI not found in PATH"
