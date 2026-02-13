<!-- Efficiency: SDK calls: 2, Bash calls: 0, Context: ~5% -->

# /htmlgraph:feature-complete

Mark a feature as complete

## Usage

```
/htmlgraph:feature-complete [feature-id]
```

## Parameters

- `feature-id` (optional): The feature ID to complete. If not provided, completes the current active feature.


## Examples

```bash
/htmlgraph:feature-complete feature-001
```
Complete a specific feature

```bash
/htmlgraph:feature-complete
```
Complete the current active feature



## Instructions for Claude

This command uses the SDK's `features.complete()` and `get_status()` methods.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 2 SDK CALLS INSTEAD OF 4 CLI CALLS):**

1. **Get current feature if not specified:**
   ```python
   if not feature_id:
       # Get active features
       active = sdk.features.where(status="in-progress")
       if not active:
           print("Error: No active features to complete")
           return
       feature_id = active[0].id
   ```

2. **Complete the feature (single SDK call):**
   ```python
   completed = sdk.features.complete(feature_id)
   if not completed:
       print(f"Error: Feature {feature_id} not found")
       return
   ```

3. **Get project status (single SDK call):**
   ```python
   status = sdk.get_status()
   pending = sdk.features.where(status="todo")
   ```

   **Context usage: <5% (compared to 30% with 4 CLI calls)**

4. **Present summary** using the output template below

5. **Recommend next steps:**
   - If pending features exist → Suggest starting the next feature
   - If all features done → Congratulate on completion
   - Offer to run `/htmlgraph:plan` for new work
```

### Output Format:

## Feature Completed

**ID:** {feature_id}
**Title:** {title}
**Status:** done

### Progress Update
**Completed:** {status['done_count']}/{status['total_nodes']} ({percentage}%)
**Active:** {status['in_progress_count']} features

### What's Next?
{Use this code after showing progress:}
```python
# Get recommendations for next work
recs = sdk.recommend_next_work(agent_count=3)

print(f"\n### What's Next?")
if recs:
    top = recs[0]
    print(f"**Top recommendation:** {top['title']} (score: {top['score']:.2f})")
    if top.get('reasons'):
        print(f"**Reason:** {top['reasons'][0]}")
    print(f"\nSee all recommendations: `/htmlgraph:recommend`")
else:
    print(f"No pending work. Plan new features: `/htmlgraph:plan`")

print(f"\n**DELEGATION**: Delegate implementation based on complexity:")
print(f"- Simple fixes (1-2 files) → `Task(subagent_type=\"htmlgraph:haiku-coder\")`")
print(f"- Features (3-8 files) → `Task(subagent_type=\"htmlgraph:sonnet-coder\")`")
print(f"- Architecture (10+ files) → `Task(subagent_type=\"htmlgraph:opus-coder\")`")
```
