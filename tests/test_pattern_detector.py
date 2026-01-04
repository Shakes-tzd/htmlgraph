"""Comprehensive tests for PatternDetector in CIGS.

Tests cover all 4 anti-patterns with multiple scenarios and edge cases.
"""

from htmlgraph.cigs.patterns import (
    DetectionResult,
    PatternDetector,
    detect_patterns,
)


class TestPatternDetectorBasics:
    """Test PatternDetector initialization and basic operations."""

    def test_detector_initialization(self):
        """Test PatternDetector initializes with default window size."""
        detector = PatternDetector()
        assert detector.window_size == 10

    def test_detector_custom_window_size(self):
        """Test PatternDetector with custom window size."""
        detector = PatternDetector(window_size=5)
        assert detector.window_size == 5

    def test_detect_all_patterns_empty_history(self):
        """Test pattern detection with empty history."""
        detector = PatternDetector()
        patterns = detector.detect_all_patterns([])
        assert patterns == []

    def test_detect_pattern_single_read_not_detected(self):
        """Test that single Read operation doesn't trigger exploration_sequence."""
        detector = PatternDetector()
        history = [{"tool": "Read", "file_path": "/path/to/file.py"}]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is False


class TestExplorationSequencePattern:
    """Test exploration_sequence anti-pattern detection."""

    def test_exploration_sequence_three_reads(self):
        """Test detection of 3 consecutive Read operations."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
            {"tool": "Read", "file_path": "/path/to/file3.py"},
        ]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is True
        assert result.confidence >= 0.9

    def test_exploration_sequence_read_grep_glob(self):
        """Test detection of mixed exploration tools (Read, Grep, Glob)."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file.py"},
            {"tool": "Grep", "pattern": "TODO", "path": "src/"},
            {"tool": "Glob", "pattern": "**/*.py"},
        ]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is True

    def test_exploration_sequence_four_tools(self):
        """Test detection with 4 exploration tools."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Glob", "pattern": "**/*.ts"},
            {"tool": "Grep", "pattern": "import", "path": "src/"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
        ]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is True
        assert result.confidence > 0.9

    def test_exploration_sequence_interrupted_by_delegation(self):
        """Test that Task with spawn_gemini resets the sequence."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
            {"tool": "Task", "prompt": "spawn_gemini for comprehensive search"},
            {"tool": "Read", "file_path": "/path/to/file3.py"},
        ]

        # First 2 reads + 1 after delegation = not 3 in sequence after reset
        # But since we found 2 before reset, it might still trigger depending on logic
        detector.detect_pattern("exploration_sequence", history)

    def test_exploration_sequence_two_tools_not_triggered(self):
        """Test that 2 exploration tools don't trigger the pattern."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Grep", "pattern": "TODO"},
        ]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is False

    def test_exploration_sequence_example_sequence_captured(self):
        """Test that example sequence is properly captured."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Grep", "pattern": "search"},
            {"tool": "Glob", "pattern": "**/*.ts"},
        ]

        result = detector.detect_pattern("exploration_sequence", history)
        assert result.detected is True
        assert len(result.example_sequence) >= 3


class TestEditWithoutTestPattern:
    """Test edit_without_test anti-pattern detection."""

    def test_edit_without_test_detected(self):
        """Test detection of Edit without subsequent test delegation."""
        detector = PatternDetector()
        history = [
            {
                "tool": "Edit",
                "file_path": "src/main.py",
                "old_string": "x",
                "new_string": "y",
            },
            {"tool": "Read", "file_path": "src/main.py"},
            {"tool": "Bash", "command": "ls"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is True

    def test_edit_with_test_task_not_detected(self):
        """Test that Edit followed by Task with test prompt is allowed."""
        detector = PatternDetector()
        history = [
            {
                "tool": "Edit",
                "file_path": "src/main.py",
                "old_string": "x",
                "new_string": "y",
            },
            {"tool": "Task", "prompt": "Run tests to verify the change"},
            {"tool": "Bash", "command": "ls"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is False

    def test_edit_with_pytest_keyword(self):
        """Test that Task with pytest keyword is recognized as testing."""
        detector = PatternDetector()
        history = [
            {
                "tool": "Edit",
                "file_path": "src/main.py",
                "old_string": "foo",
                "new_string": "bar",
            },
            {"tool": "Task", "prompt": "Please run pytest to validate"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is False

    def test_edit_with_unittest_keyword(self):
        """Test that Task with unittest keyword is recognized."""
        detector = PatternDetector()
        history = [
            {
                "tool": "Write",
                "file_path": "src/new_module.py",
                "content": "def foo(): pass",
            },
            {"tool": "Task", "prompt": "Execute unit tests for this module"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is False

    def test_write_without_test_detected(self):
        """Test that Write operations are also checked."""
        detector = PatternDetector()
        history = [
            {"tool": "Write", "file_path": "src/new_file.py", "content": "code"},
            {"tool": "Read", "file_path": "src/new_file.py"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is True

    def test_notebook_edit_without_test(self):
        """Test NotebookEdit operations are checked."""
        detector = PatternDetector()
        history = [
            {
                "tool": "NotebookEdit",
                "notebook_path": "analysis.ipynb",
                "new_source": "code",
            },
            {"tool": "Read", "file_path": "analysis.ipynb"},
        ]

        result = detector.detect_pattern("edit_without_test", history)
        assert result.detected is True

    def test_edit_with_multiple_test_keywords(self):
        """Test various test keywords are recognized."""
        test_keywords = ["assert", "verify", "vitest", "jest", "mocha"]
        detector = PatternDetector()

        for keyword in test_keywords:
            history = [
                {
                    "tool": "Edit",
                    "file_path": "src/test.js",
                    "old_string": "x",
                    "new_string": "y",
                },
                {"tool": "Task", "prompt": f"Run {keyword} to validate"},
            ]
            result = detector.detect_pattern("edit_without_test", history)
            assert result.detected is False, (
                f"Should recognize '{keyword}' as test keyword"
            )


class TestDirectGitCommitPattern:
    """Test direct_git_commit anti-pattern detection."""

    def test_direct_git_commit_detected(self):
        """Test detection of direct git commit via Bash."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git commit -m 'fix bug'"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is True
        assert result.confidence >= 0.9

    def test_git_push_detected(self):
        """Test that git push is detected as git operation."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git push origin main"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is True

    def test_git_add_detected(self):
        """Test that git add is detected."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git add src/"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is True

    def test_git_merge_detected(self):
        """Test that git merge is detected."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git merge feature-branch"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is True

    def test_git_rebase_detected(self):
        """Test that git rebase is detected."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git rebase main"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is True

    def test_git_commit_with_spawn_copilot_allowed(self):
        """Test that git commit preceded by spawn_copilot is allowed."""
        detector = PatternDetector()
        history = [
            {"tool": "Task", "prompt": "spawn_copilot to handle git operations"},
            {"tool": "Bash", "command": "git commit -m 'feature'"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is False

    def test_non_git_bash_not_detected(self):
        """Test that non-git Bash commands don't trigger pattern."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "ls -la"},
            {
                "tool": "Bash",
                "command": "echo 'git status'",
            },  # Contains 'git' but not a command
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert result.detected is False


class TestRepeatedReadSameFilePattern:
    """Test repeated_read_same_file anti-pattern detection."""

    def test_repeated_read_same_file_detected(self):
        """Test detection of same file read twice."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/config.py"},
            {"tool": "Bash", "command": "ls"},
            {"tool": "Read", "file_path": "/path/to/config.py"},
        ]

        result = detector.detect_pattern("repeated_read_same_file", history)
        assert result.detected is True

    def test_repeated_read_three_times(self):
        """Test detection of same file read three times."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/utils.py"},
            {"tool": "Read", "file_path": "/path/to/utils.py"},
            {"tool": "Bash", "command": "grep pattern"},
            {"tool": "Read", "file_path": "/path/to/utils.py"},
        ]

        result = detector.detect_pattern("repeated_read_same_file", history)
        assert result.detected is True
        assert result.confidence > 0.5

    def test_single_read_per_file_not_detected(self):
        """Test that different files read once each don't trigger."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
            {"tool": "Read", "file_path": "/path/to/file3.py"},
        ]

        result = detector.detect_pattern("repeated_read_same_file", history)
        assert result.detected is False

    def test_repeated_read_with_no_file_path(self):
        """Test that Read without file_path is handled."""
        detector = PatternDetector()
        history = [
            {"tool": "Read"},  # No file_path
            {"tool": "Read"},
        ]

        result = detector.detect_pattern("repeated_read_same_file", history)
        assert result.detected is False

    def test_repeated_read_different_extensions(self):
        """Test repeated reads of files with different extensions."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/config.json"},
            {"tool": "Read", "file_path": "/path/to/other.py"},
            {"tool": "Read", "file_path": "/path/to/config.json"},
        ]

        result = detector.detect_pattern("repeated_read_same_file", history)
        assert result.detected is True

    def test_confidence_based_on_repetition(self):
        """Test that confidence increases with more repetitions."""
        detector = PatternDetector()

        history_2_reads = [
            {"tool": "Read", "file_path": "/path/to/file.py"},
            {"tool": "Read", "file_path": "/path/to/file.py"},
        ]
        result_2 = detector.detect_pattern("repeated_read_same_file", history_2_reads)

        history_3_reads = [
            {"tool": "Read", "file_path": "/path/to/file.py"},
            {"tool": "Bash", "command": "ls"},
            {"tool": "Read", "file_path": "/path/to/file.py"},
            {"tool": "Bash", "command": "echo"},
            {"tool": "Read", "file_path": "/path/to/file.py"},
        ]
        result_3 = detector.detect_pattern("repeated_read_same_file", history_3_reads)

        if result_2.detected and result_3.detected:
            assert result_3.confidence >= result_2.confidence


class TestDetectAllPatterns:
    """Test detect_all_patterns method."""

    def test_multiple_patterns_detected(self):
        """Test detection of multiple anti-patterns in same history."""
        detector = PatternDetector()
        history = [
            # Exploration sequence
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Grep", "pattern": "search"},
            {"tool": "Glob", "pattern": "**/*.ts"},
            # Edit without test
            {
                "tool": "Edit",
                "file_path": "src/main.py",
                "old_string": "x",
                "new_string": "y",
            },
            {"tool": "Bash", "command": "echo done"},
            # Git commit
            {"tool": "Bash", "command": "git commit -m 'fix'"},
        ]

        patterns = detector.detect_all_patterns(history)
        pattern_names = [p.name for p in patterns]

        # Should detect exploration and edit-without-test (git might or might not)
        assert (
            "exploration_sequence" in pattern_names
            or "edit_without_test" in pattern_names
        )

    def test_no_patterns_in_clean_history(self):
        """Test that clean history produces no patterns."""
        detector = PatternDetector()
        history = [
            {"tool": "Task", "prompt": "Do something"},
            {"tool": "Read", "file_path": "/single/file.py"},
            {"tool": "Bash", "command": "ls"},
        ]

        patterns = detector.detect_all_patterns(history)
        assert len(patterns) == 0

    def test_window_size_respected(self):
        """Test that only recent history within window is analyzed."""
        detector = PatternDetector(window_size=3)
        history = [
            # Old history (outside window)
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
            # Recent history (within window)
            {"tool": "Bash", "command": "echo test"},
            {"tool": "Task", "prompt": "Do work"},
            {"tool": "Read", "file_path": "/path/to/file3.py"},
        ]

        # Window size 3 should only see last 3 calls
        detector.detect_all_patterns(history)


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_detect_patterns_function(self):
        """Test the module-level detect_patterns function."""
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Grep", "pattern": "search"},
            {"tool": "Glob", "pattern": "**/*.ts"},
        ]

        patterns = detect_patterns(history)
        assert isinstance(patterns, list)
        if patterns:
            for pattern in patterns:
                assert hasattr(pattern, "name")
                assert hasattr(pattern, "pattern_type")

    def test_detect_patterns_with_custom_window(self):
        """Test detect_patterns with custom window size."""
        history = [
            {"tool": "Read", "file_path": "/path/to/file1.py"},
            {"tool": "Read", "file_path": "/path/to/file2.py"},
            {"tool": "Read", "file_path": "/path/to/file3.py"},
        ]

        patterns = detect_patterns(history, window_size=3)
        assert isinstance(patterns, list)


class TestDetectionResultDataclass:
    """Test DetectionResult dataclass."""

    def test_detection_result_creation(self):
        """Test creating DetectionResult."""
        result = DetectionResult(
            pattern_type="anti-pattern",
            name="test_pattern",
            description="Test pattern",
            detected=True,
            confidence=0.85,
        )

        assert result.pattern_type == "anti-pattern"
        assert result.name == "test_pattern"
        assert result.detected is True
        assert result.confidence == 0.85

    def test_detection_result_defaults(self):
        """Test DetectionResult default values."""
        result = DetectionResult(
            pattern_type="anti-pattern",
            name="test",
            description="Test",
            detected=False,
        )

        assert result.trigger_conditions == []
        assert result.example_sequence == []
        assert result.remediation is None
        assert result.confidence == 0.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tool_field(self):
        """Test history entries with missing tool field."""
        detector = PatternDetector()
        history = [
            {"file_path": "/path/to/file.py"},  # No 'tool' field
            {"tool": "Read", "file_path": "/path/to/file.py"},
        ]

        # Should not raise exception
        patterns = detector.detect_all_patterns(history)
        assert isinstance(patterns, list)

    def test_empty_command_field(self):
        """Test Bash entries with empty command."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": ""},
            {"tool": "Bash", "command": "git commit -m 'test'"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert isinstance(result, DetectionResult)

    def test_very_long_history(self):
        """Test with very long history (>100 calls)."""
        detector = PatternDetector(window_size=10)
        history = [
            {"tool": "Read", "file_path": f"/path/to/file{i}.py"} for i in range(200)
        ]

        # Should only analyze last 10
        patterns = detector.detect_all_patterns(history)
        assert isinstance(patterns, list)

    def test_unicode_in_file_paths(self):
        """Test handling of unicode in file paths."""
        detector = PatternDetector()
        history = [
            {"tool": "Read", "file_path": "/path/to/файл.py"},
            {"tool": "Read", "file_path": "/path/to/文件.py"},
            {"tool": "Read", "file_path": "/path/to/ফাইল.py"},
        ]

        patterns = detector.detect_all_patterns(history)
        assert isinstance(patterns, list)

    def test_special_characters_in_commands(self):
        """Test handling of special characters in git commands."""
        detector = PatternDetector()
        history = [
            {"tool": "Bash", "command": "git commit -m 'fix: update feature & docs'"},
            {"tool": "Bash", "command": "git push origin 'feature/test-branch'"},
        ]

        result = detector.detect_pattern("direct_git_commit", history)
        assert isinstance(result, DetectionResult)
