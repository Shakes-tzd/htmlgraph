"""
Imperative Message Generation for CIGS

Generates escalating imperative messages for delegation enforcement.

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 4)
"""

from .models import OperationClassification


class ImperativeMessageGenerator:
    """Generate imperative messages with escalation for delegation violations.

    The generator supports 4 escalation levels:
    - Level 0: Guidance (informative, no cost shown)
    - Level 1: Imperative (commanding, includes cost)
    - Level 2: Final Warning (urgent, includes consequences)
    - Level 3: Circuit Breaker (blocking, requires acknowledgment)

    Each level includes progressively more urgent messaging and additional context.
    """

    ESCALATION_LEVELS = {
        0: {
            "prefix": "💡 GUIDANCE",
            "tone": "informative",
            "includes_cost": False,
            "includes_suggestion": True,
            "includes_consequences": False,
            "requires_acknowledgment": False,
        },
        1: {
            "prefix": "🔴 IMPERATIVE",
            "tone": "commanding",
            "includes_cost": True,
            "includes_suggestion": True,
            "includes_consequences": False,
            "requires_acknowledgment": False,
        },
        2: {
            "prefix": "⚠️ FINAL WARNING",
            "tone": "urgent",
            "includes_cost": True,
            "includes_suggestion": True,
            "includes_consequences": True,
            "requires_acknowledgment": False,
        },
        3: {
            "prefix": "🚨 CIRCUIT BREAKER",
            "tone": "blocking",
            "includes_cost": True,
            "includes_suggestion": True,
            "includes_consequences": True,
            "requires_acknowledgment": True,
        },
    }

    # Tool-specific core messages
    TOOL_MESSAGES = {
        "Read": "YOU MUST delegate file reading to Explorer subagent",
        "Grep": "YOU MUST delegate code search to Explorer subagent",
        "Glob": "YOU MUST delegate file search to Explorer subagent",
        "Edit": "YOU MUST delegate code changes to Coder subagent",
        "Write": "YOU MUST delegate file writing to Coder subagent",
        "NotebookEdit": "YOU MUST delegate notebook editing to Coder subagent",
        "Bash": "YOU MUST delegate command execution to appropriate subagent",
    }

    # Category-specific rationales (WHY delegation is mandatory)
    RATIONALES = {
        "direct_exploration": (
            "Exploration operations have unpredictable scope. "
            "What looks like 'one Read' often becomes 3-5 reads. "
            "Each direct read pollutes your strategic context with tactical details."
        ),
        "direct_implementation": (
            "Implementation requires iteration (write → test → fix → test). "
            "Delegating keeps your context focused on architecture, "
            "while subagent handles the edit-test cycle."
        ),
        "exploration_sequence": (
            "You have already executed multiple exploration operations. "
            "This pattern indicates research work that should be delegated. "
            "Subagent can explore comprehensively and return a summary."
        ),
        "direct_git": (
            "Git operations cascade unpredictably (hooks, conflicts, push failures). "
            "Copilot specializes in git AND costs 60% less than Task()."
        ),
        "direct_testing": (
            "Test execution requires multiple iterations and debugging cycles. "
            "Delegating test runs keeps test output out of your strategic context."
        ),
    }

    def generate(
        self,
        tool: str,
        classification: OperationClassification,
        violation_count: int,
        autonomy_level: str = "strict",
    ) -> str:
        """Generate imperative message based on context.

        Args:
            tool: Tool being used (Read, Grep, Edit, etc.)
            classification: Operation classification with delegation details
            violation_count: Number of violations in current session (0-3+)
            autonomy_level: Current autonomy level ("strict", "guided", "observer")

        Returns:
            Formatted imperative message with appropriate escalation level
        """
        # Determine escalation level (0-3)
        level = min(violation_count, 3)
        config = self.ESCALATION_LEVELS[level]

        message_parts = []

        # 1. Prefix with escalation indicator + core message
        core_msg = self._get_core_message(tool, classification)
        message_parts.append(f"{config['prefix']}: {core_msg}")

        # 2. WHY this is mandatory
        rationale = self._get_rationale(classification)
        message_parts.append(f"\n\n**WHY:** {rationale}")

        # 3. Cost impact (if applicable for this level)
        if config["includes_cost"]:
            cost_msg = self._get_cost_message(classification)
            message_parts.append(f"\n\n**COST IMPACT:** {cost_msg}")

        # 4. What to do instead
        if config["includes_suggestion"]:
            message_parts.append(
                f"\n\n**INSTEAD:** {classification.suggested_delegation}"
            )

        # 5. Consequences (for levels 2+)
        if config["includes_consequences"]:
            consequence = self._get_consequence_message(level)
            message_parts.append(f"\n\n**CONSEQUENCE:** {consequence}")

        # 6. Acknowledgment requirement (level 3 only)
        if config["requires_acknowledgment"]:
            message_parts.append(
                "\n\n**REQUIRED:** Acknowledge this violation before proceeding:\n"
                "`uv run htmlgraph orchestrator acknowledge-violation`\n\n"
                "OR disable enforcement:\n"
                "`uv run htmlgraph orchestrator set-level guidance`"
            )

        return "".join(message_parts)

    def _get_core_message(
        self, tool: str, classification: OperationClassification
    ) -> str:
        """Get core imperative message based on tool.

        Args:
            tool: Tool name
            classification: Operation classification

        Returns:
            Core imperative message
        """
        return self.TOOL_MESSAGES.get(
            tool, f"YOU MUST delegate {tool} operations to appropriate subagent"
        )

    def _get_rationale(self, classification: OperationClassification) -> str:
        """Explain WHY delegation is mandatory.

        Args:
            classification: Operation classification

        Returns:
            Rationale explaining why delegation is required
        """
        # Use category-specific rationale or classification reason
        rationale = self.RATIONALES.get(
            classification.category, "Delegation preserves your strategic context."
        )

        # If classification provides specific reason, append it
        if classification.reason and classification.reason not in rationale:
            rationale = f"{rationale} {classification.reason}"

        return rationale

    def _get_cost_message(self, classification: OperationClassification) -> str:
        """Generate cost impact message.

        Args:
            classification: Operation classification with cost estimates

        Returns:
            Formatted cost impact message
        """
        if classification.predicted_cost > 0 and classification.optimal_cost > 0:
            savings_pct = classification.waste_percentage
            return (
                f"Direct execution costs ~{classification.predicted_cost:,} tokens in your context. "
                f"Delegation would cost ~{classification.optimal_cost:,} tokens "
                f"({savings_pct:.0f}% savings)."
            )
        else:
            # Generic message if costs not available
            return (
                "Direct execution pollutes your context with tactical details. "
                "Delegation isolates these details in subagent context."
            )

    def _get_consequence_message(self, level: int) -> str:
        """Get consequence message for high escalation levels.

        Args:
            level: Escalation level (0-3)

        Returns:
            Consequence message appropriate for the level
        """
        if level == 2:
            return (
                "Next violation will trigger circuit breaker, "
                "requiring manual acknowledgment before further operations."
            )
        elif level == 3:
            return (
                "Circuit breaker is now ACTIVE. "
                "All delegation-required operations require explicit acknowledgment until reset."
            )
        return ""


class PositiveReinforcementGenerator:
    """Generate positive feedback for correct delegation patterns.

    Provides encouraging messages when Claude correctly delegates operations,
    reinforcing good behavior and showing concrete benefits.
    """

    ENCOURAGEMENTS = [
        "Excellent delegation pattern!",
        "Perfect use of subagent!",
        "Context preserved effectively!",
        "Optimal delegation choice!",
        "Great strategic thinking!",
        "Correct workflow applied!",
    ]

    def generate(
        self,
        tool: str,
        cost_savings: int,
        compliance_rate: float,
        session_waste: int = 0,
    ) -> str:
        """Generate positive reinforcement message.

        Args:
            tool: Delegation tool used (Task, spawn_gemini, etc.)
            cost_savings: Estimated tokens saved by delegating
            compliance_rate: Current session compliance rate (0.0-1.0)
            session_waste: Total waste tokens accumulated this session

        Returns:
            Formatted positive reinforcement message
        """
        import random

        base = random.choice(self.ENCOURAGEMENTS)

        message_parts = [f"✅ {base}"]

        # Impact section
        impact_lines = [
            "\n\n**Impact:**",
            f"- Saved ~{cost_savings:,} tokens of context",
            "- Subagent handled tactical details",
            "- Your strategic view remains clean",
        ]
        message_parts.append("\n".join(impact_lines))

        # Session stats section
        stats_lines = [
            "\n\n**Session Stats:**",
            f"- Delegation compliance: {compliance_rate:.0%}",
        ]

        if session_waste > 0:
            stats_lines.append(
                f"- Waste avoided: {session_waste:,} tokens saved by delegating"
            )

        if compliance_rate >= 0.9:
            stats_lines.append(
                "- Outstanding! Keep up the excellent delegation pattern."
            )
        elif compliance_rate >= 0.75:
            stats_lines.append(
                "- Keep it up! Consistent delegation improves response quality."
            )
        else:
            stats_lines.append(
                "- Good progress! Continue delegating to improve efficiency."
            )

        message_parts.append("\n".join(stats_lines))

        return "".join(message_parts)

    def generate_session_summary(
        self,
        total_delegations: int,
        compliance_rate: float,
        efficiency_score: float,
        total_savings: int,
    ) -> str:
        """Generate end-of-session positive summary.

        Args:
            total_delegations: Number of successful delegations
            compliance_rate: Session compliance rate (0.0-1.0)
            efficiency_score: Cost efficiency score (0-100)
            total_savings: Total tokens saved through delegation

        Returns:
            Session summary message
        """
        message_parts = ["## ✅ Delegation Session Summary\n"]

        # Overall performance
        if compliance_rate >= 0.9 and efficiency_score >= 80:
            message_parts.append(
                "**Outstanding Performance!** Excellent delegation discipline.\n"
            )
        elif compliance_rate >= 0.75:
            message_parts.append(
                "**Good Performance!** Strong delegation patterns observed.\n"
            )
        else:
            message_parts.append(
                "**Room for Improvement.** Continue working on delegation.\n"
            )

        # Metrics
        metrics = [
            "\n**Metrics:**",
            f"- Total delegations: {total_delegations}",
            f"- Compliance rate: {compliance_rate:.1%}",
            f"- Efficiency score: {efficiency_score:.0f}/100",
            f"- Tokens saved: {total_savings:,}",
        ]
        message_parts.append("\n".join(metrics))

        # Encouragement
        if compliance_rate < 0.75:
            message_parts.append(
                "\n\n**Next Session:** Focus on delegating exploration and implementation "
                "tasks to specialized subagents."
            )

        return "\n".join(message_parts)
