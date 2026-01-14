from __future__ import annotations

"""System prompt management for HtmlGraph projects.

Provides a two-tier system:
1. Plugin Default - Included with HtmlGraph plugin, available to all users
2. Project Override - Optional, project-specific customization

Architecture:
- System prompts are injected via SessionStart hook's additionalContext
- Survives Claude Code compact/resume cycles
- SDK provides methods for creation, validation, and management
"""


import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SystemPromptValidator:
    """Validate system prompts against token budgets and quality criteria."""

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Estimate or count tokens in text.

        Uses tiktoken if available (accurate), falls back to character-based
        estimation if tiktoken not installed.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated or exact token count
        """
        if not text:
            return 0

        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimation (1 token ≈ 4 characters)
            # This is a conservative estimate used by Claude
            return max(1, len(text) // 4)

    @staticmethod
    def validate(
        text: str,
        max_tokens: int = 1000,
        min_tokens: int = 50,
    ) -> dict:
        """
        Validate system prompt against token budget and quality criteria.

        Args:
            text: Prompt text to validate
            max_tokens: Maximum allowed tokens (default: 1000)
            min_tokens: Minimum expected tokens (default: 50)

        Returns:
            Validation result dictionary:
            {
                "is_valid": bool,
                "tokens": int,
                "warnings": List[str],
                "message": str
            }
        """
        tokens = SystemPromptValidator.count_tokens(text)
        warnings = []

        # Token budget validation
        if tokens > max_tokens:
            warnings.append(f"Prompt exceeds budget: {tokens} > {max_tokens} tokens")

        if tokens < min_tokens:
            warnings.append(
                f"Prompt is very short ({tokens} tokens) - "
                f"may not provide sufficient guidance (minimum: {min_tokens})"
            )

        # Content quality checks
        if len(text) < 100:
            warnings.append(
                "Prompt is very brief - consider adding more detail for better guidance"
            )

        # Determine validity
        is_valid = min_tokens <= tokens <= max_tokens

        # Build message
        if is_valid:
            message = (
                f"Valid prompt: {tokens} tokens (within {max_tokens} token budget)"
            )
        elif tokens > max_tokens:
            message = f"Invalid: {tokens} tokens exceeds {max_tokens} token limit"
        else:
            message = (
                f"Warning: {tokens} tokens below recommended minimum ({min_tokens}). "
                f"Prompt may not provide sufficient guidance."
            )

        return {
            "is_valid": is_valid,
            "tokens": tokens,
            "warnings": warnings,
            "message": message,
        }


class SystemPromptManager:
    """Manage system prompts for a project.

    Provides methods to:
    - Load plugin default system prompt
    - Load/create project-level overrides
    - Validate prompt token counts
    - Manage prompt lifecycle

    Architecture:
    - Plugin Default: Included with plugin, loaded via importlib.resources
    - Project Override: Optional .claude/system-prompt.md file
    - Strategy: Project override takes precedence over plugin default
    """

    def __init__(self, graph_dir: Path | str):
        """
        Initialize system prompt manager.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        self.graph_dir = Path(graph_dir)
        self.project_dir = self.graph_dir.parent
        self.claude_dir = self.project_dir / ".claude"

    def get_default(self) -> str | None:
        """
        Get plugin default system prompt.

        Tries multiple strategies:
        1. Load via importlib.resources (when installed via pip)
        2. Load via package file path (development mode)
        3. Return None if not found

        Returns:
            Default prompt text, or None if not found
        """
        # Strategy 1: importlib.resources (standard Python 3.7+)
        try:
            from importlib.resources import files

            try:
                # Try new package structure (if htmlgraph_plugin is a package)
                plugin_resources = files("htmlgraph_plugin").joinpath(
                    ".claude-plugin/system-prompt-default.md"
                )
                if plugin_resources.is_file():
                    return plugin_resources.read_text(encoding="utf-8")
            except Exception:
                pass

            # Try alternative path
            try:
                plugin_resources = files("htmlgraph").joinpath(
                    "plugin/.claude-plugin/system-prompt-default.md"
                )
                if plugin_resources.is_file():
                    return plugin_resources.read_text(encoding="utf-8")
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"importlib.resources not available: {e}")

        # Strategy 2: Direct file path (development and package installations)
        try:
            import htmlgraph

            htmlgraph_path = Path(htmlgraph.__file__).parent
            # Try relative paths from htmlgraph package
            possible_paths = [
                htmlgraph_path
                / "plugin"
                / ".claude-plugin"
                / "system-prompt-default.md",
                htmlgraph_path.parent
                / "packages"
                / "claude-plugin"
                / ".claude-plugin"
                / "system-prompt-default.md",
                Path(__file__).parent.parent
                / "packages"
                / "claude-plugin"
                / ".claude-plugin"
                / "system-prompt-default.md",
            ]

            for path in possible_paths:
                if path.exists():
                    try:
                        content = path.read_text(encoding="utf-8")
                        logger.info(f"Loaded plugin default from {path}")
                        return content
                    except Exception as e:
                        logger.debug(f"Failed to read {path}: {e}")
        except Exception as e:
            logger.debug(f"Could not load via htmlgraph package: {e}")

        logger.debug("Plugin default system prompt not found")
        return None

    def get_project(self) -> str | None:
        """
        Get project-level system prompt override.

        Looks for: `.claude/system-prompt.md`

        Returns:
            Project prompt text if exists, None otherwise

        Raises:
            RuntimeError: If file exists but cannot be read
        """
        prompt_file = self.claude_dir / "system-prompt.md"

        if not prompt_file.exists():
            return None

        try:
            content = prompt_file.read_text(encoding="utf-8")
            logger.info(f"Loaded project system prompt ({len(content)} chars)")
            return content
        except Exception as e:
            logger.error(f"Failed to read project system prompt: {e}")
            raise RuntimeError(
                f"Failed to read project system prompt at {prompt_file}: {e}"
            )

    def get_active(self) -> str | None:
        """
        Get active system prompt (project override OR plugin default).

        Strategy:
        1. If `.claude/system-prompt.md` exists → use it (project override)
        2. Else if plugin default exists → use it
        3. Else → return None

        Returns:
            Active prompt text, or None if neither available

        Note:
            Project override always takes precedence over plugin default.
            This allows teams to customize guidance while maintaining
            a sensible default for users who haven't customized yet.
        """
        try:
            project = self.get_project()
            if project:
                logger.info("Using project system prompt override")
                return project
        except RuntimeError:
            # Project file exists but couldn't be read—log but continue
            logger.warning("Could not read project prompt, falling back to default")

        default = self.get_default()
        if default:
            logger.info("Using plugin default system prompt")
            return default

        logger.warning(
            "No system prompt found (neither project override nor plugin default)"
        )
        return None

    def create(
        self,
        template: str,
        overwrite: bool = False,
    ) -> SystemPromptManager:
        """
        Create or update project system prompt.

        Creates `.claude/system-prompt.md` with provided template.

        Args:
            template: Prompt template text
            overwrite: Whether to overwrite existing prompt (default: False)

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If file exists and overwrite=False, or if write fails

        Example:
            sdk = SDK(agent="claude")
            sdk.system_prompts.create('''
            # Team Rules
            - Use TypeScript, not JavaScript
            - All PRs need 2 approvals
            ''')
        """
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = self.claude_dir / "system-prompt.md"

        if prompt_file.exists() and not overwrite:
            raise RuntimeError(
                f"System prompt already exists at {prompt_file}. "
                f"Use overwrite=True to replace, or delete the file first."
            )

        try:
            prompt_file.write_text(template, encoding="utf-8")
            logger.info(
                f"Created system prompt at {prompt_file} ({len(template)} chars)"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to write system prompt at {prompt_file}: {e}")

        return self

    def validate(
        self,
        text: str | None = None,
        max_tokens: int = 1000,
        min_tokens: int = 50,
    ) -> dict:
        """
        Validate a system prompt.

        Args:
            text: Prompt to validate (uses active prompt if None)
            max_tokens: Maximum allowed tokens (default: 1000)
            min_tokens: Minimum expected tokens (default: 50)

        Returns:
            Validation result dict with keys:
            - is_valid: bool
            - tokens: int
            - warnings: List[str]
            - message: str

        Example:
            result = sdk.system_prompts.validate()
            print(result['message'])
            if not result['is_valid']:
                for warning in result['warnings']:
                    print(f"  - {warning}")
        """
        prompt_text = text or self.get_active() or ""
        return SystemPromptValidator.validate(
            prompt_text,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
        )

    def delete(self) -> bool:
        """
        Delete project system prompt override.

        Removes `.claude/system-prompt.md` if it exists.
        Falls back to plugin default on next session.

        Returns:
            True if file was deleted, False if didn't exist

        Raises:
            RuntimeError: If file exists but cannot be deleted

        Example:
            sdk = SDK(agent="claude")
            if sdk.system_prompts.delete():
                print("Deleted project prompt, using plugin default")
        """
        prompt_file = self.claude_dir / "system-prompt.md"

        if not prompt_file.exists():
            return False

        try:
            prompt_file.unlink()
            logger.info(f"Deleted system prompt at {prompt_file}")
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete system prompt at {prompt_file}: {e}")

    def get_stats(self) -> dict:
        """
        Get statistics about the system prompt.

        Returns:
            Dictionary with:
            - source: "project_override" | "plugin_default" | "none"
            - tokens: int
            - bytes: int
            - file_path: str | None

        Example:
            stats = sdk.system_prompts.get_stats()
            print(f"Using {stats['source']}: {stats['tokens']} tokens")
        """
        prompt = self.get_active()

        if not prompt:
            return {
                "source": "none",
                "tokens": 0,
                "bytes": 0,
                "file_path": None,
            }

        # Determine source
        project = self.get_project()
        if project:
            source = "project_override"
            file_path = str(self.claude_dir / "system-prompt.md")
        else:
            source = "plugin_default"
            file_path = None  # Plugin default has no single path

        return {
            "source": source,
            "tokens": SystemPromptValidator.count_tokens(prompt),
            "bytes": len(prompt.encode("utf-8")),
            "file_path": file_path,
        }


# Integration with SDK
def _register_system_prompts_with_sdk() -> None:
    """Register system_prompts property with SDK class.

    This function is called during SDK initialization to add the
    system_prompts property, enabling usage like:

        sdk = SDK(agent="claude")
        prompt = sdk.system_prompts.get_active()
    """
    pass  # Integration handled via SDK property decorator
