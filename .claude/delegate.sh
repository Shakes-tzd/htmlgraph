#!/bin/bash
# -*- mode: bash -*-
# Delegation Helper Script
#
# Purpose: Help with delegation pattern decisions and model selection
# Usage: source .claude/delegate.sh (or run directly for examples)

set -euo pipefail

# Colors for output (if running interactively)
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# ============================================================================
# Model Selection Helper
# ============================================================================

select_model_for_task() {
    local task_description="$1"

    # Analyze task characteristics
    local complexity=0
    local time_estimate=0

    # Simple keyword matching for complexity
    if echo "$task_description" | grep -qiE "(design|architecture|research|novel|complex|algorithm); then
        complexity=$((complexity + 3))
    fi

    if echo "$task_description" | grep -qiE "(refactor|fix|implement|quick|simple)" then
        complexity=$((complexity - 2))
    fi

    # Recommend model based on complexity
    if [[ $complexity -le 0 ]]; then
        echo "haiku"
    elif [[ $complexity -le 2 ]]; then
        echo "sonnet"
    else
        echo "opus"
    fi
}

# ============================================================================
# Delegation Decision Helper
# ============================================================================

should_delegate() {
    local work_size_minutes="$1"
    local file_count="$2"
    local needs_tests="${3:-false}"
    local is_complex="${4:-false}"

    # Rules from system prompt
    # Delegate if ANY of these apply:
    # - >30 minutes work
    # - 3+ files
    # - New tests needed
    # - Multi-component impact

    if [[ $work_size_minutes -gt 30 ]]; then
        echo "true"
        return 0
    fi

    if [[ $file_count -ge 3 ]]; then
        echo "true"
        return 0
    fi

    if [[ "$needs_tests" == "true" ]]; then
        echo "true"
        return 0
    fi

    if [[ "$is_complex" == "true" ]]; then
        echo "true"
        return 0
    fi

    # Do directly if ALL of these apply:
    # - Single file
    # - <30 minutes
    # - Trivial change
    # - Easy to revert
    echo "false"
}

# ============================================================================
# Task Description Template Generator
# ============================================================================

generate_task_template() {
    local task_type="$1"

    case "$task_type" in
        bug-fix)
            cat <<'EOF'
Task: Fix bug in [FILE]

Location: [FILE:FUNCTION]
Problem: [DESCRIBE THE BUG]
Impact: [WHO/WHAT IS AFFECTED]

Steps to reproduce:
1. [STEP 1]
2. [STEP 2]

Expected behavior: [WHAT SHOULD HAPPEN]
Actual behavior: [WHAT ACTUALLY HAPPENS]

Acceptance criteria:
- [ ] Bug is fixed
- [ ] Tests pass
- [ ] No regressions
- [ ] Code is reviewed

Report results to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='fixer')
sdk.spikes.create('Bug Fix Results').set_findings('[RESULTS]').save()
EOF
            ;;

        feature)
            cat <<'EOF'
Task: Implement feature - [FEATURE NAME]

Requirements:
- [REQUIREMENT 1]
- [REQUIREMENT 2]
- [REQUIREMENT 3]

Design approach:
[DESCRIBE YOUR APPROACH]

Files to create/modify:
- [FILE 1]
- [FILE 2]

Acceptance criteria:
- [ ] Feature works as specified
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No breaking changes

Report results to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='builder')
sdk.spikes.create('Feature Implementation').set_findings('[RESULTS]').save()
EOF
            ;;

        refactor)
            cat <<'EOF'
Task: Refactor [COMPONENT/MODULE]

Current issues:
- [ISSUE 1]
- [ISSUE 2]

Goals:
- [GOAL 1]
- [GOAL 2]

Files affected:
- [FILE 1]
- [FILE 2]

Acceptance criteria:
- [ ] Code is cleaner/more maintainable
- [ ] All tests pass
- [ ] No functional changes
- [ ] Performance maintained or improved

Report results to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='refactorer')
sdk.spikes.create('Refactor Results').set_findings('[RESULTS]').save()
EOF
            ;;

        research)
            cat <<'EOF'
Task: Research - [TOPIC]

Research questions:
1. [QUESTION 1]
2. [QUESTION 2]
3. [QUESTION 3]

Resources to check:
- Documentation: [DOC LINKS]
- Code: [CODE FILES]
- External: [EXTERNAL REFERENCES]

Deliverables:
- Summary of findings
- Recommendations
- Trade-offs analysis
- Next steps

Report findings to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='researcher')
sdk.spikes.create('Research Findings').set_findings('[FINDINGS]').save()
EOF
            ;;

        test)
            cat <<'EOF'
Task: Write tests for [COMPONENT]

What to test:
- [TEST CASE 1]
- [TEST CASE 2]
- [TEST CASE 3]

Test file location: [LOCATION]

Coverage goals:
- [COVERAGE GOAL 1]
- [COVERAGE GOAL 2]

Acceptance criteria:
- [ ] All tests written
- [ ] Tests passing
- [ ] Coverage >80%
- [ ] Edge cases covered

Report results to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='tester')
sdk.spikes.create('Test Results').set_findings('[RESULTS]').save()
EOF
            ;;

        docs)
            cat <<'EOF'
Task: Write documentation for [COMPONENT]

Topics to cover:
- Overview
- Installation/setup
- Usage examples
- Configuration
- Troubleshooting
- FAQ

Acceptance criteria:
- [ ] All sections complete
- [ ] Examples are accurate
- [ ] Formatting is consistent
- [ ] No broken links

Report results to HtmlGraph using:
from htmlgraph import SDK
sdk = SDK(agent='documenter')
sdk.spikes.create('Documentation').set_findings('[RESULTS]').save()
EOF
            ;;

        *)
            echo "Unknown task type: $task_type"
            echo "Valid types: bug-fix, feature, refactor, research, test, docs"
            return 1
            ;;
    esac
}

# ============================================================================
# Model Comparison Helper
# ============================================================================

compare_models() {
    cat <<'EOF'
┌─────────┬──────────────────────┬────────────────────┬──────────────────────┐
│ Model   │ Best For             │ Execution Speed    │ Best When            │
├─────────┼──────────────────────┼────────────────────┼──────────────────────┤
│ Haiku   │ Delegation,          │ 40-80ms (fastest)  │ You need quick        │
│         │ Orchestration,       │ ~50 tokens/sec     │ results or are        │
│         │ Quick fixes          │ Lowest cost        │ delegating work       │
│         │ Following patterns   │                    │                       │
├─────────┼──────────────────────┼────────────────────┼──────────────────────┤
│ Sonnet  │ Complex logic,       │ 100-200ms          │ Task needs multi-     │
│         │ Architecture,        │ ~30 tokens/sec     │ step reasoning but    │
│         │ Optimization,        │ Medium cost        │ not completely novel  │
│         │ Code review          │                    │                       │
├─────────┼──────────────────────┼────────────────────┼──────────────────────┤
│ Opus    │ Novel problems,      │ 150-300ms          │ Problem is completely │
│         │ Deep research,       │ ~20 tokens/sec     │ new or previous       │
│         │ Strategic design     │ Highest cost       │ attempts insufficient │
└─────────┴──────────────────────┴────────────────────┴──────────────────────┘

DECISION TREE:

1. Is this task something you've done before?
   → YES: Use Haiku (it's good at patterns)
   → NO:  Go to 2

2. Does it need detailed design/reasoning?
   → YES: Use Sonnet (strong reasoning)
   → NO:  Use Haiku (fast is better)

3. Is this a completely novel problem?
   → YES: Use Opus (strongest reasoning)
   → NO:  Use Sonnet (good balance)

COST OPTIMIZATION:

Simple task + Haiku   = Fast + Cheap ✅
Simple task + Sonnet  = Slow + Expensive ❌
Simple task + Opus    = Slow + Very Expensive ❌

Complex task + Haiku  = Fast but may miss nuance ⚠️
Complex task + Sonnet = Good balance ✅
Complex task + Opus   = Best solution but expensive ✅

Novel task + Haiku    = May fail ❌
Novel task + Sonnet   = Good attempt ✅
Novel task + Opus     = Highest success rate ✅
EOF
}

# ============================================================================
# Orchestration Decision Helper
# ============================================================================

orchestration_checklist() {
    cat <<'EOF'
ORCHESTRATION DECISION CHECKLIST

When to DELEGATE (use Task()):
☐ Task takes >30 minutes
☐ Requires exploring 3+ files
☐ Needs new tests written
☐ Affects multiple components
☐ Hard to revert if wrong
☐ Need specialized subagent (explorer, tester, coder)

When to EXECUTE DIRECTLY:
☐ Task is <30 minutes
☐ Single file change
☐ Trivial, obvious change
☐ Easy to verify/revert
☐ No new tests needed
☐ Something straightforward

DELEGATION TEMPLATE:

from htmlgraph import SDK

# 1. Create work item (if needed)
sdk = SDK(agent="claude-code")
feature = sdk.features.create("Task Name").save()

# 2. Delegate with clear task description
Task(
    prompt="""
    [Clear description of what needs to be done]

    Context:
    - [Background information]
    - [What's been tried]
    - [Success criteria]

    Report results to HtmlGraph:
    from htmlgraph import SDK
    sdk = SDK(agent='[subagent-type]')
    sdk.spikes.create('Task Results').set_findings('[RESULTS]').save()
    """,
    subagent_type="general-purpose"  # or specific type
)

# 3. Wait for Task completion
# 4. Retrieve results from HtmlGraph
results = SDK().spikes.get_latest(agent='[subagent-type]')
print(results[0].findings if results else 'No results')

# 5. Use findings for next steps
EOF
}

# ============================================================================
# Quick Reference
# ============================================================================

show_quick_reference() {
    cat <<'EOF'
SYSTEM PROMPT DELEGATION QUICK REFERENCE

MODEL SELECTION:
  Haiku   → Orchestration, delegation, quick tasks (DEFAULT)
  Sonnet  → Complex reasoning, architecture decisions
  Opus    → Novel problems, research-heavy investigations

DELEGATION RULES:
  Delegate if ANY:
    • >30 minutes of work
    • 3+ files involved
    • New tests needed
    • Multi-component impact
    • Hard to revert if wrong

  Execute directly if ALL:
    • Single file
    • <30 minutes
    • Trivial change
    • Easy to verify
    • No tests needed

MODEL CHOICE FACTORS:
  ✓ Complexity:     Low→Haiku | Medium→Sonnet | High→Opus
  ✓ Novelty:        Familiar→Haiku | Somewhat→Sonnet | Novel→Opus
  ✓ Cost concern:   Low budget→Haiku | Balanced→Sonnet | Quality critical→Opus
  ✓ Speed needed:   Fast→Haiku | Normal→Sonnet | Thorough→Opus

TASK TYPES:
  • Bug fix:        Usually delegate if >30min or affects 3+ files
  • Feature:        Delegate (usually multi-file, >30min)
  • Refactor:       Delegate if 3+ files, otherwise direct
  • Test:           Delegate if 100+ LOC, otherwise direct
  • Doc:            Direct (usually <30min, single file)
  • Research:       Delegate (always—specializes in exploration)

HtmlGraph INTEGRATION:
  • Feature tracking: Create feature before delegating
  • Session tracking: Automatic, no action needed
  • Results capture: Always use spikes.create() pattern
  • Model tracking:  Logs which model completed which tasks
EOF
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    if [[ $# -eq 0 ]]; then
        # No arguments - show usage
        cat <<'EOF'
Delegation Helper - Usage Guide

Commands:
  delegate show-models          Show model comparison table
  delegate decide TASK_TYPE     Decide if task should be delegated
  delegate template BUG_FIX     Generate task template (bug-fix, feature, etc)
  delegate checklist            Show orchestration decision checklist
  delegate reference            Show quick reference guide

Examples:
  delegate show-models
  delegate template feature
  delegate checklist
  delegate reference

For model selection:
  - Haiku (default):  Quick fixes, orchestration, delegation
  - Sonnet:          Complex reasoning, architecture
  - Opus:            Novel problems, deep research

See .claude/system-prompt.md for full guidance.
EOF
        return 0
    fi

    case "$1" in
        show-models|models)
            compare_models
            ;;
        decide)
            if [[ $# -lt 2 ]]; then
                echo "Usage: delegate decide TASK_DESCRIPTION"
                return 1
            fi
            shift
            select_model_for_task "$@"
            ;;
        template)
            if [[ $# -lt 2 ]]; then
                echo "Usage: delegate template {bug-fix|feature|refactor|research|test|docs}"
                return 1
            fi
            generate_task_template "$2"
            ;;
        checklist)
            orchestration_checklist
            ;;
        reference|quick)
            show_quick_reference
            ;;
        *)
            echo "Unknown command: $1"
            echo "Try: delegate show-models, delegate template, delegate checklist"
            return 1
            ;;
    esac
}

# Export functions for use when sourced
export -f select_model_for_task
export -f should_delegate
export -f generate_task_template
export -f compare_models
export -f orchestration_checklist
export -f show_quick_reference

# Run main if script is executed (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
