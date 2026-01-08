"""
Unit tests for RepoHash - Repository hashing and git awareness.

Tests cover:
- Stable hash computation (path + remote + inode)
- Hash independence from branch changes
- Git information extraction (branch, commit, dirty state)
- Monorepo detection and project identification
- Non-git directory handling
- Error handling and edge cases
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from htmlgraph.repo_hash import (
    RepoHash,
    compute_hash_inputs,
    get_current_branch,
    get_current_commit,
    get_git_remote,
    get_inode,
    get_last_commit_date,
    is_git_dirty,
)


class TestRepoHashInitialization:
    """Test RepoHash initialization."""

    def test_init_with_default_cwd(self, tmp_path, monkeypatch):
        """Test initialization with current directory."""
        monkeypatch.chdir(tmp_path)
        repo = RepoHash()

        assert repo.repo_path == tmp_path.resolve()

    def test_init_with_explicit_path(self, tmp_path):
        """Test initialization with explicit path."""
        repo = RepoHash(tmp_path)

        assert repo.repo_path == tmp_path.resolve()

    def test_init_with_nonexistent_path(self, tmp_path):
        """Test initialization with nonexistent path raises error."""
        nonexistent = tmp_path / "does" / "not" / "exist"

        with pytest.raises(OSError):
            RepoHash(nonexistent)

    def test_init_resolves_relative_paths(self, tmp_path, monkeypatch):
        """Test that relative paths are resolved to absolute."""
        monkeypatch.chdir(tmp_path)
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        repo = RepoHash(Path("subdir"))

        assert repo.repo_path == subdir.resolve()
        assert repo.repo_path.is_absolute()


class TestComputeRepoHash:
    """Test stable repository hash computation."""

    def test_compute_repo_hash_format(self, tmp_path):
        """Test that hash has correct format."""
        repo = RepoHash(tmp_path)
        hash_value = repo.compute_repo_hash()

        # Format: "repo-{12_hex_chars}"
        assert hash_value.startswith("repo-")
        assert len(hash_value) == 17  # "repo-" (5) + 12 hex chars
        assert all(c in "0123456789abcdef" for c in hash_value[5:])

    def test_compute_repo_hash_stable(self, tmp_path):
        """Test that same repo produces same hash."""
        repo = RepoHash(tmp_path)
        hash1 = repo.compute_repo_hash()
        hash2 = repo.compute_repo_hash()

        assert hash1 == hash2

    def test_compute_repo_hash_caching(self, tmp_path):
        """Test that hash is cached."""
        repo = RepoHash(tmp_path)
        repo.compute_repo_hash()

        # Modify cache to verify it's used
        repo._repo_hash_cache = "cached-value"
        hash2 = repo.compute_repo_hash()

        assert hash2 == "cached-value"

    def test_different_paths_different_hashes(self, tmp_path):
        """Test that different paths produce different hashes."""
        path1 = tmp_path / "path1"
        path2 = tmp_path / "path2"
        path1.mkdir()
        path2.mkdir()

        repo1 = RepoHash(path1)
        repo2 = RepoHash(path2)

        hash1 = repo1.compute_repo_hash()
        hash2 = repo2.compute_repo_hash()

        assert hash1 != hash2

    @patch("htmlgraph.repo_hash.get_git_remote")
    @patch("htmlgraph.repo_hash.get_inode")
    def test_hash_independent_of_branch(self, mock_inode, mock_remote, tmp_path):
        """Test that branch changes don't affect hash."""
        # Remote and inode are stable, so hash should be stable
        mock_remote.return_value = "https://github.com/user/repo.git"
        mock_inode.return_value = 12345

        repo = RepoHash(tmp_path)
        hash1 = repo.compute_repo_hash()

        # "Change branch" by clearing cache
        repo._repo_hash_cache = None
        hash2 = repo.compute_repo_hash()

        assert hash1 == hash2


class TestComputeHashInputs:
    """Test hash input combination."""

    def test_compute_hash_inputs_deterministic(self):
        """Test that same inputs produce same output."""
        path = "/Users/user/repo"
        remote = "https://github.com/user/repo.git"
        inode = 12345

        result1 = compute_hash_inputs(path, remote, inode)
        result2 = compute_hash_inputs(path, remote, inode)

        assert result1 == result2

    def test_compute_hash_inputs_with_none_remote(self):
        """Test hash input with no remote."""
        path = "/Users/user/repo"
        result = compute_hash_inputs(path, None, 12345)

        assert "remote:none" in result
        assert path in result
        assert "12345" in result

    def test_compute_hash_inputs_contains_all_parts(self):
        """Test that all inputs are represented."""
        path = "/path"
        remote = "https://example.com"
        inode = 999

        result = compute_hash_inputs(path, remote, inode)

        assert "path:" in result
        assert "remote:" in result
        assert "inode:" in result
        assert "|" in result  # Separator


class TestGetGitRemote:
    """Test git remote retrieval."""

    @patch("subprocess.run")
    def test_get_git_remote_success(self, mock_run, tmp_path):
        """Test successful remote retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo.git\n",
        )

        result = get_git_remote(tmp_path)

        assert result == "https://github.com/user/repo.git"

    @patch("subprocess.run")
    def test_get_git_remote_not_git_repo(self, mock_run, tmp_path):
        """Test non-git directory returns None."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_git_remote(tmp_path)

        assert result is None

    @patch("subprocess.run")
    def test_get_git_remote_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_git_remote(tmp_path)

        assert result is None

    @patch("subprocess.run")
    def test_get_git_remote_strips_whitespace(self, mock_run, tmp_path):
        """Test that whitespace is stripped."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  https://github.com/user/repo.git  \n",
        )

        result = get_git_remote(tmp_path)

        assert result == "https://github.com/user/repo.git"


class TestGetCurrentBranch:
    """Test current branch retrieval."""

    @patch("subprocess.run")
    def test_get_current_branch_success(self, mock_run, tmp_path):
        """Test successful branch retrieval."""
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")

        result = get_current_branch(tmp_path)

        assert result == "main"

    @patch("subprocess.run")
    def test_get_current_branch_not_git_repo(self, mock_run, tmp_path):
        """Test non-git directory returns None."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_current_branch(tmp_path)

        assert result is None

    @patch("subprocess.run")
    def test_get_current_branch_detached_head(self, mock_run, tmp_path):
        """Test detached HEAD state."""
        mock_run.return_value = MagicMock(returncode=0, stdout="HEAD\n")

        result = get_current_branch(tmp_path)

        assert result == "HEAD"

    @patch("subprocess.run")
    def test_get_current_branch_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_current_branch(tmp_path)

        assert result is None


class TestGetCurrentCommit:
    """Test current commit SHA retrieval."""

    @patch("subprocess.run")
    def test_get_current_commit_success(self, mock_run, tmp_path):
        """Test successful commit retrieval."""
        mock_run.return_value = MagicMock(returncode=0, stdout="d78e458\n")

        result = get_current_commit(tmp_path)

        assert result == "d78e458"

    @patch("subprocess.run")
    def test_get_current_commit_short_format(self, mock_run, tmp_path):
        """Test that commit is short format (7 chars)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234\n")

        result = get_current_commit(tmp_path)

        assert len(result) == 7

    @patch("subprocess.run")
    def test_get_current_commit_not_git_repo(self, mock_run, tmp_path):
        """Test non-git directory returns None."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_current_commit(tmp_path)

        assert result is None

    @patch("subprocess.run")
    def test_get_current_commit_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_current_commit(tmp_path)

        assert result is None


class TestIsGitDirty:
    """Test git dirty state detection."""

    @patch("subprocess.run")
    def test_is_git_dirty_clean_repo(self, mock_run, tmp_path):
        """Test clean repository."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = is_git_dirty(tmp_path)

        assert result is False

    @patch("subprocess.run")
    def test_is_git_dirty_with_changes(self, mock_run, tmp_path):
        """Test repository with uncommitted changes."""
        mock_run.return_value = MagicMock(returncode=0, stdout=" M src/file.py\n")

        result = is_git_dirty(tmp_path)

        assert result is True

    @patch("subprocess.run")
    def test_is_git_dirty_not_git_repo(self, mock_run, tmp_path):
        """Test non-git directory returns False."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = is_git_dirty(tmp_path)

        assert result is False

    @patch("subprocess.run")
    def test_is_git_dirty_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = is_git_dirty(tmp_path)

        assert result is False


class TestGetLastCommitDate:
    """Test last commit date retrieval."""

    @patch("subprocess.run")
    def test_get_last_commit_date_success(self, mock_run, tmp_path):
        """Test successful commit date retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="2026-01-08 12:34:56 +0000\n"
        )

        result = get_last_commit_date(tmp_path)

        assert result is not None
        assert "2026-01-08" in result
        assert result.endswith("Z")

    @patch("subprocess.run")
    def test_get_last_commit_date_iso_format(self, mock_run, tmp_path):
        """Test that result is ISO 8601 format."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="2026-01-08 12:34:56 +0000\n"
        )

        result = get_last_commit_date(tmp_path)

        assert result is not None
        assert "T" in result  # ISO format has T
        assert result.endswith("Z")  # UTC marker

    @patch("subprocess.run")
    def test_get_last_commit_date_not_git_repo(self, mock_run, tmp_path):
        """Test non-git directory returns None."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_last_commit_date(tmp_path)

        assert result is None

    @patch("subprocess.run")
    def test_get_last_commit_date_timeout(self, mock_run, tmp_path):
        """Test timeout handling."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("git", 5)

        result = get_last_commit_date(tmp_path)

        assert result is None


class TestGetInode:
    """Test inode retrieval."""

    def test_get_inode_success(self, tmp_path):
        """Test successful inode retrieval."""
        inode = get_inode(tmp_path)

        assert isinstance(inode, int)
        assert inode > 0

    def test_get_inode_nonexistent_path(self, tmp_path):
        """Test inode retrieval for nonexistent path raises error."""
        nonexistent = tmp_path / "does" / "not" / "exist"

        with pytest.raises(OSError):
            get_inode(nonexistent)

    def test_get_inode_different_paths_different_values(self, tmp_path):
        """Test that different paths have different inodes."""
        path1 = tmp_path / "path1"
        path2 = tmp_path / "path2"
        path1.mkdir()
        path2.mkdir()

        inode1 = get_inode(path1)
        inode2 = get_inode(path2)

        assert inode1 != inode2

    def test_get_inode_stability(self, tmp_path):
        """Test that inode is stable across calls."""
        inode1 = get_inode(tmp_path)
        inode2 = get_inode(tmp_path)

        assert inode1 == inode2


class TestGetGitInfo:
    """Test git information retrieval via RepoHash."""

    @patch("htmlgraph.repo_hash.get_current_branch")
    @patch("htmlgraph.repo_hash.get_current_commit")
    @patch("htmlgraph.repo_hash.get_git_remote")
    @patch("htmlgraph.repo_hash.is_git_dirty")
    @patch("htmlgraph.repo_hash.get_last_commit_date")
    def test_get_git_info_structure(
        self, mock_date, mock_dirty, mock_remote, mock_commit, mock_branch, tmp_path
    ):
        """Test that git_info returns expected structure."""
        mock_branch.return_value = "main"
        mock_commit.return_value = "d78e458"
        mock_remote.return_value = "https://github.com/user/repo.git"
        mock_dirty.return_value = False
        mock_date.return_value = "2026-01-08T12:34:56Z"

        repo = RepoHash(tmp_path)
        info = repo.get_git_info()

        assert isinstance(info, dict)
        assert "branch" in info
        assert "commit" in info
        assert "remote" in info
        assert "dirty" in info
        assert "last_commit_date" in info

    @patch("htmlgraph.repo_hash.get_current_branch")
    @patch("htmlgraph.repo_hash.get_current_commit")
    @patch("htmlgraph.repo_hash.get_git_remote")
    @patch("htmlgraph.repo_hash.is_git_dirty")
    @patch("htmlgraph.repo_hash.get_last_commit_date")
    def test_get_git_info_values(
        self, mock_date, mock_dirty, mock_remote, mock_commit, mock_branch, tmp_path
    ):
        """Test that git_info values are correct."""
        mock_branch.return_value = "feature/test"
        mock_commit.return_value = "abc1234"
        mock_remote.return_value = "https://github.com/user/repo.git"
        mock_dirty.return_value = True
        mock_date.return_value = "2026-01-08T12:34:56Z"

        repo = RepoHash(tmp_path)
        info = repo.get_git_info()

        assert info["branch"] == "feature/test"
        assert info["commit"] == "abc1234"
        assert info["remote"] == "https://github.com/user/repo.git"
        assert info["dirty"] is True
        assert info["last_commit_date"] == "2026-01-08T12:34:56Z"

    @patch("htmlgraph.repo_hash.get_current_branch")
    def test_get_git_info_caching(self, mock_branch, tmp_path):
        """Test that git_info is cached."""
        mock_branch.return_value = "main"

        repo = RepoHash(tmp_path)
        repo.get_git_info()

        # Modify cache to verify it's used
        repo._git_info_cache = {"branch": "cached"}
        info2 = repo.get_git_info()

        assert info2 == {"branch": "cached"}


class TestMonorepoDetection:
    """Test monorepo structure detection."""

    def test_is_monorepo_single_project(self, tmp_path):
        """Test single project is not detected as monorepo."""
        repo = RepoHash(tmp_path)
        result = repo.is_monorepo()

        assert result is False

    def test_is_monorepo_multiple_pyproject(self, tmp_path):
        """Test multiple pyproject.toml files detected."""
        (tmp_path / "project1").mkdir()
        (tmp_path / "project1" / "pyproject.toml").touch()
        (tmp_path / "project2").mkdir()
        (tmp_path / "project2" / "pyproject.toml").touch()

        repo = RepoHash(tmp_path)
        result = repo.is_monorepo()

        assert result is True

    def test_is_monorepo_multiple_package_json(self, tmp_path):
        """Test multiple package.json files detected."""
        (tmp_path / "packages/project1").mkdir(parents=True)
        (tmp_path / "packages/project1" / "package.json").touch()
        (tmp_path / "packages/project2").mkdir(parents=True)
        (tmp_path / "packages/project2" / "package.json").touch()

        repo = RepoHash(tmp_path)
        result = repo.is_monorepo()

        assert result is True

    def test_is_monorepo_workspaces_field(self, tmp_path):
        """Test npm workspaces field detected."""
        package_json = {"workspaces": ["packages/*"]}
        with open(tmp_path / "package.json", "w") as f:
            json.dump(package_json, f)

        repo = RepoHash(tmp_path)
        result = repo.is_monorepo()

        assert result is True

    def test_is_monorepo_error_handling(self, tmp_path):
        """Test error handling in monorepo detection."""
        # Create invalid package.json
        (tmp_path / "package.json").write_text("invalid json{")

        repo = RepoHash(tmp_path)
        # Should not raise, should return False
        result = repo.is_monorepo()

        assert isinstance(result, bool)


class TestGetMonorepoProject:
    """Test monorepo project identification."""

    def test_get_monorepo_project_not_monorepo(self, tmp_path):
        """Test non-monorepo returns None."""
        repo = RepoHash(tmp_path)
        result = repo.get_monorepo_project()

        assert result is None

    def test_get_monorepo_project_with_pyproject(self, tmp_path):
        """Test project identification with pyproject.toml."""
        (tmp_path / "packages/claude-plugin").mkdir(parents=True)
        (tmp_path / "packages/claude-plugin" / "pyproject.toml").touch()
        (tmp_path / "packages/gemini-ext").mkdir(parents=True)
        (tmp_path / "packages/gemini-ext" / "pyproject.toml").touch()
        (tmp_path / ".git").mkdir()

        # Test from subdirectory
        plugin_dir = tmp_path / "packages/claude-plugin"
        repo = RepoHash(plugin_dir)

        result = repo.get_monorepo_project()

        assert result is not None
        assert "claude-plugin" in result

    def test_get_monorepo_project_with_package_json(self, tmp_path):
        """Test project identification with package.json."""
        (tmp_path / "packages/project1").mkdir(parents=True)
        (tmp_path / "packages/project1" / "package.json").touch()
        (tmp_path / "packages/project2").mkdir(parents=True)
        (tmp_path / "packages/project2" / "package.json").touch()
        (tmp_path / ".git").mkdir()

        project_dir = tmp_path / "packages/project1"
        repo = RepoHash(project_dir)

        result = repo.get_monorepo_project()

        assert result is not None
        assert "project1" in result

    def test_get_monorepo_project_error_handling(self, tmp_path):
        """Test error handling in project identification."""
        (tmp_path / ".git").mkdir()

        repo = RepoHash(tmp_path)
        # Should not raise
        result = repo.get_monorepo_project()

        assert result is None or isinstance(result, str)


class TestRepoHashIntegration:
    """Integration tests for RepoHash."""

    @patch("htmlgraph.repo_hash.get_git_remote")
    @patch("htmlgraph.repo_hash.get_current_branch")
    @patch("htmlgraph.repo_hash.get_current_commit")
    @patch("htmlgraph.repo_hash.is_git_dirty")
    def test_full_repo_hash_workflow(
        self, mock_dirty, mock_commit, mock_branch, mock_remote, tmp_path
    ):
        """Test complete RepoHash workflow."""
        mock_remote.return_value = "https://github.com/user/repo.git"
        mock_branch.return_value = "main"
        mock_commit.return_value = "d78e458"
        mock_dirty.return_value = False

        repo = RepoHash(tmp_path)

        # Get hash
        hash_val = repo.compute_repo_hash()
        assert hash_val.startswith("repo-")

        # Get git info
        info = repo.get_git_info()
        assert info["branch"] == "main"
        assert info["commit"] == "d78e458"
        assert info["remote"] == "https://github.com/user/repo.git"
        assert info["dirty"] is False

        # Check not monorepo
        assert repo.is_monorepo() is False
        assert repo.get_monorepo_project() is None

    def test_repo_hash_with_multiple_instances(self, tmp_path):
        """Test that multiple instances of same repo produce same hash."""
        repo1 = RepoHash(tmp_path)
        repo2 = RepoHash(tmp_path)

        hash1 = repo1.compute_repo_hash()
        hash2 = repo2.compute_repo_hash()

        assert hash1 == hash2
