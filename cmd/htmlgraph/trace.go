package main

import (
	"fmt"
	"path/filepath"
	"strings"

	dbpkg "github.com/shakestzd/htmlgraph/internal/db"
	"github.com/spf13/cobra"
)

func traceCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "trace <commit-sha>",
		Short: "Trace a commit back to its work item and session",
		Long: `Takes a commit SHA (full or prefix) and returns:
  - The session that produced it
  - The feature/bug active during that session
  - The parent track`,
		Args: cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			return runTrace(args[0])
		},
	}
}

func runTrace(sha string) error {
	dir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	database, err := dbpkg.Open(filepath.Join(dir, "htmlgraph.db"))
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer database.Close()

	commits, err := dbpkg.TraceCommit(database, sha)
	if err != nil {
		return err
	}
	if len(commits) == 0 {
		return fmt.Errorf("commit %s not found in git_commits table\nRun 'htmlgraph ingest commits' to import git history", sha)
	}

	sep := strings.Repeat("─", 60)
	fmt.Println(sep)
	fmt.Printf("  Trace: %s\n", truncate(sha, 10))
	fmt.Println(sep)

	for _, c := range commits {
		fmt.Printf("  Commit    %s\n", truncate(c.CommitHash, 10))
		if c.Message != "" {
			fmt.Printf("  Message   %s\n", truncate(c.Message, 55))
		}
		fmt.Printf("  Session   %s\n", c.SessionID)
		if c.FeatureID != "" {
			fmt.Printf("  Feature   %s\n", c.FeatureID)
		}
		if c.TrackID != "" {
			fmt.Printf("  Track     %s\n", c.TrackID)
		}
		if len(commits) > 1 {
			fmt.Println()
		}
	}
	return nil
}
