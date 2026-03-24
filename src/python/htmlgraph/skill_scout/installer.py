"""Plugin installer: wraps claude plugin install with HtmlGraph tracking."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

INSTALL_HISTORY_FILE = ".htmlgraph/installed-plugins.json"


@dataclass
class InstallResult:
    """Result of a plugin installation attempt."""

    plugin_name: str
    success: bool
    message: str
    installed_at: str = ""

    def __post_init__(self) -> None:
        if self.success and not self.installed_at:
            self.installed_at = datetime.now(timezone.utc).isoformat()


def install_plugin(
    plugin_name: str,
    marketplace: str = "",
    project_root: Path | None = None,
) -> InstallResult:
    """Install a Claude Code plugin and track it in .htmlgraph/.

    Args:
        plugin_name: Plugin name (e.g., "commit-commands")
        marketplace: Optional marketplace qualifier (e.g., "anthropics-claude-code")
        project_root: Project root for tracking file. Defaults to cwd.
    """
    root = project_root or Path.cwd()
    install_target = f"{plugin_name}@{marketplace}" if marketplace else plugin_name

    try:
        result = subprocess.run(
            ["claude", "plugin", "install", install_target],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            install_result = InstallResult(
                plugin_name=plugin_name,
                success=True,
                message=f"Successfully installed {install_target}",
            )
            _record_installation(root, install_result)
            return install_result

        return InstallResult(
            plugin_name=plugin_name,
            success=False,
            message=f"Install failed: {result.stderr.strip()}",
        )

    except FileNotFoundError:
        return InstallResult(
            plugin_name=plugin_name,
            success=False,
            message="claude CLI not found. Install Claude Code first.",
        )
    except subprocess.TimeoutExpired:
        return InstallResult(
            plugin_name=plugin_name,
            success=False,
            message="Install timed out after 60 seconds.",
        )


def _record_installation(root: Path, result: InstallResult) -> None:
    """Record successful installation in .htmlgraph/installed-plugins.json."""
    history_file = root / INSTALL_HISTORY_FILE
    history_file.parent.mkdir(parents=True, exist_ok=True)

    history: list[dict] = []  # type: ignore[type-arg]
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text())
        except json.JSONDecodeError:
            history = []

    history.append(
        {
            "plugin_name": result.plugin_name,
            "installed_at": result.installed_at,
            "message": result.message,
        }
    )

    history_file.write_text(json.dumps(history, indent=2) + "\n")


def get_install_history(project_root: Path | None = None) -> list[dict]:  # type: ignore[type-arg]
    """Read installation history from .htmlgraph/."""
    root = project_root or Path.cwd()
    history_file = root / INSTALL_HISTORY_FILE
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text())  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return []


def verify_plugin(plugin_name: str) -> bool:
    """Check if a plugin is currently installed and loadable."""
    try:
        result = subprocess.run(
            ["claude", "plugin", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return plugin_name in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
