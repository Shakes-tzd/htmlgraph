package plantmpl

import (
	"fmt"
	"html/template"
	"io"
)

// DesignSection renders the design rationale zone containing
// architecture notes and design decisions.
type DesignSection struct {
	Content template.HTML
}

// Render writes the design section zone placeholder.
func (d *DesignSection) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- design-section zone placeholder -->")
	return err
}
