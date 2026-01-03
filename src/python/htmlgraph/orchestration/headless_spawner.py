"""Headless AI spawner for multi-AI orchestration."""

import json
import subprocess
from dataclasses import dataclass


@dataclass
class AIResult:
    """Result from AI CLI execution."""

    success: bool
    response: str
    tokens_used: int | None
    error: str | None
    raw_output: dict | list | str | None


class HeadlessSpawner:
    """
    Spawn AI agents in headless CLI mode.

    Supports multiple AI CLIs:
    - spawn_gemini(): Google Gemini (free tier)
    - spawn_codex(): OpenAI Codex (ChatGPT Plus+)
    - spawn_copilot(): GitHub Copilot (GitHub subscription)
    - spawn_claude(): Claude Code (same login as Task tool)

    spawn_claude() vs Task() Tool:
    --------------------------------
    Both use the same Claude Code authentication and billing, but:

    spawn_claude():
    - Isolated execution (no context sharing)
    - Fresh session each call
    - Best for: independent tasks, external scripts, parallel processing
    - Cache miss on each call (higher token usage)

    Task():
    - Shared conversation context
    - Builds on previous work
    - Best for: orchestration, related sequential work
    - Cache hits in session (5x cheaper for related work)

    Example - When to use spawn_claude():
        # Independent tasks in external script
        spawner = HeadlessSpawner()
        for file in files:
            result = spawner.spawn_claude(f"Analyze {file} independently")
            save_result(file, result)

    Example - When to use Task() instead:
        # Related tasks in orchestration workflow
        Task(prompt="Analyze all files and compare them")
        # Better: shares context, uses caching
    """

    def __init__(self) -> None:
        """Initialize spawner."""
        pass

    def spawn_gemini(
        self,
        prompt: str,
        output_format: str = "json",
        model: str | None = None,
        include_directories: list[str] | None = None,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn Gemini in headless mode.

        Args:
            prompt: Task description for Gemini
            output_format: "json" or "stream-json"
            model: Model selection (e.g., "gemini-2.0-flash"). Default: None (uses default)
            include_directories: List of directories to include for context. Default: None
            timeout: Max seconds to wait

        Returns:
            AIResult with response or error
        """
        try:
            # Build command based on tested pattern from spike spk-4029eef3
            cmd = ["gemini", "-p", prompt, "--output-format", output_format]

            # Add model option if specified
            if model:
                cmd.extend(["-m", model])

            # Add include directories if specified
            if include_directories:
                for directory in include_directories:
                    cmd.extend(["--include-directories", directory])

            # CRITICAL: Add --yolo for headless mode (auto-approve all tools)
            cmd.append("--yolo")

            # Execute with timeout and stderr redirection
            # Note: Cannot use capture_output with stderr parameter
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Redirect stderr to avoid polluting JSON
                text=True,
                timeout=timeout,
            )

            # Check for command execution errors
            if result.returncode != 0:
                return AIResult(
                    success=False,
                    response="",
                    tokens_used=None,
                    error=f"Gemini CLI failed with exit code {result.returncode}",
                    raw_output=None,
                )

            # Parse JSON response
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                return AIResult(
                    success=False,
                    response="",
                    tokens_used=None,
                    error=f"Failed to parse JSON output: {e}",
                    raw_output={"stdout": result.stdout},
                )

            # Extract response and token usage from parsed output
            # Response is at top level in JSON output
            response_text = output.get("response", "")

            # Token usage is in stats.models (sum across all models)
            tokens = None
            stats = output.get("stats", {})
            if stats and "models" in stats:
                total_tokens = 0
                for model_stats in stats["models"].values():
                    model_tokens = model_stats.get("tokens", {}).get("total", 0)
                    total_tokens += model_tokens
                tokens = total_tokens if total_tokens > 0 else None

            return AIResult(
                success=True,
                response=response_text,
                tokens_used=tokens,
                error=None,
                raw_output=output,
            )

        except subprocess.TimeoutExpired:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Gemini CLI timed out after {timeout} seconds",
                raw_output=None,
            )
        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Gemini CLI not found. Ensure 'gemini' is installed and in PATH.",
                raw_output=None,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                raw_output=None,
            )

    def spawn_codex(
        self,
        prompt: str,
        output_json: bool = True,
        model: str | None = None,
        sandbox: str | None = None,
        full_auto: bool = True,
        images: list[str] | None = None,
        output_last_message: str | None = None,
        output_schema: str | None = None,
        skip_git_check: bool = False,
        working_directory: str | None = None,
        use_oss: bool = False,
        bypass_approvals: bool = False,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn Codex in headless mode.

        Args:
            prompt: Task description for Codex
            output_json: Use --json flag for JSONL output
            model: Model selection (e.g., "gpt-4-turbo"). Default: None
            sandbox: Sandbox mode ("read-only", "workspace-write", "danger-full-access"). Default: None
            full_auto: Enable full auto mode (--full-auto). Default: True (required for headless)
            images: List of image paths (--image). Default: None
            output_last_message: Write last message to file (--output-last-message). Default: None
            output_schema: JSON schema for validation (--output-schema). Default: None
            skip_git_check: Skip git repo check (--skip-git-repo-check). Default: False
            working_directory: Workspace directory (--cd). Default: None
            use_oss: Use local Ollama provider (--oss). Default: False
            bypass_approvals: Dangerously bypass approvals (--dangerously-bypass-approvals-and-sandbox). Default: False
            timeout: Max seconds to wait

        Returns:
            AIResult with response or error
        """
        cmd = ["codex", "exec"]

        if output_json:
            cmd.append("--json")

        # Add model if specified
        if model:
            cmd.extend(["--model", model])

        # Add sandbox mode if specified
        if sandbox:
            cmd.extend(["--sandbox", sandbox])

        # Add full auto flag
        if full_auto:
            cmd.append("--full-auto")

        # Add images
        if images:
            for image in images:
                cmd.extend(["--image", image])

        # Add output last message file if specified
        if output_last_message:
            cmd.extend(["--output-last-message", output_last_message])

        # Add output schema if specified
        if output_schema:
            cmd.extend(["--output-schema", output_schema])

        # Add skip git check flag
        if skip_git_check:
            cmd.append("--skip-git-repo-check")

        # Add working directory if specified
        if working_directory:
            cmd.extend(["--cd", working_directory])

        # Add OSS flag
        if use_oss:
            cmd.append("--oss")

        # Add bypass approvals flag
        if bypass_approvals:
            cmd.append("--dangerously-bypass-approvals-and-sandbox")

        # Add prompt as final argument
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=timeout,
            )

            if not output_json:
                # Plain text mode - return as-is
                return AIResult(
                    success=result.returncode == 0,
                    response=result.stdout.strip(),
                    tokens_used=None,
                    error=None if result.returncode == 0 else "Command failed",
                    raw_output=result.stdout,
                )

            # Parse JSONL output
            events = []
            for line in result.stdout.splitlines():
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # Extract agent message
            response = None
            for event in events:
                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        response = item.get("text")

            # Extract token usage from turn.completed event
            tokens = None
            for event in events:
                if event.get("type") == "turn.completed":
                    usage = event.get("usage", {})
                    # Sum all token types
                    tokens = sum(usage.values())

            return AIResult(
                success=result.returncode == 0,
                response=response or "",
                tokens_used=tokens,
                error=None if result.returncode == 0 else "Command failed",
                raw_output=events,
            )

        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Codex CLI not found. Install from: https://github.com/openai/codex",
                raw_output=None,
            )
        except subprocess.TimeoutExpired:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Timed out after {timeout} seconds",
                raw_output=None,
            )

    def spawn_copilot(
        self,
        prompt: str,
        allow_tools: list[str] | None = None,
        allow_all_tools: bool = False,
        deny_tools: list[str] | None = None,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn GitHub Copilot in headless mode.

        Args:
            prompt: Task description for Copilot
            allow_tools: List of tools to auto-approve (e.g., ["shell(git)", "write(*.py)"])
            allow_all_tools: Auto-approve all tools (--allow-all-tools). Default: False
            deny_tools: List of tools to deny (--deny-tool). Default: None
            timeout: Max seconds to wait

        Returns:
            AIResult with response or error
        """
        cmd = ["copilot", "-p", prompt]

        # Add allow all tools flag
        if allow_all_tools:
            cmd.append("--allow-all-tools")

        # Add tool permissions
        if allow_tools:
            for tool in allow_tools:
                cmd.extend(["--allow-tool", tool])

        # Add denied tools
        if deny_tools:
            for tool in deny_tools:
                cmd.extend(["--deny-tool", tool])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            # Parse output: response is before stats block
            lines = result.stdout.split("\n")

            # Find where stats start (look for "Total usage est:" or "Usage by model")
            stats_start = len(lines)
            for i, line in enumerate(lines):
                if "Total usage est" in line or "Usage by model" in line:
                    stats_start = i
                    break

            # Response is everything before stats
            response = "\n".join(lines[:stats_start]).strip()

            # Try to extract token count from stats
            tokens = None
            for line in lines[stats_start:]:
                # Look for token counts like "25.8k input, 5 output"
                if "input" in line and "output" in line:
                    # Simple extraction: just note we found stats
                    # TODO: More sophisticated parsing if needed
                    tokens = 0  # Placeholder
                    break

            return AIResult(
                success=result.returncode == 0,
                response=response,
                tokens_used=tokens,
                error=None if result.returncode == 0 else result.stderr,
                raw_output=result.stdout,
            )

        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Copilot CLI not found. Install from: https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line",
                raw_output=None,
            )
        except subprocess.TimeoutExpired:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Timed out after {timeout} seconds",
                raw_output=None,
            )

    def spawn_claude(
        self,
        prompt: str,
        output_format: str = "json",
        permission_mode: str = "bypassPermissions",
        resume: str | None = None,
        verbose: bool = False,
        timeout: int = 300,
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

        Returns:
            AIResult with response or error

        Example:
            >>> spawner = HeadlessSpawner()
            >>> result = spawner.spawn_claude("What is 2+2?")
            >>> if result.success:
            ...     print(result.response)  # "4"
            ...     print(f"Cost: ${result.raw_output['total_cost_usd']}")
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
        except subprocess.TimeoutExpired:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Timed out after {timeout} seconds",
                raw_output=None,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {str(e)}",
                raw_output=None,
            )
