---
name: diagnose
description: Diagnose orchestrator delegation enforcement gaps in the current session
allowed-tools: ["Bash", "Read"]
user_invocable: true
---

<!-- Efficiency: SDK calls: 1, Bash calls: 1, Context: ~8% -->

# /htmlgraph:diagnose

Audit delegation compliance for the current session and identify enforcement gaps.

## Usage

```
/htmlgraph:diagnose
```

## Examples

```
/htmlgraph:diagnose
```
Analyze current session and show delegation score, gaps, and recommendations.

## Instructions for Claude

Run the delegation diagnostic and present a structured report.

### Implementation

```python
from htmlgraph import SDK
from pathlib import Path
import sqlite3

sdk = SDK(agent="claude")

# 1. Get orchestrator state
from htmlgraph.orchestrator_mode import OrchestratorModeManager
manager = OrchestratorModeManager(Path(".htmlgraph"))
mode = manager.load()
orch_status = manager.status()

# 2. Query current session events
conn = sqlite3.connect(".htmlgraph/htmlgraph.db")

row = conn.execute(
    "SELECT session_id FROM agent_events ORDER BY timestamp DESC LIMIT 1"
).fetchone()
session_id = row[0] if row else None

direct_ops, git_writes, delegations, direct_impl = [], [], [], []

if session_id:
    direct_ops = conn.execute("""
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name = 'Bash'
          AND input_summary NOT LIKE '%ruff%'
          AND input_summary NOT LIKE '%pytest%'
          AND input_summary NOT LIKE '%mypy%'
          AND input_summary NOT LIKE '%git status%'
          AND input_summary NOT LIKE '%git log%'
          AND input_summary NOT LIKE '%git diff%'
          AND input_summary NOT LIKE '%git show%'
          AND input_summary NOT LIKE '%ls %'
        ORDER BY timestamp
    """, (session_id,)).fetchall()

    git_writes = [
        op for op in direct_ops
        if any(kw in (op[2] or '') for kw in [
            'git commit', 'git push', 'git tag', 'git merge',
            'git rebase', 'git reset', 'git branch -d'
        ])
    ]

    delegations = conn.execute("""
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name IN ('Task', 'Agent')
        ORDER BY timestamp
    """, (session_id,)).fetchall()

    direct_impl = conn.execute("""
        SELECT event_id, tool_name, input_summary, timestamp
        FROM agent_events
        WHERE session_id = ? AND tool_name IN ('Edit', 'Write')
        ORDER BY timestamp
    """, (session_id,)).fetchall()

conn.close()

# 3. Compute delegation score
impl_total = len(delegations) + len(direct_impl) + len(git_writes)
score = int(len(delegations) / impl_total * 100) if impl_total > 0 else 100
```

### Output Format

Present the results as:

```markdown
## Delegation Diagnostic Report

### Orchestrator State
- Mode: {enabled/disabled}
- Enforcement: {strict/guidance}
- Violations: {N}/3
- Circuit breaker: {triggered/normal}

### Delegation Score: {score}% ({delegations}/{total} actions delegated)

### Gaps Found

#### Git Write Operations (should use /htmlgraph:copilot)
| Time | Command | Recommended |
|------|---------|-------------|
| HH:MM | git commit ... | /htmlgraph:copilot |

#### Direct Implementation (should delegate to agent)
| Time | Tool | Summary | Recommended |
|------|------|---------|-------------|
| HH:MM | Edit | file.py | Task("htmlgraph:sonnet-coder", ...) |

### Recommendations
{Numbered list of specific actions based on gaps found}
```

If no gaps: report "Delegation score: 100%. No enforcement gaps found in this session."

If no session data: report "No events found. Verify hooks are active with `/hooks`."
