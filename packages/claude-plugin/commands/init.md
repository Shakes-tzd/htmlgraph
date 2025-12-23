# /htmlgraph:init

Initialize HtmlGraph in a project

## Usage

```
/htmlgraph:init
```

## Parameters



## Examples

```bash
/htmlgraph:init
```
Set up HtmlGraph directory structure in project



## Instructions for Claude

This command uses the SDK's `None()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS:**

1. **Check if already initialized:**
   ```bash
   ls -la .htmlgraph 2>/dev/null || echo "Not initialized"
   ```

2. **Determine initialization status:**
   - If `.htmlgraph/` exists → Already initialized, skip step 3
   - If not found → Proceed to initialize

3. **If not initialized, run initialization:**
   ```bash
   htmlgraph init
   ```

4. **Verify initialization completed:**
   ```bash
   ls -la .htmlgraph/
   htmlgraph status
   ```

5. **Parse the output** to confirm:
   - `.htmlgraph/` directory created
   - Subdirectories created: `features/`, `sessions/`, `bugs/`
   - Status command succeeds

6. **Present the summary** using the output template above

7. **Guide next steps:**
   - How to add features: `htmlgraph feature add "title"`
   - How to start working: `htmlgraph feature start <id>`
   - How to access dashboard: `htmlgraph serve`

8. **Highlight key point:**
   - All subsequent work will be tracked automatically
   - Use SDK for all operations (never edit `.htmlgraph/` files directly)
   - Access dashboard to view progress visually
```

### Output Format:

## HtmlGraph Initialized

Created `.htmlgraph/` directory with:
- `features/` - Feature HTML files
- `sessions/` - Session HTML files
- `bugs/` - Bug tracking (optional)

### Next Steps
1. Add features: `htmlgraph feature add "Feature title"`
2. Start working: `htmlgraph feature start <id>`
3. View dashboard: `htmlgraph serve`

### Dashboard
Open in a browser or run:
```bash
htmlgraph serve
# Open http://localhost:8080
```
