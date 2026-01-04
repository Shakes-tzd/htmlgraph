#!/usr/bin/env python3
"""
CIGS Wave 2: Hook Integration & CLI

This script launches parallel agents to integrate CIGS components into HtmlGraph hooks and CLI.

Wave 2 Components:
- A2: SessionStart hook enhancement (CIGSSessionInitializer)
- B2: UserPromptSubmit hook enhancement (CIGSPromptInterceptor)
- C2: PreToolUse hook enhancement (CIGSPreToolEnforcer)
- D2: PostToolUse hook enhancement (CIGSPostToolAnalyzer)
- E2: Stop hook enhancement (CIGSSessionSummarizer)
- F2: CLI commands (status, acknowledge-violation, etc.)
- G2: Integration tests
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """Launch Wave 2 agents for CIGS integration."""

    print("=" * 80)
    print("CIGS Wave 2: Hook Integration & CLI")
    print("=" * 80)
    print()

    # Define Wave 2 agents
    agents = [
        {
            "id": "A2-1",
            "name": "SessionStart Hook Enhancement",
            "description": "Integrate CIGSSessionInitializer into session-start.py hook",
            "prompt": """
Integrate CIGS into the SessionStart hook.

**Component:** CIGSSessionInitializer

**Files to modify:**
- packages/claude-plugin/hooks/scripts/session-start.py

**Requirements:**
1. Import CIGS modules (ViolationTracker, PatternAnalyzer, AutonomyRecommender)
2. Load violation history from last 5 sessions
3. Detect patterns using PatternDetector
4. Recommend autonomy level using AutonomyRecommender
5. Generate personalized context injection based on history
6. Return hookSpecificOutput with additionalContext

**Output format:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## CIGS Status\\n\\nAutonomy Level: GUIDED\\n..."
  }
}
```

**Reference:** See .htmlgraph/spikes/computational-imperative-guidance-system-design.md section 2.1

**Testing:** Create test_session_start_cigs.py to verify context injection

Implement the full SessionStart hook enhancement with CIGS integration.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "B2-1",
            "name": "UserPromptSubmit Hook Enhancement",
            "description": "Integrate CIGSPromptInterceptor into user-prompt-submit.py hook",
            "prompt": """
Integrate CIGS into the UserPromptSubmit hook.

**Component:** CIGSPromptInterceptor

**Files to modify:**
- packages/claude-plugin/hooks/scripts/user-prompt-submit.py

**Requirements:**
1. Create PromptClassifier to detect intent (exploration, code changes, git)
2. Load current session violation count
3. Generate pre-response imperative guidance based on intent
4. Include violation warnings if count > 0
5. Return hookSpecificOutput with additionalContext

**Detection logic:**
- Exploration: Keywords like "search", "find", "what files", "analyze"
- Code changes: Keywords like "implement", "fix", "update", "refactor"
- Git: Keywords like "commit", "push", "merge", "branch"

**Output format:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "IMPERATIVE: This request involves exploration. YOU MUST use spawn_gemini()..."
  }
}
```

**Reference:** See design doc section 2.2

**Testing:** Create test_user_prompt_submit_cigs.py with various prompt types

Implement the full UserPromptSubmit hook enhancement.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "C2-1",
            "name": "PreToolUse Hook Enhancement",
            "description": "Integrate CIGSPreToolEnforcer into pretooluse.py hook",
            "prompt": """
Integrate CIGS into the PreToolUse hook.

**Component:** CIGSPreToolEnforcer

**Files to modify:**
- packages/claude-plugin/hooks/scripts/pretooluse.py (or create new orchestrator-pretooluse.py)

**Requirements:**
1. Use existing OrchestratorValidator for base classification
2. Load session violation count from ViolationTracker
3. Classify operation using OperationClassification
4. Generate imperative message using ImperativeMessageGenerator
5. Calculate cost prediction using CostCalculator
6. Record violation if should_delegate=True
7. Return hookSpecificOutput with imperative message

**Tool categories:**
- ALWAYS_ALLOWED: Task, AskUserQuestion, TodoWrite, SDK operations
- EXPLORATION_TOOLS: Read, Grep, Glob
- IMPLEMENTATION_TOOLS: Edit, Write, NotebookEdit

**Escalation levels:**
- Level 0: First occurrence (guidance)
- Level 1: Second occurrence (imperative)
- Level 2: Third occurrence (final warning)
- Level 3: Circuit breaker (requires acknowledgment)

**Output format:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "additionalContext": "🔴 IMPERATIVE: YOU MUST delegate..."
  }
}
```

**Reference:** See design doc section 2.3

**Testing:** Create test_pretooluse_cigs.py with escalation scenarios

Implement the full PreToolUse hook enhancement with escalation.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "D2-1",
            "name": "PostToolUse Hook Enhancement",
            "description": "Integrate CIGSPostToolAnalyzer into posttooluse.py hook",
            "prompt": """
Integrate CIGS into the PostToolUse hook.

**Component:** CIGSPostToolAnalyzer

**Files to modify:**
- packages/claude-plugin/hooks/scripts/posttooluse.py (or create new orchestrator-posttooluse.py)

**Requirements:**
1. Calculate actual cost using CostCalculator
2. Load prediction from ViolationTracker (if violation was recorded in PreToolUse)
3. Determine if operation was delegation (Task, spawn_*)
4. Generate positive reinforcement for delegations
5. Generate cost accounting for direct executions
6. Update violation tracker with actual costs
7. Record ignored warnings for pattern detection

**Two paths:**
- **Delegation:** Positive reinforcement with savings calculation
- **Direct execution:** Cost accounting with reflection

**Output format (delegation):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "✅ Correct delegation pattern used. Saved ~4500 tokens..."
  }
}
```

**Output format (violation):**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "📊 Direct execution completed. Cost Impact (Violation): ..."
  }
}
```

**Reference:** See design doc section 2.4

**Testing:** Create test_posttooluse_cigs.py with delegation and violation scenarios

Implement the full PostToolUse hook enhancement.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "E2-1",
            "name": "Stop Hook Enhancement",
            "description": "Integrate CIGSSessionSummarizer into stop.py hook",
            "prompt": """
Integrate CIGS into the Stop hook.

**Component:** CIGSSessionSummarizer

**Files to modify:**
- packages/claude-plugin/hooks/scripts/stop.py

**Requirements:**
1. Load session violations from ViolationTracker
2. Analyze session patterns using PatternAnalyzer
3. Calculate session costs
4. Generate autonomy recommendation for next session
5. Build comprehensive session summary
6. Persist summary to .htmlgraph/cigs/session-summaries/{session_id}.json

**Summary sections:**
- Delegation Metrics (compliance rate, violations, circuit breaker)
- Cost Analysis (total tokens, waste, efficiency score)
- Detected Patterns (good patterns and anti-patterns)
- Autonomy Recommendation (level for next session with reason)
- Learning Applied (what was recorded for future sessions)

**Output format:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "## 📊 CIGS Session Summary\\n\\n### Delegation Metrics..."
  }
}
```

**Reference:** See design doc section 2.5

**Testing:** Create test_stop_cigs.py to verify summary generation

Implement the full Stop hook enhancement with session summary.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "F2-1",
            "name": "CLI Commands",
            "description": "Add CIGS CLI commands to htmlgraph CLI",
            "prompt": """
Add CIGS CLI commands to the htmlgraph CLI.

**Files to modify:**
- src/python/htmlgraph/cli.py
- src/python/htmlgraph/orchestrator_mode.py (add new methods)

**Commands to add:**

1. `htmlgraph cigs status`
   - Show current session violations
   - Show compliance rate
   - Show autonomy level
   - Show recent patterns

2. `htmlgraph cigs summary [session-id]`
   - Show detailed session summary
   - Default to current session if no ID provided

3. `htmlgraph cigs patterns`
   - List all detected patterns (good and anti)
   - Show occurrence counts
   - Show remediation suggestions

4. `htmlgraph cigs reset-violations`
   - Reset violation count for current session
   - Requires confirmation

5. `htmlgraph orchestrator acknowledge-violation`
   - Acknowledge circuit breaker violation
   - Reset circuit breaker state
   - Continue with current session

**Implementation:**
- Use Click for CLI commands
- Integrate with existing OrchestratorMode class
- Use ViolationTracker, PatternAnalyzer for data
- Format output with rich/colored text

**Reference:** See design doc Appendix B for message examples

**Testing:** Create test_cigs_cli.py to verify all commands

Implement all CIGS CLI commands with proper formatting.
""",
            "subagent_type": "general-purpose",
        },
        {
            "id": "G2-1",
            "name": "Integration Tests",
            "description": "Create comprehensive integration tests for CIGS system",
            "prompt": """
Create comprehensive integration tests for the CIGS system.

**Files to create:**
- tests/integration/test_cigs_integration.py
- tests/integration/test_cigs_hook_flow.py
- tests/integration/test_cigs_learning.py

**Test scenarios:**

1. **Full Hook Flow Test:**
   - SessionStart → load history
   - UserPromptSubmit → detect exploration intent
   - PreToolUse → generate imperative
   - Tool execution
   - PostToolUse → cost accounting
   - Stop → session summary

2. **Escalation Test:**
   - First violation → Level 1 message
   - Second violation → Level 2 message
   - Third violation → Circuit breaker
   - Acknowledgment → Reset

3. **Pattern Detection Test:**
   - Trigger exploration sequence
   - Verify pattern detection
   - Verify pattern persistence
   - Verify pattern-based guidance

4. **Cross-Session Learning:**
   - Session 1: High violations → strict autonomy
   - Session 2: Load strict context
   - Session 3: Improved compliance → relax autonomy

5. **Cost Calculation Test:**
   - Direct execution vs delegation
   - Verify waste calculation
   - Verify efficiency score

**Use pytest fixtures:**
- Mock session context
- Mock tool history
- Mock violation records

**Reference:** All design doc sections

Implement comprehensive integration tests for CIGS.
""",
            "subagent_type": "general-purpose",
        },
    ]

    print(f"📋 Wave 2 Plan: {len(agents)} integration components")
    print()
    for agent in agents:
        print(f"  • {agent['id']}: {agent['name']}")
    print()

    # Store agent metadata for result collection
    results_file = Path(".htmlgraph/cigs/wave2-results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    metadata = {
        "wave": 2,
        "timestamp": datetime.now().isoformat(),
        "agents": agents,
        "status": "launched",
    }

    results_file.write_text(json.dumps(metadata, indent=2))

    print(f"✅ Wave 2 metadata saved to {results_file}")
    print()
    print("🚀 Ready to launch agents in parallel!")
    print()
    print("Use Claude Code to launch all agents with Task() calls.")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
