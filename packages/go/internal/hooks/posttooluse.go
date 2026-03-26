package hooks

import (
	"database/sql"
	"time"
)

// PostToolUse handles the PostToolUse Claude Code hook event.
// It finds the most recent "started" event for this session/tool and marks it completed.
// Note: env vars don't persist between hook processes, so we query the DB instead.
func PostToolUse(event *CloudEvent, database *sql.DB) (*HookResult, error) {
	sessionID := EnvSessionID(event.SessionID)
	if sessionID == "" {
		return &HookResult{Continue: true}, nil
	}

	success := isSuccess(event.ToolResult)
	status := "completed"
	if !success {
		status = "failed"
	}

	now := time.Now().UTC().Format(time.RFC3339)
	outputSummary := summariseOutput(event.ToolResult)

	// Find the most recent "started" event for this session and tool.
	var eventID string
	err := database.QueryRow(`
		SELECT event_id FROM agent_events
		WHERE session_id = ? AND tool_name = ? AND status = 'started'
		ORDER BY timestamp DESC
		LIMIT 1`, sessionID, event.ToolName,
	).Scan(&eventID)

	if err != nil {
		return &HookResult{Continue: true}, nil
	}

	_, _ = database.Exec(`
		UPDATE agent_events
		SET status = ?,
		    output_summary = ?,
		    updated_at = ?
		WHERE event_id = ?`,
		status, outputSummary, now, eventID,
	)

	return &HookResult{Continue: true}, nil
}

// isSuccess returns false when the tool result contains an explicit error flag.
func isSuccess(result map[string]any) bool {
	if result == nil {
		return true
	}
	if v, ok := result["is_error"].(bool); ok && v {
		return false
	}
	return true
}

// summariseOutput extracts a short string from the tool result map.
func summariseOutput(result map[string]any) string {
	if result == nil {
		return ""
	}
	for _, key := range []string{"output", "content", "result", "error"} {
		if v, ok := result[key].(string); ok && v != "" {
			if len(v) > 200 {
				v = v[:200] + "…"
			}
			return v
		}
	}
	return ""
}

// ensure sql is referenced (used indirectly via nullable helpers).
var _ *sql.DB
