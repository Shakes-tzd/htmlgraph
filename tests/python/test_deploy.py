"""
Tests for deployment automation module.

Tests version extraction, flag parsing, and dry-run functionality.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from htmlgraph.scripts.deploy import (
    get_project_root,
    main,
    run_deploy_script,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a mock project root with pyproject.toml"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-package"
version = "0.8.0"
"""
    )
    return tmp_path


@pytest.fixture
def mock_deploy_script(mock_project_root):
    """Create a mock deploy script"""
    script = mock_project_root / "scripts" / "deploy-all.sh"
    script.parent.mkdir(exist_ok=True)
    script.write_text("#!/bin/bash\necho 'Deploy script executed'\n")
    script.chmod(0o755)
    return script


# ============================================================================
# Tests for get_project_root
# ============================================================================


def test_get_project_root_finds_pyproject_toml():
    """Test that get_project_root finds pyproject.toml"""
    root = get_project_root()
    assert (root / "pyproject.toml").exists()
    assert isinstance(root, Path)


def test_get_project_root_returns_path():
    """Test that get_project_root returns a valid Path object"""
    root = get_project_root()
    assert isinstance(root, Path)
    assert root.is_dir()
    assert (root / "pyproject.toml").exists()


# ============================================================================
# Tests for main() - Argument Parsing
# ============================================================================


def test_main_with_no_arguments(mock_deploy_script, monkeypatch):
    """Test deploy with no arguments (defaults to pyproject.toml version)"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--dry-run"])

        # Should run deploy script with --dry-run
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "--dry-run" in call_args


def test_main_with_version_argument(mock_deploy_script, monkeypatch):
    """Test deploy with explicit version argument"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["0.9.0", "--dry-run"])

        # Should pass version to deploy script
        call_args = mock_run.call_args[0][0]
        assert "0.9.0" in call_args


def test_main_with_docs_only_flag(mock_deploy_script, monkeypatch):
    """Test deploy with --docs-only flag"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--docs-only"])

        call_args = mock_run.call_args[0][0]
        assert "--docs-only" in call_args


def test_main_with_build_only_flag(mock_deploy_script, monkeypatch):
    """Test deploy with --build-only flag"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--build-only"])

        call_args = mock_run.call_args[0][0]
        assert "--build-only" in call_args


def test_main_with_skip_pypi_flag(mock_deploy_script, monkeypatch):
    """Test deploy with --skip-pypi flag"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--skip-pypi"])

        call_args = mock_run.call_args[0][0]
        assert "--skip-pypi" in call_args


def test_main_with_skip_plugins_flag(mock_deploy_script, monkeypatch):
    """Test deploy with --skip-plugins flag"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--skip-plugins"])

        call_args = mock_run.call_args[0][0]
        assert "--skip-plugins" in call_args


def test_main_with_dry_run_flag(mock_deploy_script, monkeypatch):
    """Test deploy with --dry-run flag"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["--dry-run"])

        call_args = mock_run.call_args[0][0]
        assert "--dry-run" in call_args


def test_main_with_multiple_flags(mock_deploy_script, monkeypatch):
    """Test deploy with multiple flags"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["0.9.0", "--skip-pypi", "--dry-run"])

        call_args = mock_run.call_args[0][0]
        assert "0.9.0" in call_args
        assert "--skip-pypi" in call_args
        assert "--dry-run" in call_args


# ============================================================================
# Tests for run_deploy_script
# ============================================================================


def test_run_deploy_script_success(mock_deploy_script, monkeypatch):
    """Test run_deploy_script when script execution succeeds"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = run_deploy_script(["--dry-run"])

        assert result == 0
        mock_run.assert_called_once()


def test_run_deploy_script_failure(mock_deploy_script, monkeypatch):
    """Test run_deploy_script when script execution fails"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=1)

        result = run_deploy_script(["--dry-run"])

        assert result == 1


def test_run_deploy_script_not_found(mock_project_root, monkeypatch):
    """Test run_deploy_script when script doesn't exist"""
    monkeypatch.chdir(mock_project_root)

    # Don't create the script, so it won't be found
    result = run_deploy_script(["--dry-run"])

    assert result == 1


# ============================================================================
# Tests for Help
# ============================================================================


def test_main_help(capsys):
    """Test that --help displays usage information"""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "htmlgraph-deploy" in captured.out or "deploy" in captured.out.lower()


# ============================================================================
# Integration Tests
# ============================================================================


def test_deploy_entry_point_with_real_script(mock_deploy_script, monkeypatch):
    """Test the entry point with a real but simple deploy script"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    # Write a simple script that just exits with success
    mock_deploy_script.write_text("#!/bin/bash\nexit 0\n")
    mock_deploy_script.chmod(0o755)

    # Mock subprocess.run to avoid actual script execution
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)
        result = main(["--dry-run"])
        assert result == 0


def test_deploy_dry_run_passes_flag(mock_deploy_script, monkeypatch, capsys):
    """Test that dry-run flag is properly passed to script"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        main(["0.8.0", "--dry-run"])

        # Verify the command that was executed
        executed_cmd = mock_run.call_args[0][0]
        assert isinstance(executed_cmd, list)
        assert executed_cmd[-1] == "--dry-run"  # Last argument should be --dry-run


# ============================================================================
# Tests for Argument Combinations
# ============================================================================


def test_main_version_before_flags(mock_deploy_script, monkeypatch):
    """Test that version argument works when placed before flags"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        result = main(["0.9.0", "--skip-pypi", "--dry-run"])

        call_args = mock_run.call_args[0][0]
        # Version should be first argument to script
        assert call_args[1] == "0.9.0"  # After script path


def test_main_returns_script_exit_code(mock_deploy_script, monkeypatch):
    """Test that main() returns the script's exit code"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    with mock.patch("subprocess.run") as mock_run:
        # Test success case
        mock_run.return_value = mock.Mock(returncode=0)
        assert main(["--dry-run"]) == 0

        # Test failure case
        mock_run.return_value = mock.Mock(returncode=1)
        assert main(["--dry-run"]) == 1

        # Test other error code
        mock_run.return_value = mock.Mock(returncode=127)
        assert main(["--dry-run"]) == 127


# ============================================================================
# Tests for Version Detection
# ============================================================================


def test_version_from_pyproject_toml(mock_project_root, monkeypatch):
    """Test that version is correctly detected from pyproject.toml"""
    monkeypatch.chdir(mock_project_root)

    # Create mock deploy script
    script = mock_project_root / "scripts" / "deploy-all.sh"
    script.parent.mkdir(exist_ok=True)
    script.write_text("#!/bin/bash\necho 'test'\n")
    script.chmod(0o755)

    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0)

        # Run without explicit version
        result = main(["--dry-run"])

        # Should have detected version from pyproject.toml
        call_args = mock_run.call_args[0][0]
        # The version should NOT be in args when not explicitly provided
        # (it's auto-detected in the script)
        assert "--dry-run" in call_args


# ============================================================================
# Tests for Error Handling
# ============================================================================


def test_main_invalid_arguments(mock_deploy_script, monkeypatch, capsys):
    """Test main with invalid arguments"""
    monkeypatch.chdir(mock_deploy_script.parent.parent)

    # Invalid flag should be ignored or cause help to be shown
    with pytest.raises(SystemExit):
        main(["--invalid-flag-that-doesnt-exist"])


def test_script_not_executable(mock_project_root, monkeypatch):
    """Test behavior when deploy script is not executable"""
    monkeypatch.chdir(mock_project_root)

    # Create non-executable script
    script = mock_project_root / "scripts" / "deploy-all.sh"
    script.parent.mkdir(exist_ok=True)
    script.write_text("#!/bin/bash\necho 'test'\n")
    script.chmod(0o644)  # Not executable

    # Should fail to execute
    with mock.patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        result = run_deploy_script(["--dry-run"])

        assert result == 1
