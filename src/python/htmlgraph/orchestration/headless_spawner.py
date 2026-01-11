"""Headless AI spawner for multi-AI orchestration."""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from htmlgraph.sdk import SDK


@dataclass
class AIResult:
    """Result from AI CLI execution."""

    success: bool
    response: str
    tokens_used: int | None
    error: str | None
    raw_output: dict | list | str | None
    tracked_events: list[dict] | None = None  # Events tracked in HtmlGraph


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

    def _get_sdk(self) -> "SDK | None":
        """
        Get SDK instance for HtmlGraph tracking with parent session support.

        Returns None if SDK unavailable.
        """
        try:
            from htmlgraph.sdk import SDK

            # Read parent session context from environment
            parent_session = os.getenv("HTMLGRAPH_PARENT_SESSION")
            parent_agent = os.getenv("HTMLGRAPH_PARENT_AGENT")

            # Create SDK with parent session context
            sdk = SDK(
                agent=f"spawner-{parent_agent}" if parent_agent else "spawner",
                parent_session=parent_session,  # Pass parent session
            )

            return sdk

        except Exception:
            # SDK unavailable or not properly initialized (optional dependency)
            # This happens in test contexts without active sessions
            # Don't log error to avoid noise in tests
            return None

    def _parse_and_track_gemini_events(
        self, jsonl_output: str, sdk: "SDK"
    ) -> list[dict]:
        """
        Parse Gemini stream-json events and track in HtmlGraph.

        Args:
            jsonl_output: JSONL output from Gemini CLI
            sdk: HtmlGraph SDK instance for tracking

        Returns:
            Parsed events list
        """
        events = []

        # Get parent context for metadata
        parent_activity = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")
        nesting_depth_str = os.getenv("HTMLGRAPH_NESTING_DEPTH", "0")
        nesting_depth = int(nesting_depth_str) if nesting_depth_str.isdigit() else 0

        for line in jsonl_output.splitlines():
            if not line.strip():
                continue

            try:
                event = json.loads(line)
                events.append(event)

                # Track based on event type
                event_type = event.get("type")

                try:
                    if event_type == "tool_use":
                        tool_name = event.get("tool_name", "unknown_tool")
                        parameters = event.get("parameters", {})
                        payload = {
                            "tool_name": tool_name,
                            "parameters": parameters,
                        }
                        if parent_activity:
                            payload["parent_activity"] = parent_activity
                        if nesting_depth > 0:
                            payload["nesting_depth"] = nesting_depth
                        sdk.track_activity(
                            tool="gemini_tool_call",
                            summary=f"Gemini called {tool_name}",
                            payload=payload,
                        )

                    elif event_type == "tool_result":
                        status = event.get("status", "unknown")
                        success = status == "success"
                        tool_id = event.get("tool_id", "unknown")
                        payload = {"tool_id": tool_id, "status": status}
                        if parent_activity:
                            payload["parent_activity"] = parent_activity
                        if nesting_depth > 0:
                            payload["nesting_depth"] = nesting_depth
                        sdk.track_activity(
                            tool="gemini_tool_result",
                            summary=f"Gemini tool result: {status}",
                            success=success,
                            payload=payload,
                        )

                    elif event_type == "message":
                        role = event.get("role")
                        if role == "assistant":
                            content = event.get("content", "")
                            # Truncate for summary
                            summary = (
                                content[:100] + "..." if len(content) > 100 else content
                            )
                            payload = {"role": role, "content_length": len(content)}
                            if parent_activity:
                                payload["parent_activity"] = parent_activity
                            if nesting_depth > 0:
                                payload["nesting_depth"] = nesting_depth
                            sdk.track_activity(
                                tool="gemini_message",
                                summary=f"Gemini: {summary}",
                                payload=payload,
                            )

                    elif event_type == "result":
                        stats = event.get("stats", {})
                        payload = {"stats": stats}
                        if parent_activity:
                            payload["parent_activity"] = parent_activity
                        if nesting_depth > 0:
                            payload["nesting_depth"] = nesting_depth
                        sdk.track_activity(
                            tool="gemini_completion",
                            summary="Gemini task completed",
                            payload=payload,
                        )
                except Exception:
                    # Tracking failure should not break parsing
                    pass

            except json.JSONDecodeError:
                # Skip malformed lines
                continue

        return events

    def _parse_and_track_codex_events(
        self, jsonl_output: str, sdk: "SDK"
    ) -> list[dict]:
        """
        Parse Codex JSONL events and track in HtmlGraph.

        Args:
            jsonl_output: JSONL output from Codex CLI
            sdk: HtmlGraph SDK instance for tracking

        Returns:
            Parsed events list
        """
        events = []
        parse_errors = []

        # Get parent context for metadata
        parent_activity = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")
        nesting_depth_str = os.getenv("HTMLGRAPH_NESTING_DEPTH", "0")
        nesting_depth = int(nesting_depth_str) if nesting_depth_str.isdigit() else 0

        for line_num, line in enumerate(jsonl_output.splitlines(), start=1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
                events.append(event)

                event_type = event.get("type")

                try:
                    # Track item.started events
                    if event_type == "item.started":
                        item = event.get("item", {})
                        item_type = item.get("type")

                        if item_type == "command_execution":
                            command = item.get("command", "")
                            payload = {"command": command}
                            if parent_activity:
                                payload["parent_activity"] = parent_activity
                            if nesting_depth > 0:
                                payload["nesting_depth"] = nesting_depth
                            sdk.track_activity(
                                tool="codex_command",
                                summary=f"Codex executing: {command[:80]}",
                                payload=payload,
                            )

                    # Track item.completed events
                    elif event_type == "item.completed":
                        item = event.get("item", {})
                        item_type = item.get("type")

                        if item_type == "file_change":
                            path = item.get("path", "unknown")
                            payload = {"path": path}
                            if parent_activity:
                                payload["parent_activity"] = parent_activity
                            if nesting_depth > 0:
                                payload["nesting_depth"] = nesting_depth
                            sdk.track_activity(
                                tool="codex_file_change",
                                summary=f"Codex modified: {path}",
                                file_paths=[path],
                                payload=payload,
                            )

                        elif item_type == "agent_message":
                            text = item.get("text", "")
                            summary = text[:100] + "..." if len(text) > 100 else text
                            payload = {"text_length": len(text)}
                            if parent_activity:
                                payload["parent_activity"] = parent_activity
                            if nesting_depth > 0:
                                payload["nesting_depth"] = nesting_depth
                            sdk.track_activity(
                                tool="codex_message",
                                summary=f"Codex: {summary}",
                                payload=payload,
                            )

                    # Track turn.completed for token usage
                    elif event_type == "turn.completed":
                        usage = event.get("usage", {})
                        total_tokens = sum(usage.values())
                        payload = {"usage": usage}
                        if parent_activity:
                            payload["parent_activity"] = parent_activity
                        if nesting_depth > 0:
                            payload["nesting_depth"] = nesting_depth
                        sdk.track_activity(
                            tool="codex_completion",
                            summary=f"Codex turn completed ({total_tokens} tokens)",
                            payload=payload,
                        )
                except Exception:
                    # Tracking failure should not break parsing
                    pass

            except json.JSONDecodeError as e:
                parse_errors.append(
                    {
                        "line_number": line_num,
                        "error": str(e),
                        "content": line[:100],
                    }
                )
                continue

        return events

    def _parse_and_track_copilot_events(
        self, prompt: str, response: str, sdk: "SDK"
    ) -> list[dict]:
        """
        Track Copilot execution (start and result only).

        Args:
            prompt: Original prompt
            response: Response from Copilot
            sdk: HtmlGraph SDK instance for tracking

        Returns:
            Synthetic events list for consistency
        """
        events = []

        # Get parent context for metadata
        parent_activity = os.getenv("HTMLGRAPH_PARENT_ACTIVITY")
        nesting_depth_str = os.getenv("HTMLGRAPH_NESTING_DEPTH", "0")
        nesting_depth = int(nesting_depth_str) if nesting_depth_str.isdigit() else 0

        try:
            # Track start
            start_event = {"type": "copilot_start", "prompt": prompt[:100]}
            events.append(start_event)
            payload: dict[str, str | int] = {"prompt_length": len(prompt)}
            if parent_activity:
                payload["parent_activity"] = parent_activity
            if nesting_depth > 0:
                payload["nesting_depth"] = nesting_depth
            sdk.track_activity(
                tool="copilot_start",
                summary=f"Copilot started with prompt: {prompt[:80]}",
                payload=payload,
            )
        except Exception:
            pass

        try:
            # Track result
            result_event = {"type": "copilot_result", "response": response[:100]}
            events.append(result_event)
            payload_result: dict[str, str | int] = {"response_length": len(response)}
            if parent_activity:
                payload_result["parent_activity"] = parent_activity
            if nesting_depth > 0:
                payload_result["nesting_depth"] = nesting_depth
            sdk.track_activity(
                tool="copilot_result",
                summary=f"Copilot completed: {response[:80]}",
                payload=payload_result,
            )
        except Exception:
            pass

        return events

    def spawn_gemini(
        self,
        prompt: str,
        output_format: str = "stream-json",
        model: str | None = None,
        include_directories: list[str] | None = None,
        track_in_htmlgraph: bool = True,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn Gemini in headless mode.

        Args:
            prompt: Task description for Gemini
            output_format: "json" or "stream-json" (enables real-time tracking)
            model: Model selection (e.g., "gemini-2.0-flash"). Default: None
            include_directories: Directories to include for context. Default: None
            track_in_htmlgraph: Enable HtmlGraph activity tracking. Default: True
            timeout: Max seconds to wait

        Returns:
            AIResult with response, error, and tracked events if tracking enabled
        """
        # Initialize tracking if enabled
        sdk: SDK | None = None
        tracked_events: list[dict] = []
        if track_in_htmlgraph:
            sdk = self._get_sdk()

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

            # Track spawner start if SDK available
            if sdk:
                try:
                    sdk.track_activity(
                        tool="gemini_spawn_start",
                        summary=f"Spawning Gemini: {prompt[:80]}",
                        payload={"prompt_length": len(prompt), "model": model},
                    )
                except Exception:
                    # Tracking failure should not break execution
                    pass

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
                    tracked_events=tracked_events,
                )

            # Handle stream-json format with real-time tracking
            if output_format == "stream-json" and sdk:
                try:
                    tracked_events = self._parse_and_track_gemini_events(
                        result.stdout, sdk
                    )
                    # Only use stream-json parsing if we got valid events
                    if tracked_events:
                        # For stream-json, we need to extract response differently
                        # Collect all assistant message content, then check result
                        response_text = ""
                        for event in tracked_events:
                            if event.get("type") == "message":
                                # Only collect assistant messages
                                if event.get("role") == "assistant":
                                    content = event.get("content", "")
                                    if content:
                                        response_text += content
                            elif event.get("type") == "result":
                                # Result event may have response field (override if present)
                                if "response" in event and event["response"]:
                                    response_text = event["response"]
                                # Don't break - we've already collected messages

                        # Token usage from stats in result event
                        tokens = None
                        for event in tracked_events:
                            if event.get("type") == "result":
                                stats = event.get("stats", {})
                                if stats and "models" in stats:
                                    total_tokens = 0
                                    for model_stats in stats["models"].values():
                                        model_tokens = model_stats.get(
                                            "tokens", {}
                                        ).get("total", 0)
                                        total_tokens += model_tokens
                                    tokens = total_tokens if total_tokens > 0 else None
                                break

                        return AIResult(
                            success=True,
                            response=response_text,
                            tokens_used=tokens,
                            error=None,
                            raw_output={"events": tracked_events},
                            tracked_events=tracked_events,
                        )

                except Exception:
                    # Fall back to regular JSON parsing if tracking fails
                    pass

            # Parse JSON response (for json format or fallback)
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                return AIResult(
                    success=False,
                    response="",
                    tokens_used=None,
                    error=f"Failed to parse JSON output: {e}",
                    raw_output={"stdout": result.stdout},
                    tracked_events=tracked_events,
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
                tracked_events=tracked_events,
            )

        except subprocess.TimeoutExpired as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Gemini CLI timed out after {timeout} seconds",
                raw_output={
                    "partial_stdout": e.stdout.decode() if e.stdout else None,
                    "partial_stderr": e.stderr.decode() if e.stderr else None,
                }
                if e.stdout or e.stderr
                else None,
                tracked_events=tracked_events,
            )
        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Gemini CLI not found. Ensure 'gemini' is installed and in PATH.",
                raw_output=None,
                tracked_events=tracked_events,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                raw_output=None,
                tracked_events=tracked_events,
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
        track_in_htmlgraph: bool = True,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn Codex in headless mode.

        Args:
            prompt: Task description for Codex
            output_json: JSONL output flag (enables real-time tracking)
            model: Model selection (e.g., "gpt-4-turbo"). Default: None
            sandbox: Sandbox mode ("read-only", "workspace-write", or full)
            full_auto: Enable full auto mode. Default: True (required headless)
            images: List of image paths (--image). Default: None
            output_last_message: Write last message to file. Default: None
            output_schema: JSON schema for validation. Default: None
            skip_git_check: Skip git repo check. Default: False
            working_directory: Workspace directory (--cd). Default: None
            use_oss: Use local Ollama provider (--oss). Default: False
            bypass_approvals: Bypass approval checks. Default: False
            track_in_htmlgraph: Enable HtmlGraph activity tracking. Default: True
            timeout: Max seconds to wait

        Returns:
            AIResult with response, error, and tracked events if tracking enabled
        """
        # Initialize tracking if enabled
        sdk: SDK | None = None
        tracked_events: list[dict] = []
        if track_in_htmlgraph and output_json:
            sdk = self._get_sdk()

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

        # Track spawner start if SDK available
        if sdk:
            try:
                sdk.track_activity(
                    tool="codex_spawn_start",
                    summary=f"Spawning Codex: {prompt[:80]}",
                    payload={
                        "prompt_length": len(prompt),
                        "model": model,
                        "sandbox": sandbox,
                    },
                )
            except Exception:
                # Tracking failure should not break execution
                pass

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
                    tracked_events=tracked_events,
                )

            # Parse JSONL output
            events = []
            parse_errors = []

            # Use tracking parser if SDK is available
            if sdk:
                tracked_events = self._parse_and_track_codex_events(result.stdout, sdk)
                events = tracked_events
            else:
                # Fallback to regular parsing without tracking
                for line_num, line in enumerate(result.stdout.splitlines(), start=1):
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            parse_errors.append(
                                {
                                    "line_number": line_num,
                                    "error": str(e),
                                    "content": line[
                                        :100
                                    ],  # First 100 chars for debugging
                                }
                            )
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
                raw_output={
                    "events": events,
                    "parse_errors": parse_errors if parse_errors else None,
                },
                tracked_events=tracked_events,
            )

        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Codex CLI not found. Install from: https://github.com/openai/codex",
                raw_output=None,
                tracked_events=tracked_events,
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
                tracked_events=tracked_events,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                raw_output=None,
                tracked_events=tracked_events,
            )

    def spawn_copilot(
        self,
        prompt: str,
        allow_tools: list[str] | None = None,
        allow_all_tools: bool = False,
        deny_tools: list[str] | None = None,
        track_in_htmlgraph: bool = True,
        timeout: int = 120,
    ) -> AIResult:
        """
        Spawn GitHub Copilot in headless mode.

        Args:
            prompt: Task description for Copilot
            allow_tools: Tools to auto-approve (e.g., ["shell(git)"])
            allow_all_tools: Auto-approve all tools. Default: False
            deny_tools: Tools to deny (--deny-tool). Default: None
            track_in_htmlgraph: Enable HtmlGraph activity tracking. Default: True
            timeout: Max seconds to wait

        Returns:
            AIResult with response, error, and tracked events if tracking enabled
        """
        # Initialize tracking if enabled
        sdk = None
        tracked_events = []
        if track_in_htmlgraph:
            sdk = self._get_sdk()

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

        # Track spawner start if SDK available
        if sdk:
            try:
                sdk.track_activity(
                    tool="copilot_spawn_start",
                    summary=f"Spawning Copilot: {prompt[:80]}",
                    payload={"prompt_length": len(prompt)},
                )
            except Exception:
                # Tracking failure should not break execution
                pass

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

            # Track Copilot execution if SDK available
            if sdk:
                tracked_events = self._parse_and_track_copilot_events(
                    prompt, response, sdk
                )

            return AIResult(
                success=result.returncode == 0,
                response=response,
                tokens_used=tokens,
                error=None if result.returncode == 0 else result.stderr,
                raw_output=result.stdout,
                tracked_events=tracked_events,
            )

        except FileNotFoundError:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error="Copilot CLI not found. Install from: https://docs.github.com/en/copilot/using-github-copilot/using-github-copilot-in-the-command-line",
                raw_output=None,
                tracked_events=tracked_events,
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
                tracked_events=tracked_events,
            )
        except Exception as e:
            return AIResult(
                success=False,
                response="",
                tokens_used=None,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                raw_output=None,
                tracked_events=tracked_events,
            )

    def spawn_claude(
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
