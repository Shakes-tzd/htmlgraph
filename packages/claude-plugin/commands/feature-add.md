# /htmlgraph:feature-add

Add a new feature to the backlog

## Usage

```
/htmlgraph:feature-add [title]
```

## Parameters

- `title` (optional): The feature title. If not provided, ask the user.


## Examples

```bash
/htmlgraph:feature-add User Authentication
```
Add a new feature with the title "User Authentication"

```bash
/htmlgraph:feature-add
```
Prompt the user for a feature title



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Check if title is provided:**
   - If title argument provided → proceed to step 2
   - If no title → ask the user: "What feature would you like to add?"

2. **Create the feature:**
   ```bash
   htmlgraph feature add "<title>"
   ```

3. **List features to show the new one:**
   ```bash
   htmlgraph feature list
   ```

4. **Present confirmation** using the output template above with:
   - feature_id: The ID of the newly created feature
   - title: The feature title provided or entered by user

5. **Suggest next steps:**
   - Show command to start working: `htmlgraph feature start {feature_id}`
   - Optionally suggest `/htmlgraph:plan` to plan the feature
```

### Output Format:

## Feature Added

**ID:** {feature_id}
**Title:** {title}
**Status:** todo

Start working on it with:
```bash
htmlgraph feature start {feature_id}
```
