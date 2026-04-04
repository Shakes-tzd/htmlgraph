package plantmpl

import (
	"fmt"
	"io"
)

// ProgressBar renders the plan progress indicator showing
// approved vs pending vs total slice counts.
type ProgressBar struct {
	Approved int
	Total    int
	Pending  int
}

// Render writes the progress bar zone placeholder.
func (pb *ProgressBar) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- progress-bar zone placeholder -->")
	return err
}
