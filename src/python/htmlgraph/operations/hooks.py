from __future__ import annotations

"""Git hook operations for HtmlGraph."""


import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HookInstallResult:
    installed: list[str]
    skipped: list[str]
    warnings: list[str]
    config_used: dict[str, Any]


@dataclass(frozen=True)
class HookListResult:
    enabled: list[str]
    disabled: list[str]
    missing: list[str]


@dataclass(frozen=True)
class HookValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]


class HookConfigError(ValueError):
    """Invalid hook configuration."""


class HookInstallError(RuntimeError):
    """Hook installation failed."""


def _load_hook_config(project_dir: Path) -> dict[str, Any]:
    """Load hook configuration from project."""
    config_path = project_dir / ".htmlgraph" / "hooks-config.json"

    # Default configuration
    default_config: dict[str, Any] = {
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

    if not config_path.exists():
        return default_config

    try:
        with open(config_path, encoding="utf-8") as f:
            user_config = json.load(f)
            # Merge with defaults
            config = default_config.copy()
            config.update(user_config)
            return config
    except Exception as e:
        raise HookConfigError(f"Failed to load hook config: {e}") from e


def _validate_environment(project_dir: Path) -> None:
    """Validate that environment is ready for hook installation."""
    git_dir = project_dir / ".git"
    htmlgraph_dir = project_dir / ".htmlgraph"

    if not git_dir.exists():
        raise HookInstallError("Not a git repository (no .git directory found)")

    if not htmlgraph_dir.exists():
        raise HookInstallError("HtmlGraph not initialized (run 'htmlgraph init' first)")

    git_hooks_dir = git_dir / "hooks"
    if not git_hooks_dir.exists():
        try:
            git_hooks_dir.mkdir(parents=True)
        except Exception as e:
            raise HookInstallError(f"Cannot create .git/hooks directory: {e}") from e


def _install_single_hook(
    hook_name: str,
    *,
    project_dir: Path,
    config: dict[str, Any],
    force: bool = False,
) -> tuple[bool, str]:
    """Install a single git hook."""
    from htmlgraph.hooks import HOOKS_DIR

    # Check if hook is enabled
    if hook_name not in config.get("enabled_hooks", []):
        return False, f"Hook '{hook_name}' is disabled in configuration"

    # Source hook file
    hook_source = HOOKS_DIR / f"{hook_name}.sh"
    if not hook_source.exists():
        return False, f"Hook template not found: {hook_source}"

    # Destination in .htmlgraph/hooks/ (versioned)
    htmlgraph_dir = project_dir / ".htmlgraph"
    versioned_hooks_dir = htmlgraph_dir / "hooks"
    versioned_hooks_dir.mkdir(exist_ok=True)
    hook_dest = versioned_hooks_dir / f"{hook_name}.sh"

    # Git hooks directory
    git_dir = project_dir / ".git"
    git_hooks_dir = git_dir / "hooks"
    git_hook_path = git_hooks_dir / hook_name

    # Copy hook to .htmlgraph/hooks/ (versioned)
    try:
        shutil.copy(hook_source, hook_dest)
        hook_dest.chmod(0o755)
    except Exception as e:
        raise HookInstallError(f"Failed to copy hook to {hook_dest}: {e}") from e

    # Handle existing git hook
    if git_hook_path.exists() and not force:
        if config.get("backup_existing", True):
            backup_path = git_hook_path.with_suffix(".backup")
            if not backup_path.exists():
                shutil.copy(git_hook_path, backup_path)

            if config.get("chain_existing", True):
                # Create chained hook
                return _create_chained_hook(
                    hook_name, hook_dest, git_hook_path, backup_path
                )
            else:
                return False, (
                    f"Hook {hook_name} already exists. "
                    f"Backed up to {backup_path}. "
                    f"Use force=True to overwrite."
                )

    # Install hook (symlink or copy)
    use_symlinks = not force and config.get("use_symlinks", True)

    try:
        if use_symlinks:
            # Remove existing symlink if present
            if git_hook_path.is_symlink():
                git_hook_path.unlink()

            git_hook_path.symlink_to(hook_dest.resolve())
            return True, f"Installed {hook_name} (symlink)"
        else:
            shutil.copy(hook_dest, git_hook_path)
            git_hook_path.chmod(0o755)
            return True, f"Installed {hook_name} (copy)"
    except Exception as e:
        raise HookInstallError(f"Failed to install {hook_name}: {e}") from e


def _create_chained_hook(
    hook_name: str, htmlgraph_hook: Path, git_hook: Path, backup_hook: Path
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
        return True, f"Installed {hook_name} (chained)"
    except Exception as e:
        raise HookInstallError(f"Failed to create chained hook: {e}") from e


def install_hooks(*, project_dir: Path, use_copy: bool = False) -> HookInstallResult:
    """
    Install HtmlGraph git hooks into the project.

    Args:
        project_dir: Project root directory
        use_copy: Force copy instead of symlink

    Returns:
        HookInstallResult with installation details

    Raises:
        HookInstallError: If installation fails
        HookConfigError: If configuration is invalid
    """
    project_dir = Path(project_dir).resolve()

    # Validate environment
    _validate_environment(project_dir)

    # Load configuration
    config = _load_hook_config(project_dir)

    # Override use_symlinks if use_copy is requested
    if use_copy:
        config["use_symlinks"] = False

    installed: list[str] = []
    skipped: list[str] = []
    warnings: list[str] = []

    # Install each enabled hook
    for hook_name in config.get("enabled_hooks", []):
        try:
            success, message = _install_single_hook(
                hook_name,
                project_dir=project_dir,
                config=config,
                force=False,
            )

            if success:
                installed.append(hook_name)
            else:
                skipped.append(hook_name)
                warnings.append(message)
        except Exception as e:
            skipped.append(hook_name)
            warnings.append(f"{hook_name}: {e}")

    return HookInstallResult(
        installed=installed,
        skipped=skipped,
        warnings=warnings,
        config_used=config,
    )


def list_hooks(*, project_dir: Path) -> HookListResult:
    """
    Return enabled/disabled/missing hooks for a project.

    Args:
        project_dir: Project root directory

    Returns:
        HookListResult with hook status
    """
    from htmlgraph.hooks import AVAILABLE_HOOKS

    project_dir = Path(project_dir).resolve()
    git_dir = project_dir / ".git"

    # Load configuration
    try:
        config = _load_hook_config(project_dir)
    except HookConfigError:
        config = {"enabled_hooks": []}

    enabled_hooks = config.get("enabled_hooks", [])

    enabled: list[str] = []
    disabled: list[str] = []
    missing: list[str] = []

    for hook_name in AVAILABLE_HOOKS:
        git_hook_path = git_dir / "hooks" / hook_name
        is_enabled = hook_name in enabled_hooks

        if is_enabled:
            if git_hook_path.exists():
                enabled.append(hook_name)
            else:
                missing.append(hook_name)
        else:
            disabled.append(hook_name)

    return HookListResult(
        enabled=enabled,
        disabled=disabled,
        missing=missing,
    )


def validate_hook_config(*, project_dir: Path) -> HookValidationResult:
    """
    Validate hook configuration for a project.

    Args:
        project_dir: Project root directory

    Returns:
        HookValidationResult with validation status
    """
    from htmlgraph.hooks import AVAILABLE_HOOKS

    project_dir = Path(project_dir).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    # Check git repository
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        errors.append("Not a git repository (no .git directory found)")

    # Check HtmlGraph initialization
    htmlgraph_dir = project_dir / ".htmlgraph"
    if not htmlgraph_dir.exists():
        errors.append("HtmlGraph not initialized (run 'htmlgraph init' first)")

    # Load and validate configuration
    try:
        config = _load_hook_config(project_dir)

        # Validate enabled_hooks
        enabled_hooks = config.get("enabled_hooks", [])
        if not isinstance(enabled_hooks, list):
            errors.append("enabled_hooks must be a list")
        else:
            for hook_name in enabled_hooks:
                if hook_name not in AVAILABLE_HOOKS:
                    warnings.append(f"Unknown hook '{hook_name}' in configuration")

        # Validate boolean options
        for key in ["use_symlinks", "backup_existing", "chain_existing"]:
            value = config.get(key)
            if value is not None and not isinstance(value, bool):
                errors.append(f"{key} must be a boolean")

    except HookConfigError as e:
        errors.append(str(e))

    return HookValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
