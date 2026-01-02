### /htmlgraph:plan

Start planning a new track with spike or create directly

**Usage:** `/htmlgraph:plan <description> [--spike] [--timebox HOURS]
`

**Parameters:**
- `description` (required): What you want to plan (e.g., "User authentication system")
- `--spike` (optional) (default: True): Create a planning spike first (recommended for complex work)
- `--timebox` (optional) (default: 4.0): Time limit for spike in hours


**Examples:**
```bash
/htmlgraph:plan "User authentication system"
```
Create a planning spike for auth system (4h timebox)

```bash
/htmlgraph:plan "Real-time notifications" --timebox 3
```
Create planning spike with 3-hour timebox

```bash
/htmlgraph:plan "Simple bug fix dashboard" --no-spike
```
Create track directly without spike



**Implementation:**
Execute the following HtmlGraph commands:

```bash

```



---
