"""Tests for .githooks/pre-commit-systematic-check.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

# Import the hook script by file path (hyphens in filename prevent normal import)
_hook_path = Path(__file__).parents[2] / ".githooks" / "pre-commit-systematic-check.py"
_spec = importlib.util.spec_from_file_location(
    "pre_commit_systematic_check", _hook_path
)
assert _spec and _spec.loader
hook = importlib.util.module_from_spec(_spec)
sys.modules["pre_commit_systematic_check"] = hook
_spec.loader.exec_module(hook)

# ---------------------------------------------------------------------------
# _extract_renamed_pairs
# ---------------------------------------------------------------------------


def test_detects_simple_rename_pair() -> None:
    """Finds (old_term, new_term) when a token disappears and a new one appears."""
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1 +1 @@
-    old_handler = get_old_handler()
+    new_handler = get_new_handler()
"""
    pairs = hook._extract_renamed_pairs(diff)
    old_terms = {p[0] for p in pairs}
    assert "old_handler" in old_terms or "get_old_handler" in old_terms


def test_no_pairs_when_diff_is_additions_only() -> None:
    """No old terms when the diff only adds new lines with no removals."""
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -0,0 +1,2 @@
+def brand_new_function():
+    pass
"""
    pairs = hook._extract_renamed_pairs(diff)
    assert pairs == []


def test_skips_short_tokens() -> None:
    """Tokens shorter than 4 characters are not treated as systematic old terms."""
    diff = """\
--- a/foo.py
+++ b/foo.py
@@ -1 +1 @@
-    xyz = abc
+    xyz = def_value
"""
    pairs = hook._extract_renamed_pairs(diff)
    old_terms = {p[0] for p in pairs}
    # 'abc' has 3 chars — should be skipped
    assert "abc" not in old_terms


# ---------------------------------------------------------------------------
# _is_systematic
# ---------------------------------------------------------------------------


def test_is_systematic_detects_diff_keyword() -> None:
    diff = "This commit renames the module"
    assert hook._is_systematic(diff, "") is True


def test_is_systematic_detects_message_keyword() -> None:
    assert hook._is_systematic("", "refactor: move utilities") is True


def test_is_systematic_false_when_no_keywords() -> None:
    assert hook._is_systematic("just a normal change", "fix: typo") is False


def test_is_systematic_all_keywords() -> None:
    for word in ("renamed", "replacing", "migrating", "refactoring", "moving"):
        assert hook._is_systematic(word, "") is True, f"Expected True for '{word}'"


# ---------------------------------------------------------------------------
# _grep_remaining
# ---------------------------------------------------------------------------


def test_finds_remaining_instances(tmp_path: Path) -> None:
    """grep finds the old term in a Python file."""
    (tmp_path / "module.py").write_text("old_handler = None\n")
    results = hook._grep_remaining("old_handler", tmp_path)
    assert any("old_handler" in r for r in results)


def test_no_remaining_when_term_absent(tmp_path: Path) -> None:
    """Returns empty list when term doesn't exist in the tree."""
    (tmp_path / "module.py").write_text("new_handler = None\n")
    results = hook._grep_remaining("old_handler", tmp_path)
    assert results == []


def test_ignores_excluded_directories(tmp_path: Path) -> None:
    """Files inside excluded dirs are not reported."""
    excluded = tmp_path / ".htmlgraph"
    excluded.mkdir()
    (excluded / "data.html").write_text("old_handler = still here\n")
    # Also put the term in a non-excluded .py file so grep runs
    (tmp_path / "clean.py").write_text("# nothing relevant\n")
    results = hook._grep_remaining("old_handler", tmp_path)
    # .htmlgraph dir excluded — result should be empty
    assert all(".htmlgraph" not in r for r in results)


def test_returns_relative_paths(tmp_path: Path) -> None:
    """Results use relative paths, not absolute."""
    (tmp_path / "src.py").write_text("old_term_xyz = 1\n")
    results = hook._grep_remaining("old_term_xyz", tmp_path)
    assert results, "Expected at least one match"
    assert not results[0].startswith(str(tmp_path)), "Path should be relative"


# ---------------------------------------------------------------------------
# _format_warning
# ---------------------------------------------------------------------------


def test_format_warning_shows_count() -> None:
    instances = ["foo.py:1: old_name = x", "bar.py:5: old_name()"]
    msg = hook._format_warning("old_name", instances)
    assert "old_name" in msg
    assert "2 location(s)" in msg


def test_format_warning_truncates_long_list() -> None:
    instances = [f"file{i}.py:1: term" for i in range(20)]
    msg = hook._format_warning("term", instances)
    assert "more." in msg
    # Only MAX_INSTANCES_SHOWN shown explicitly
    shown_count = msg.count("file")
    assert shown_count == hook.MAX_INSTANCES_SHOWN


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


def test_main_returns_0_with_empty_diff() -> None:
    with patch.object(hook, "_staged_diff", return_value=""):
        assert hook.main() == 0


def test_main_returns_0_when_no_systematic_keyword() -> None:
    diff = "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-foo\n+bar\n"
    with (
        patch.object(hook, "_staged_diff", return_value=diff),
        patch.object(hook, "_commit_message", return_value="fix: normal patch"),
    ):
        assert hook.main() == 0


def test_main_returns_0_even_when_warning_emitted(tmp_path: Path) -> None:
    """Hook is non-blocking — always returns 0."""
    (tmp_path / "leftover.py").write_text("legacy_widget = True\n")
    diff = (
        "--- a/x.py\n+++ b/x.py\n"
        "@@ -1 +1 @@\n"
        "-legacy_widget = True\n"
        "+modern_widget = True\n"
    )
    with (
        patch.object(hook, "_staged_diff", return_value=diff),
        patch.object(hook, "_commit_message", return_value="rename: legacy to modern"),
        patch.object(hook, "_git_root", return_value=tmp_path),
    ):
        assert hook.main() == 0


def test_main_returns_0_when_change_complete(tmp_path: Path) -> None:
    """No warning when old term no longer exists anywhere."""
    # File uses new name only
    (tmp_path / "done.py").write_text("modern_widget = True\n")
    diff = (
        "--- a/x.py\n+++ b/x.py\n"
        "@@ -1 +1 @@\n"
        "-legacy_widget = True\n"
        "+modern_widget = True\n"
    )
    with (
        patch.object(hook, "_staged_diff", return_value=diff),
        patch.object(hook, "_commit_message", return_value="rename: legacy to modern"),
        patch.object(hook, "_git_root", return_value=tmp_path),
    ):
        assert hook.main() == 0
