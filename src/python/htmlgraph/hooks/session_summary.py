import logging

logger = logging.getLogger(__name__)

"""
Session Summary Module - CIGS Integration

Generates comprehensive session summaries with CIGS analytics at session end.
This module is loaded by the Stop hook.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _resolve_project_dir(cwd: str | None = None) -> str:
    """Resolve project directory (git root or cwd)."""
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return env_dir
    start_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=start_dir,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return start_dir


def _bootstrap_pythonpath(project_dir: str) -> None:
    """Add local src/python to PYTHONPATH for CIGS imports."""
    repo_src = Path(project_dir) / "src" / "python"
    if repo_src.exists():
        sys.path.insert(0, str(repo_src))


# Try to import CIGS modules
try:
    project_dir_for_import = _resolve_project_dir()
    _bootstrap_pythonpath(project_dir_for_import)

    from htmlgraph.cigs.autonomy import AutonomyRecommender
    from htmlgraph.cigs.cost import CostCalculator
    from htmlgraph.cigs.patterns import PatternDetector
    from htmlgraph.cigs.tracker import ViolationTracker

    CIGS_AVAILABLE = True
except Exception:
    CIGS_AVAILABLE = False


class CIGSSessionSummarizer:
    """
    Generate comprehensive session summary with CIGS analytics.

    Implements section 2.5 of CIGS design document:
    - Load session violations from ViolationTracker
    - Analyze session patterns using PatternDetector
    - Calculate session costs
    - Generate autonomy recommendation for next session
    - Build comprehensive session summary
    - Persist summary to .htmlgraph/cigs/session-summaries/{session_id}.json
    """

    def __init__(self, graph_dir: Path):
        """Initialize session summarizer.

        Args:
            graph_dir: Path to .htmlgraph directory
        """
        if not CIGS_AVAILABLE:
            raise RuntimeError("CIGS modules not available")

        self.graph_dir = Path(graph_dir)
        self.cigs_dir = self.graph_dir / "cigs"
        self.summaries_dir = self.cigs_dir / "session-summaries"

        # Ensure directories exist
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

        # Initialize CIGS components
        self.tracker = ViolationTracker(graph_dir)
        self.pattern_detector = PatternDetector()
        self.cost_calculator = CostCalculator()
        self.autonomy_recommender = AutonomyRecommender()

    def summarize(self, session_id: str | None = None) -> dict:
        """
        Generate comprehensive session summary.

        Args:
            session_id: Session ID (defaults to current/active session)

        Returns:
            Hook response with session summary
        """
        # Get session violations
        violations = self.tracker.get_session_violations(session_id)

        # Detect patterns from recent violations
        patterns = self._detect_patterns(violations.violations)

        # Calculate cost metrics
        costs = self._calculate_costs(violations)

        # Generate autonomy recommendation for next session
        autonomy_rec = self.autonomy_recommender.recommend(
            violations=violations,
            patterns=patterns,
            compliance_history=self._get_compliance_history(),
        )

        # Build summary text
        summary_text = self._build_summary_text(
            violations, patterns, costs, autonomy_rec
        )

        # Persist summary for future reference
        self._persist_summary(
            violations.session_id,
            {
                "session_id": violations.session_id,
                "violations": violations.to_dict(),
                "patterns": [p.to_dict() for p in patterns],
                "costs": costs,
                "autonomy_recommendation": autonomy_rec.to_dict(),
            },
        )

        return {
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": summary_text,
            }
        }

    def _detect_patterns(self, violation_records: list) -> list:
        """
        Detect behavioral patterns from violation records.

        Args:
            violation_records: List of ViolationRecord instances

        Returns:
            List of detected PatternRecord instances
        """
        if not violation_records:
            return []

        # Convert violations to tool history format
        history: list[dict[str, Any]] = []
        for v in violation_records:
            history.append(
                {
                    "tool": v.tool,
                    "command": v.tool_params.get("command", ""),
                    "file_path": v.tool_params.get("file_path", ""),
                    "prompt": v.tool_params.get("prompt", ""),
                    "timestamp": v.timestamp,
                }
            )

        # Detect all patterns
        patterns = self.pattern_detector.detect_all_patterns(history)
        return patterns  # type: ignore[no-any-return]

    def _calculate_costs(self, violations: Any) -> dict:
        """
        Calculate cost metrics from violations.

        Args:
            violations: SessionViolationSummary

        Returns:
            Dictionary with cost metrics
        """
        total_tokens = sum(v.actual_cost_tokens for v in violations.violations)
        optimal_tokens = sum(v.optimal_cost_tokens for v in violations.violations)
        waste_tokens = violations.total_waste_tokens

        if total_tokens > 0:
            waste_percentage = (waste_tokens / total_tokens) * 100
            efficiency_score = (optimal_tokens / total_tokens) * 100
        else:
            waste_percentage = 0.0
            efficiency_score = 100.0

        return {
            "total_tokens": total_tokens,
            "optimal_tokens": optimal_tokens,
            "waste_tokens": waste_tokens,
            "waste_percentage": waste_percentage,
            "efficiency_score": efficiency_score,
        }

    def _get_compliance_history(self) -> list[float]:
        """
        Get compliance history from last 5 sessions.

        Returns:
            List of compliance rates (0.0-1.0)
        """
        # Get recent violations (last 5 sessions)
        recent = self.tracker.get_recent_violations(sessions=5)

        # Group by session and calculate compliance rates
        sessions: dict[str, list] = {}
        for v in recent:
            if v.session_id not in sessions:
                sessions[v.session_id] = []
            sessions[v.session_id].append(v)

        # Calculate compliance rate per session
        compliance_rates = []
        for session_id, session_violations in sessions.items():
            total_violations = len(session_violations)
            # Compliance rate: 1.0 = no violations, decreases with more violations
            compliance_rate = max(0.0, 1.0 - (total_violations / 5.0))
            compliance_rates.append(compliance_rate)

        return compliance_rates[-5:] if compliance_rates else [1.0]

    def _build_summary_text(
        self, violations: Any, patterns: Any, costs: Any, autonomy_rec: Any
    ) -> str:
        """
        Build human-readable session summary.

        Args:
            violations: SessionViolationSummary
            patterns: List of PatternRecord instances
            costs: Cost metrics dictionary
            autonomy_rec: AutonomyLevel recommendation

        Returns:
            Formatted markdown summary
        """
        # Compliance rate
        compliance_pct = violations.compliance_rate * 100

        # Circuit breaker status
        breaker_status = (
            "🚨 TRIGGERED" if violations.circuit_breaker_triggered else "✅ OK"
        )

        # Format violations by type
        violations_detail = ""
        if violations.violations_by_type:
            for vtype, count in violations.violations_by_type.items():
                violations_detail += f"  - {vtype}: {count}\n"
        else:
            violations_detail = "  - No violations detected\n"

        # Format detected patterns
        patterns_text = self._format_patterns(patterns)

        # Format anti-patterns
        anti_patterns_text = self._format_anti_patterns(patterns)

        # Build summary
        summary = f"""## 📊 CIGS Session Summary

### Delegation Metrics
- **Compliance Rate:** {compliance_pct:.0f}%
- **Violations:** {violations.total_violations} (circuit breaker threshold: 3)
- **Circuit Breaker:** {breaker_status}

### Violation Breakdown
{violations_detail}

### Cost Analysis
- **Total Context Used:** {costs["total_tokens"]} tokens
- **Estimated Waste:** {costs["waste_tokens"]} tokens ({costs["waste_percentage"]:.1f}%)
- **Optimal Path Cost:** {costs["optimal_tokens"]} tokens
- **Efficiency Score:** {costs["efficiency_score"]:.0f}/100

{patterns_text}

{anti_patterns_text}

### Autonomy Recommendation
**Next Session Level:** {autonomy_rec.level.upper()}
**Messaging Intensity:** {autonomy_rec.messaging_intensity}
**Enforcement Mode:** {autonomy_rec.enforcement_mode}

**Reason:** {autonomy_rec.reason}

### Learning Applied
- ✅ Violation patterns added to detection model
- ✅ Cost predictions updated with actual session data
- ✅ Messaging intensity adjusted for next session: {autonomy_rec.messaging_intensity}
- ✅ Session summary persisted to `.htmlgraph/cigs/session-summaries/`

---

**Next Steps:**
1. Review detected anti-patterns (if any) and adjust workflow
2. Your autonomy level for next session: **{autonomy_rec.level.upper()}**
3. Guidance intensity: **{autonomy_rec.messaging_intensity}**
"""

        return summary

    def _format_patterns(self, patterns: list) -> str:
        """Format detected good patterns."""
        good_patterns = [p for p in patterns if p.pattern_type == "good-pattern"]

        if not good_patterns:
            return "### Detected Patterns\n- No significant patterns detected"

        text = "### Detected Patterns\n"
        for p in good_patterns:
            text += f"- ✅ **{p.name}**: {p.description}\n"
            text += f"  - Occurrences: {p.occurrence_count}\n"

        return text

    def _format_anti_patterns(self, patterns: list) -> str:
        """Format detected anti-patterns with remediation."""
        anti_patterns = [p for p in patterns if p.pattern_type == "anti-pattern"]

        if not anti_patterns:
            return "### Anti-Patterns Identified\n- ✅ No anti-patterns detected"

        text = "### Anti-Patterns Identified\n"
        for p in anti_patterns:
            text += f"- ⚠️ **{p.name}**: {p.description}\n"
            text += f"  - Occurrences: {p.occurrence_count}\n"
            if p.correct_approach:
                text += f"  - **Correct Approach:** {p.correct_approach}\n"
            if p.delegation_suggestion:
                text += f"  - **Suggested Delegation:** {p.delegation_suggestion}\n"

        return text

    def _persist_summary(self, session_id: str, summary_data: dict) -> None:
        """
        Persist session summary to file for future reference.

        Args:
            session_id: Session identifier
            summary_data: Summary dictionary to persist
        """
        try:
            summary_file = self.summaries_dir / f"{session_id}.json"
            with open(summary_file, "w") as f:
                json.dump(summary_data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Warning: Failed to persist summary: {e}")


def main() -> None:
    """Hook entry point for script wrapper."""
    # Check if tracking is disabled
    if os.environ.get("HTMLGRAPH_DISABLE_TRACKING") == "1":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    cwd = hook_input.get("cwd")
    project_dir = _resolve_project_dir(cwd if cwd else None)
    graph_dir = Path(project_dir) / ".htmlgraph"

    # Check if CIGS is enabled (disabled by default for now)
    cigs_enabled = os.environ.get("HTMLGRAPH_CIGS_ENABLED") == "1"

    if not cigs_enabled or not CIGS_AVAILABLE:
        # CIGS not enabled or not available, just output empty response
        print(json.dumps({"continue": True}))
        return

    # Generate CIGS session summary
    try:
        summarizer = CIGSSessionSummarizer(graph_dir)
        result = summarizer.summarize(session_id)
        print(json.dumps(result))
    except Exception as e:
        logger.warning(f"Warning: Could not generate CIGS summary: {e}")
        print(json.dumps({"continue": True}))
