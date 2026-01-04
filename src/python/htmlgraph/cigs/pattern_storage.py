"""
Pattern Storage for CIGS (Computational Imperative Guidance System).

Provides thread-safe storage and retrieval of detected behavioral patterns
in HtmlGraph format (.htmlgraph/cigs/patterns.json).

Features:
- Atomic JSON read/write with file locking
- Thread-safe operations with lock management
- Pattern persistence across sessions
- Pattern analytics and aggregation

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 3.2)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, cast
from uuid import uuid4

from htmlgraph.cigs.models import PatternRecord

logger = logging.getLogger(__name__)


class PatternStorage:
    """
    Thread-safe storage for behavioral patterns in HtmlGraph format.

    Storage format: `.htmlgraph/cigs/patterns.json`

    JSON Schema:
    {
      "patterns": [
        {
          "id": "pattern-001",
          "pattern_type": "anti-pattern",
          "name": "Read-Grep-Read Sequence",
          "description": "Multiple exploration tools used in sequence",
          "trigger_conditions": ["3+ exploration tools in last 5 calls"],
          "example_sequence": ["Read", "Grep", "Read"],
          "occurrence_count": 15,
          "sessions_affected": ["sess-abc", "sess-def"],
          "correct_approach": "Use spawn_gemini() for exploration",
          "delegation_suggestion": "spawn_gemini(prompt='...')"
        }
      ],
      "good_patterns": [...]
    }
    """

    def __init__(self, graph_dir: Path):
        """
        Initialize pattern storage.

        Args:
            graph_dir: Path to .htmlgraph directory (e.g., /project/.htmlgraph)
        """
        self.graph_dir = Path(graph_dir)
        self.patterns_file = self.graph_dir / "cigs" / "patterns.json"
        self._lock = Lock()

        # Ensure directory exists
        self.patterns_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.patterns_file.exists():
            self._write_atomic({"patterns": [], "good_patterns": []})

    def add_pattern(self, pattern: PatternRecord) -> str:
        """
        Add a new pattern to storage.

        Args:
            pattern: PatternRecord to add

        Returns:
            Pattern ID (generated if not provided)
        """
        if not pattern.id:
            pattern.id = f"pattern-{uuid4().hex[:8]}"

        with self._lock:
            data = self._read_atomic()

            # Determine which list to add to
            if pattern.pattern_type == "anti-pattern":
                patterns_list = data["patterns"]
            else:
                patterns_list = data["good_patterns"]

            # Check if pattern already exists
            existing = next((p for p in patterns_list if p["id"] == pattern.id), None)

            if existing:
                # Update existing pattern
                patterns_list[patterns_list.index(existing)] = self._pattern_to_dict(
                    pattern
                )
                logger.debug(f"Updated pattern: {pattern.id}")
            else:
                # Add new pattern
                patterns_list.append(self._pattern_to_dict(pattern))
                logger.debug(f"Added pattern: {pattern.id}")

            self._write_atomic(data)

        return pattern.id

    def get_pattern(self, pattern_id: str) -> PatternRecord | None:
        """
        Retrieve a pattern by ID.

        Args:
            pattern_id: Pattern ID to retrieve

        Returns:
            PatternRecord if found, None otherwise
        """
        with self._lock:
            data = self._read_atomic()

            # Search in both lists
            for pattern_dict in data["patterns"] + data["good_patterns"]:
                if pattern_dict["id"] == pattern_id:
                    return self._dict_to_pattern(pattern_dict)

        return None

    def get_all_patterns(self) -> list[PatternRecord]:
        """
        Retrieve all patterns (both anti-patterns and good patterns).

        Returns:
            List of all PatternRecord objects
        """
        with self._lock:
            data = self._read_atomic()

            patterns = []
            for pattern_dict in data["patterns"] + data["good_patterns"]:
                patterns.append(self._dict_to_pattern(pattern_dict))

            return patterns

    def get_anti_patterns(self) -> list[PatternRecord]:
        """
        Retrieve only anti-patterns.

        Returns:
            List of anti-pattern PatternRecord objects
        """
        with self._lock:
            data = self._read_atomic()

            patterns = []
            for pattern_dict in data["patterns"]:
                patterns.append(self._dict_to_pattern(pattern_dict))

            return patterns

    def get_good_patterns(self) -> list[PatternRecord]:
        """
        Retrieve only good patterns.

        Returns:
            List of good pattern PatternRecord objects
        """
        with self._lock:
            data = self._read_atomic()

            patterns = []
            for pattern_dict in data["good_patterns"]:
                patterns.append(self._dict_to_pattern(pattern_dict))

            return patterns

    def update_pattern_occurrence(self, pattern_id: str, session_id: str) -> bool:
        """
        Update pattern occurrence count and add session.

        Args:
            pattern_id: Pattern to update
            session_id: Session where pattern was detected

        Returns:
            True if updated, False if pattern not found
        """
        with self._lock:
            data = self._read_atomic()

            # Search in both lists
            for patterns_list in [data["patterns"], data["good_patterns"]]:
                for pattern_dict in patterns_list:
                    if pattern_dict["id"] == pattern_id:
                        pattern_dict["occurrence_count"] += 1

                        # Add session if not already present
                        if session_id not in pattern_dict["sessions_affected"]:
                            pattern_dict["sessions_affected"].append(session_id)

                        self._write_atomic(data)
                        logger.debug(
                            f"Updated occurrence for pattern {pattern_id}: "
                            f"count={pattern_dict['occurrence_count']}"
                        )
                        return True

        return False

    def remove_pattern(self, pattern_id: str) -> bool:
        """
        Remove a pattern by ID.

        Args:
            pattern_id: Pattern ID to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            data = self._read_atomic()

            # Search and remove from both lists
            for patterns_list in [data["patterns"], data["good_patterns"]]:
                for i, pattern_dict in enumerate(patterns_list):
                    if pattern_dict["id"] == pattern_id:
                        patterns_list.pop(i)
                        self._write_atomic(data)
                        logger.debug(f"Removed pattern: {pattern_id}")
                        return True

        return False

    def query_patterns(
        self,
        pattern_type: str | None = None,
        min_occurrences: int = 0,
    ) -> list[PatternRecord]:
        """
        Query patterns with filters.

        Args:
            pattern_type: Filter by type ("anti-pattern", "good-pattern", None for all)
            min_occurrences: Minimum occurrence count to include

        Returns:
            List of matching PatternRecord objects
        """
        with self._lock:
            data = self._read_atomic()

            patterns = []

            # Add anti-patterns if requested
            if pattern_type is None or pattern_type == "anti-pattern":
                for pattern_dict in data["patterns"]:
                    if pattern_dict["occurrence_count"] >= min_occurrences:
                        patterns.append(self._dict_to_pattern(pattern_dict))

            # Add good patterns if requested
            if pattern_type is None or pattern_type == "good-pattern":
                for pattern_dict in data["good_patterns"]:
                    if pattern_dict["occurrence_count"] >= min_occurrences:
                        patterns.append(self._dict_to_pattern(pattern_dict))

            return patterns

    def get_patterns_by_session(self, session_id: str) -> list[PatternRecord]:
        """
        Get all patterns detected in a specific session.

        Args:
            session_id: Session ID to query

        Returns:
            List of patterns detected in that session
        """
        with self._lock:
            data = self._read_atomic()

            patterns = []
            for pattern_dict in data["patterns"] + data["good_patterns"]:
                if session_id in pattern_dict["sessions_affected"]:
                    patterns.append(self._dict_to_pattern(pattern_dict))

            return patterns

    def export_analytics(self) -> dict:
        """
        Export pattern analytics for reporting.

        Returns:
            Dictionary with aggregated statistics
        """
        with self._lock:
            data = self._read_atomic()

            anti_patterns = data["patterns"]
            good_patterns = data["good_patterns"]

            total_anti = len(anti_patterns)
            total_good = len(good_patterns)
            total_occurrences = sum(p["occurrence_count"] for p in anti_patterns)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_anti_patterns": total_anti,
                    "total_good_patterns": total_good,
                    "total_detections": total_occurrences,
                },
                "anti_patterns": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "occurrences": p["occurrence_count"],
                        "sessions_affected": len(p["sessions_affected"]),
                    }
                    for p in sorted(
                        anti_patterns,
                        key=lambda x: -x["occurrence_count"],
                    )
                ],
                "good_patterns": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "occurrences": p["occurrence_count"],
                        "sessions_affected": len(p["sessions_affected"]),
                    }
                    for p in sorted(
                        good_patterns,
                        key=lambda x: -x["occurrence_count"],
                    )
                ],
            }

    def clear_all(self) -> None:
        """Clear all patterns from storage. Use with caution."""
        with self._lock:
            self._write_atomic({"patterns": [], "good_patterns": []})
            logger.warning("Cleared all patterns from storage")

    # Private methods

    def _read_atomic(self) -> dict[str, list]:
        """
        Read patterns file atomically.

        Returns:
            Dictionary with "patterns" and "good_patterns" keys
        """
        try:
            if not self.patterns_file.exists():
                return {"patterns": [], "good_patterns": []}

            content = self.patterns_file.read_text(encoding="utf-8")
            data: Any = json.loads(content)

            # Validate structure
            if "patterns" not in data:
                data["patterns"] = []
            if "good_patterns" not in data:
                data["good_patterns"] = []

            return cast(dict[str, list], data)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error reading patterns file: {e}")
            return {"patterns": [], "good_patterns": []}

    def _write_atomic(self, data: dict[str, list]) -> None:
        """
        Write patterns file atomically using temp file + rename.

        Args:
            data: Dictionary with "patterns" and "good_patterns" keys
        """
        try:
            # Write to temporary file first
            temp_file = self.patterns_file.with_suffix(".json.tmp")

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.patterns_file)
            logger.debug(f"Wrote patterns to {self.patterns_file}")

        except OSError as e:
            logger.error(f"Error writing patterns file: {e}")
            raise

    @staticmethod
    def _pattern_to_dict(pattern: PatternRecord) -> dict:
        """Convert PatternRecord to dictionary for JSON."""
        return {
            "id": pattern.id,
            "pattern_type": pattern.pattern_type,
            "name": pattern.name,
            "description": pattern.description,
            "trigger_conditions": pattern.trigger_conditions,
            "example_sequence": pattern.example_sequence,
            "occurrence_count": pattern.occurrence_count,
            "sessions_affected": pattern.sessions_affected,
            "correct_approach": pattern.correct_approach,
            "delegation_suggestion": pattern.delegation_suggestion,
        }

    @staticmethod
    def _dict_to_pattern(data: dict) -> PatternRecord:
        """Convert dictionary (from JSON) to PatternRecord."""
        return PatternRecord(
            id=data["id"],
            pattern_type=data["pattern_type"],
            name=data["name"],
            description=data["description"],
            trigger_conditions=data["trigger_conditions"],
            example_sequence=data["example_sequence"],
            occurrence_count=data.get("occurrence_count", 0),
            sessions_affected=data.get("sessions_affected", []),
            correct_approach=data.get("correct_approach"),
            delegation_suggestion=data.get("delegation_suggestion"),
        )
