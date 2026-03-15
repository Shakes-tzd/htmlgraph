"""
Sub-node query and update layer for HtmlGraph.

Operates on elements WITHIN an HTML file using CSS selectors,
complementing the Node-level operations that treat files as atomic units.

HTML elements (sections, lists, divs with data-* attributes) are the
sub-node structure. This module queries and mutates them in place using
justhtml, then saves the modified document back to disk.

Example:
    doc = SubNodeDocument.from_file(".htmlgraph/tracks/trk-abc.html")

    # Query tasks
    todo_tasks = doc.query('[data-task][data-status="todo"]')
    must_haves = doc.query('[data-requirement][data-priority="must-have"]')

    # Update a task
    doc.update('[data-task="task-1-1"]', {"data-status": "done"})

    # Complete a task (convenience)
    doc.complete_task("task-1-1")

    # Save changes
    doc.save()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from justhtml import JustHTML


@dataclass
class Element:
    """Lightweight wrapper around a justhtml element for sub-node access."""

    _el: Any

    @property
    def tag(self) -> str:
        """Element tag name."""
        result: str = self._el.name
        return result

    @property
    def attrs(self) -> dict[str, str]:
        """All attributes on this element."""
        return dict(self._el.attrs)

    @property
    def data(self) -> dict[str, str]:
        """All data-* attributes, without the 'data-' prefix."""
        return {k[5:]: v for k, v in self._el.attrs.items() if k.startswith("data-")}

    @property
    def text(self) -> str:
        """Text content of this element."""
        result: str = self._el.to_text().strip()
        return result

    @property
    def html(self) -> str:
        """Outer HTML of this element."""
        result: str = self._el.to_html()
        return result

    def __repr__(self) -> str:
        tag = self.tag
        data = self.data
        if data:
            attrs_str = " ".join(f"{k}={v}" for k, v in data.items())
            return f"<{tag} {attrs_str}>"
        return f"<{tag}>"


@dataclass
class SubNodeDocument:
    """
    Query and update elements within a single HTML file.

    Uses CSS selectors to find elements, mutate their attributes,
    and save the modified document back to disk.
    """

    _doc: JustHTML
    _path: Path | None = None
    _dirty: bool = field(default=False, init=False)

    @classmethod
    def from_file(cls, path: Path | str) -> SubNodeDocument:
        """Load an HTML file for sub-node operations."""
        path = Path(path)
        html = path.read_text(encoding="utf-8")
        return cls(_doc=JustHTML(html), _path=path)

    @classmethod
    def from_string(cls, html: str) -> SubNodeDocument:
        """Create from HTML string (no file backing)."""
        return cls(_doc=JustHTML(html))

    def query(self, selector: str) -> list[Element]:
        """
        Query elements using CSS selector.

        Works with any valid CSS selector targeting sub-node elements:
            '[data-task]'                        - all tasks
            '[data-task][data-status="todo"]'     - todo tasks
            '[data-requirement][data-priority="must-have"]' - must-have reqs
            'details[data-phase="phase-1"]'      - phase 1
            'section[data-section="plan"]'       - plan section

        Returns:
            List of matching Element wrappers.
        """
        return [Element(_el=el) for el in self._doc.query(selector)]

    def query_one(self, selector: str) -> Element | None:
        """Query a single element. Returns None if not found."""
        results = self._doc.query(selector)
        return Element(_el=results[0]) if results else None

    def update(self, selector: str, attrs: dict[str, str]) -> int:
        """
        Update attributes on all elements matching the selector.

        Args:
            selector: CSS selector to find elements.
            attrs: Dict of attribute names to new values.
                   Use data-* keys for data attributes.

        Returns:
            Number of elements updated.
        """
        elements = self._doc.query(selector)
        for el in elements:
            for key, value in attrs.items():
                el.attrs[key] = value
        if elements:
            self._dirty = True
        return len(elements)

    def remove_attr(self, selector: str, attr: str) -> int:
        """
        Remove an attribute from all elements matching the selector.

        Returns:
            Number of elements modified.
        """
        elements = self._doc.query(selector)
        count = 0
        for el in elements:
            if attr in el.attrs:
                del el.attrs[attr]
                count += 1
        if count:
            self._dirty = True
        return count

    # -- Convenience methods for tracks --

    def tasks(
        self, status: str | None = None, phase: str | None = None
    ) -> list[Element]:
        """
        Query tasks, optionally filtered by status and/or phase.

        Args:
            status: Filter by data-status ("todo", "done", "in-progress").
            phase: Filter by phase id (e.g. "phase-1").

        Returns:
            List of matching task Elements.
        """
        parts = []
        if phase:
            parts.append(f'[data-phase="{phase}"] ')
        parts.append("[data-task]")
        if status:
            parts.append(f'[data-status="{status}"]')
        selector = "".join(parts)
        return self.query(selector)

    def requirements(self, priority: str | None = None) -> list[Element]:
        """
        Query requirements, optionally filtered by priority.

        Args:
            priority: Filter by data-priority ("must-have", "should-have", "nice-to-have").
        """
        selector = "[data-requirement]"
        if priority:
            selector += f'[data-priority="{priority}"]'
        return self.query(selector)

    def phases(self) -> list[Element]:
        """Query all phases."""
        return self.query("[data-phase]")

    def complete_task(self, task_id: str) -> bool:
        """
        Mark a task as done.

        Updates data-status to "done" and checks the checkbox.

        Args:
            task_id: The task identifier (e.g. "task-1-1").

        Returns:
            True if the task was found and updated.
        """
        elements = self._doc.query(f'[data-task="{task_id}"]')
        if not elements:
            return False

        el = elements[0]
        el.attrs["data-status"] = "done"

        # Update checkbox
        checkboxes = el.query('input[type="checkbox"]')
        if not checkboxes:
            checkboxes = el.query("input[type=checkbox]")
        for cb in checkboxes:
            cb.attrs["checked"] = ""

        self._dirty = True
        self._refresh_progress()
        return True

    def uncomplete_task(self, task_id: str) -> bool:
        """
        Mark a task as todo (undo completion).

        Returns:
            True if the task was found and updated.
        """
        elements = self._doc.query(f'[data-task="{task_id}"]')
        if not elements:
            return False

        el = elements[0]
        el.attrs["data-status"] = "todo"

        # Uncheck checkbox
        checkboxes = el.query('input[type="checkbox"]')
        if not checkboxes:
            checkboxes = el.query("input[type=checkbox]")
        for cb in checkboxes:
            if "checked" in cb.attrs:
                del cb.attrs["checked"]

        self._dirty = True
        self._refresh_progress()
        return True

    def verify_requirement(self, req_id: str) -> bool:
        """
        Mark a requirement as verified.

        Args:
            req_id: The requirement identifier (e.g. "req-1").

        Returns:
            True if found and updated.
        """
        elements = self._doc.query(f'[data-requirement="{req_id}"]')
        if not elements:
            return False

        el = elements[0]
        el.attrs["data-verified"] = "true"
        self._dirty = True
        return True

    def _refresh_progress(self) -> None:
        """Recalculate and update the progress bar and counts."""
        all_tasks = self._doc.query("[data-task]")
        done_tasks = self._doc.query('[data-task][data-status="done"]')
        total = len(all_tasks)
        completed = len(done_tasks)
        pct = int((completed / total) * 100) if total > 0 else 0

        # Update progress-fill width (justhtml supports attr mutation)
        fills = self._doc.query(".progress-fill")
        for fill in fills:
            fill.attrs["style"] = f"width: {pct}%"

        # Update phase summaries
        for phase_el in self._doc.query("[data-phase]"):
            phase_tasks = phase_el.query("[data-task]")
            phase_done = phase_el.query('[data-task][data-status="done"]')
            # Update summary text with count
            summaries = phase_el.query("summary")
            for summary in summaries:
                text = summary.to_text()
                # Replace (N/M tasks) pattern
                new_count = f"({len(phase_done)}/{len(phase_tasks)} tasks)"
                import re as _re

                updated = _re.sub(r"\(\d+/\d+ tasks\)", new_count, text)
                if updated == text:
                    # No pattern found, skip
                    pass

    def section(self, name: str) -> Element | None:
        """
        Get a named section by data-section value.

        Args:
            name: Section name ("description", "overview", "context",
                  "requirements", "plan", "acceptance-criteria").
        """
        return self.query_one(f'[data-section="{name}"]')

    def progress(self) -> dict[str, int]:
        """
        Get current progress stats.

        Returns:
            Dict with "total", "done", "todo", "percent" keys.
        """
        all_tasks = self.query("[data-task]")
        done = [t for t in all_tasks if t.data.get("status") == "done"]
        todo = [t for t in all_tasks if t.data.get("status") != "done"]
        total = len(all_tasks)
        pct = int((len(done) / total) * 100) if total > 0 else 0
        return {
            "total": total,
            "done": len(done),
            "todo": len(todo),
            "percent": pct,
        }

    def to_html(self) -> str:
        """Serialize the document back to HTML string."""
        result: str = self._doc.to_html()
        return result

    def save(self, path: Path | str | None = None) -> Path:
        """
        Save the (possibly modified) document to disk.

        Args:
            path: Override output path. Uses original path if None.

        Returns:
            Path the file was written to.

        Raises:
            ValueError: If no path provided and document wasn't loaded from file.
        """
        target = Path(path) if path else self._path
        if not target:
            raise ValueError(
                "No file path — provide path argument or load with from_file()"
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_html(), encoding="utf-8")
        self._dirty = False
        return target

    @property
    def is_dirty(self) -> bool:
        """Whether the document has unsaved modifications."""
        return self._dirty
