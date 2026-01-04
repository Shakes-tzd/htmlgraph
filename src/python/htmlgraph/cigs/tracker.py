"""
ViolationTracker for CIGS (Computational Imperative Guidance System)

Tracks delegation violations in JSONL format, providing thread-safe access
to violation records and session metrics.

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 3)
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from htmlgraph.cigs.models import (
    OperationClassification,
    SessionViolationSummary,
    TokenCost,
    ViolationRecord,
    ViolationType,
)


class ViolationTracker:
    """
    Thread-safe tracker for delegation violations.

    Stores violations in JSONL format at `.htmlgraph/cigs/violations.jsonl`
    """

    def __init__(self, graph_dir: Path | None = None):
        """
        Initialize ViolationTracker.

        Args:
            graph_dir: Root directory for HtmlGraph (defaults to .htmlgraph)
        """
        if graph_dir is None:
            graph_dir = Path.cwd() / ".htmlgraph"

        self.graph_dir = Path(graph_dir)
        self.cigs_dir = self.graph_dir / "cigs"
        self.violations_file = self.cigs_dir / "violations.jsonl"

        # Create directory if needed
        self.cigs_dir.mkdir(parents=True, exist_ok=True)

        # Thread-safe access
        self._lock = threading.RLock()

        # Current session ID (set externally or detect from environment)
        self._session_id: str | None = self._detect_session_id()

    def _detect_session_id(self) -> str | None:
        """Detect current session ID from environment or HtmlGraph session manager."""
        # First check environment variable
        if "HTMLGRAPH_SESSION_ID" in os.environ:
            return os.environ["HTMLGRAPH_SESSION_ID"]

        # Try to get from session manager if available
        try:
            from htmlgraph.session_manager import SessionManager

            sm = SessionManager(self.graph_dir)
            current = sm.get_active_session()
            if current:
                return str(current.id)
        except Exception:
            pass

        return None

    def record_violation(
        self,
        tool: str,
        params: dict,
        classification: OperationClassification,
        predicted_waste: int,
    ) -> str:
        """
        Record a violation.

        Args:
            tool: Tool name (Read, Grep, Edit, etc.)
            params: Tool parameters passed
            classification: OperationClassification with context
            predicted_waste: Predicted wasted tokens

        Returns:
            Violation ID
        """
        with self._lock:
            violation_id = f"viol-{uuid4().hex[:12]}"
            timestamp = datetime.utcnow()

            # Get current session
            session_id = self._session_id or "unknown"

            record = ViolationRecord(
                id=violation_id,
                session_id=session_id,
                timestamp=timestamp,
                tool=tool,
                tool_params=params,
                violation_type=self._classify_violation(tool, classification),
                context_before=None,
                should_have_delegated_to=classification.suggested_delegation,
                actual_cost_tokens=classification.predicted_cost,
                optimal_cost_tokens=classification.optimal_cost,
                waste_tokens=predicted_waste,
                warning_level=1,
                was_warned=False,
                warning_ignored=False,
                agent="claude-code",
                feature_id=None,
            )

            # Append to JSONL file
            self._append_violation(record)

            return violation_id

    def _classify_violation(
        self, tool: str, classification: OperationClassification
    ) -> ViolationType:
        """Classify the violation type based on tool and context."""
        if classification.is_exploration_sequence:
            return ViolationType.EXPLORATION_SEQUENCE

        # Map tools to violation types
        if tool in ("Read", "Grep", "Glob"):
            return ViolationType.DIRECT_EXPLORATION
        elif tool in ("Edit", "Write", "NotebookEdit"):
            return ViolationType.DIRECT_IMPLEMENTATION
        elif tool == "Bash" and "git" in str(classification.reason).lower():
            return ViolationType.DIRECT_GIT
        elif tool == "Bash":
            return ViolationType.DIRECT_TESTING

        return ViolationType.DIRECT_EXPLORATION

    def _append_violation(self, record: ViolationRecord) -> None:
        """Append violation record to JSONL file (thread-safe)."""
        with self._lock:
            try:
                with open(self.violations_file, "a") as f:
                    f.write(json.dumps(record.to_dict()) + "\n")
            except Exception as e:
                # Log but don't crash on storage errors
                print(f"Warning: Failed to record violation: {e}")

    def get_session_violations(
        self, session_id: str | None = None
    ) -> SessionViolationSummary:
        """
        Get violations for current or specific session.

        Args:
            session_id: Session ID (defaults to current session)

        Returns:
            SessionViolationSummary with aggregated metrics
        """
        if session_id is None:
            session_id = self._session_id or "unknown"

        with self._lock:
            violations = self._load_violations()

        # Filter to session
        session_violations = [v for v in violations if v.session_id == session_id]

        # Aggregate by type
        violations_by_type = {}
        for vtype in ViolationType:
            count = sum(1 for v in session_violations if v.violation_type == vtype)
            if count > 0:
                violations_by_type[vtype] = count

        # Calculate totals
        total_violations = len(session_violations)
        total_waste = sum(v.waste_tokens for v in session_violations)
        circuit_breaker = total_violations >= 3

        # Compliance rate: 1.0 = no violations, 0.0 = many violations
        # For simplicity: (max_violations - actual) / max_violations
        # where max_violations = 5 (violation rate saturates)
        compliance_rate = max(0.0, 1.0 - (total_violations / 5.0))

        return SessionViolationSummary(
            session_id=session_id,
            total_violations=total_violations,
            violations_by_type=violations_by_type,
            total_waste_tokens=total_waste,
            circuit_breaker_triggered=circuit_breaker,
            compliance_rate=compliance_rate,
            violations=session_violations,
        )

    def get_recent_violations(self, sessions: int = 5) -> list[ViolationRecord]:
        """
        Get violations from last N sessions.

        Args:
            sessions: Number of sessions to include

        Returns:
            List of violation records from recent sessions
        """
        with self._lock:
            violations = self._load_violations()

        # Group by session and get N most recent
        session_ids = set(v.session_id for v in violations)
        recent_sessions = sorted(session_ids)[-sessions:]

        return [v for v in violations if v.session_id in recent_sessions]

    def record_actual_cost(self, tool: str, cost: TokenCost) -> None:
        """
        Update violation with actual cost after execution.

        This updates the most recent violation for the given tool.

        Args:
            tool: Tool name
            cost: TokenCost with actual metrics
        """
        with self._lock:
            violations = self._load_violations()

        if not violations:
            return

        # Find most recent violation for this tool (in current session)
        session_id = self._session_id or "unknown"
        matching = [
            v for v in violations if v.tool == tool and v.session_id == session_id
        ]

        if not matching:
            return

        # Update most recent
        latest = matching[-1]
        latest.actual_cost_tokens = cost.total_tokens
        latest.waste_tokens = cost.total_tokens - latest.optimal_cost_tokens

        # Rewrite file (simple approach - replace entire file)
        self._write_violations(violations)

    def _write_violations(self, violations: list[ViolationRecord]) -> None:
        """Write violations back to JSONL file."""
        with self._lock:
            try:
                with open(self.violations_file, "w") as f:
                    for v in violations:
                        f.write(json.dumps(v.to_dict()) + "\n")
            except Exception as e:
                print(f"Warning: Failed to write violations: {e}")

    def _load_violations(self) -> list[ViolationRecord]:
        """Load all violations from JSONL file."""
        violations: list[ViolationRecord] = []

        if not self.violations_file.exists():
            return violations

        try:
            with open(self.violations_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        violations.append(ViolationRecord.from_dict(data))
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Warning: Failed to parse violation record: {e}")
                        continue
        except Exception as e:
            print(f"Warning: Failed to load violations: {e}")

        return violations

    def get_session_waste(self) -> int:
        """
        Get total wasted tokens for current session.

        Returns:
            Total waste tokens
        """
        summary = self.get_session_violations()
        return summary.total_waste_tokens

    def set_session_id(self, session_id: str) -> None:
        """
        Set the current session ID.

        Args:
            session_id: Session ID to use for subsequent violations
        """
        self._session_id = session_id

    def clear_session_file(self) -> None:
        """
        Clear the violations file (useful for testing).

        WARNING: This deletes all violation records!
        """
        with self._lock:
            try:
                if self.violations_file.exists():
                    self.violations_file.unlink()
            except Exception as e:
                print(f"Warning: Failed to clear violations file: {e}")
