# /htmlgraph:feature-primary

Set the primary feature for activity attribution

## Usage

```
/htmlgraph:feature-primary <feature-id>
```

## Parameters

- `feature-id` (required): The feature ID to set as primary


## Examples

```bash
/htmlgraph:feature-primary feature-001
```
Set feature-001 as the primary feature for activity attribution



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Run this command:**
   ```bash
   htmlgraph feature primary <feature-id>
   ```

2. **Parse the output** to extract:
   - The feature ID and title
   - Confirmation that it was set as primary
   - List of other in-progress features

3. **Present a summary** using the output template above

4. **Inform the user:**
   - All new activity will be attributed to this feature by default
   - The feature's patterns can override this for matching activity
   - Other features remain in progress and can be worked on
```

### Output Format:

## Primary Feature Set

**ID:** {feature_id}
**Title:** {title}

All subsequent activity will be attributed to this feature unless it matches another feature's patterns better.

### Other Active Features
{other_active_features}
