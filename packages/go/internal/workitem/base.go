// Package workitem provides internal work item operations for HtmlGraph.
//
// It manages collections for features, bugs, spikes, tracks, and sessions
// with functional options for creation and a dual-write strategy
// (HTML canonical, SQLite read-index).
package workitem

import "database/sql"

// Base holds the shared context needed by all collection operations.
type Base struct {
	// ProjectDir is the path to the .htmlgraph/ directory.
	ProjectDir string

	// Agent is the identifier of the agent using this package.
	Agent string

	// DB is the optional SQLite database (read index).
	DB *sql.DB
}
