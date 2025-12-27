#!/bin/bash
# HtmlGraph Session Start Hook
# Installs dependencies, imports transcripts, and enforces orchestrator pattern
set -euo pipefail

# Output async mode for non-blocking startup (5 min timeout)
echo '{"async": true, "asyncTimeout": 300000}'

# Only run on Claude Code web (remote) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  echo "Not a remote session, skipping setup"
  exit 0
fi

echo "=== HtmlGraph Session Start ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Install project dependencies
echo "Installing dependencies..."
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"
uv sync --quiet

# 3. Set up PYTHONPATH for htmlgraph
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export PYTHONPATH="${CLAUDE_PROJECT_DIR}/src/python:${PYTHONPATH:-}"' >> "$CLAUDE_ENV_FILE"
fi

# 4. Auto-link transcripts by git branch
echo "Linking transcripts..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
uv run htmlgraph transcript auto-link --branch "$CURRENT_BRANCH" 2>/dev/null || echo "No transcripts to link"

# 5. List available transcripts for reference
echo "Available transcripts:"
uv run htmlgraph transcript list --limit 3 2>/dev/null || echo "None found"

# 6. Show session context and orchestrator directive
echo ""
echo "=============================================="
echo "       ORCHESTRATOR MODE ACTIVATED"
echo "=============================================="
echo ""

uv run python -c "
from htmlgraph import SDK
sdk = SDK(agent='claude')
info = sdk.get_session_start_info()

print('SESSION CONTEXT:')
print(f\"  Session: {info.get('session_id', 'new')}\")

if info.get('active_work'):
    work = info['active_work']
    print(f\"  Active Work: {work.get('id')} - {work.get('title')}\")
    print(f\"  Status: {work.get('status')}\")
    print(f\"  Type: {work.get('type')}\")
else:
    print('  Active Work: None')
    recs = info.get('analytics', {}).get('recommendations', [])
    if recs:
        print(f\"  Recommended: {recs[0].get('title', 'N/A')}\")

print()
print('ORCHESTRATOR DIRECTIVES:')
print('  1. DELEGATE exploration to Task(subagent_type=\"Explore\")')
print('  2. DELEGATE implementation to Task(subagent_type=\"general-purpose\")')
print('  3. CREATE work items before code changes: sdk.features.create(...).save()')
print('  4. PARALLELIZE independent tasks with multiple Task() calls')
print('  5. PRESERVE context - let subagents do heavy lifting')
print()
print('SDK QUICK REFERENCE:')
print('  sdk = SDK(agent=\"claude\")')
print('  sdk.features.create(\"Title\").save()  # Create feature')
print('  sdk.bugs.create(\"Title\").save()      # Create bug')
print('  sdk.features.start(id)               # Start work')
print('  sdk.features.complete(id)            # Complete work')
print()
print('AVAILABLE METHODS:')
print('  Orchestration:')
print('    sdk.spawn_explorer(task, scope)     # Research codebase')
print('    sdk.spawn_coder(feature_id, context) # Implement changes')
print('    sdk.orchestrate(feature_id, scope)  # Full workflow')
print('  Analytics:')
print('    sdk.find_bottlenecks()              # Find blocked items')
print('    sdk.recommend_next_work()           # Get suggestions')
print('    sdk.get_parallel_work(max_agents)   # Parallelizable tasks')
print('  Learning:')
print('    sdk.patterns.get_anti_patterns()   # Patterns to avoid')
print('    sdk.insights.get_low_efficiency()  # Sessions needing improvement')
print('    LearningPersistence(sdk).persist_session_insight(id)  # Save insights')
print('  Help:')
print('    sdk.help()                          # Show all methods')
print('    sdk.help(\"features\")               # Topic-specific help')

# Learning insights section
print()
print('LEARNING INSIGHTS:')

try:
    # Check for anti-patterns
    anti_patterns = list(sdk.patterns.where(pattern_type=\"anti-pattern\"))
    if anti_patterns:
        print('  ⚠️  Anti-patterns to avoid:')
        for p in anti_patterns[:2]:
            seq = getattr(p, 'sequence', [])
            print(f'      - {\" -> \".join(seq)}')

    # Check recent efficiency
    insights = list(sdk.insights.all())
    if insights:
        recent = insights[0]
        eff = getattr(recent, 'efficiency_score', 0)
        if eff > 0:
            print(f'  📊 Last session efficiency: {eff:.0%}')
            issues = getattr(recent, 'issues_detected', [])
            for issue in issues[:2]:
                print(f'      💡 {issue}')

    # Show optimal patterns
    optimal = list(sdk.patterns.where(pattern_type=\"optimal\"))
    if optimal:
        print('  ✅ Optimal patterns:')
        for p in optimal[:2]:
            seq = getattr(p, 'sequence', [])
            print(f'      - {\" -> \".join(seq)}')
except Exception as e:
    print(f'  (Learning data not available: {e})')

print()
" 2>/dev/null || echo "SDK not available"

echo "=== HtmlGraph Ready - You are the ORCHESTRATOR ==="
