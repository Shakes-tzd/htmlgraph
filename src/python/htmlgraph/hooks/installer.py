import logging

logger = logging.getLogger(__name__)

"""
Git hooks installation and configuration management.
"""

import json
import shutil
from pathlib import Path
from typing import Any


class HookConfig:
    """Configuration for git hooks installation."""

    DEFAULT_CONFIG: dict[str, Any] = {
        "enabled_hooks": [
            "post-commit",
            "post-checkout",
            "post-merge",
            "pre-push",
        ],
        "use_symlinks": True,
        "backup_existing": True,
        "chain_existing": True,
    }

    def __init__(self, config_path: Path | None = None):
        """
        Initialize hook configuration.

        Args:
            config_path: Path to hooks-config.json (defaults to .htmlgraph/hooks-config.json)
        """
        self.config_path = config_path
        # Deep copy to avoid mutating DEFAULT_CONFIG
        self.config = {
            "enabled_hooks": self.DEFAULT_CONFIG["enabled_hooks"].copy(),
            "use_symlinks": self.DEFAULT_CONFIG["use_symlinks"],
            "backup_existing": self.DEFAULT_CONFIG["backup_existing"],
            "chain_existing": self.DEFAULT_CONFIG["chain_existing"],
        }

        if config_path and config_path.exists():
            self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path or not self.config_path.exists():
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
                user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            logger.info(f"Warning: Failed to load hook config: {e}")

    def save(self) -> None:
        """Save configuration to file."""
        if not self.config_path:
            return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)

    def is_hook_enabled(self, hook_name: str) -> bool:
        """Check if a hook is enabled."""
        return hook_name in self.config.get("enabled_hooks", [])

    def enable_hook(self, hook_name: str) -> None:
        """Enable a specific hook."""
        enabled = self.config.get("enabled_hooks", [])
        if hook_name not in enabled:
            enabled.append(hook_name)
            self.config["enabled_hooks"] = enabled

    def disable_hook(self, hook_name: str) -> None:
        """Disable a specific hook."""
        enabled = self.config.get("enabled_hooks", [])
        if hook_name in enabled:
            enabled.remove(hook_name)
            self.config["enabled_hooks"] = enabled


class HookInstaller:
    """Handles installation of git hooks."""

    def __init__(self, project_dir: Path, config: HookConfig | None = None):
        """
        Initialize hook installer.

        Args:
            project_dir: Project root directory
            config: Hook configuration (creates default if not provided)
        """
        self.project_dir = Path(project_dir).resolve()
        self.git_dir = self.project_dir / ".git"
        self.htmlgraph_dir = self.project_dir / ".htmlgraph"
        self.hooks_source_dir = Path(__file__).parent

        # Load or create config
        config_path = self.htmlgraph_dir / "hooks-config.json"
        self.config = config or HookConfig(config_path)

    def validate_environment(self) -> tuple[bool, str]:
        """
        Validate that the environment is ready for hook installation.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.git_dir.exists():
            return False, "Not a git repository (no .git directory found)"

        if not self.htmlgraph_dir.exists():
            return False, "HtmlGraph not initialized (run 'htmlgraph init' first)"

        git_hooks_dir = self.git_dir / "hooks"
        if not git_hooks_dir.exists():
            try:
                git_hooks_dir.mkdir(parents=True)
            except Exception as e:
                return False, f"Cannot create .git/hooks directory: {e}"

        return True, ""

    def install_hook(
        self, hook_name: str, force: bool = False, dry_run: bool = False
    ) -> tuple[bool, str]:
        """
        Install a single git hook.

        Args:
            hook_name: Name of the hook (e.g., "pre-commit")
            force: Force installation even if hook exists
            dry_run: Show what would be done without doing it

        Returns:
            Tuple of (success, message)
        """
        # Check if hook is enabled
        if not self.config.is_hook_enabled(hook_name):
            return False, f"Hook '{hook_name}' is disabled in configuration"

        # Source hook file
        hook_source = self.hooks_source_dir / f"{hook_name}.sh"
        if not hook_source.exists():
            return False, f"Hook template not found: {hook_source}"

        # Destination in .htmlgraph/hooks/
        versioned_hooks_dir = self.htmlgraph_dir / "hooks"
        versioned_hooks_dir.mkdir(exist_ok=True)
        hook_dest = versioned_hooks_dir / f"{hook_name}.sh"

        # Git hooks directory
        git_hooks_dir = self.git_dir / "hooks"
        git_hook_path = git_hooks_dir / hook_name

        if dry_run:
            msg = f"[DRY RUN] Would install {hook_name}:\n"
            msg += f"  Source: {hook_source}\n"
            msg += f"  Versioned: {hook_dest}\n"
            msg += f"  Git hook: {git_hook_path}"
            return True, msg

        # Copy hook to .htmlgraph/hooks/ (versioned)
        try:
            shutil.copy(hook_source, hook_dest)
            hook_dest.chmod(0o755)
        except Exception as e:
            return False, f"Failed to copy hook to {hook_dest}: {e}"

        # Handle existing git hook
        if git_hook_path.exists() and not force:
            if self.config.config.get("backup_existing", True):
                backup_path = git_hook_path.with_suffix(".backup")
                if not backup_path.exists():
                    shutil.copy(git_hook_path, backup_path)

                if self.config.config.get("chain_existing", True):
                    # Create chained hook
                    return self._create_chained_hook(
                        hook_name, hook_dest, git_hook_path, backup_path
                    )
                else:
                    return False, (
                        f"Hook {hook_name} already exists. "
                        f"Backed up to {backup_path}. "
                        f"Use --force to overwrite."
                    )

        # Install hook (symlink or copy)
        try:
            if self.config.config.get("use_symlinks", True):
                # Remove existing symlink if present
                if git_hook_path.is_symlink():
                    git_hook_path.unlink()

                git_hook_path.symlink_to(hook_dest.resolve())
                return (
                    True,
                    f"Installed {hook_name} (symlink): {git_hook_path} -> {hook_dest}",
                )
            else:
                shutil.copy(hook_dest, git_hook_path)
                git_hook_path.chmod(0o755)
                return True, f"Installed {hook_name} (copy): {git_hook_path}"
        except Exception as e:
            return False, f"Failed to install {hook_name}: {e}"

    def _create_chained_hook(
        self, hook_name: str, htmlgraph_hook: Path, git_hook: Path, backup_hook: Path
    ) -> tuple[bool, str]:
        """Create a chained hook that runs both existing and HtmlGraph hooks."""
        chain_content = f'''#!/bin/bash
# Chained hook - runs existing hook then HtmlGraph hook

# Run existing hook
if [ -f "{backup_hook}" ]; then
  "{backup_hook}" || exit $?
fi

# Run HtmlGraph hook
if [ -f "{htmlgraph_hook}" ]; then
  "{htmlgraph_hook}" || true
fi
'''

        try:
            git_hook.write_text(chain_content, encoding="utf-8")
            git_hook.chmod(0o755)
            return True, (
                f"Installed {hook_name} (chained):\n"
                f"  Backed up existing: {backup_hook}\n"
                f"  Installed wrapper: {git_hook}"
            )
        except Exception as e:
            return False, f"Failed to create chained hook: {e}"

    def install_all_hooks(
        self, force: bool = False, dry_run: bool = False
    ) -> dict[str, tuple[bool, str]]:
        """
        Install all enabled hooks.

        Args:
            force: Force installation even if hooks exist
            dry_run: Show what would be done without doing it

        Returns:
            Dictionary mapping hook names to (success, message) tuples
        """
        results = {}

        for hook_name in self.config.config.get("enabled_hooks", []):
            success, message = self.install_hook(
                hook_name, force=force, dry_run=dry_run
            )
            results[hook_name] = (success, message)

        return results

    def uninstall_hook(self, hook_name: str) -> tuple[bool, str]:
        """
        Uninstall a git hook.

        Args:
            hook_name: Name of the hook to uninstall

        Returns:
            Tuple of (success, message)
        """
        git_hook_path = self.git_dir / "hooks" / hook_name

        if not git_hook_path.exists():
            return False, f"Hook {hook_name} is not installed"

        # Check if it's a symlink to our hook
        versioned_hook = self.htmlgraph_dir / "hooks" / f"{hook_name}.sh"

        try:
            if git_hook_path.is_symlink():
                target = git_hook_path.resolve()
                if target == versioned_hook.resolve():
                    git_hook_path.unlink()
                    return True, f"Uninstalled {hook_name} (symlink removed)"
                else:
                    return False, f"Hook {hook_name} points to {target}, not our hook"
            else:
                # Not a symlink - check for backup
                backup_path = git_hook_path.with_suffix(".backup")
                if backup_path.exists():
                    git_hook_path.unlink()
                    shutil.move(backup_path, git_hook_path)
                    return True, f"Uninstalled {hook_name} (restored backup)"
                else:
                    return False, (
                        f"Hook {hook_name} exists but no backup found. "
                        f"Manual removal required."
                    )
        except Exception as e:
            return False, f"Failed to uninstall {hook_name}: {e}"

    def list_hooks(self) -> dict[str, dict[str, Any]]:
        """
        List all hooks and their installation status.

        Returns:
            Dictionary mapping hook names to status info
        """
        from . import AVAILABLE_HOOKS

        status = {}

        for hook_name in AVAILABLE_HOOKS:
            git_hook_path = self.git_dir / "hooks" / hook_name
            versioned_hook = self.htmlgraph_dir / "hooks" / f"{hook_name}.sh"

            info: dict[str, Any] = {
                "enabled": self.config.is_hook_enabled(hook_name),
                "installed": git_hook_path.exists(),
                "versioned": versioned_hook.exists(),
                "is_symlink": git_hook_path.is_symlink()
                if git_hook_path.exists()
                else False,
            }

            if info["is_symlink"]:
                try:
                    target = git_hook_path.resolve()
                    info["symlink_target"] = str(target)
                    info["our_hook"] = target == versioned_hook.resolve()
                except Exception:
                    info["symlink_target"] = "unknown"
                    info["our_hook"] = False

            status[hook_name] = info

        return status
