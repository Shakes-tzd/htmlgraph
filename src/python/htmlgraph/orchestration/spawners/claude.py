"""Claude spawner implementation."""

import json
import logging
import subprocess
from typing import TYPE_CHECKING

from .base import AIResult, BaseSpawner

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class ClaudeSpawner(BaseSpawner):
    """
    Spawner for Claude Code CLI.

    NOTE: Uses same Claude Code authentication as Task() tool, but provides
    isolated execution context. Each call creates a new session without shared
    context. Best for independent tasks or external scripts.

    For orchestration workflows with shared context, prefer Task() tool which
    leverages prompt caching (5x cheaper for related work).
    """

    def spawn(
        self,
        prompt: str,
        output_format: str = "json",
        permission_mode: str = "bypassPermissions",
        resume: str | None = None,
        verbose: bool = False,
        timeout: int = 300,
        extra_args: list[str] | None = None,
    ) -> AIResult:
        """
        Spawn Claude in headless mode.

        NOTE: Uses same Claude Code authentication as Task() tool, but provides
        isolated execution context. Each call creates a new session without shared
        context. Best for independent tasks or external scripts.

        For orchestration workflows with shared context, prefer Task() tool which
        leverages prompt caching (5x cheaper for related work).

        Args:
            prompt: Task description for Claude
            output_format: "text" or "json" (stream-json requires --verbose)
            permission_mode: Permission handling mode:
                - "bypassPermissions": Auto-approve all (default)
                - "acceptEdits": Auto-approve edits only
                - "dontAsk": Fail on permission prompts
                - "default": Normal interactive prompts
                - "plan": Plan mode (no execution)
                - "delegate": Delegation mode
            resume: Resume from previous session (--resume). Default: None
            verbose: Enable verbose output (--verbose). Default: False
            timeout: Max seconds (default: 300, Claude can be slow with initialization)
            extra_args: Additional arguments to pass to Claude CLI

        Returns:
            AIResult with response or error

        Example:
            >>> spawner = ClaudeSpawner()
            >>> result = spawner.spawn("What is 2+2?")
            >>> if result.success:
            ...     logger.info("%s", result.response)  # "4"
            ...     logger.info(f"Cost: ${result.raw_output['total_cost_usd']}")
        """
        cmd = ["claude", "-p"]

        if output_format != "text":
            cmd.extend(["--output-format", output_format])

        if permission_mode:
            cmd.extend(["--permission-mode", permission_mode])

        # Add resume flag if specified
        if resume:
            cmd.extend(["--resume", resume])

        # Add verbose flag
        if verbose:
            cmd.append("--verbose")

        # Add extra args
        if extra_args:
            cmd.extend(extra_args)

        # Use -- separator to ensure prompt isn't consumed by variadic args
        cmd.append("--")
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if output_format == "json":
                # Parse JSON output
                try:
                    output = json.loads(result.stdout)
                except json.JSONDecodeError as e:
                    return AIResult(
                        success=False,
                        response="",
                        tokens_used=None,
                        error=f"Failed to parse JSON output: {e}",
                        raw_output=result.stdout,
                    )

                # Extract result and metadata
                usage = output.get("usage", {})
                tokens = (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("output_tokens", 0)
                )

                return AIResult(
                    success=output.get("type") == "result"
                    and not output.get("is_error"),
                    response=output.get("result", ""),
                    tokens_used=tokens,
                    error=output.get("error") if output.get("is_error") else None,
                    raw_output=output,
                )
            else:
                # Plain text output
                return AIResult(
                    success=result.returncode == 0,
                    response=result.stdout.strip(),
                    tokens_used=None,
                    error=None if result.returncode == 0 else result.stderr,
                    raw_output=result.stdout,
                )

        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Claude CLI not found. Install Claude Code from: https://claude.com/claude-code",
                raw_output=None,
            )
        except subprocess.TimeoutExpired as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Timed out after {timeout} seconds",
                raw_output={
                    "partial_stdout": e.stdout.decode() if e.stdout else None,
                    "partial_stderr": e.stderr.decode() if e.stderr else None,
                }
                if e.stdout or e.stderr
                else None,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                raw_output=None,
            )
