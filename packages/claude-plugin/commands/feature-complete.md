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

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Get current feature if not specified:**
   - If feature-id argument is not provided, run:
     ```bash
     htmlgraph feature list --status in-progress
     ```
   - Extract the first active feature ID from the output

2. **Complete the feature:**
   ```bash
   htmlgraph feature complete <feature-id>
   ```

3. **Show updated status:**
   ```bash
   htmlgraph status
   htmlgraph feature list
   ```

4. **Parse the output** to extract:
   - Completed feature ID and title
   - Total features and completion percentage
   - Any pending/in-progress features

5. **Present summary** using the output template above

6. **Recommend next steps:**
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
**Completed:** {done}/{total} ({percentage}%)

### What's Next?
{pending_features}

Would you like to start the next feature?
