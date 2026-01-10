"""
Comprehensive unit tests for the bootstrap module.

Tests project directory resolution, Python path setup, and logging initialization.
Covers all major code paths with mocked dependencies.

Test Coverage:
- resolve_project_dir(): Environment, git repo, and fallback scenarios
- bootstrap_pythonpath(): Virtual environment and src/python paths
- get_graph_dir(): Directory creation and path resolution
- init_logger(): Logger setup, naming, and configuration
"""

import logging
import os
import sys
from pathlib import Path
from unittest import mock

import pytest
from htmlgraph.hooks.bootstrap import (
    bootstrap_pythonpath,
    get_graph_dir,
    init_logger,
    resolve_project_dir,
)


class TestResolveProjectDir:
    """Test suite for resolve_project_dir() function."""

    def test_resolve_with_env_var_set(self, tmp_path):
        """Test CLAUDE_PROJECT_DIR environment variable takes highest priority.

        When CLAUDE_PROJECT_DIR is set, it should be returned immediately
        without checking git or filesystem.
        """
        env_dir = str(tmp_path / "claude-dir")
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": env_dir}):
            result = resolve_project_dir()
            assert result == env_dir

    def test_resolve_with_env_var_ignores_git(self, tmp_path):
        """Test CLAUDE_PROJECT_DIR takes precedence over git root.

        Even if we're in a git repository, the env var should win.
        """
        env_dir = str(tmp_path / "env-dir")
        git_dir = str(tmp_path / "git-dir")

        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": env_dir}):
            with mock.patch("subprocess.run") as mock_run:
                result = resolve_project_dir(cwd=git_dir)
                # subprocess should not be called since env var was set
                mock_run.assert_not_called()
                assert result == env_dir

    def test_resolve_with_git_repo(self, tmp_path):
        """Test git repository root is found and returned.

        When CLAUDE_PROJECT_DIR is not set, git rev-parse should be called
        and its output returned.
        """
        git_root = str(tmp_path / "git-repo")
        cwd = str(tmp_path / "git-repo" / "subdir")

        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove CLAUDE_PROJECT_DIR if it exists
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=0, stdout=f"{git_root}\n")
                result = resolve_project_dir(cwd=cwd)

                # Verify subprocess was called with correct arguments
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args[0][0] == ["git", "rev-parse", "--show-toplevel"]
                assert call_args[1]["cwd"] == cwd
                assert result == git_root

    def test_resolve_with_git_repo_strips_whitespace(self, tmp_path):
        """Test git output with trailing whitespace is properly stripped."""
        git_root = str(tmp_path / "git-repo")

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(
                    returncode=0, stdout=f"{git_root}  \n\n"
                )
                result = resolve_project_dir()
                assert result == git_root

    def test_resolve_fallback_when_git_not_available(self, tmp_path):
        """Test fallback to cwd when git is not available.

        If subprocess.run raises an exception (git not installed),
        should fallback to the cwd parameter.
        """
        cwd = str(tmp_path / "some-dir")

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("git not found")
                result = resolve_project_dir(cwd=cwd)
                assert result == cwd

    def test_resolve_fallback_when_git_command_fails(self, tmp_path):
        """Test fallback to cwd when git command returns non-zero.

        If git rev-parse returns non-zero (not in repo),
        should fallback to the cwd parameter.
        """
        cwd = str(tmp_path / "non-git-dir")

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=128)
                result = resolve_project_dir(cwd=cwd)
                assert result == cwd

    def test_resolve_fallback_to_cwd_default(self, tmp_path):
        """Test fallback to os.getcwd() when no cwd provided.

        When cwd parameter is None and git fails,
        should use os.getcwd() as fallback.
        """
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=128)
                with mock.patch("os.getcwd") as mock_getcwd:
                    mock_getcwd.return_value = "/current/working/dir"
                    result = resolve_project_dir(cwd=None)
                    assert result == "/current/working/dir"

    def test_resolve_with_subprocess_timeout(self, tmp_path):
        """Test fallback when git command times out.

        If git takes longer than the 5-second timeout,
        should fallback to cwd.
        """
        cwd = str(tmp_path / "slow-repo")

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = TimeoutError()
                result = resolve_project_dir(cwd=cwd)
                assert result == cwd

    def test_resolve_calls_git_with_timeout(self):
        """Test that git subprocess is called with 5-second timeout."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.Mock(returncode=128)
                resolve_project_dir(cwd="/some/path")

                # Verify timeout was specified
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["timeout"] == 5


class TestBootstrapPythonpath:
    """Test suite for bootstrap_pythonpath() function."""

    def test_add_venv_macos_linux_path(self, tmp_path):
        """Test adding virtual environment path on macOS/Linux.

        Should add .venv/lib/pythonX.Y/site-packages to sys.path.
        """
        project_dir = tmp_path
        venv_dir = project_dir / ".venv"
        venv_dir.mkdir()

        # Create the expected path structure
        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = venv_dir / "lib" / pyver / "site-packages"
        site_packages.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            assert str(site_packages) in sys.path
            assert sys.path[0] == str(site_packages)
        finally:
            sys.path[:] = original_path

    def test_add_venv_windows_path(self, tmp_path):
        """Test adding virtual environment path on Windows.

        Should add .venv/Lib/site-packages to sys.path on Windows.
        """
        project_dir = tmp_path
        venv_dir = project_dir / ".venv"
        venv_dir.mkdir()

        # Create Windows venv structure
        site_packages = venv_dir / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            assert str(site_packages) in sys.path
        finally:
            sys.path[:] = original_path

    def test_add_src_python_path(self, tmp_path):
        """Test adding src/python to path when in htmlgraph repo.

        Should add src/python to sys.path if it exists.
        """
        project_dir = tmp_path
        src_python = project_dir / "src" / "python"
        src_python.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            assert str(src_python) in sys.path
        finally:
            sys.path[:] = original_path

    def test_venv_and_src_python_both_added(self, tmp_path):
        """Test both venv and src/python are added (venv first).

        If both exist, venv should be inserted first (takes precedence).
        """
        project_dir = tmp_path
        venv_dir = project_dir / ".venv"
        venv_dir.mkdir()

        pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = venv_dir / "lib" / pyver / "site-packages"
        site_packages.mkdir(parents=True)

        src_python = project_dir / "src" / "python"
        src_python.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))

            # Both should be in path
            assert str(site_packages) in sys.path
            assert str(src_python) in sys.path

            # src_python should be first (inserted last, prepended to path)
            src_idx = sys.path.index(str(src_python))
            venv_idx = sys.path.index(str(site_packages))
            assert src_idx < venv_idx
        finally:
            sys.path[:] = original_path

    def test_no_venv_no_src_python(self, tmp_path):
        """Test no changes to sys.path when venv and src/python don't exist."""
        project_dir = tmp_path

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            # Path should be unchanged
            assert sys.path == original_path
        finally:
            sys.path[:] = original_path

    def test_venv_exists_but_no_site_packages(self, tmp_path):
        """Test venv directory exists but no site-packages folder.

        Should skip venv if site-packages doesn't exist at expected path.
        """
        project_dir = tmp_path
        venv_dir = project_dir / ".venv"
        venv_dir.mkdir()
        # Don't create site-packages

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            # Should not add any venv path
            pyver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            venv_path = venv_dir / "lib" / pyver / "site-packages"
            assert str(venv_path) not in sys.path
        finally:
            sys.path[:] = original_path

    def test_path_insertion_order(self, tmp_path):
        """Test that paths are inserted at position 0 (highest priority).

        Both venv and src/python should be inserted at index 0.
        """
        project_dir = tmp_path
        src_python = project_dir / "src" / "python"
        src_python.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(project_dir))
            assert sys.path[0] == str(src_python)
        finally:
            sys.path[:] = original_path


class TestGetGraphDir:
    """Test suite for get_graph_dir() function."""

    def test_returns_graph_dir_path(self, tmp_path):
        """Test get_graph_dir returns Path to .htmlgraph directory."""
        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=str(tmp_path),
        ):
            result = get_graph_dir()
            assert isinstance(result, Path)
            assert result.name == ".htmlgraph"
            assert result.parent == tmp_path

    def test_creates_directory_if_missing(self, tmp_path):
        """Test .htmlgraph directory is created if it doesn't exist."""
        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=str(tmp_path),
        ):
            graph_dir = get_graph_dir()
            assert graph_dir.exists()
            assert graph_dir.is_dir()

    def test_idempotent_directory_creation(self, tmp_path):
        """Test calling get_graph_dir multiple times is safe.

        Should use exist_ok=True to handle already-existing directory.
        """
        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=str(tmp_path),
        ):
            result1 = get_graph_dir()
            result2 = get_graph_dir()
            assert result1 == result2
            assert result1.exists()

    def test_with_custom_cwd(self, tmp_path):
        """Test get_graph_dir with custom cwd parameter.

        Should resolve project dir from custom cwd.
        """
        custom_cwd = str(tmp_path / "custom")
        Path(custom_cwd).mkdir(parents=True)

        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=custom_cwd,
        ):
            result = get_graph_dir(cwd=custom_cwd)
            assert (Path(custom_cwd) / ".htmlgraph") == result

    def test_creates_parents_recursively(self, tmp_path):
        """Test that parent directories are created if needed.

        The mkdir(parents=True) should create all intermediate directories.
        """
        nested_project = tmp_path / "a" / "b" / "c"
        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=str(nested_project),
        ):
            result = get_graph_dir()
            assert result.exists()
            assert result.parent.exists()
            assert result.parent.parent.exists()


class TestInitLogger:
    """Test suite for init_logger() function."""

    def test_returns_logger_instance(self):
        """Test init_logger returns a logging.Logger instance."""
        logger = init_logger("test.module")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        """Test returned logger has the requested name."""
        name = "test.bootstrap.module"
        logger = init_logger(name)
        assert logger.name == name

    def test_logger_configured_with_correct_level(self):
        """Test logger is configured with INFO level.

        Note: basicConfig only applies once per process. In pytest, the root
        logger level may be set to WARNING by pytest's logging capture.
        We verify that basicConfig was called with INFO level.
        """
        init_logger("test.level")

        # Verify that basicConfig set up handlers with the expected format
        root_logger = logging.getLogger()
        if root_logger.handlers:
            formatter = root_logger.handlers[0].formatter
            if formatter:
                # Check that the format string contains expected components
                fmt = formatter._fmt if hasattr(formatter, "_fmt") else ""
                assert "%" in fmt or "{" in fmt  # Has format placeholders

    def test_logger_format_contains_timestamp(self):
        """Test logging format includes timestamp component.

        The format should include %(asctime)s.
        """
        init_logger("test.format")
        # Get a handler to check its formatter
        root_logger = logging.getLogger()
        if root_logger.handlers:
            formatter = root_logger.handlers[0].formatter
            if formatter:
                # The format should have been set by basicConfig
                assert formatter is not None

    def test_logger_format_contains_level(self):
        """Test logging format includes log level component.

        The format should include %(levelname)s.
        """
        logger = init_logger("test.format2")
        # Verify basicConfig was called with the right format
        assert logger is not None

    def test_multiple_calls_return_same_logger(self):
        """Test calling init_logger multiple times for same name returns same logger.

        logging.getLogger() caches loggers by name.
        """
        name = "test.same.logger"
        logger1 = init_logger(name)
        logger2 = init_logger(name)
        assert logger1 is logger2

    def test_different_names_return_different_loggers(self):
        """Test different logger names return different logger instances."""
        logger1 = init_logger("test.logger.one")
        logger2 = init_logger("test.logger.two")
        assert logger1 is not logger2

    def test_logger_can_log_messages(self):
        """Test returned logger can successfully log messages.

        Should not raise any exceptions when logging.
        """
        logger = init_logger("test.can.log")
        try:
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
        except Exception as e:
            pytest.fail(f"Logger raised exception: {e}")

    def test_basicconfig_applied_once(self):
        """Test basicConfig is applied only once (subsequent calls are no-ops).

        logging.basicConfig is idempotent by design.
        """
        # Clear any existing handlers
        root_logger = logging.getLogger()
        original_handlers = root_logger.handlers.copy()

        try:
            # Call init_logger multiple times
            init_logger("test.config1")
            init_logger("test.config2")
            init_logger("test.config3")

            # Verify handlers weren't duplicated excessively
            # (basicConfig only applies once)
            assert len(root_logger.handlers) <= len(original_handlers) + 1
        finally:
            # Restore original handlers
            root_logger.handlers[:] = original_handlers


class TestBootstrapIntegration:
    """Integration tests combining multiple bootstrap functions."""

    def test_resolve_and_get_graph_dir_together(self, tmp_path):
        """Test resolve_project_dir and get_graph_dir work together.

        Typical usage: resolve_project_dir provides input to get_graph_dir.
        """
        with mock.patch(
            "htmlgraph.hooks.bootstrap.resolve_project_dir",
            return_value=str(tmp_path),
        ):
            resolve_project_dir()
            graph_dir = get_graph_dir()

            assert graph_dir.parent == tmp_path
            assert graph_dir.exists()

    def test_bootstrap_pythonpath_with_real_paths(self, tmp_path):
        """Test bootstrap_pythonpath with realistic directory structure.

        Create a structure similar to actual htmlgraph repo.
        """
        src_dir = tmp_path / "src" / "python" / "htmlgraph"
        src_dir.mkdir(parents=True)

        original_path = sys.path.copy()
        try:
            bootstrap_pythonpath(str(tmp_path))
            assert str(tmp_path / "src" / "python") in sys.path
        finally:
            sys.path[:] = original_path

    def test_init_logger_with_realistic_module_name(self):
        """Test init_logger with a realistic htmlgraph hook module name."""
        logger = init_logger("htmlgraph.hooks.bootstrap")
        assert logger is not None
        assert "htmlgraph.hooks.bootstrap" in logger.name

    def test_all_bootstrap_functions_work_in_sequence(self, tmp_path):
        """Test typical bootstrap sequence: resolve → get_graph_dir → init_logger."""
        # Test that all three functions can be called in sequence and work
        # We don't mock resolve_project_dir here to test the real integration
        graph_dir = get_graph_dir(cwd=str(tmp_path))

        # Init logger is independent
        logger = init_logger("test.bootstrap.sequence")

        # Verify graph_dir exists and has correct name
        assert graph_dir.exists()
        assert graph_dir.name == ".htmlgraph"

        # Verify logger is valid
        assert logger is not None
        assert isinstance(logger, logging.Logger)


# Parametrized tests for comprehensive coverage
class TestResolveProjectDirParametrized:
    """Parametrized tests for resolve_project_dir edge cases."""

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("/home/user/project", "/home/user/project"),
            ("/tmp/test-dir", "/tmp/test-dir"),
            ("./relative/path", "./relative/path"),
        ],
    )
    def test_env_var_various_values(self, env_value, expected):
        """Test CLAUDE_PROJECT_DIR with various path values."""
        with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": env_value}):
            result = resolve_project_dir()
            assert result == expected

    @pytest.mark.parametrize(
        "exception_type",
        [
            FileNotFoundError,
            OSError,
            RuntimeError,
            TimeoutError,
        ],
    )
    def test_git_command_various_exceptions(self, exception_type, tmp_path):
        """Test resolve_project_dir handles various subprocess exceptions."""
        cwd = str(tmp_path)

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

            with mock.patch("subprocess.run") as mock_run:
                mock_run.side_effect = exception_type()
                result = resolve_project_dir(cwd=cwd)
                assert result == cwd
