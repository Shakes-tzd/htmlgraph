package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/shakestzd/htmlgraph/internal/graph"
	"github.com/shakestzd/htmlgraph/internal/htmlparse"
	"github.com/shakestzd/htmlgraph/internal/models"
	"github.com/spf13/cobra"
)

// trackCmdWithExtras builds the standard workitem commands for tracks,
// then replaces the generic show with a track-specific one that lists
// linked features.
func trackCmdWithExtras() *cobra.Command {
	cmd := workitemCmd("track", "tracks")
	// Replace generic show with track-specific show (shows linked features)
	for i, sub := range cmd.Commands() {
		if sub.Use == "show <id>" {
			cmd.RemoveCommand(sub)
			newCmds := append(cmd.Commands()[:i], cmd.Commands()[i:]...)
			_ = newCmds // removal already happened
			break
		}
	}
	cmd.AddCommand(trackShowCmd())
	return cmd
}

// loadFeatureCounts returns a map of track ID → feature count.
func loadFeatureCounts(htmlgraphDir string) map[string]int {
	counts := make(map[string]int)
	nodes, err := graph.LoadDir(filepath.Join(htmlgraphDir, "features"))
	if err != nil {
		return counts
	}
	for _, n := range nodes {
		if n.TrackID != "" {
			counts[n.TrackID]++
		}
	}
	return counts
}

// trackShowCmd shows a single track by ID.
func trackShowCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "show <id>",
		Short: "Show track details",
		Args:  cobra.ExactArgs(1),
		RunE: func(_ *cobra.Command, args []string) error {
			return runTrackShow(args[0])
		},
	}
}

func runTrackShow(id string) error {
	dir, err := findHtmlgraphDir()
	if err != nil {
		return err
	}

	path := filepath.Join(dir, "tracks", id+".html")
	if _, err := os.Stat(path); err != nil {
		return fmt.Errorf("track %q not found", id)
	}

	node, err := htmlparse.ParseFile(path)
	if err != nil {
		return fmt.Errorf("parse %s: %w", path, err)
	}

	printTrackDetail(node, dir)
	return nil
}

func printTrackDetail(n *models.Node, htmlgraphDir string) {
	sep := strings.Repeat("─", 60)
	fmt.Println(sep)
	fmt.Printf("  %s\n", n.Title)
	fmt.Println(sep)
	fmt.Printf("  ID        %s\n", n.ID)
	fmt.Printf("  Type      %s\n", n.Type)
	fmt.Printf("  Status    %s\n", n.Status)
	fmt.Printf("  Priority  %s\n", n.Priority)
	if !n.CreatedAt.IsZero() {
		fmt.Printf("  Created   %s\n", n.CreatedAt.Format("2006-01-02"))
	}

	features := loadLinkedFeatures(htmlgraphDir, n.ID)
	if len(features) > 0 {
		fmt.Printf("\nLinked features (%d):\n", len(features))
		for _, f := range features {
			marker := "  "
			if f.Status == models.StatusInProgress {
				marker = "* "
			}
			fmt.Printf("  %s%-20s  %-11s  %s\n",
				marker, f.ID, f.Status, truncate(f.Title, 38))
		}
	}

	if n.Content != "" {
		fmt.Println("\nDescription:")
		for _, line := range strings.Split(n.Content, "\n") {
			fmt.Printf("  %s\n", line)
		}
	}

	if len(n.Steps) > 0 {
		done := 0
		for _, s := range n.Steps {
			if s.Completed {
				done++
			}
		}
		fmt.Printf("\nRequirements: %d/%d complete\n", done, len(n.Steps))
		for _, s := range n.Steps {
			tick := "[ ]"
			if s.Completed {
				tick = "[x]"
			}
			fmt.Printf("  %s  %s\n", tick, s.Description)
		}
	}
}

// loadLinkedFeatures returns features whose TrackID matches trackID.
func loadLinkedFeatures(htmlgraphDir, trackID string) []*models.Node {
	nodes, err := graph.LoadDir(filepath.Join(htmlgraphDir, "features"))
	if err != nil {
		return nil
	}
	var linked []*models.Node
	for _, n := range nodes {
		if n.TrackID == trackID {
			linked = append(linked, n)
		}
	}
	sort.Slice(linked, func(i, j int) bool {
		return linked[i].ID < linked[j].ID
	})
	return linked
}

