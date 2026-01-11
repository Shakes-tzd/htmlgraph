#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "htmlgraph",
# ]
# ///
"""
PreToolUse Spawner Router Hook - Phase 3 Implementation

Intercepts Task() calls with spawner subagent_type (gemini, codex, copilot)
and routes them to the appropriate spawner agent.

Architecture:
- Reads event from stdin (JSON PreToolUse hook input)
- Extracts tool_name and params
- Only intercepts if tool_name == "Task"
- For non-spawner types: pass through (return None or early exit)
- For spawner types:
  * Load plugin.json to get agent registry
  * Check if required CLI is available (using shutil.which)
  * If CLI unavailable: return explicit error (action: "block")
  * If CLI available: execute spawner agent via subprocess
  * Return result or error to caller

Error Handling:
- CLI not found → explicit error message with installation instructions
- Execution failure → block and return error
- Success → return response with tokens

Spawner Types:
- gemini → agents/gemini-spawner.py (requires: gemini CLI)
- codex → agents/codex-spawner.py (requires: codex CLI)
- copilot → agents/copilot-spawner.py (requires: gh CLI)
"""

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Check if tracking is disabled
if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
    print(json.dumps({"continue": True}))
    sys.exit(0)


def load_plugin_manifest() -> dict[str, object]:
    """
    Load agents registry from plugin.json.

    Returns:
        Dict with agents configuration, or empty dict if not found
    """
    try:
        # Find plugin.json - it should be in the same directory as this script
        # or in a parent .claude-plugin directory
        script_dir = Path(__file__).parent.parent.parent  # .claude-plugin/
        plugin_json = script_dir / "plugin.json"

        if not plugin_json.exists():
            # Try alternative paths
            possible_paths = [
                Path.cwd() / ".claude-plugin" / "plugin.json",
                Path.home() / ".claude" / "plugins" / "htmlgraph" / "plugin.json",
            ]
            for path in possible_paths:
                if path.exists():
                    plugin_json = path
                    break

        if plugin_json.exists():
            with open(plugin_json) as f:
                manifest: dict[str, object] = json.load(f)
            logger.info(f"Loaded plugin manifest from {plugin_json}")
            return manifest
        else:
            logger.warning(f"Plugin manifest not found at {plugin_json}")
            return {}

    except Exception as e:
        logger.warning(f"Failed to load plugin manifest: {e}")
        return {}


def detect_current_model(hook_input: dict) -> str | None:
    """
    Detect the current Claude model from multiple sources.

    Checks in order of priority:
    1. Task() model parameter (if tool_name == 'Task')
    2. ANTHROPIC_MODEL or CLAUDE_MODEL environment variables
    3. Claude settings file (.claude/settings.json)

    Args:
        hook_input: Hook input dict containing tool_name and tool_input

    Returns:
        Model name string (e.g., 'claude-opus', 'claude-sonnet', 'claude-haiku')
        or None if not detected
    """
    # 1. Check for Task() model parameter
    tool_name = hook_input.get("tool_name", "") or hook_input.get("name", "")
    tool_input = hook_input.get("tool_input", {}) or hook_input.get("input", {})

    if tool_name == "Task" and "model" in tool_input:
        model = tool_input.get("model")
        if model and isinstance(model, str):
            # Normalize model name
            model = model.strip().lower()
            # Ensure claude- prefix
            if not model.startswith("claude-"):
                model = f"claude-{model}"
            logger.info(f"Detected model from Task() parameter: {model}")
            return model

    # 2. Check environment variables
    for env_var in ["ANTHROPIC_MODEL", "CLAUDE_MODEL", "HTMLGRAPH_MODEL"]:
        model = os.environ.get(env_var)
        if model and isinstance(model, str):
            model = model.strip()
            if model:
                logger.info(f"Detected model from {env_var}: {model}")
                return model

    # 3. Check Claude settings file
    settings_paths = [
        Path.home() / ".claude" / "settings.json",
        Path.cwd() / ".claude" / "settings.json",
    ]
    for settings_path in settings_paths:
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
                    if "model" in settings:
                        model = settings["model"]
                        if isinstance(model, str):
                            model = model.strip()
                            logger.info(f"Detected model from {settings_path}: {model}")
                            return model
            except Exception as e:
                logger.debug(f"Failed to read settings from {settings_path}: {e}")

    logger.debug("No model detected from any source")
    return None


def is_cli_available(cli_name: str) -> bool:
    """
    Check if CLI tool is available (using shutil.which).

    Args:
        cli_name: Name of the CLI tool to check (e.g., 'gemini', 'codex', 'gh')

    Returns:
        True if CLI is available, False otherwise
    """
    try:
        result = shutil.which(cli_name)
        is_available = result is not None
        logger.info(
            f"CLI check '{cli_name}': {'available' if is_available else 'not found'}"
        )
        return is_available
    except Exception as e:
        logger.warning(f"Failed to check CLI availability for '{cli_name}': {e}")
        return False


def get_spawner_cli_requirements() -> dict:
    """
    Get CLI requirements and installation URLs for each spawner.

    Returns:
        Dict mapping spawner type to (cli_name, install_url)
    """
    return {
        "gemini": {
            "cli": "gemini",
            "install_url": "https://ai.google.dev/gemini-api/docs/cli",
            "description": "Google Gemini CLI",
        },
        "codex": {
            "cli": "codex",
            "install_url": "https://github.com/openai/codex",
            "description": "OpenAI Codex CLI",
        },
        "copilot": {
            "cli": "gh",
            "install_url": "https://cli.github.com/",
            "description": "GitHub CLI (gh)",
        },
    }


def get_spawner_agent_config(
    manifest: dict[str, object], spawner_type: str
) -> dict[str, object] | None:
    """
    Get spawner agent configuration from manifest.

    Args:
        manifest: Plugin manifest dict
        spawner_type: Type of spawner (gemini, codex, copilot)

    Returns:
        Agent config dict, or None if not found
    """
    try:
        agents = manifest.get("agents", {})
        config = agents.get(spawner_type) if isinstance(agents, dict) else None

        if config:
            logger.info(f"Found agent config for '{spawner_type}'")
            return config  # type: ignore[return-value]
        else:
            logger.warning(f"No agent config found for '{spawner_type}'")
            return None

    except Exception as e:
        logger.warning(f"Failed to get agent config for '{spawner_type}': {e}")
        return None


def check_spawner_requirements(
    spawner_type: str, agent_config: dict[str, object]
) -> tuple[bool, str]:
    """
    Check if spawner has all required dependencies.

    Args:
        spawner_type: Type of spawner
        agent_config: Agent configuration from manifest

    Returns:
        Tuple of (is_available, error_message)
        - is_available: True if all requirements met
        - error_message: Human-readable error message if not available
    """
    cli_requirements = get_spawner_cli_requirements()

    if spawner_type not in cli_requirements:
        error = f"Unknown spawner type: {spawner_type}"
        logger.error(error)
        return False, error

    requirement = cli_requirements[spawner_type]
    required_cli = requirement["cli"]
    install_url = requirement["install_url"]
    description = requirement["description"]

    # Check if CLI is available
    if not is_cli_available(required_cli):
        error = (
            f"❌ {description} not available\n\n"
            f"Spawner '{spawner_type}' requires the '{required_cli}' CLI.\n\n"
            f"Install from: {install_url}\n\n"
            f"This operation cannot proceed without the required CLI."
        )
        logger.error(f"CLI check failed for {spawner_type}: {required_cli}")
        return False, error

    return True, ""


def get_parent_query_event_id() -> str | None:
    """
    Query HtmlGraph database for the most recent UserQuery event.

    Returns:
        Event ID string, or None if not found or database unavailable
    """
    try:
        from htmlgraph.db.schema import HtmlGraphDB

        # Get correct database path from project root
        project_root = os.environ.get("HTMLGRAPH_PROJECT_ROOT", os.getcwd())
        db_path = Path(project_root) / ".htmlgraph" / "index.sqlite"

        if not db_path.exists():
            logger.debug(f"Database not found at {db_path}")
            return None

        db = HtmlGraphDB(str(db_path))
        if db.connection is None:
            logger.debug("Failed to connect to database")
            return None

        cursor = db.connection.cursor()

        cursor.execute(
            """
            SELECT event_id FROM agent_events
            WHERE tool_name = 'UserQuery'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row:
            parent_id = row[0]
            logger.info(f"Found parent UserQuery event: {parent_id}")
            return str(parent_id)
        else:
            logger.debug("No UserQuery event found in database")
            return None

    except ImportError:
        logger.debug("HtmlGraphDB not available")
        return None
    except Exception as e:
        logger.debug(f"Failed to query parent UserQuery event: {e}")
        return None


def route_to_spawner(
    spawner_type: str,
    prompt: str,
    manifest: dict[str, object],
    hook_input: dict | None = None,
    **kwargs: object,
) -> dict[str, object]:
    """
    Route Task() call to appropriate spawner agent.

    Args:
        spawner_type: Type of spawner (gemini, codex, copilot)
        prompt: Task prompt to execute
        manifest: Plugin manifest for agent config
        hook_input: Original hook input for model detection (optional)
        **kwargs: Additional Task() parameters

    Returns:
        Hook response dict with result or error
    """
    # Get agent config
    agent_config = get_spawner_agent_config(manifest, spawner_type)
    if not agent_config:
        error_msg = (
            f"Agent configuration for '{spawner_type}' not found in plugin.json\n\n"
            f"Available spawners: gemini, codex, copilot"
        )
        logger.error(error_msg)
        return {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"🚫 SPAWNER ROUTING ERROR: {error_msg}",
            },
        }

    # Check requirements
    is_available, error_message = check_spawner_requirements(spawner_type, agent_config)
    if not is_available:
        logger.error(f"Spawner requirements not met for {spawner_type}")
        return {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"🚫 SPAWNER UNAVAILABLE: {error_message}",
            },
        }

    # Spawn agent via subprocess
    try:
        agent_executable = agent_config.get("executable")
        if not agent_executable:
            error_msg = f"No executable specified for {spawner_type} in plugin.json"
            logger.error(error_msg)
            return {
                "continue": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": f"🚫 SPAWNER ERROR: {error_msg}",
                },
            }

        # Resolve executable path relative to plugin root
        plugin_root = Path(__file__).parent.parent.parent  # .claude-plugin/
        executable_path = plugin_root / agent_executable
        if not executable_path.exists():
            error_msg = f"Spawner executable not found: {executable_path}"
            logger.error(error_msg)
            return {
                "continue": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": f"🚫 SPAWNER ERROR: {error_msg}",
                },
            }

        # Build command: uv run <executable> -p <prompt>
        cmd: list[str] = ["uv", "run", str(executable_path), "-p", prompt]

        logger.info(f"Spawning {spawner_type} agent: {cmd[0]} ... -p '<prompt>'")

        # Get parent query event ID for context
        parent_query_event_id = get_parent_query_event_id()

        # Build environment with parent context
        env = os.environ.copy()

        # Set project root for spawner database access
        project_root = os.environ.get("HTMLGRAPH_PROJECT_ROOT", os.getcwd())
        env["HTMLGRAPH_PROJECT_ROOT"] = project_root

        if parent_query_event_id:
            env["HTMLGRAPH_PARENT_EVENT"] = parent_query_event_id
            logger.info(
                f"Passing parent query event to spawner: {parent_query_event_id}"
            )

        # Detect and pass model to spawner
        if hook_input:
            detected_model = detect_current_model(hook_input)
            if detected_model:
                env["HTMLGRAPH_MODEL"] = detected_model
                logger.info(f"Passing model to spawner: {detected_model}")

        # Execute spawner agent
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env,
        )

        if result.returncode != 0:
            error_msg = f"Spawner execution failed:\n{result.stderr}"
            logger.error(error_msg)
            return {
                "continue": False,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": f"🚫 SPAWNER ERROR: {error_msg}",
                },
            }

        # Success - spawner executed
        logger.info(f"Spawner {spawner_type} executed successfully")

        # Parse spawner output for response
        try:
            spawner_result = json.loads(result.stdout)
            response_text = spawner_result.get("response", result.stdout)
        except json.JSONDecodeError:
            response_text = result.stdout

        # Return response - block normal Task and provide spawner result
        # Using 'decision' field to substitute result (Claude Code 1.0.17+)
        return {
            "continue": False,
            "decision": "block",
            "reason": f"Handled by {spawner_type} spawner",
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"✅ {spawner_type.upper()} SPAWNER RESULT:\n\n{response_text}",
            },
        }

    except subprocess.TimeoutExpired:
        error_msg = f"Spawner {spawner_type} execution timed out (5 min limit)"
        logger.error(error_msg)
        return {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"🚫 SPAWNER TIMEOUT: {error_msg}",
            },
        }
    except Exception as e:
        error_msg = f"Spawner execution error: {e}"
        logger.error(error_msg)
        return {
            "continue": False,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"🚫 SPAWNER ERROR: {error_msg}",
            },
        }


def is_spawner_type(subagent_type: str) -> bool:
    """
    Check if subagent_type is a spawner type.

    Args:
        subagent_type: Type of subagent (e.g., "gemini" or ".claude-plugin:gemini")

    Returns:
        True if it's a spawner type (gemini, codex, copilot)
    """
    # Handle both bare names ("gemini") and prefixed names (".claude-plugin:gemini")
    spawner_types = ["gemini", "codex", "copilot"]
    name = subagent_type.lower().strip()

    # Direct match
    if name in spawner_types:
        return True

    # Check for prefixed format (e.g., ".claude-plugin:gemini")
    if ":" in name:
        suffix = name.split(":")[-1]
        if suffix in spawner_types:
            return True

    return False


def get_base_spawner_type(subagent_type: str) -> str:
    """
    Extract base spawner type from subagent_type.

    Args:
        subagent_type: Type of subagent (e.g., "gemini" or ".claude-plugin:gemini")

    Returns:
        Base spawner type (e.g., "gemini")
    """
    name = subagent_type.lower().strip()

    # Handle prefixed format (e.g., ".claude-plugin:gemini")
    if ":" in name:
        return name.split(":")[-1]

    return name


def main() -> None:
    """Main hook entry point for PreToolUse event."""
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from stdin")
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # Get tool name and parameters
    tool_name = hook_input.get("name", "") or hook_input.get("tool_name", "")
    tool_input = hook_input.get("input", {}) or hook_input.get("tool_input", {})

    # Only intercept Task() calls
    if tool_name != "Task":
        # Pass through for non-Task tools
        logger.debug(f"Not a Task call (tool: {tool_name}), passing through")
        print(json.dumps({"continue": True}))
        return

    # Extract subagent_type from Task parameters
    subagent_type = tool_input.get("subagent_type", "").strip()

    # Check if it's a spawner type
    if not is_spawner_type(subagent_type):
        # Not a spawner - pass through
        logger.debug(
            f"Not a spawner type (subagent_type: {subagent_type}), passing through"
        )
        print(json.dumps({"continue": True}))
        return

    # Load manifest for agent config
    manifest = load_plugin_manifest()
    if not manifest:
        logger.warning(
            "Could not load plugin manifest, allowing Task() to pass through"
        )
        print(json.dumps({"continue": True}))
        return

    # Extract prompt
    prompt = tool_input.get("prompt", "")
    if not prompt:
        logger.warning("Task() has no prompt, passing through")
        print(json.dumps({"continue": True}))
        return

    # Route to spawner (use base type for config lookup)
    base_spawner_type = get_base_spawner_type(subagent_type)
    logger.info(
        f"Routing Task() to spawner: {subagent_type} (base: {base_spawner_type})"
    )
    # Remove prompt from tool_input to avoid duplicate argument
    extra_kwargs = {k: v for k, v in tool_input.items() if k != "prompt"}
    response = route_to_spawner(
        base_spawner_type, prompt, manifest, hook_input=hook_input, **extra_kwargs
    )

    # Output JSON response
    print(json.dumps(response))


if __name__ == "__main__":
    main()
