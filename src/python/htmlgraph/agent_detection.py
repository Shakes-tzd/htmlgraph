"""
Agent Detection Utilities

Intelligently detect which AI agent/interface is running HtmlGraph.
"""

import os
import sys
from pathlib import Path


def detect_agent_name() -> str:
    """
    Detect the current agent/interface name based on environment.

    Returns:
        Agent name (e.g., "claude", "gemini", "cli")

    Detection order:
        1. HTMLGRAPH_AGENT environment variable (explicit override)
        2. Claude Code detection (CLAUDE_CODE_VERSION, parent process)
        3. Gemini detection (GEMINI environment markers)
        4. Fall back to "cli"
    """
    # 1. Explicit override
    explicit = os.environ.get("HTMLGRAPH_AGENT")
    if explicit:
        return explicit.strip()

    # 2. Claude Code detection
    if _is_claude_code():
        return "claude"

    # 3. Gemini detection
    if _is_gemini():
        return "gemini"

    # 4. Default to CLI
    return "cli"


def _is_claude_code() -> bool:
    """Check if running in Claude Code environment."""
    # Check for Claude Code environment variables
    if os.environ.get("CLAUDE_CODE_VERSION"):
        return True

    if os.environ.get("CLAUDE_API_KEY"):
        return True

    # Check for .claude directory in user home or project
    claude_config = Path.home() / ".claude"
    if claude_config.exists():
        # Check if there's a recent session or settings
        settings = claude_config / "settings.json"
        if settings.exists():
            return True

    # Check parent process name (heuristic)
    try:
        import psutil
        current = psutil.Process()
        parent = current.parent()
        if parent:
            parent_name = parent.name().lower()
            if "claude" in parent_name:
                return True
    except (ImportError, Exception):
        pass

    return False


def _is_gemini():
    """Check if running in Gemini environment."""
    # Check for Gemini-specific environment variables
    if os.environ.get("GEMINI_API_KEY"):
        return True

    if os.environ.get("GOOGLE_AI_STUDIO"):
        return True

    # Check for gemini in command line args
    if any("gemini" in arg.lower() for arg in sys.argv):
        return True

    return False


def get_agent_display_name(agent: str) -> str:
    """
    Get a human-friendly display name for an agent.

    Args:
        agent: Agent identifier (e.g., "claude", "cli", "gemini")

    Returns:
        Display name (e.g., "Claude", "CLI", "Gemini")
    """
    display_names = {
        "claude": "Claude",
        "claude-code": "Claude",
        "gemini": "Gemini",
        "cli": "CLI",
        "haiku": "Haiku",
        "opus": "Opus",
        "sonnet": "Sonnet",
    }

    return display_names.get(agent.lower(), agent.title())
