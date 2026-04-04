package plantmpl

import (
	"fmt"
	"io"
)

// DependencyGraph renders the interactive dependency graph zone showing
// slice relationships and approval status.
type DependencyGraph struct {
	Nodes []GraphNode
}

// GraphNode represents a single node in the dependency graph.
type GraphNode struct {
	Num    int
	Name   string
	Status string // "pending", "approved", etc.
	Deps   string // comma-separated dep numbers
	Files  int
}

// Render writes the dependency graph zone placeholder.
func (g *DependencyGraph) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- dependency-graph zone placeholder -->")
	return err
}
