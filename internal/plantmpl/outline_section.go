package plantmpl

import (
	"fmt"
	"html/template"
	"io"
)

// OutlineSection renders the plan outline zone containing
// the high-level implementation plan narrative.
type OutlineSection struct {
	Content template.HTML
}

// Render writes the outline section zone placeholder.
func (o *OutlineSection) Render(w io.Writer) error {
	_, err := fmt.Fprint(w, "<!-- outline-section zone placeholder -->")
	return err
}
