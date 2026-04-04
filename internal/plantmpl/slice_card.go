package plantmpl

import (
	"fmt"
	"io"
)

// SliceCard renders a single implementation slice with its metadata,
// dependencies, and approval status.
type SliceCard struct {
	Num         int
	ID          string // feature ID like "feat-abc123"
	Title       string
	Description string
	Effort      string // "S", "M", "L"
	Risk        string // "Low", "Med", "High"
	Deps        string // comma-separated slice numbers
	Files       string // comma-separated file paths
	Status      string
}

// Render writes the slice card zone placeholder.
func (sc *SliceCard) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- slice-card zone placeholder -->")
	return err
}
