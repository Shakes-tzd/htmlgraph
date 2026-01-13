# /htmlgraph:start

Start a new session with context continuity and status overview

## Usage

```
/htmlgraph:start
```

## Parameters



## Examples

```bash
/htmlgraph:start
```
Begin a new development session and choose what to work on



## Instructions for Claude

This command uses the SDK's `get_session_start_info()` method.

### Implementation:

```python
from htmlgraph import SDK

sdk = SDK(agent="claude")

# Parse arguments
**DO THIS (OPTIMIZED - 2 CALLS INSTEAD OF 6+):**

1. **Get comprehensive session start info:**
   ```bash
   uv run htmlgraph snapshot --summary  # Quick visual overview (colors preserved)
   uv run htmlgraph session start-info  # Detailed analytics
   ```

   This replaces 6+ separate calls:
   - htmlgraph status
   - htmlgraph feature list
   - htmlgraph session list
   - git log --oneline -5
   - SDK analytics (bottlenecks)
   - SDK analytics (recommendations, parallel)

   **Context usage: <5% instead of 30%**

2. **Parse the output** to extract:
   - Project status: nodes, WIP count, completion %
   - Active features with step progress
   - Recent sessions
   - Git commit history
   - Strategic insights:
     - Bottlenecks (count, titles, impact scores)
     - Recommendations (top 3 with scores and reasons)
     - Parallel capacity (max parallelism, ready tasks)

3. **Present the comprehensive summary** using the output template above

4. **Recommend specific next action** based on analytics:
   - If bottlenecks exist → Highlight them as priority
   - If recommendations available → Show top recommendation with score
   - If parallel capacity > 1 → Mention coordination opportunity
   - Default → Continue current work or start new

5. **Ask the user what they want to work on** with data-driven options

6. **Wait for user direction** before taking any action

7. **Apply constraints:**
   - Maximum 3 features can be in progress (WIP limit)
   - Prioritize unblocking bottlenecks
   - Prioritize finishing existing work over starting new
   - Use SDK for all operations
   - Mark steps complete immediately after finishing

8. **Remind the user:**
   - All activity is automatically tracked to features
   - View progress in browser: `htmlgraph serve` → http://localhost:8080
   - Use `/htmlgraph:plan` to start new work with proper planning
```

### Output Format:

## Session Status

**Project:** {project_name}
**Progress:** {completed}/{total} features ({percentage}%)
**Active Features (WIP):** {in_progress_count}

---

### Previous Session
{summarize_previous_work}

---

### Current Feature(s)
**Working On:** {feature_descriptions}
**Status:** in_progress

#### Step Progress
{step_checklist}

---

### Recent Commits
{last_5_commits}

---

### 🎯 Strategic Insights

#### Bottlenecks ({bottleneck_count})
{bottleneck_list}

#### Top Recommendations
{recommendation_list}

#### Parallel Work
**Can work on {max_parallelism} tasks simultaneously**
- {parallel_ready_count} tasks ready now

---

## What would you like to work on?

Based on strategic analysis, I recommend:
1. **{top_recommendation}** (score: {top_score})
   - Why: {top_reasons}
2. Continue with current feature
3. Start a different feature
4. Create new work item (`/htmlgraph:plan`)
5. Something else
