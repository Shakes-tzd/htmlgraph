"""
Integration tests for CIGS hook flow simulation.

Simulates the complete lifecycle of CIGS hooks through a realistic session:
1. SessionStart: Load history, set autonomy
2. UserPromptSubmit: Detect intent, inject reminders
3. PreToolUse: Generate imperatives, track violations
4. Tool execution (simulated)
5. PostToolUse: Cost accounting, feedback
6. Stop: Session summary, pattern analysis

Reference: .htmlgraph/spikes/computational-imperative-guidance-system-design.md (Part 2)
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from htmlgraph.cigs import (
    AutonomyRecommender,
    ImperativeMessageGenerator,
    PatternDetector,
    PositiveReinforcementGenerator,
    ViolationTracker,
)
from htmlgraph.cigs.cost import CostCalculator


@dataclass
class HookContext:
    """Simulated hook execution context."""

    session_id: str
    graph_dir: Path
    tool_history: list[dict[str, Any]]
    violation_count: int = 0
    autonomy_level: str = "strict"


class MockHookSystem:
    """Mock hook system for testing CIGS integration."""

    def __init__(self, graph_dir: Path):
        self.graph_dir = graph_dir
        self.tracker = ViolationTracker(graph_dir)
        self.pattern_detector = PatternDetector()
        self.cost_calc = CostCalculator()
        self.message_gen = ImperativeMessageGenerator()
        self.pos_gen = PositiveReinforcementGenerator()
        self.autonomy_rec = AutonomyRecommender()
        self.context: HookContext | None = None

    def session_start(self, session_id: str) -> dict[str, Any]:
        """Simulate SessionStart hook."""
        self.tracker.set_session_id(session_id)
        self.context = HookContext(
            session_id=session_id,
            graph_dir=self.graph_dir,
            tool_history=[],
        )

        # Load violation history
        summary = self.tracker.get_session_violations()

        # Recommend autonomy level
        autonomy = self.autonomy_rec.recommend(summary)
        self.context.autonomy_level = autonomy.level

        # Build context injection
        context_msg = f"""## CIGS Status

Autonomy Level: {autonomy.level.upper()}
Previous Violations: {summary.total_violations}
Compliance Rate: {summary.compliance_rate:.1%}

IMPERATIVE: Follow delegation principles for optimal efficiency.
"""

        return {
            "hookEventName": "SessionStart",
            "additionalContext": context_msg,
            "autonomy_level": autonomy.level,
            "violations_summary": summary,
        }

    def user_prompt_submit(self, prompt: str) -> dict[str, Any]:
        """Simulate UserPromptSubmit hook."""
        if not self.context:
            raise RuntimeError("Session not started")

        # Classify prompt intent
        involves_exploration = any(
            kw in prompt.lower()
            for kw in ["search", "find", "explore", "analyze", "read", "grep", "look"]
        )
        involves_implementation = any(
            kw in prompt.lower()
            for kw in [
                "edit",
                "write",
                "modify",
                "change",
                "update",
                "fix",
                "implement",
            ]
        )
        involves_git = any(
            kw in prompt.lower() for kw in ["commit", "push", "git", "merge"]
        )

        # Generate pre-response guidance
        guidance_parts = []

        if involves_exploration:
            guidance_parts.append(
                "IMPERATIVE: This request involves exploration. "
                "YOU MUST use spawn_gemini() (FREE). "
                "DO NOT use Read/Grep/Glob directly."
            )

        if involves_implementation:
            guidance_parts.append(
                "IMPERATIVE: This request involves code changes. "
                "YOU MUST use spawn_codex() or Task(). "
                "DO NOT use Edit/Write directly."
            )

        if involves_git:
            guidance_parts.append(
                "IMPERATIVE: This request involves git operations. "
                "YOU MUST use spawn_copilot(). "
                "DO NOT run git commands directly."
            )

        if self.context.violation_count > 0:
            guidance_parts.append(
                f"WARNING: You have {self.context.violation_count} violations this session. "
                f"Circuit breaker triggers at 3."
            )

        guidance = "\n\n".join(guidance_parts) if guidance_parts else ""

        return {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": guidance,
            "intent": {
                "exploration": involves_exploration,
                "implementation": involves_implementation,
                "git": involves_git,
            },
        }

    def pre_tool_use(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Simulate PreToolUse hook."""
        if not self.context:
            raise RuntimeError("Session not started")

        # Quick allow for orchestrator tools
        if tool in ["Task", "AskUserQuestion", "TodoWrite"]:
            return {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": "",
            }

        # Classify operation
        is_exploration_sequence = (
            sum(
                1
                for h in self.context.tool_history[-5:]
                if h.get("tool") in ["Read", "Grep", "Glob"]
            )
            >= 2
        )

        classification = self.cost_calc.classify_operation(
            tool, params, is_exploration_sequence=is_exploration_sequence
        )

        # Generate imperative message if should delegate
        if classification.category in ["exploration", "implementation"]:
            message = self.message_gen.generate(
                tool=tool,
                classification=classification,
                violation_count=self.context.violation_count,
                autonomy_level=self.context.autonomy_level,
            )

            # Record violation
            predicted_waste = (
                classification.predicted_cost - classification.optimal_cost
            )
            self.tracker.record_violation(
                tool=tool,
                params=params,
                classification=classification,
                predicted_waste=predicted_waste,
            )
            self.context.violation_count += 1

            return {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",  # Guidance, not blocking
                "additionalContext": message,
                "classification": classification,
            }

        return {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": "",
        }

    def execute_tool(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Simulate tool execution."""
        # Record in tool history
        if self.context:
            self.context.tool_history.append({"tool": tool, **params})

        # Simulate results based on tool
        if tool == "Read":
            return {
                "output": f"# File contents for {params.get('file_path', 'unknown')}\n...",
                "cost": 5000,
            }
        elif tool == "Grep":
            return {
                "output": f"Found matches for {params.get('pattern', 'unknown')}",
                "cost": 3000,
            }
        elif tool == "Edit":
            return {"output": "File edited successfully", "cost": 4000}
        elif tool == "Task":
            return {
                "output": "Task delegated successfully",
                "cost": 500,
            }
        else:
            return {"output": "Operation completed", "cost": 2000}

    def post_tool_use(
        self, tool: str, params: dict[str, Any], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Simulate PostToolUse hook."""
        if not self.context:
            raise RuntimeError("Session not started")

        # Calculate actual cost
        actual_cost = self.cost_calc.calculate_actual_cost(tool, result)

        # Determine if this was delegation or direct
        was_delegation = tool in ["Task"] or tool.startswith("spawn_")

        if was_delegation:
            # Positive reinforcement
            summary = self.tracker.get_session_violations()
            message = self.pos_gen.generate(
                tool=tool,
                cost_savings=actual_cost.estimated_savings,
                compliance_rate=summary.compliance_rate,
            )

            return {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
                "cost": actual_cost,
            }
        else:
            # Cost accounting for direct execution
            summary = self.tracker.get_session_violations()

            # Get predicted cost from PreToolUse (simplified)
            classification = self.cost_calc.classify_operation(tool, params)

            message = f"""Direct execution completed.

**Cost Impact:**
- Actual cost: {actual_cost.total_tokens} tokens
- If delegated: ~{classification.optimal_cost} tokens
- Waste: {actual_cost.total_tokens - classification.optimal_cost} tokens

**Session Statistics:**
- Violations: {summary.total_violations}
- Total waste: {summary.total_waste_tokens} tokens
- Compliance rate: {summary.compliance_rate:.1%}

REFLECTION: Consider delegating similar operations in the future.
"""

            return {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
                "cost": actual_cost,
            }

    def stop(self) -> dict[str, Any]:
        """Simulate Stop hook (session end)."""
        if not self.context:
            raise RuntimeError("Session not started")

        # Get session summary
        summary = self.tracker.get_session_violations()

        # Detect patterns
        patterns = self.pattern_detector.detect_all_patterns(self.context.tool_history)

        # Recommend autonomy for next session
        autonomy = self.autonomy_rec.recommend(summary, patterns)

        # Build summary report
        violations_detail = ""
        for vtype, count in summary.violations_by_type.items():
            violations_detail += f"  • {vtype}: {count}\n"

        patterns_detail = ""
        for pattern in patterns:
            patterns_detail += f"  • {pattern.name}: {pattern.description}\n"

        report = f"""
## CIGS Session Summary

### Delegation Metrics
- **Compliance Rate:** {summary.compliance_rate:.1%}
- **Violations:** {summary.total_violations} (threshold: 3)
- **Circuit Breaker:** {"Triggered 🚨" if summary.circuit_breaker_triggered else "Not triggered"}

### Cost Analysis
- **Total Waste:** {summary.total_waste_tokens} tokens

### Violations by Type
{violations_detail if violations_detail else "  (none)"}

### Detected Patterns
{patterns_detail if patterns_detail else "  (none)"}

### Autonomy Recommendation
**Next Session:** {autonomy.level}
**Reason:** {autonomy.reason}
**Messaging Intensity:** {autonomy.messaging_intensity}
"""

        return {
            "hookEventName": "Stop",
            "additionalContext": report,
            "summary": summary,
            "patterns": patterns,
            "autonomy_recommendation": autonomy,
        }


class TestHookFlowScenarios:
    """Test realistic hook flow scenarios."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def hook_system(self, temp_graph_dir):
        return MockHookSystem(temp_graph_dir)

    def test_complete_session_lifecycle(self, hook_system):
        """Test complete session from start to stop."""
        # 1. SessionStart
        session_result = hook_system.session_start("sess-lifecycle-test")

        assert session_result["hookEventName"] == "SessionStart"
        assert "autonomy_level" in session_result
        assert "CIGS Status" in session_result["additionalContext"]

        # 2. UserPromptSubmit
        prompt_result = hook_system.user_prompt_submit(
            "Search the codebase for authentication patterns"
        )

        assert prompt_result["hookEventName"] == "UserPromptSubmit"
        assert prompt_result["intent"]["exploration"]
        assert "spawn_gemini()" in prompt_result["additionalContext"]

        # 3. PreToolUse
        pre_result = hook_system.pre_tool_use("Read", {"file_path": "/test/auth.py"})

        assert pre_result["hookEventName"] == "PreToolUse"
        assert pre_result["permissionDecision"] == "allow"
        assert (
            "IMPERATIVE" in pre_result["additionalContext"]
            or "GUIDANCE" in pre_result["additionalContext"]
        )

        # 4. Tool execution
        tool_result = hook_system.execute_tool("Read", {"file_path": "/test/auth.py"})

        assert "output" in tool_result
        assert "cost" in tool_result

        # 5. PostToolUse
        post_result = hook_system.post_tool_use(
            "Read", {"file_path": "/test/auth.py"}, tool_result
        )

        assert post_result["hookEventName"] == "PostToolUse"
        assert "Cost Impact" in post_result["additionalContext"]

        # 6. Stop
        stop_result = hook_system.stop()

        assert stop_result["hookEventName"] == "Stop"
        assert "Session Summary" in stop_result["additionalContext"]
        assert stop_result["summary"].total_violations >= 1

    def test_exploration_sequence_detection(self, hook_system):
        """Test detection of exploration sequence pattern."""
        hook_system.session_start("sess-exploration-seq")

        # Multiple exploration operations
        for file_path in ["/test/file1.py", "/test/file2.py", "/test/file3.py"]:
            hook_system.user_prompt_submit(f"Read {file_path}")
            hook_system.pre_tool_use("Read", {"file_path": file_path})
            result = hook_system.execute_tool("Read", {"file_path": file_path})
            hook_system.post_tool_use("Read", {"file_path": file_path}, result)

        # Stop and check for pattern
        stop_result = hook_system.stop()

        patterns = stop_result["patterns"]
        exploration_patterns = [p for p in patterns if p.name == "exploration_sequence"]

        assert len(exploration_patterns) > 0
        assert "exploration_sequence" in stop_result["additionalContext"]

    def test_circuit_breaker_trigger(self, hook_system):
        """Test circuit breaker triggering at 3 violations."""
        hook_system.session_start("sess-circuit-breaker")

        # Trigger 3 violations
        for i in range(3):
            hook_system.user_prompt_submit(f"Read file {i}")
            pre_result = hook_system.pre_tool_use(
                "Read", {"file_path": f"/test/file{i}.py"}
            )
            result = hook_system.execute_tool(
                "Read", {"file_path": f"/test/file{i}.py"}
            )
            hook_system.post_tool_use(
                "Read", {"file_path": f"/test/file{i}.py"}, result
            )

            # Check escalation level
            if i == 2:  # Third violation (warning level 2, not 3 yet)
                assert (
                    "WARNING" in pre_result["additionalContext"]
                    or "CIRCUIT" in pre_result["additionalContext"]
                )

        # Verify circuit breaker in summary
        stop_result = hook_system.stop()
        assert stop_result["summary"].circuit_breaker_triggered
        assert "Triggered 🚨" in stop_result["additionalContext"]

    def test_positive_reinforcement_for_delegation(self, hook_system):
        """Test positive reinforcement when using Task()."""
        hook_system.session_start("sess-positive")

        # Use delegation (Task)
        hook_system.user_prompt_submit("Delegate exploration to subagent")
        hook_system.pre_tool_use(
            "Task", {"prompt": "Explore codebase for auth patterns"}
        )
        result = hook_system.execute_tool(
            "Task", {"prompt": "Explore codebase for auth patterns"}
        )
        post_result = hook_system.post_tool_use(
            "Task", {"prompt": "Explore codebase for auth patterns"}, result
        )

        # Should get positive feedback
        assert "✅" in post_result["additionalContext"]
        assert "Impact" in post_result["additionalContext"]

    def test_autonomy_level_escalation(self, hook_system):
        """Test autonomy level escalation with violations."""
        # Session 1: High violations
        hook_system.session_start("sess-autonomy-1")

        for i in range(5):
            hook_system.user_prompt_submit(f"Read file {i}")
            hook_system.pre_tool_use("Read", {"file_path": f"/test/file{i}.py"})
            result = hook_system.execute_tool(
                "Read", {"file_path": f"/test/file{i}.py"}
            )
            hook_system.post_tool_use(
                "Read", {"file_path": f"/test/file{i}.py"}, result
            )

        stop_result_1 = hook_system.stop()
        autonomy_1 = stop_result_1["autonomy_recommendation"]

        # Should recommend strict enforcement
        assert autonomy_1.level == "operator"
        assert autonomy_1.enforcement_mode == "strict"

    def test_mixed_operations_compliance(self, hook_system):
        """Test session with mix of direct and delegated operations."""
        hook_system.session_start("sess-mixed")

        # Direct operation (violation)
        hook_system.user_prompt_submit("Read auth.py")
        hook_system.pre_tool_use("Read", {"file_path": "/test/auth.py"})
        result1 = hook_system.execute_tool("Read", {"file_path": "/test/auth.py"})
        hook_system.post_tool_use("Read", {"file_path": "/test/auth.py"}, result1)

        # Delegated operation (correct)
        hook_system.user_prompt_submit("Delegate exploration")
        hook_system.pre_tool_use("Task", {"prompt": "Explore codebase"})
        result2 = hook_system.execute_tool("Task", {"prompt": "Explore codebase"})
        hook_system.post_tool_use("Task", {"prompt": "Explore codebase"}, result2)

        # Second direct operation (violation)
        hook_system.user_prompt_submit("Grep for patterns")
        hook_system.pre_tool_use("Grep", {"pattern": "authenticate"})
        result3 = hook_system.execute_tool("Grep", {"pattern": "authenticate"})
        hook_system.post_tool_use("Grep", {"pattern": "authenticate"}, result3)

        # Check compliance
        stop_result = hook_system.stop()

        # Should have 2 violations, 1 delegation
        # Compliance = not perfect but not zero
        assert 0 < stop_result["summary"].compliance_rate < 1.0
        assert stop_result["summary"].total_violations == 2

    def test_session_start_with_history(self, temp_graph_dir):
        """Test SessionStart loads previous session history."""
        # Session 1: Create some violations
        hook_system_1 = MockHookSystem(temp_graph_dir)
        hook_system_1.session_start("sess-history-1")

        for i in range(2):
            hook_system_1.pre_tool_use("Read", {"file_path": f"/test/file{i}.py"})
            result = hook_system_1.execute_tool(
                "Read", {"file_path": f"/test/file{i}.py"}
            )
            hook_system_1.post_tool_use(
                "Read", {"file_path": f"/test/file{i}.py"}, result
            )

        hook_system_1.stop()

        # Session 2: Should load history
        hook_system_2 = MockHookSystem(temp_graph_dir)
        session_result = hook_system_2.session_start("sess-history-2")

        # Should reference previous violations in context
        # (exact format depends on implementation, but should mention history)
        assert "CIGS Status" in session_result["additionalContext"]


class TestErrorHandling:
    """Test error handling in hook flow."""

    @pytest.fixture
    def temp_graph_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_hook_without_session_start_fails(self, temp_graph_dir):
        """Test that hooks fail gracefully without SessionStart."""
        hook_system = MockHookSystem(temp_graph_dir)

        # Try to call PreToolUse without SessionStart
        with pytest.raises(RuntimeError, match="Session not started"):
            hook_system.pre_tool_use("Read", {})

    def test_malformed_tool_params(self, temp_graph_dir):
        """Test handling of malformed tool parameters."""
        hook_system = MockHookSystem(temp_graph_dir)
        hook_system.session_start("sess-malformed")

        # Missing required params - should not crash
        pre_result = hook_system.pre_tool_use("Read", {})

        assert pre_result["hookEventName"] == "PreToolUse"
        assert pre_result["permissionDecision"] == "allow"

    def test_empty_tool_history_patterns(self, temp_graph_dir):
        """Test pattern detection with empty tool history."""
        hook_system = MockHookSystem(temp_graph_dir)
        hook_system.session_start("sess-empty")

        # Stop immediately (no operations)
        stop_result = hook_system.stop()

        assert stop_result["summary"].total_violations == 0
        assert len(stop_result["patterns"]) == 0
        assert stop_result["summary"].compliance_rate == 1.0
