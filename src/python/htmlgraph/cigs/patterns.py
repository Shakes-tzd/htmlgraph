"""
Pattern Detection for CIGS - Identify behavioral anti-patterns from tool usage history.

Detects anti-patterns that violate HtmlGraph delegation principles:
1. exploration_sequence: 3+ Read/Grep/Glob in sequence (should use spawn_gemini)
2. edit_without_test: Edit operations without subsequent test delegation
3. direct_git_commit: git commit via Bash instead of spawn_copilot
4. repeated_read_same_file: Same file read multiple times in short window

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 5, Section 5.3)
"""

from dataclasses import dataclass, field
from typing import Any

from .models import PatternRecord

# Define exploration and implementation tool categories
EXPLORATION_TOOLS = {"Read", "Grep", "Glob"}
IMPLEMENTATION_TOOLS = {"Edit", "Write", "NotebookEdit"}
TESTING_TOOLS = {"Bash"}  # pytest, npm test, yarn test


@dataclass
class DetectionResult:
    """Result of pattern detection."""

    pattern_type: str  # "anti-pattern" or "good-pattern"
    name: str
    description: str
    detected: bool
    trigger_conditions: list[str] = field(default_factory=list)
    example_sequence: list[str] = field(default_factory=list)
    remediation: str | None = None
    confidence: float = 0.0  # 0.0 to 1.0


class PatternDetector:
    """
    Detect behavioral patterns from tool usage history.

    Uses a sliding window approach to identify anti-patterns that violate
    HtmlGraph delegation principles.
    """

    # Window size for analysis (last N tool calls)
    DEFAULT_WINDOW_SIZE = 10

    def __init__(self, window_size: int = DEFAULT_WINDOW_SIZE):
        """Initialize pattern detector.

        Args:
            window_size: Number of recent tool calls to analyze
        """
        self.window_size = window_size
        self._anti_patterns = self._init_anti_patterns()

    def _init_anti_patterns(self) -> dict[str, Any]:
        """Initialize anti-pattern definitions."""
        return {
            "exploration_sequence": {
                "description": "Multiple exploration tools in sequence",
                "trigger_conditions": [
                    "3+ exploration tools (Read/Grep/Glob) in last N calls",
                    "No delegation (spawn_gemini/Task) between them",
                ],
                "remediation": "Use spawn_gemini() for comprehensive exploration",
                "min_occurrences": 3,
                "detector": self._detect_exploration_sequence,
            },
            "edit_without_test": {
                "description": "Edit operations without subsequent test delegation",
                "trigger_conditions": [
                    "Edit/Write operation detected",
                    "No Task() with 'test' in prompt within next 3 calls",
                ],
                "remediation": "Include testing in Task() prompt for code changes",
                "detector": self._detect_edit_without_test,
            },
            "direct_git_commit": {
                "description": "Git commit executed directly instead of via spawn_copilot",
                "trigger_conditions": [
                    "Bash tool with 'git commit' command",
                    "No spawn_copilot() delegation",
                ],
                "remediation": "Use spawn_copilot() for git operations",
                "detector": self._detect_direct_git_commit,
            },
            "repeated_read_same_file": {
                "description": "Same file read multiple times in short window",
                "trigger_conditions": [
                    "Same file_path in 2+ Read operations",
                    "Within last 10 tool calls",
                    "No delegation between reads",
                ],
                "remediation": "Delegate to Explorer (spawn_gemini) for comprehensive file analysis",
                "detector": self._detect_repeated_read_same_file,
            },
        }

    def detect_all_patterns(self, history: list[dict[str, Any]]) -> list[PatternRecord]:
        """
        Detect all anti-patterns in tool usage history.

        Args:
            history: List of tool call records with structure:
                {
                    "tool": str,
                    "command": str (for Bash),
                    "file_path": str (for Read),
                    "prompt": str (for Task),
                    "timestamp": datetime,
                    ...
                }

        Returns:
            List of detected PatternRecord instances
        """
        detected = []
        history_window = (
            history[-self.window_size :] if len(history) > self.window_size else history
        )

        for pattern_name, pattern_def in self._anti_patterns.items():
            detector_func: Any = pattern_def["detector"]
            result = detector_func(history_window)
            if result.detected:
                detected.append(
                    PatternRecord(
                        id=f"pattern-{pattern_name}",
                        pattern_type="anti-pattern",
                        name=pattern_name,
                        description=result.description,
                        trigger_conditions=result.trigger_conditions,
                        example_sequence=result.example_sequence,
                        occurrence_count=1,
                        sessions_affected=[],
                        correct_approach=result.remediation,
                        delegation_suggestion=self._get_delegation_suggestion(
                            pattern_name
                        ),
                    )
                )

        return detected

    def detect_pattern(
        self, pattern_name: str, history: list[dict[str, Any]]
    ) -> DetectionResult:
        """
        Detect a specific anti-pattern.

        Args:
            pattern_name: Name of pattern to detect
            history: Tool usage history

        Returns:
            DetectionResult with detection details
        """
        if pattern_name not in self._anti_patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        pattern_def = self._anti_patterns[pattern_name]
        history_window = (
            history[-self.window_size :] if len(history) > self.window_size else history
        )

        detector_func: Any = pattern_def["detector"]
        return detector_func(history_window)  # type: ignore[no-any-return]

    def _detect_exploration_sequence(
        self, history: list[dict[str, Any]]
    ) -> DetectionResult:
        """
        Detect exploration_sequence anti-pattern.

        Triggers when 3+ exploration tools (Read/Grep/Glob) appear in sequence
        without delegation to spawn_gemini() or Task().
        """
        pattern_name = "exploration_sequence"
        pattern_def = self._anti_patterns[pattern_name]

        if not history:
            return DetectionResult(
                pattern_type="anti-pattern",
                name=pattern_name,
                description=pattern_def["description"],
                detected=False,
            )

        # Count exploration tools in history
        exploration_count = 0
        exploration_tools_found = []

        for call in history:
            tool = call.get("tool", "")

            if tool in EXPLORATION_TOOLS:
                exploration_count += 1
                exploration_tools_found.append(tool)
            elif tool in {"Task", "Bash"} and "spawn_gemini" in call.get(
                "prompt", ""
            ) + call.get("command", ""):
                # Delegation found, reset
                exploration_count = 0
                exploration_tools_found = []
            elif tool not in EXPLORATION_TOOLS:
                # Non-exploration tool breaks the sequence (unless it's delegation)
                if tool not in {"Task"} or not any(
                    d in call.get("prompt", "") for d in ["spawn_", "gemini"]
                ):
                    pass  # Don't reset, continue counting

        detected = exploration_count >= 3
        confidence = min(1.0, exploration_count / 3) if detected else 0.0

        return DetectionResult(
            pattern_type="anti-pattern",
            name=pattern_name,
            description=pattern_def["description"],
            detected=detected,
            trigger_conditions=pattern_def["trigger_conditions"],
            example_sequence=exploration_tools_found[-3:]
            if len(exploration_tools_found) >= 3
            else [],
            remediation=pattern_def["remediation"],
            confidence=confidence,
        )

    def _detect_edit_without_test(
        self, history: list[dict[str, Any]]
    ) -> DetectionResult:
        """
        Detect edit_without_test anti-pattern.

        Triggers when Edit/Write operations exist without subsequent Task()
        delegation containing test keywords within next 3 calls.
        """
        pattern_name = "edit_without_test"
        pattern_def = self._anti_patterns[pattern_name]

        if not history:
            return DetectionResult(
                pattern_type="anti-pattern",
                name=pattern_name,
                description=pattern_def["description"],
                detected=False,
            )

        test_keywords = {
            "test",
            "pytest",
            "unittest",
            "vitest",
            "jest",
            "mocha",
            "assert",
            "verify",
        }

        # Check for Edit/Write without subsequent test delegation
        for i, call in enumerate(history):
            tool = call.get("tool", "")

            if tool in IMPLEMENTATION_TOOLS:
                # Found an edit, check next 3 calls for test delegation
                test_found = False
                remaining_calls = history[i + 1 : i + 4]

                for next_call in remaining_calls:
                    next_tool = next_call.get("tool", "")
                    prompt = next_call.get("prompt", "").lower()

                    # Check if this is a test delegation
                    if next_tool == "Task" and any(
                        kw in prompt for kw in test_keywords
                    ):
                        test_found = True
                        break

                if not test_found and len(history) > i + 1:
                    # Edit found without subsequent test delegation
                    example_seq = [call.get("tool", "")] + [
                        c.get("tool", "") for c in remaining_calls[:3]
                    ]
                    return DetectionResult(
                        pattern_type="anti-pattern",
                        name=pattern_name,
                        description=pattern_def["description"],
                        detected=True,
                        trigger_conditions=pattern_def["trigger_conditions"],
                        example_sequence=example_seq,
                        remediation=pattern_def["remediation"],
                        confidence=0.8,
                    )

        return DetectionResult(
            pattern_type="anti-pattern",
            name=pattern_name,
            description=pattern_def["description"],
            detected=False,
        )

    def _detect_direct_git_commit(
        self, history: list[dict[str, Any]]
    ) -> DetectionResult:
        """
        Detect direct_git_commit anti-pattern.

        Triggers when git commit is executed via Bash directly instead of
        delegating to spawn_copilot().
        """
        pattern_name = "direct_git_commit"
        pattern_def = self._anti_patterns[pattern_name]

        if not history:
            return DetectionResult(
                pattern_type="anti-pattern",
                name=pattern_name,
                description=pattern_def["description"],
                detected=False,
            )

        git_commit_commands = [
            "git commit",
            "git push",
            "git add",
            "git merge",
            "git rebase",
        ]

        for i, call in enumerate(history):
            tool = call.get("tool", "")

            if tool == "Bash":
                command = call.get("command", "").lower()

                # Check if this is a git commit operation
                is_git_commit = any(cmd in command for cmd in git_commit_commands)

                if is_git_commit:
                    # Check if this was preceded by spawn_copilot delegation
                    was_delegated = False
                    if i > 0:
                        prev_call = history[i - 1]
                        if prev_call.get("tool", "") == "Task":
                            prompt = prev_call.get("prompt", "").lower()
                            if "copilot" in prompt or "git" in prompt:
                                was_delegated = True

                    if not was_delegated:
                        return DetectionResult(
                            pattern_type="anti-pattern",
                            name=pattern_name,
                            description=pattern_def["description"],
                            detected=True,
                            trigger_conditions=pattern_def["trigger_conditions"],
                            example_sequence=["Bash", command.split()[0:2]],
                            remediation=pattern_def["remediation"],
                            confidence=0.95,
                        )

        return DetectionResult(
            pattern_type="anti-pattern",
            name=pattern_name,
            description=pattern_def["description"],
            detected=False,
        )

    def _detect_repeated_read_same_file(
        self, history: list[dict[str, Any]]
    ) -> DetectionResult:
        """
        Detect repeated_read_same_file anti-pattern.

        Triggers when the same file is read multiple times within the window
        without delegation to explore comprehensively.
        """
        pattern_name = "repeated_read_same_file"
        pattern_def = self._anti_patterns[pattern_name]

        if not history:
            return DetectionResult(
                pattern_type="anti-pattern",
                name=pattern_name,
                description=pattern_def["description"],
                detected=False,
            )

        # Track file reads
        file_read_count: dict[str, int] = {}
        file_read_sequence: list[tuple[str, str]] = []

        for call in history:
            tool = call.get("tool", "")

            if tool == "Read":
                file_path = call.get("file_path", "")
                if file_path:
                    file_read_count[file_path] = file_read_count.get(file_path, 0) + 1
                    file_read_sequence.append(("Read", file_path))

        # Check for repeated reads of the same file
        repeated_files = {
            f: count for f, count in file_read_count.items() if count >= 2
        }

        if repeated_files:
            # File was read multiple times
            most_repeated = max(repeated_files.items(), key=lambda x: x[1])
            example_seq = [tool for tool, _ in file_read_sequence if tool == "Read"][
                -3:
            ]

            return DetectionResult(
                pattern_type="anti-pattern",
                name=pattern_name,
                description=pattern_def["description"],
                detected=True,
                trigger_conditions=[f"{most_repeated[1]}x reads of: {most_repeated[0]}"]
                + pattern_def["trigger_conditions"],
                example_sequence=example_seq,
                remediation=pattern_def["remediation"],
                confidence=min(1.0, most_repeated[1] / 3),
            )

        return DetectionResult(
            pattern_type="anti-pattern",
            name=pattern_name,
            description=pattern_def["description"],
            detected=False,
        )

    def _get_delegation_suggestion(self, pattern_name: str) -> str:
        """Get delegation suggestion for a detected anti-pattern."""
        suggestions = {
            "exploration_sequence": (
                "spawn_gemini(prompt='Comprehensive search and analysis of codebase for...')"
            ),
            "edit_without_test": (
                "Task(prompt='Make the following changes AND run tests to verify: ...')"
            ),
            "direct_git_commit": (
                "spawn_copilot(prompt='Commit changes with message: ...')"
            ),
            "repeated_read_same_file": (
                "spawn_gemini(prompt='Analyze the entire file and extract all relevant sections: ...')"
            ),
        }
        return suggestions.get(
            pattern_name,
            "Delegate this operation to an appropriate subagent",
        )

    def get_pattern_statistics(
        self, all_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyze pattern statistics across entire history.

        Args:
            all_history: Complete tool usage history (not just window)

        Returns:
            Dictionary with pattern statistics
        """
        stats = {}

        # Check each anti-pattern with sliding windows across history
        for i in range(max(0, len(all_history) - 50), len(all_history)):
            window = all_history[i : i + self.window_size]
            if not window:
                continue

            detected = self.detect_all_patterns(window)
            for pattern in detected:
                if pattern.name not in stats:
                    stats[pattern.name] = {"count": 0, "sessions": set()}
                stats[pattern.name]["count"] = stats[pattern.name]["count"] + 1  # type: ignore[operator]

        return {
            name: {"occurrence_count": data["count"]} for name, data in stats.items()
        }


# Helper function for external use
def detect_patterns(
    history: list[dict[str, Any]], window_size: int = 10
) -> list[PatternRecord]:
    """
    Detect anti-patterns from tool usage history.

    Convenience function that creates a detector and finds all patterns.

    Args:
        history: Tool usage history
        window_size: Window size for pattern detection

    Returns:
        List of detected PatternRecord instances
    """
    detector = PatternDetector(window_size=window_size)
    return detector.detect_all_patterns(history)
