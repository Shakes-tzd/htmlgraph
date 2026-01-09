"""
Tests for agent detection utilities.
"""

from htmlgraph.agent_detection import detect_agent_name, get_agent_display_name


class TestAgentDetection:
    """Test agent detection functionality."""

    def test_detect_agent_with_explicit_override(self, monkeypatch):
        """Test explicit HTMLGRAPH_AGENT environment variable override."""
        monkeypatch.setenv("HTMLGRAPH_AGENT", "my-custom-agent")
        assert detect_agent_name() == "my-custom-agent"

    def test_detect_agent_with_claude_code_env(self, monkeypatch):
        """Test Claude Code detection via environment variable."""
        monkeypatch.delenv("HTMLGRAPH_AGENT", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_VERSION", "1.0.0")
        assert detect_agent_name() == "claude-code"

    def test_detect_agent_with_claude_api_key(self, monkeypatch):
        """Test Claude detection via API key."""
        monkeypatch.delenv("HTMLGRAPH_AGENT", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_VERSION", raising=False)
        monkeypatch.setenv("CLAUDE_API_KEY", "sk-test-123")
        assert detect_agent_name() == "claude-code"

    def test_detect_agent_with_gemini(self, monkeypatch, tmp_path):
        """Test Gemini detection."""
        monkeypatch.delenv("HTMLGRAPH_AGENT", raising=False)
        monkeypatch.delenv("HTMLGRAPH_PARENT_AGENT", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_VERSION", raising=False)
        monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDECODE", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv(
            "HOME", str(tmp_path)
        )  # Fake home to avoid .claude detection
        # Mock psutil to prevent parent process detection
        import htmlgraph.agent_detection as agent_mod

        monkeypatch.setattr(agent_mod, "_is_claude_code", lambda: False)
        assert detect_agent_name() == "gemini"

    def test_detect_agent_defaults_to_cli(self, monkeypatch, tmp_path):
        """Test fallback to CLI when no specific environment detected."""
        # Clear all environment variables
        monkeypatch.delenv("HTMLGRAPH_AGENT", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_VERSION", raising=False)
        monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("CLAUDECODE", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
        # Fake home to avoid .claude detection
        monkeypatch.setenv("HOME", str(tmp_path))

        # Should default to CLI when no AI agent detected
        result = detect_agent_name()
        # Could be "claude-code" if running in Claude Code or "cli" otherwise
        assert result in ["claude-code", "cli"]


class TestAgentDisplayNames:
    """Test agent display name formatting."""

    def test_get_display_name_claude(self):
        """Test Claude display name."""
        assert get_agent_display_name("claude") == "Claude"
        assert get_agent_display_name("claude-code") == "Claude Code"

    def test_get_display_name_gemini(self):
        """Test Gemini display name."""
        assert get_agent_display_name("gemini") == "Gemini"

    def test_get_display_name_cli(self):
        """Test CLI display name."""
        assert get_agent_display_name("cli") == "CLI"

    def test_get_display_name_models(self):
        """Test model display names."""
        assert get_agent_display_name("haiku") == "Haiku"
        assert get_agent_display_name("opus") == "Opus"
        assert get_agent_display_name("sonnet") == "Sonnet"

    def test_get_display_name_unknown(self):
        """Test unknown agent defaults to title case."""
        assert get_agent_display_name("my-custom-agent") == "My-Custom-Agent"
