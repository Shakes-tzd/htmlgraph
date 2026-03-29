package main

import (
	"fmt"
	"path/filepath"
	"time"

	dbpkg "github.com/shakestzd/htmlgraph/internal/db"
	"github.com/shakestzd/htmlgraph/internal/htmlparse"
	"github.com/spf13/cobra"
)

func reindexCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "reindex",
		Short: "Sync HTML work items to SQLite index",
		Long: `Reads all HTML work item files from .htmlgraph/features/, .htmlgraph/tracks/,
and .htmlgraph/spikes/ and upserts them into the features SQLite table.
Safe to run multiple times — uses ON CONFLICT upsert.`,
		RunE: runReindex,
	}
}

func runReindex(_ *cobra.Command, _ []string) error {
	htmlgraphDir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	database, err := dbpkg.Open(filepath.Join(htmlgraphDir, "htmlgraph.db"))
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer database.Close()

	dirs := []string{"features", "tracks", "spikes"}
	var total, upserted, errCount int

	for _, dir := range dirs {
		pattern := filepath.Join(htmlgraphDir, dir, "*.html")
		files, _ := filepath.Glob(pattern)

		for _, f := range files {
			total++
			node, parseErr := htmlparse.ParseFile(f)
			if parseErr != nil {
				errCount++
				continue
			}

			stepsTotal := len(node.Steps)
			stepsCompleted := 0
			for _, s := range node.Steps {
				if s.Completed {
					stepsCompleted++
				}
			}

			desc := node.Content
			if len([]rune(desc)) > 500 {
				desc = string([]rune(desc)[:499]) + "…"
			}

			createdAt := node.CreatedAt
			if createdAt.IsZero() {
				createdAt = time.Now()
			}
			updatedAt := node.UpdatedAt
			if updatedAt.IsZero() {
				updatedAt = createdAt
			}

			feat := &dbpkg.Feature{
				ID:             node.ID,
				Type:           mapNodeType(node.Type),
				Title:          node.Title,
				Description:    desc,
				Status:         string(node.Status),
				Priority:       string(node.Priority),
				AssignedTo:     node.AgentAssigned,
				TrackID:        node.TrackID,
				CreatedAt:      createdAt,
				UpdatedAt:      updatedAt,
				StepsTotal:     stepsTotal,
				StepsCompleted: stepsCompleted,
			}

			if upsertErr := dbpkg.UpsertFeature(database, feat); upsertErr != nil {
				errCount++
				continue
			}
			upserted++
		}
	}

	fmt.Printf("Reindexed: %d upserted, %d errors (of %d HTML files)\n",
		upserted, errCount, total)
	return nil
}

// mapNodeType converts HTML node types to the features table CHECK constraint values.
// features table allows: feature, bug, spike, chore, epic, task
func mapNodeType(nodeType string) string {
	switch nodeType {
	case "feature":
		return "feature"
	case "bug":
		return "bug"
	case "spike":
		return "spike"
	case "track":
		return "epic"
	case "chore":
		return "chore"
	case "plan", "spec":
		return "task"
	default:
		return "feature"
	}
}
