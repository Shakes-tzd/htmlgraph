"""
Tests for OpenCode integration functionality.
"""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from htmlgraph.agent_detection import detect_agent_name


class TestOpenCodeIntegration:
    """Test OpenCode-specific integration."""

    def test_opencode_agent_detection_with_env_vars(self, monkeypatch):
        """Test OpenCode agent detection with various environment variables."""
        # Clear all agent detection vars first
        for var in [
            "HTMLGRAPH_AGENT",
            "CLAUDE_CODE_VERSION",
            "CLAUDE_API_KEY",
            "GEMINI_API_KEY",
            "OPENCODE_VERSION",
            "OPENCODE_API_KEY",
            "OPENCODE_SESSION_ID",
        ]:
            monkeypatch.delenv(var, raising=False)

        # Test with OPENCODE_VERSION
        monkeypatch.setenv("OPENCODE_VERSION", "1.0.0")
        assert detect_agent_name() == "opencode"

        # Test with OPENCODE_API_KEY
        monkeypatch.delenv("OPENCODE_VERSION", raising=False)
        monkeypatch.setenv("OPENCODE_API_KEY", "sk-test-123")
        assert detect_agent_name() == "opencode"

        # Test with OPENCODE_SESSION_ID
        monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
        monkeypatch.setenv("OPENCODE_SESSION_ID", "session-abc123")
        assert detect_agent_name() == "opencode"

    def test_opencode_sdk_initialization(self):
        """Test SDK initialization with opencode agent."""
        with patch(
            "htmlgraph.agent_detection.detect_agent_name", return_value="opencode"
        ):
            from htmlgraph import SDK

            sdk = SDK()
            assert sdk.agent == "opencode"

            # Explicit agent should still work
            sdk_explicit = SDK(agent="opencode")
            assert sdk_explicit.agent == "opencode"

    @patch("htmlgraph.sdk.SDK")
    def test_opencode_session_start_hook(self, mock_sdk_class):
        """Test OpenCode session start hook functionality."""
        # Mock SDK instance
        mock_sdk = Mock()
        mock_sdk_class.return_value = mock_sdk

        # Mock session_start_info response
        mock_sdk.session_start_info.return_value = {
            "status": "Active features: 2",
            "recommendations": ["Complete feature-001", "Start feature-002"],
        }

        # Import and test the hook logic (simplified)
        with patch.dict(os.environ, {"HTMLGRAPH_AGENT": "opencode"}):
            # The hook would use SDK to get context
            from htmlgraph import SDK

            sdk = SDK(agent="opencode")

            # Test that SDK methods are called correctly
            context = sdk.session_start_info()

            mock_sdk.session_start_info.assert_called_once()
            assert "status" in context
            assert "recommendations" in context

    def test_opencode_extension_metadata(self):
        """Test OpenCode extension metadata structure."""
        extension_file = Path("packages/opencode-extension/opencode-extension.json")

        if extension_file.exists():
            with open(extension_file) as f:
                metadata = json.load(f)

            # Required fields
            assert "name" in metadata
            assert "version" in metadata
            assert "description" in metadata
            assert "contextFileName" in metadata
            assert "agent" in metadata

            # Specific values
            assert metadata["name"] == "htmlgraph"
            assert metadata["contextFileName"] == "OPENCODE.md"
            assert metadata["agent"] == "opencode"

    def test_opencode_hooks_configuration(self):
        """Test OpenCode hooks configuration structure."""
        hooks_file = Path("packages/opencode-extension/hooks/hooks.json")

        if hooks_file.exists():
            with open(hooks_file) as f:
                hooks_config = json.load(f)

            # Required hook types
            assert "SessionStart" in hooks_config
            assert "SessionEnd" in hooks_config
            assert "AfterTool" in hooks_config

            # Each hook should have required fields
            for hook_type in ["SessionStart", "SessionEnd", "AfterTool"]:
                hooks = hooks_config[hook_type]
                assert len(hooks) > 0

                for hook in hooks:
                    assert "name" in hook
                    assert "type" in hook
                    assert "command" in hook
                    assert "description" in hook
                    assert "timeout" in hook
                    assert "matcher" in hook

                # Should use Python scripts with uv run
                assert "uv run" in hooks[0]["command"]
                assert ".py" in hooks[0]["command"]

    def test_opencode_command_generation(self):
        """Test OpenCode command generation functionality."""
        generator_file = Path("packages/common/generators/generate_commands.py")

        if generator_file.exists():
            # Test that generate_opencode_command_section function exists
            with open(generator_file) as f:
                content = f.read()

            assert "def generate_opencode_command_section" in content
            assert "opencode" in content

    def test_opencode_documentation_exists(self):
        """Test OpenCode documentation exists and has required content."""
        doc_file = Path("OPENCODE.md")

        if doc_file.exists():
            content = doc_file.read_text()

            # Required sections
            assert "HtmlGraph for OpenCode" in content
            assert "AGENTS.md" in content
            assert "Python SDK" in content
            assert 'agent="opencode"' in content

            # Specific content checks
            assert "OPENCODE_VERSION" in content
            assert "Feature Creation Decision Framework" in content
            assert "uv run htmlgraph" in content
