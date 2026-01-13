"""Tests for htmlgraph bootstrap command."""

import json
from pathlib import Path

from htmlgraph.operations.bootstrap import (
    bootstrap_htmlgraph,
    check_already_initialized,
    create_bootstrap_structure,
    detect_project_type,
    get_next_steps,
    initialize_database,
)


class TestDetectProjectType:
    """Test project type detection."""

    def test_detects_python_with_pyproject_toml(self, tmp_path: Path) -> None:
        """Should detect Python project from pyproject.toml."""
        (tmp_path / "pyproject.toml").touch()
        assert detect_project_type(tmp_path) == "python"

    def test_detects_python_with_setup_py(self, tmp_path: Path) -> None:
        """Should detect Python project from setup.py."""
        (tmp_path / "setup.py").touch()
        assert detect_project_type(tmp_path) == "python"

    def test_detects_python_with_requirements_txt(self, tmp_path: Path) -> None:
        """Should detect Python project from requirements.txt."""
        (tmp_path / "requirements.txt").touch()
        assert detect_project_type(tmp_path) == "python"

    def test_detects_node_with_package_json(self, tmp_path: Path) -> None:
        """Should detect Node project from package.json."""
        (tmp_path / "package.json").touch()
        assert detect_project_type(tmp_path) == "node"

    def test_detects_multi_when_both_present(self, tmp_path: Path) -> None:
        """Should detect multi-language project."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "package.json").touch()
        assert detect_project_type(tmp_path) == "multi"

    def test_detects_unknown_when_no_markers(self, tmp_path: Path) -> None:
        """Should return unknown when no project markers found."""
        assert detect_project_type(tmp_path) == "unknown"


class TestCheckAlreadyInitialized:
    """Test initialization status check."""

    def test_returns_false_when_not_initialized(self, tmp_path: Path) -> None:
        """Should return False when .htmlgraph doesn't exist."""
        assert check_already_initialized(tmp_path) is False

    def test_returns_true_when_initialized(self, tmp_path: Path) -> None:
        """Should return True when .htmlgraph exists."""
        (tmp_path / ".htmlgraph").mkdir()
        assert check_already_initialized(tmp_path) is True


class TestCreateBootstrapStructure:
    """Test directory structure creation."""

    def test_creates_htmlgraph_directory(self, tmp_path: Path) -> None:
        """Should create .htmlgraph directory."""
        create_bootstrap_structure(tmp_path)
        assert (tmp_path / ".htmlgraph").exists()
        assert (tmp_path / ".htmlgraph").is_dir()

    def test_creates_subdirectories(self, tmp_path: Path) -> None:
        """Should create all required subdirectories."""
        create_bootstrap_structure(tmp_path)
        subdirs = ["sessions", "features", "spikes", "tracks", "events", "logs"]
        for subdir in subdirs:
            assert (tmp_path / ".htmlgraph" / subdir).exists()

    def test_creates_gitignore(self, tmp_path: Path) -> None:
        """Should create .gitignore file."""
        result = create_bootstrap_structure(tmp_path)
        gitignore = tmp_path / ".htmlgraph" / ".gitignore"
        assert gitignore.exists()
        assert str(gitignore) in result["files"]

    def test_creates_config_json(self, tmp_path: Path) -> None:
        """Should create config.json file."""
        result = create_bootstrap_structure(tmp_path)
        config_file = tmp_path / ".htmlgraph" / "config.json"
        assert config_file.exists()
        assert str(config_file) in result["files"]

        # Verify config content
        config_data = json.loads(config_file.read_text())
        assert config_data["bootstrapped"] is True
        assert "version" in config_data

    def test_returns_created_paths(self, tmp_path: Path) -> None:
        """Should return lists of created directories and files."""
        result = create_bootstrap_structure(tmp_path)
        assert "directories" in result
        assert "files" in result
        assert len(result["directories"]) > 0
        assert len(result["files"]) > 0

    def test_idempotent_creation(self, tmp_path: Path) -> None:
        """Should handle running twice without errors."""
        create_bootstrap_structure(tmp_path)
        result2 = create_bootstrap_structure(tmp_path)
        # Second run shouldn't create new files if they already exist
        assert len(result2["files"]) == 0  # Files already exist


class TestInitializeDatabase:
    """Test database initialization."""

    def test_creates_database_file(self, tmp_path: Path) -> None:
        """Should create htmlgraph.db file."""
        graph_dir = tmp_path / ".htmlgraph"
        graph_dir.mkdir()
        db_path = initialize_database(graph_dir)
        assert Path(db_path).exists()
        assert Path(db_path).name == "htmlgraph.db"

    def test_creates_database_with_schema(self, tmp_path: Path) -> None:
        """Should initialize database with all tables."""
        import sqlite3

        graph_dir = tmp_path / ".htmlgraph"
        graph_dir.mkdir()
        db_path = initialize_database(graph_dir)

        # Check tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Should have core tables
        assert "sessions" in tables
        assert "agent_events" in tables
        assert "features" in tables


class TestGetNextSteps:
    """Test next steps generation."""

    def test_includes_claude_install_when_not_available(self) -> None:
        """Should include Claude Code installation step."""
        steps = get_next_steps(
            project_type="python", has_claude=False, plugin_installed=False
        )
        assert any("Install Claude Code CLI" in step for step in steps)

    def test_includes_plugin_install_when_needed(self) -> None:
        """Should include plugin installation step."""
        steps = get_next_steps(
            project_type="python", has_claude=True, plugin_installed=False
        )
        assert any("claude plugin install" in step for step in steps)

    def test_skips_plugin_when_installed(self) -> None:
        """Should skip plugin installation when already installed."""
        steps = get_next_steps(
            project_type="python", has_claude=True, plugin_installed=True
        )
        # First step should be to use Claude Code
        assert "claude --dev" in steps[0]

    def test_includes_feature_tracking_step(self) -> None:
        """Should include feature tracking guidance."""
        steps = get_next_steps(
            project_type="python", has_claude=True, plugin_installed=True
        )
        assert any("htmlgraph feature create" in step for step in steps)

    def test_includes_status_check_step(self) -> None:
        """Should include status checking step."""
        steps = get_next_steps(
            project_type="python", has_claude=True, plugin_installed=True
        )
        assert any("htmlgraph status" in step for step in steps)

    def test_includes_serve_dashboard_step(self) -> None:
        """Should include dashboard serving step."""
        steps = get_next_steps(
            project_type="python", has_claude=True, plugin_installed=True
        )
        assert any("htmlgraph serve" in step for step in steps)


class TestBootstrapIntegration:
    """Integration tests for full bootstrap process."""

    def test_bootstrap_creates_complete_setup(self, tmp_path: Path) -> None:
        """Should create complete HtmlGraph setup."""
        from htmlgraph.cli.models import BootstrapConfig

        # Create a Python project marker
        (tmp_path / "pyproject.toml").touch()

        config = BootstrapConfig(project_path=str(tmp_path), no_plugins=True)

        # Mock input for "already initialized" check
        # (not needed for first run)
        result = bootstrap_htmlgraph(config)

        assert result["success"] is True
        assert result["project_type"] == "python"
        assert Path(result["graph_dir"]).exists()

        # Verify directory structure
        graph_dir = Path(result["graph_dir"])
        assert (graph_dir / "sessions").exists()
        assert (graph_dir / "features").exists()
        assert (graph_dir / "htmlgraph.db").exists()

    def test_bootstrap_detects_existing_installation(self, tmp_path: Path) -> None:
        """Should detect and handle existing .htmlgraph directory."""
        # Pre-create .htmlgraph
        (tmp_path / ".htmlgraph").mkdir()

        assert check_already_initialized(tmp_path) is True
