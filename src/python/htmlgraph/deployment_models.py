"""
Pydantic Models for Deployment Configuration and Operations

These models provide validated, type-safe deployment configurations with:
- Semantic version validation
- Configuration schema validation
- Automatic field documentation
- JSON schema generation for tooling
"""

import re
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class DeploymentStep(str, Enum):
    """Available deployment steps."""

    GIT_PUSH = "git-push"
    BUILD = "build"
    PYPI_PUBLISH = "pypi-publish"
    LOCAL_INSTALL = "local-install"
    UPDATE_PLUGINS = "update-plugins"


class SemanticVersion(BaseModel):
    """Semantic version string (major.minor.patch)."""

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")
    prerelease: str | None = Field(
        None, description="Pre-release identifier (alpha, beta, rc)"
    )
    build: str | None = Field(None, description="Build metadata")

    @classmethod
    def from_string(cls, version_str: str) -> "SemanticVersion":
        """Parse semantic version from string.

        Examples:
            - "1.2.3"
            - "2.0.0-alpha.1"
            - "3.1.4-beta+build.123"
        """
        # SemVer regex pattern
        pattern = r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

        match = re.match(pattern, version_str)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    def to_string(self) -> str:
        """Convert to semantic version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __str__(self) -> str:
        """
        Convert version to string representation.

        Enables using str() and string formatting on SemanticVersion instances.

        Returns:
            str: Version string in semver format (e.g., "1.2.3", "2.0.0-beta.1")

        Example:
            >>> version = SemanticVersion(1, 2, 3)
            >>> str(version)
            '1.2.3'
            >>> print(f"Version: {version}")
            Version: 1.2.3
            >>> version_pre = SemanticVersion(2, 0, 0, prerelease="beta.1")
            >>> str(version_pre)
            '2.0.0-beta.1'
        """
        return self.to_string()

    def __lt__(self, other: "SemanticVersion") -> bool:
        """
        Compare versions for sorting.

        Enables using <, >, <=, >= operators and sorting SemanticVersion instances.
        Follows semantic versioning precedence rules:
        - Major, minor, patch compared numerically
        - Prerelease versions have lower precedence than release versions
        - Build metadata is ignored in comparisons

        Args:
            other: SemanticVersion to compare with

        Returns:
            bool: True if self is less than other

        Example:
            >>> v1 = SemanticVersion(1, 0, 0)
            >>> v2 = SemanticVersion(2, 0, 0)
            >>> v1 < v2
            True
            >>> v1_pre = SemanticVersion(1, 0, 0, prerelease="beta.1")
            >>> v1_pre < v1
            True
            >>> versions = [v2, v1_pre, v1]
            >>> sorted(versions)
            [SemanticVersion(1, 0, 0, prerelease='beta.1'), SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0)]
        """
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.patch != other.patch:
            return self.patch < other.patch

        # Prerelease versions have lower precedence
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False

        return False


class GitConfig(BaseModel):
    """Git configuration for deployment."""

    branch: str = Field(default="main", description="Git branch to push to")
    remote: str = Field(default="origin", description="Git remote name")
    push_tags: bool = Field(default=True, description="Push tags with commits")

    @field_validator("branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate git branch name."""
        if not v or not v.strip():
            raise ValueError("Branch name cannot be empty")
        # Basic validation - no spaces, special characters
        if re.search(r"[^\w\-/.]", v):
            raise ValueError(f"Invalid branch name: {v}")
        return v


class BuildConfig(BaseModel):
    """Build configuration for package."""

    command: str = Field(default="uv build", description="Build command to execute")
    clean_dist: bool = Field(default=True, description="Clean dist/ before building")
    verify_artifacts: bool = Field(
        default=True, description="Verify build artifacts exist"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate build command."""
        if not v or not v.strip():
            raise ValueError("Build command cannot be empty")
        return v.strip()


class PyPIConfig(BaseModel):
    """PyPI publishing configuration."""

    token_env_var: str = Field(
        default="PyPI_API_TOKEN",
        description="Environment variable containing PyPI API token",
    )
    wait_after_publish: int = Field(
        default=10,
        ge=0,
        le=60,
        description="Seconds to wait after publishing (for PyPI to process)",
    )
    verify_publication: bool = Field(
        default=True, description="Verify package appears on PyPI after publishing"
    )

    @field_validator("token_env_var")
    @classmethod
    def validate_token_var(cls, v: str) -> str:
        """Validate environment variable name."""
        if not v or not v.strip():
            raise ValueError("Token environment variable name cannot be empty")
        # Must be valid env var name
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", v):
            raise ValueError(f"Invalid environment variable name: {v}")
        return v


class PluginConfig(BaseModel):
    """Plugin update configuration."""

    name: str = Field(..., description="Plugin name")
    command: str = Field(
        ..., description="Update command with {package} and {version} placeholders"
    )
    required: bool = Field(
        default=False, description="Fail deployment if plugin update fails"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate plugin update command."""
        if not v or not v.strip():
            raise ValueError("Plugin command cannot be empty")

        # Check for required placeholders
        if "{package}" not in v and "{version}" not in v:
            raise ValueError(
                "Plugin command must contain {package} or {version} placeholder"
            )

        return v.strip()


class DeploymentHooks(BaseModel):
    """Custom deployment hooks."""

    pre_build: list[str] = Field(
        default_factory=list, description="Commands to run before build"
    )
    post_build: list[str] = Field(
        default_factory=list, description="Commands to run after build"
    )
    pre_publish: list[str] = Field(
        default_factory=list, description="Commands to run before publish"
    )
    post_publish: list[str] = Field(
        default_factory=list, description="Commands to run after publish"
    )

    @field_validator("pre_build", "post_build", "pre_publish", "post_publish")
    @classmethod
    def validate_hooks(cls, v: list[str]) -> list[str]:
        """Validate hook commands."""
        return [cmd.strip() for cmd in v if cmd.strip()]


class DeploymentConfig(BaseModel):
    """Complete deployment configuration with validation.

    Example:
        ```python
        config = DeploymentConfig(
            project_name="htmlgraph",
            pypi_package="htmlgraph",
            version="0.10.0",
            steps=[
                DeploymentStep.GIT_PUSH,
                DeploymentStep.BUILD,
                DeploymentStep.PYPI_PUBLISH
            ]
        )
        ```
    """

    # Project info
    project_name: str = Field(..., min_length=1, description="Project name")
    pypi_package: str | None = Field(
        None, description="PyPI package name (if different from project)"
    )
    version: str | None = Field(None, description="Version to deploy")

    # Deployment steps
    steps: list[DeploymentStep] = Field(
        default=[
            DeploymentStep.GIT_PUSH,
            DeploymentStep.BUILD,
            DeploymentStep.PYPI_PUBLISH,
            DeploymentStep.LOCAL_INSTALL,
            DeploymentStep.UPDATE_PLUGINS,
        ],
        description="Deployment steps to execute in order",
    )

    # Component configs
    git: GitConfig = Field(default_factory=GitConfig, description="Git configuration")
    build: BuildConfig = Field(
        default_factory=BuildConfig, description="Build configuration"
    )
    pypi: PyPIConfig = Field(
        default_factory=PyPIConfig, description="PyPI configuration"
    )

    # Plugins and hooks
    plugins: list[PluginConfig] = Field(
        default_factory=list, description="Plugin update configs"
    )
    hooks: DeploymentHooks = Field(
        default_factory=DeploymentHooks, description="Custom deployment hooks"
    )

    # Flags
    dry_run: bool = Field(
        default=False, description="Simulate deployment without executing"
    )
    skip_confirmations: bool = Field(
        default=False, description="Skip confirmation prompts"
    )

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, v: str) -> str:
        """Validate project name."""
        if not v or not v.strip():
            raise ValueError("Project name cannot be empty")

        # Basic validation - alphanumeric, hyphens, underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(f"Invalid project name: {v}")

        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str | None) -> str | None:
        """Validate semantic version string."""
        if v is None:
            return None

        # Validate it's a valid semantic version
        try:
            SemanticVersion.from_string(v)
        except ValueError as e:
            raise ValueError(f"Invalid version format: {e}")

        return v

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: list[DeploymentStep]) -> list[DeploymentStep]:
        """Validate deployment steps."""
        if not v:
            raise ValueError("Must specify at least one deployment step")

        # Check for duplicate steps
        if len(v) != len(set(v)):
            raise ValueError("Duplicate deployment steps found")

        return v

    @model_validator(mode="after")
    def validate_config_consistency(self) -> "DeploymentConfig":
        """Validate configuration consistency."""
        # If PyPI publish is enabled, ensure we have build step first
        if DeploymentStep.PYPI_PUBLISH in self.steps:
            if DeploymentStep.BUILD not in self.steps:
                raise ValueError("PyPI publish requires build step")

            # Build must come before publish
            build_idx = self.steps.index(DeploymentStep.BUILD)
            publish_idx = self.steps.index(DeploymentStep.PYPI_PUBLISH)
            if build_idx > publish_idx:
                raise ValueError("Build step must come before PyPI publish")

        # If local install is enabled, must have either build or publish
        if DeploymentStep.LOCAL_INSTALL in self.steps:
            if (
                DeploymentStep.BUILD not in self.steps
                and DeploymentStep.PYPI_PUBLISH not in self.steps
            ):
                raise ValueError("Local install requires build or PyPI publish step")

        return self

    @classmethod
    def from_toml(cls, config_path: Path) -> "DeploymentConfig":
        """Load configuration from TOML file.

        Args:
            config_path: Path to deployment config TOML file

        Returns:
            Validated DeploymentConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # fallback for Python < 3.11

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        # Extract sections
        project = data.get("project", {})
        deployment = data.get("deployment", {})

        # Parse plugins
        plugins = []
        for name, cmd in deployment.get("plugins", {}).items():
            plugins.append(PluginConfig(name=name, command=cmd))

        # Build config
        return cls(
            project_name=project.get("name", "my-project"),
            pypi_package=project.get("pypi_package"),
            version=project.get("version"),
            steps=[DeploymentStep(s) for s in deployment.get("steps", [])],
            git=GitConfig(**deployment.get("git", {})),
            build=BuildConfig(**deployment.get("build", {})),
            pypi=PyPIConfig(**deployment.get("pypi", {})),
            plugins=plugins,
            hooks=DeploymentHooks(**deployment.get("hooks", {})),
        )

    def to_toml_dict(self) -> dict[str, Any]:
        """Export configuration as TOML-compatible dict."""
        return {
            "project": {
                "name": self.project_name,
                "pypi_package": self.pypi_package,
                "version": self.version,
            },
            "deployment": {
                "steps": [step.value for step in self.steps],
                "git": self.git.model_dump(),
                "build": self.build.model_dump(),
                "pypi": self.pypi.model_dump(),
                "plugins": {p.name: p.command for p in self.plugins},
                "hooks": self.hooks.model_dump(),
            },
        }


class DeploymentResult(BaseModel):
    """Result of a deployment operation."""

    success: bool = Field(..., description="Whether deployment succeeded")
    version: str = Field(..., description="Version that was deployed")
    steps_completed: list[DeploymentStep] = Field(
        default_factory=list, description="Steps that completed"
    )
    steps_failed: list[DeploymentStep] = Field(
        default_factory=list, description="Steps that failed"
    )
    errors: list[str] = Field(default_factory=list, description="Error messages")
    duration_seconds: float = Field(
        default=0.0, ge=0, description="Total deployment duration"
    )

    @property
    def is_partial(self) -> bool:
        """Check if deployment was only partially successful."""
        return self.success and bool(self.steps_failed)

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate (0.0 to 1.0)."""
        total_steps = len(self.steps_completed) + len(self.steps_failed)
        if total_steps == 0:
            return 0.0
        return len(self.steps_completed) / total_steps
