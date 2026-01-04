"""
AutonomyRecommender - Adaptive autonomy level management for CIGS.

Recommends appropriate autonomy levels based on:
- Average compliance from last 5 sessions
- Anti-pattern count
- Circuit breaker triggers

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 5, Section 5.4)

Decision Matrix:
- Observer (>90% compliance): Minimal guidance, trust developer
- Consultant (70-90% compliance): Moderate guidance, gentle nudges
- Collaborator (50-70% compliance): High guidance, active collaboration
- Operator (<50% compliance): Strict enforcement, mandatory acknowledgment
"""

from dataclasses import dataclass, field

from htmlgraph.cigs.models import (
    AutonomyLevel,
    PatternRecord,
    SessionViolationSummary,
)


@dataclass
class AutonomyRecommender:
    """
    Recommend autonomy level based on compliance history and patterns.

    Implements a four-level decision matrix that adapts guidance intensity
    based on demonstrated delegation compliance and detected anti-patterns.

    Attributes:
        compliance_history: List of compliance rates from recent sessions (0.0-1.0)
        anti_pattern_count: Number of distinct anti-patterns detected
        circuit_breaker_active: Whether circuit breaker was triggered in recent sessions
    """

    compliance_history: list[float] = field(default_factory=list)
    anti_pattern_count: int = 0
    circuit_breaker_active: bool = False

    # Decision matrix thresholds
    OBSERVER_THRESHOLD = 0.90
    CONSULTANT_THRESHOLD = 0.70
    COLLABORATOR_THRESHOLD = 0.50

    def recommend(
        self,
        violations: SessionViolationSummary,
        patterns: list[PatternRecord] | None = None,
        compliance_history: list[float] | None = None,
    ) -> AutonomyLevel:
        """
        Recommend autonomy level for next session.

        Implements decision matrix:
        - Observer (>90% compliance, no anti-patterns)
        - Consultant (70-90% compliance OR 1-2 anti-patterns)
        - Collaborator (50-70% compliance OR 3+ anti-patterns)
        - Operator (<50% compliance OR circuit breaker triggered)

        Args:
            violations: Summary of violations from current/recent session
            patterns: Detected behavioral patterns (if any)
            compliance_history: Optional list of compliance rates from last 5 sessions

        Returns:
            AutonomyLevel recommendation with messaging intensity and enforcement mode
        """
        # Calculate average compliance
        if compliance_history:
            avg_compliance = sum(compliance_history) / len(compliance_history)
        else:
            avg_compliance = violations.compliance_rate

        # Count anti-patterns
        anti_pattern_count = 0
        if patterns:
            anti_pattern_count = len(
                [p for p in patterns if p.pattern_type == "anti-pattern"]
            )

        # Check circuit breaker status
        circuit_breaker_active = violations.circuit_breaker_triggered

        # Apply decision matrix
        return self._apply_decision_matrix(
            avg_compliance=avg_compliance,
            anti_pattern_count=anti_pattern_count,
            circuit_breaker_active=circuit_breaker_active,
            violations_count=violations.total_violations,
            patterns=patterns or [],
        )

    def _apply_decision_matrix(
        self,
        avg_compliance: float,
        anti_pattern_count: int,
        circuit_breaker_active: bool,
        violations_count: int,
        patterns: list[PatternRecord],
    ) -> AutonomyLevel:
        """
        Apply the decision matrix to determine autonomy level.

        Decision Logic:
        1. If circuit breaker active -> OPERATOR (strict)
        2. If avg_compliance > 90% AND no anti-patterns -> OBSERVER (minimal)
        3. If avg_compliance > 70% OR anti_pattern_count <= 2 -> CONSULTANT (moderate)
        4. If avg_compliance > 50% OR anti_pattern_count <= 4 -> COLLABORATOR (high)
        5. Otherwise -> OPERATOR (strict)

        Args:
            avg_compliance: Average compliance rate (0.0-1.0)
            anti_pattern_count: Number of anti-patterns detected
            circuit_breaker_active: Whether circuit breaker is active
            violations_count: Total violation count
            patterns: List of detected patterns

        Returns:
            AutonomyLevel recommendation
        """
        # Circuit breaker takes precedence
        if circuit_breaker_active:
            return AutonomyLevel(
                level="operator",
                messaging_intensity="maximal",
                enforcement_mode="strict",
                reason=f"Circuit breaker triggered ({violations_count} violations). Strict enforcement required.",
                based_on_violations=violations_count,
                based_on_patterns=[
                    p.name for p in patterns if p.pattern_type == "anti-pattern"
                ],
            )

        # Observer: Excellent compliance, no patterns
        if avg_compliance >= self.OBSERVER_THRESHOLD and anti_pattern_count == 0:
            return AutonomyLevel(
                level="observer",
                messaging_intensity="minimal",
                enforcement_mode="guidance",
                reason=f"Excellent compliance ({avg_compliance:.0%}). Minimal guidance needed.",
                based_on_violations=violations_count,
                based_on_patterns=[
                    p.name for p in patterns if p.pattern_type == "anti-pattern"
                ],
            )

        # Consultant: Good compliance (70-90%) AND few anti-patterns (<=2)
        if (
            self.CONSULTANT_THRESHOLD <= avg_compliance < self.OBSERVER_THRESHOLD
        ) and anti_pattern_count <= 2:
            anti_pattern_list = [
                p.name for p in patterns if p.pattern_type == "anti-pattern"
            ]
            pattern_note = (
                f", {anti_pattern_count} anti-pattern(s)"
                if anti_pattern_count > 0
                else ""
            )

            return AutonomyLevel(
                level="consultant",
                messaging_intensity="moderate",
                enforcement_mode="guidance",
                reason=f"Good compliance ({avg_compliance:.0%}){pattern_note}. Moderate guidance recommended.",
                based_on_violations=violations_count,
                based_on_patterns=anti_pattern_list,
            )

        # Collaborator: Moderate compliance (50-70%) AND moderate anti-patterns (3-4)
        if (
            self.COLLABORATOR_THRESHOLD <= avg_compliance < self.CONSULTANT_THRESHOLD
        ) and (2 < anti_pattern_count <= 4):
            anti_pattern_list = [
                p.name for p in patterns if p.pattern_type == "anti-pattern"
            ]
            return AutonomyLevel(
                level="collaborator",
                messaging_intensity="high",
                enforcement_mode="strict",
                reason=f"Moderate compliance ({avg_compliance:.0%}), {anti_pattern_count} anti-pattern(s). Active guidance needed.",
                based_on_violations=violations_count,
                based_on_patterns=anti_pattern_list,
            )

        # Operator: Low compliance (<50%) OR many anti-patterns (5+)
        anti_pattern_list = [
            p.name for p in patterns if p.pattern_type == "anti-pattern"
        ]
        return AutonomyLevel(
            level="operator",
            messaging_intensity="maximal",
            enforcement_mode="strict",
            reason=f"Low compliance ({avg_compliance:.0%}), {anti_pattern_count} anti-pattern(s). Strict enforcement required.",
            based_on_violations=violations_count,
            based_on_patterns=anti_pattern_list,
        )

    def recommend_from_compliance_history(
        self,
        compliance_history: list[float],
        anti_pattern_count: int = 0,
        circuit_breaker_active: bool = False,
    ) -> AutonomyLevel:
        """
        Recommend autonomy level from compliance history alone.

        Convenience method for cross-session recommendations when
        only compliance history is available.

        Args:
            compliance_history: List of compliance rates from last 5 sessions
            anti_pattern_count: Number of anti-patterns detected
            circuit_breaker_active: Whether circuit breaker was triggered

        Returns:
            AutonomyLevel recommendation
        """
        if not compliance_history:
            # Default to Consultant if no history
            return AutonomyLevel(
                level="consultant",
                messaging_intensity="moderate",
                enforcement_mode="guidance",
                reason="No compliance history. Defaulting to moderate guidance.",
                based_on_violations=0,
                based_on_patterns=[],
            )

        avg_compliance = sum(compliance_history) / len(compliance_history)

        # Create minimal summary for decision matrix
        violations = SessionViolationSummary(
            session_id="unknown",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=circuit_breaker_active,
            compliance_rate=avg_compliance,
        )

        return self.recommend(
            violations=violations,
            patterns=None,
            compliance_history=compliance_history,
        )

    def evaluate_autonomy_transition(
        self,
        current_level: str,
        new_level: str,
    ) -> dict[str, str | int]:
        """
        Evaluate transition between autonomy levels.

        Returns metadata about the transition for logging/reporting.

        Args:
            current_level: Current autonomy level ("observer", "consultant", etc.)
            new_level: New autonomy level

        Returns:
            Dictionary with transition details
        """
        level_order = ["observer", "consultant", "collaborator", "operator"]

        current_idx = (
            level_order.index(current_level) if current_level in level_order else -1
        )
        new_idx = level_order.index(new_level) if new_level in level_order else -1

        if new_idx < 0 or current_idx < 0:
            return {
                "transition": "unknown",
                "direction": "unknown",
                "severity": "unknown",
            }

        if new_idx > current_idx:
            direction = "escalated"
            severity = "high" if new_idx - current_idx > 1 else "moderate"
        elif new_idx < current_idx:
            direction = "relaxed"
            severity = "high" if current_idx - new_idx > 1 else "moderate"
        else:
            direction = "unchanged"
            severity = "none"

        return {
            "transition": f"{current_level} → {new_level}",
            "direction": direction,
            "severity": severity,
            "escalation_level": new_idx,
        }

    def get_messaging_config(self, level: str) -> dict[str, str | bool | int]:
        """
        Get messaging configuration for an autonomy level.

        Returns imperative message configuration based on autonomy level.

        Args:
            level: Autonomy level ("observer", "consultant", "collaborator", "operator")

        Returns:
            Dictionary with messaging configuration
        """
        config: dict[str, dict[str, str | bool | int]] = {
            "observer": {
                "prefix": "💡 GUIDANCE",
                "tone": "informative",
                "includes_cost": False,
                "includes_suggestion": True,
                "requires_acknowledgment": False,
                "escalation_level": 0,
            },
            "consultant": {
                "prefix": "🔴 IMPERATIVE",
                "tone": "commanding",
                "includes_cost": True,
                "includes_suggestion": True,
                "requires_acknowledgment": False,
                "escalation_level": 1,
            },
            "collaborator": {
                "prefix": "⚠️ FINAL WARNING",
                "tone": "urgent",
                "includes_cost": True,
                "includes_suggestion": True,
                "includes_consequences": True,
                "requires_acknowledgment": False,
                "escalation_level": 2,
            },
            "operator": {
                "prefix": "🚨 CIRCUIT BREAKER",
                "tone": "blocking",
                "includes_cost": True,
                "includes_suggestion": True,
                "includes_consequences": True,
                "requires_acknowledgment": True,
                "escalation_level": 3,
            },
        }

        return config.get(level, config["consultant"])

    def estimate_next_level(
        self,
        current_compliance: float,
        projected_violations: int = 0,
    ) -> str:
        """
        Estimate the autonomy level for next session.

        Projects autonomy level based on current trajectory.

        Args:
            current_compliance: Current session's compliance rate
            projected_violations: Projected violations for next session (0 = assume improvement)

        Returns:
            Estimated next autonomy level
        """
        # If violations decrease, estimate improvement
        if projected_violations == 0:
            estimated_compliance = min(1.0, current_compliance + 0.05)
        else:
            # Assume violations stay constant or worsen
            estimated_compliance = max(0.0, current_compliance - 0.05)

        violations = SessionViolationSummary(
            session_id="projected",
            total_violations=0,
            violations_by_type={},
            total_waste_tokens=0,
            circuit_breaker_triggered=False,
            compliance_rate=estimated_compliance,
        )

        recommendation = self.recommend(violations)
        return recommendation.level
