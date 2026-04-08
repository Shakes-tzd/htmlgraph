package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/PuerkitoBio/goquery"
	dbpkg "github.com/shakestzd/htmlgraph/internal/db"
	"github.com/shakestzd/htmlgraph/internal/models"
)

const maxInputSummaryLen = 200

// reindexSessions scans sessionDir for *.html session files and parses each
// <li> activity entry into an AgentEvent, upserting via db.UpsertEvent.
// Returns (totalFiles, totalEventsUpserted, errorFiles).
func reindexSessions(database *sql.DB, sessionDir string) (int, int, int) {
	pattern := filepath.Join(sessionDir, "*.html")
	files, _ := filepath.Glob(pattern)

	var total, upserted, errCount int
	for _, f := range files {
		total++
		n, err := parseSessionHTML(database, f)
		if err != nil {
			errCount++
			continue
		}
		upserted += n
	}
	return total, upserted, errCount
}

// parseSessionHTML reads a single session HTML file, extracts the article
// metadata (session ID, agent) and each <li> in the activity log, then
// upserts an AgentEvent per entry. Returns the number of events upserted.
func parseSessionHTML(database *sql.DB, path string) (int, error) {
	f, err := os.Open(path)
	if err != nil {
		return 0, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	doc, err := goquery.NewDocumentFromReader(f)
	if err != nil {
		return 0, fmt.Errorf("parse HTML %s: %w", path, err)
	}

	article := doc.Find("article[id]").First()
	if article.Length() == 0 {
		return 0, fmt.Errorf("no <article id=...> in %s", path)
	}

	sessionID, _ := article.Attr("id")
	if sessionID == "" {
		return 0, fmt.Errorf("empty article id in %s", path)
	}

	agentID := attrOrDefault(article, "data-agent", "unknown")
	statusAttr := attrOrDefault(article, "data-status", "completed")
	startedAt := parseSessionTimestamp(attrOrDefault(article, "data-started-at", ""))
	isSubagent := attrOrDefault(article, "data-is-subagent", "false") == "true"
	startCommit := attrOrDefault(article, "data-start-commit", "")

	// Map session HTML statuses to sessions table CHECK constraint values.
	sessionStatus := "completed"
	switch statusAttr {
	case "active":
		sessionStatus = "active"
	case "stale", "ended":
		sessionStatus = "completed"
	case "failed":
		sessionStatus = "failed"
	}

	now := time.Now().UTC()
	if startedAt.IsZero() {
		startedAt = now
	}

	// Ensure a session row exists (FK constraint on agent_events.session_id).
	_, _ = database.Exec(`
		INSERT OR IGNORE INTO sessions (session_id, agent_assigned, created_at, status, start_commit, is_subagent)
		VALUES (?, ?, ?, ?, ?, ?)`,
		sessionID, agentID, startedAt.UTC().Format(time.RFC3339),
		sessionStatus, startCommit, isSubagent,
	)

	var count int

	article.Find("section[data-activity-log] ol li").Each(func(_ int, li *goquery.Selection) {
		eventID := attrOrDefault(li, "data-event-id", "")
		if eventID == "" {
			return // skip entries without an event ID
		}

		tsStr := attrOrDefault(li, "data-ts", "")
		ts := parseSessionTimestamp(tsStr)

		toolName := attrOrDefault(li, "data-tool", "")
		featureID := attrOrDefault(li, "data-feature", "")
		parentEventID := attrOrDefault(li, "data-parent", "")

		successStr := attrOrDefault(li, "data-success", "true")
		status := "completed"
		if successStr == "false" {
			status = "failed"
		}

		summary := strings.TrimSpace(li.Text())
		if len([]rune(summary)) > maxInputSummaryLen {
			summary = string([]rune(summary)[:maxInputSummaryLen-1]) + "\u2026"
		}

		evt := &models.AgentEvent{
			EventID:       eventID,
			AgentID:       agentID,
			EventType:     models.EventToolCall,
			Timestamp:     ts,
			ToolName:      toolName,
			InputSummary:  summary,
			SessionID:     sessionID,
			FeatureID:     featureID,
			ParentEventID: parentEventID,
			Status:        status,
			Source:        "reindex",
			CreatedAt:     now,
			UpdatedAt:     now,
		}

		if upsertErr := dbpkg.UpsertEvent(database, evt); upsertErr != nil {
			_ = upsertErr // skip on upsert failure
			return
		}
		count++
	})

	return count, nil
}

// attrOrDefault returns the named attribute value from a goquery selection,
// or the fallback if the attribute is absent or empty.
func attrOrDefault(sel *goquery.Selection, name, fallback string) string {
	if v, ok := sel.Attr(name); ok && v != "" {
		return v
	}
	return fallback
}

// parseSessionTimestamp parses ISO 8601 timestamps found in session HTML.
// Tries multiple layouts to handle both timezone-naive and timezone-aware values.
func parseSessionTimestamp(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	layouts := []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02T15:04:05.999999",
		"2006-01-02T15:04:05",
	}
	for _, layout := range layouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t
		}
	}
	return time.Time{}
}
