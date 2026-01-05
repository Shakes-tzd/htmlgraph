#!/usr/bin/env python3
"""
HtmlGraph Deployment Module

Provides a flexible, configurable deployment system that can be used by any project.
Projects can customize deployment via htmlgraph-deploy.toml configuration file.
"""

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from rich.console import Console
from rich.prompt import Confirm

# Global Rich Console for beautiful CLI output
console = Console()


@dataclass
class DeploymentConfig:
    """Configuration for deployment process."""

    # Project info
    project_name: str = "my-project"
    pypi_package: str | None = None

    # Deployment steps
    steps: list[str] = field(
        default_factory=lambda: [
            "git-push",
            "build",
            "pypi-publish",
            "local-install",
            "update-plugins",
        ]
    )

    # Git config
    git_branch: str = "main"
    git_remote: str = "origin"
    git_push_tags: bool = True

    # Build config
    build_command: str = "uv build"
    clean_dist: bool = True

    # PyPI config
    pypi_token_env_var: str = "PyPI_API_TOKEN"
    pypi_wait_after_publish: int = 10  # seconds

    # Plugin config
    plugins: dict[str, str] = field(default_factory=dict)

    # Custom hooks
    pre_build_hooks: list[str] = field(default_factory=list)
    post_build_hooks: list[str] = field(default_factory=list)
    pre_publish_hooks: list[str] = field(default_factory=list)
    post_publish_hooks: list[str] = field(default_factory=list)

    @classmethod
    def from_toml(cls, config_path: Path) -> "DeploymentConfig":
        """Load configuration from TOML file."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # fallback for Python < 3.11

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Extract config sections
        project = data.get("project", {})
        deployment = data.get("deployment", {})

        # Default steps
        default_steps = [
            "git-push",
            "build",
            "pypi-publish",
            "local-install",
            "update-plugins",
        ]

        return cls(
            project_name=project.get("name", "my-project"),
            pypi_package=project.get("pypi_package"),
            steps=deployment.get("steps", default_steps),
            git_branch=deployment.get("git", {}).get("branch", "main"),
            git_remote=deployment.get("git", {}).get("remote", "origin"),
            git_push_tags=deployment.get("git", {}).get("push_tags", True),
            build_command=deployment.get("build", {}).get("command", "uv build"),
            clean_dist=deployment.get("build", {}).get("clean_dist", True),
            pypi_token_env_var=deployment.get("pypi", {}).get(
                "token_env_var", "PyPI_API_TOKEN"
            ),
            pypi_wait_after_publish=deployment.get("pypi", {}).get(
                "wait_after_publish", 10
            ),
            plugins=deployment.get("plugins", {}),
            pre_build_hooks=deployment.get("hooks", {}).get("pre_build", []),
            post_build_hooks=deployment.get("hooks", {}).get("post_build", []),
            pre_publish_hooks=deployment.get("hooks", {}).get("pre_publish", []),
            post_publish_hooks=deployment.get("hooks", {}).get("post_publish", []),
        )


class Deployer:
    """Handles deployment operations."""

    def __init__(
        self,
        config: DeploymentConfig,
        dry_run: bool = False,
        skip_steps: list[str] | None = None,
        only_steps: list[str] | None = None,
    ):
        self.config = config
        self.dry_run = dry_run
        self.skip_steps = set(skip_steps or [])
        self.only_steps = set(only_steps or [])
        self.version = self._detect_version()

        # Step handlers
        self.step_handlers: dict[str, Callable] = {
            "git-push": self._step_git_push,
            "build": self._step_build,
            "pypi-publish": self._step_pypi_publish,
            "local-install": self._step_local_install,
            "update-plugins": self._step_update_plugins,
        }

    def _detect_version(self) -> str:
        """Detect project version from pyproject.toml."""
        pyproject = Path("pyproject.toml")
        if not pyproject.exists():
            return "unknown"

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        return cast(str, data.get("project", {}).get("version", "unknown"))

    def log_section(self, message: str) -> None:
        """Log a section header."""
        console.print()
        console.print(f"[bold blue]{message}[/bold blue]")
        console.print()

    def log_success(self, message: str) -> None:
        """Log a success message."""
        console.print(f"[green]✅ {message}[/green]")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        console.print(f"[red]❌ {message}[/red]")

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        console.print(f"[yellow]⚠️  {message}[/yellow]")

    def log_info(self, message: str) -> None:
        """Log an info message."""
        console.print(f"[cyan]ℹ️  {message}[/cyan]")

    def run_command(
        self,
        cmd: list[str],
        description: str,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run a command with optional dry-run mode."""
        if self.dry_run:
            self.log_info(f"[DRY-RUN] Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0)

        self.log_info(description)

        try:
            result = subprocess.run(
                cmd,
                env=env or os.environ.copy(),
                check=check,
                capture_output=True,
                text=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log_error(f"Command failed: {' '.join(cmd)}")
            if e.stderr:
                # Print error to stderr using console (Rich supports stderr output)
                console.print(e.stderr, style="red")
            raise

    def run_hook(self, hook_commands: list[str], hook_name: str) -> None:
        """Run custom hook commands."""
        if not hook_commands:
            return

        self.log_info(f"Running {hook_name} hooks...")
        for cmd in hook_commands:
            # Replace placeholders
            cmd = cmd.format(
                version=self.version,
                package=self.config.pypi_package or self.config.project_name,
            )
            self.run_command(cmd.split(), f"Hook: {cmd}", check=False)

    def should_run_step(self, step: str) -> bool:
        """Check if a step should be run based on filters."""
        if self.only_steps and step not in self.only_steps:
            return False
        if step in self.skip_steps:
            return False
        return True

    def _step_git_push(self) -> None:
        """Push to git remote."""
        self.log_section("Step 1: Git Push")

        # Check for uncommitted changes
        result = subprocess.run(
            ["git", "diff-index", "--quiet", "HEAD", "--"], capture_output=True
        )

        if result.returncode != 0:
            self.log_warning("You have uncommitted changes")
            if not self.dry_run:
                if not Confirm.ask("Continue anyway?", default=False):
                    sys.exit(1)

        # Push to remote
        cmd = ["git", "push", self.config.git_remote, self.config.git_branch]
        if self.config.git_push_tags:
            cmd.append("--tags")

        self.run_command(
            cmd, f"Pushing to {self.config.git_remote}/{self.config.git_branch}..."
        )
        self.log_success("Git push complete")

    def _step_build(self) -> None:
        """Build the package."""
        self.log_section("Step 2: Build Package")

        # Run pre-build hooks
        self.run_hook(self.config.pre_build_hooks, "pre-build")

        # Clean dist directory
        if self.config.clean_dist:
            dist_dir = Path("dist")
            if dist_dir.exists():
                if not self.dry_run:
                    shutil.rmtree(dist_dir)
                self.log_info("Cleaned dist/ directory")

        # Build package
        build_cmd = self.config.build_command.split()
        self.run_command(build_cmd, "Building package...")

        # Run post-build hooks
        self.run_hook(self.config.post_build_hooks, "post-build")

        self.log_success("Package built successfully")

        # Show build artifacts
        if not self.dry_run:
            dist_dir = Path("dist")
            if dist_dir.exists():
                self.log_info("Build artifacts:")
                for file in dist_dir.iterdir():
                    console.print(f"[dim]  - {file.name}[/dim]")

    def _step_pypi_publish(self) -> None:
        """Publish to PyPI."""
        self.log_section("Step 3: Publish to PyPI")

        # Run pre-publish hooks
        self.run_hook(self.config.pre_publish_hooks, "pre-publish")

        # Get PyPI token
        env = os.environ.copy()
        token_var = self.config.pypi_token_env_var

        # Load from .env if not in environment
        if token_var not in env and "UV_PUBLISH_TOKEN" not in env:
            env_file = Path(".env")
            if env_file.exists():
                self.log_info("Loading credentials from .env")
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key == token_var:
                                env["UV_PUBLISH_TOKEN"] = val
                                break

        # Check for token
        if "UV_PUBLISH_TOKEN" not in env and token_var in env:
            env["UV_PUBLISH_TOKEN"] = env[token_var]

        if "UV_PUBLISH_TOKEN" not in env:
            self.log_warning(
                f"PyPI token not found (looking for {token_var} or UV_PUBLISH_TOKEN)"
            )
            if not self.dry_run:
                if not Confirm.ask("Continue anyway?", default=False):
                    sys.exit(1)

        # Publish
        package_name = self.config.pypi_package or self.config.project_name
        self.run_command(
            ["uv", "publish"],
            f"Publishing {package_name} {self.version} to PyPI...",
            env=env,
        )

        # Wait for PyPI to process
        if not self.dry_run and self.config.pypi_wait_after_publish > 0:
            self.log_info(
                f"Waiting {self.config.pypi_wait_after_publish}s for PyPI to process..."
            )
            time.sleep(self.config.pypi_wait_after_publish)

        # Run post-publish hooks
        self.run_hook(self.config.post_publish_hooks, "post-publish")

        self.log_success("Published to PyPI")
        self.log_info(
            f"View at: https://pypi.org/project/{package_name}/{self.version}/"
        )

    def _step_local_install(self) -> None:
        """Install package locally."""
        self.log_section("Step 4: Install Locally")

        package_name = self.config.pypi_package or self.config.project_name

        # Try install
        try:
            self.run_command(
                ["pip", "install", "--upgrade", f"{package_name}=={self.version}"],
                f"Installing {package_name}=={self.version}...",
            )
        except subprocess.CalledProcessError:
            self.log_warning("Install failed, trying with --force-reinstall...")
            self.run_command(
                [
                    "pip",
                    "install",
                    "--force-reinstall",
                    f"{package_name}=={self.version}",
                ],
                "Force reinstalling...",
            )

        # Verify installation
        if not self.dry_run:
            try:
                result = subprocess.run(
                    [
                        "python",
                        "-c",
                        f"import {package_name.replace('-', '_')}; print({package_name.replace('-', '_')}.__version__)",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                installed_version = result.stdout.strip()
                if installed_version == self.version:
                    self.log_success(
                        f"Verified: {package_name} {installed_version} is installed"
                    )
                else:
                    self.log_warning(
                        f"Installed version ({installed_version}) doesn't match expected ({self.version})"
                    )
            except Exception as e:
                self.log_warning(f"Could not verify installation: {e}")

    def _step_update_plugins(self) -> None:
        """Update plugins (Claude, Gemini, etc.)."""
        self.log_section("Step 5: Update Plugins")

        if not self.config.plugins:
            self.log_info("No plugins configured")
            return

        package_name = self.config.pypi_package or self.config.project_name

        for plugin_name, plugin_cmd in self.config.plugins.items():
            # Replace placeholders
            cmd = plugin_cmd.format(package=package_name, version=self.version)

            # Check if command exists
            cmd_parts = cmd.split()
            if shutil.which(cmd_parts[0]) is None:
                self.log_warning(f"{plugin_name} CLI not found, skipping")
                continue

            # Run update command
            try:
                self.run_command(
                    cmd_parts, f"Updating {plugin_name} plugin...", check=False
                )
                self.log_success(f"{plugin_name} plugin updated")
            except Exception as e:
                self.log_warning(f"{plugin_name} update failed: {e}")

    def deploy(self) -> None:
        """Run the full deployment process."""
        self.log_section(f"Deployment - {self.config.project_name} v{self.version}")

        if self.dry_run:
            self.log_warning("DRY-RUN MODE - No actual changes will be made")

        # Check we're in project root
        if not Path("pyproject.toml").exists():
            self.log_error("Must be run from project root (where pyproject.toml is)")
            sys.exit(1)

        # Run steps
        steps_to_run = [s for s in self.config.steps if self.should_run_step(s)]

        if not steps_to_run:
            self.log_warning("No steps to run")
            return

        self.log_info(f"Steps to run: {', '.join(steps_to_run)}")

        for step in steps_to_run:
            if step in self.step_handlers:
                try:
                    self.step_handlers[step]()
                except Exception as e:
                    self.log_error(f"Step '{step}' failed: {e}")
                    if not self.dry_run:
                        sys.exit(1)
            else:
                self.log_warning(f"Unknown step: {step}")

        # Summary
        self.log_section("Deployment Complete! 🎉")
        self.log_success("All deployment steps completed successfully!")
        console.print()


def create_deployment_config_template(output_path: Path) -> None:
    """Create a template deployment configuration file."""

    template = """# HtmlGraph Deployment Configuration
#
# This file configures the deployment process for your project.
# You can customize steps, hooks, and plugin updates.

[project]
name = "my-project"
pypi_package = "my-package"  # PyPI package name (if different from project name)

[deployment]
# Deployment steps (in order)
# Available steps: git-push, build, pypi-publish, local-install, update-plugins
steps = [
    "git-push",
    "build",
    "pypi-publish",
    "local-install",
    "update-plugins"
]

[deployment.git]
branch = "main"
remote = "origin"
push_tags = true

[deployment.build]
command = "uv build"
clean_dist = true

[deployment.pypi]
# Environment variable for PyPI token (reads from .env if not set)
token_env_var = "PyPI_API_TOKEN"  # or UV_PUBLISH_TOKEN
wait_after_publish = 10  # seconds to wait after publishing

[deployment.plugins]
# Plugin update commands (uses {package} and {version} placeholders)
# Uncomment and customize as needed:
# claude = "claude plugin update {package}"
# gemini = "gemini extensions update {package}"
# codex = "codex skills update {package}"

[deployment.hooks]
# Custom commands to run at various stages
# Commands can use {version} and {package} placeholders
pre_build = []
post_build = []
pre_publish = []
post_publish = []

# Example hooks:
# pre_build = ["python scripts/update_version.py {version}"]
# post_build = ["python scripts/validate_build.py"]
# post_publish = ["python scripts/notify_release.py {version}"]
"""

    output_path.write_text(template)
    console.print(
        f"[green]✅ Created deployment config template: {output_path}[/green]"
    )
    console.print()
    console.print("[bold cyan]Next steps:[/bold cyan]")
    console.print(
        "[dim]1. Edit htmlgraph-deploy.toml to customize your deployment[/dim]"
    )
    console.print("[dim]2. Run: htmlgraph deploy run[/dim]")
