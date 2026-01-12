"""AI spawner implementations for multi-AI orchestration."""

from .base import AIResult, BaseSpawner
from .claude import ClaudeSpawner
from .codex import CodexSpawner
from .copilot import CopilotSpawner
from .gemini import GeminiSpawner

__all__ = [
    "AIResult",
    "BaseSpawner",
    "ClaudeSpawner",
    "CodexSpawner",
    "CopilotSpawner",
    "GeminiSpawner",
]
