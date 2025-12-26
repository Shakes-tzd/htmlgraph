<!-- Efficiency: SDK calls: 0, Bash calls: 1, Context: ~5% -->

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

This command uses the CLI's `htmlgraph init` command (no SDK method exists yet).

### Implementation:

```python
from htmlgraph import SDK
import os

# Parse arguments
**DO THIS (OPTIMIZED - 1 CALL INSTEAD OF 4):**

1. **Check if already initialized and run init if needed:**
   ```python
   from pathlib import Path

   htmlgraph_dir = Path(".htmlgraph")

   if htmlgraph_dir.exists():
       print("## HtmlGraph Already Initialized")
       print("\n`.htmlgraph/` directory already exists.")

       # Show what's there
       subdirs = [d.name for d in htmlgraph_dir.iterdir() if d.is_dir()]
       print(f"\nExisting directories: {', '.join(subdirs)}")

   else:
       # Initialize
       import subprocess
       result = subprocess.run(["uv", "run", "htmlgraph", "init"],
                              capture_output=True, text=True)

       if result.returncode == 0:
           print("## HtmlGraph Initialized")
           print("\nCreated `.htmlgraph/` directory with:")
           print("- `features/` - Feature HTML files")
           print("- `sessions/` - Session HTML files")
           print("- `tracks/` - Track HTML files")
           print("- `spikes/` - Research spikes")
           print("- `bugs/` - Bug tracking (optional)")
       else:
           print(f"Error: {result.stderr}")
           return
   ```

   **Context usage: <5% (compared to 30% with 4 CLI calls)**

2. **Present next steps** using the output template below

3. **Guide the user:**
   - How to add features: `/htmlgraph:plan "title"`
   - How to start working: `/htmlgraph:start`
   - How to access dashboard: `htmlgraph serve`

4. **Highlight key points:**
   - All subsequent work will be tracked automatically
   - Use SDK/slash commands for all operations
   - Access dashboard to view progress visually
```

### Output Format:

## HtmlGraph Initialized

Created `.htmlgraph/` directory with:
- `features/` - Feature HTML files
- `sessions/` - Session HTML files
- `tracks/` - Track HTML files
- `spikes/` - Research spikes
- `bugs/` - Bug tracking (optional)

### Next Steps
1. Plan new work: `/htmlgraph:plan "Feature title"`
2. Start session: `/htmlgraph:start`
3. View dashboard: `htmlgraph serve`

### Quick Start
```bash
# Start planning
/htmlgraph:plan "Add user authentication"

# Begin work
/htmlgraph:start

# View progress
htmlgraph serve
# Open http://localhost:8080
```
