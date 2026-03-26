# /htmlgraph:recommend

Get smart recommendations on what to work on next

## Usage

```
/htmlgraph:recommend [--count N] [--check-bottlenecks]
```

## Parameters

- `--count` (optional) (default: 3): Number of recommendations to show
- `--check-bottlenecks` (optional) (default: True): Also show bottlenecks


## Examples

```bash
/htmlgraph:recommend
```
Get top 3 recommendations with bottleneck check

```bash
/htmlgraph:recommend --count 5
```
Get top 5 recommendations

```bash
/htmlgraph:recommend --no-check-bottlenecks
```
Recommendations only, skip bottleneck analysis



## Instructions for Claude

This command uses the SDK's `recommend_next_work()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Get recommendations
recs = sdk.recommend_next_work(agent_count=count)

# Optionally check bottlenecks
bottlenecks = []
if check_bottlenecks:
    bottlenecks = sdk.find_bottlenecks(top_n=3)

# Present bottlenecks first if any
if bottlenecks:
    print(f"## ⚠️  Bottlenecks Detected")
    for bn in bottlenecks:
        print(f"\n### {bn['title']} ({bn['id']})")
        print(f"**Impact:** {bn['impact_score']:.2f}")
        print(f"**Blocks:** {len(bn.get('blocks', []))} items")

print(f"\n## Top {count} Recommendations")

for i, rec in enumerate(recs[:count], 1):
    print(f"\n### {i}. {rec['title']} ({rec['id']})")
    print(f"**Score:** {rec['score']:.2f}")

    # Show reasoning
    if rec.get('reasons'):
        print(f"\n**Why recommended:**")
        for reason in rec['reasons']:
            print(f"- {reason}")

    # Show what this unlocks
    if rec.get('unlocks'):
        print(f"\n**Unlocks:** {len(rec['unlocks'])} dependent items")
        for dep in rec['unlocks'][:3]:
            print(f"  - {dep['title']}")
        if len(rec['unlocks']) > 3:
            print(f"  ... and {len(rec['unlocks']) - 3} more")

    # Show complexity
    if rec.get('complexity'):
        print(f"**Complexity:** {rec['complexity']}")

    # Show suggested approach
    if rec.get('suggested_approach'):
        print(f"**Approach:** {rec['suggested_approach']}")

print(f"\n---")
print(f"💡 Use `/htmlgraph:plan [id]` to start planning any of these items.")
```
```

### Output Format:

## Work Recommendations

{bottlenecks_section}

### Top {count} Recommendations

{recommendations}

---
💡 Use `/htmlgraph:plan` to start planning any of these items.

**PARALLEL ANALYSIS (MANDATORY when 2+ recommendations):**
Before presenting results, analyze whether recommendations can execute in parallel:
1. Check dependency graph between recommended items
2. Check file/module overlap (would they touch the same files?)
3. If independent → present a parallel execution plan as the DEFAULT action
4. Format: table showing Feature | Agent | Scope | Parallelizable?

**DELEGATION** (per-task model selection):
- Simple fixes (1-2 files) → `Agent(subagent_type="htmlgraph:haiku-coder", isolation="worktree")`
- Features (3-8 files) → `Agent(subagent_type="htmlgraph:sonnet-coder", isolation="worktree")`
- Architecture (10+ files) → `Agent(subagent_type="htmlgraph:opus-coder", isolation="worktree")`

**When parallelizable**, propose: "These N items have no dependencies or file overlap. Launch in parallel?"
