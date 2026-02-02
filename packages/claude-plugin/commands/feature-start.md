<!-- Efficiency: SDK calls: 2, Bash calls: 0, Context: ~5% -->

# /htmlgraph:feature-start

Start working on a feature (moves it to in-progress)

## Usage

```
/htmlgraph:feature-start [feature-id]
```

## Parameters

- `feature-id` (optional): The feature ID to start working on. If not provided, lists available features.


## Examples

```bash
/htmlgraph:feature-start feature-001
```
Start working on feature-001

```bash
/htmlgraph:feature-start
```
List available features and prompt for selection



## Instructions for Claude

This command uses the SDK's `features.where()` and `features.start()` methods.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Check if feature-id provided:**
   - If YES → Go to step 3
   - If NO → Go to step 2

2. **List available features and prompt using SDK:**
   ```python
   todo_features = sdk.features.where(status="todo")
   if not todo_features:
       print("No features available to start. Create one with /htmlgraph:feature-add")
       return
   ```
   - Show available features to the user
   - Ask the user which feature they want to start
   - Wait for user response
   - Use the selected feature-id for next step

3. **Start the feature using SDK:**
   ```python
   feature = sdk.features.start(feature_id)
   if not feature:
       print(f"Error: Feature {feature_id} not found")
       return
   ```

4. **Extract feature details:**
   - Feature title: `feature.title`
   - Feature ID: `feature.id`
   - Status: `feature.status` (should be "in-progress")
   - Description: `feature.description` (if exists)
   - Implementation steps: `feature.metadata.get('steps', [])` (if any)

5. **Show step breakdown if available:**
   - If feature has steps, show progress: "Step X/Y complete"
   - Display remaining steps clearly

6. **Present the feature context** using the output template below

7. **Confirm readiness:**
   - Show the feature details clearly
   - Ask what the user would like to work on first
```

### Output Format:

## Started: {feature_title}

**ID:** {feature_id}
**Status:** in-progress

### Description
{feature_description}

### Steps
{implementation_steps}

---

All activity will now be attributed to this feature.
What would you like to work on first?
