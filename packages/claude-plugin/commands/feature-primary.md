<!-- Efficiency: SDK calls: 2, Bash calls: 0, Context: ~4% -->

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

This command uses the SDK's `features.set_primary()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Set feature as primary using SDK:**
   ```python
   feature = sdk.features.set_primary(feature_id)
   if not feature:
       print(f"Error: Feature {feature_id} not found")
       return
   ```

2. **Extract feature details:**
   - Feature ID: `feature.id`
   - Feature title: `feature.title`
   - Status: `feature.status`

3. **Get other active features:**
   ```python
   other_active = [f for f in sdk.features.where(status="in-progress") if f.id != feature_id]
   ```

4. **Present a summary** using the output template below with:
   - feature_id: The ID of the primary feature
   - title: The feature title
   - other_active_features: List of other in-progress features

5. **Inform the user:**
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
