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
recs = sdk.recommend_next_work(agent_count=args.count)

# Optionally check bottlenecks
bottlenecks = []
if args.check_bottlenecks:
    bottlenecks = sdk.find_bottlenecks(top_n=3)

print(format_recommendations(recs, bottlenecks))
```
```

### Output Format:

## Work Recommendations

{bottlenecks_section}

### Top {count} Recommendations

{recommendations}

---
💡 Use `/htmlgraph:plan` to start planning any of these items.
