"""Tests for the sub-node query and update layer."""

from pathlib import Path

import pytest
from htmlgraph.subnode import SubNodeDocument

# -- Fixtures --

TRACK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Track: Test Integration</title>
    <style>body { color: white; }</style>
</head>
<body>
    <article id="trk-test-001" data-type="track" data-status="todo" data-priority="high">
        <header id="top">
            <h1>Test Integration</h1>
            <div class="metadata">
                <span class="badge status-todo">Planned</span>
                <span class="badge priority-high">High Priority</span>
            </div>
        </header>

        <section data-section="description">
            <p>A test track for sub-node queries.</p>
        </section>

        <section data-section="overview" id="overview">
            <h2>Overview</h2>
            <p>This is the overview text.</p>
        </section>

        <section data-section="context" id="context">
            <h2>Context</h2>
            <p>Background context here.</p>
        </section>

        <section data-section="requirements" id="requirements">
            <h2>Requirements</h2>
            <div class="requirements-list">
                <article class="requirement" data-requirement="req-1" data-priority="must-have">
                    <h4>Add networkx dependency</h4>
                    <span class="badge">must-have</span>
                </article>
                <article class="requirement" data-requirement="req-2" data-priority="must-have">
                    <h4>Create adapter</h4>
                    <span class="badge">must-have</span>
                </article>
                <article class="requirement" data-requirement="req-3" data-priority="should-have">
                    <h4>Add PageRank</h4>
                    <span class="badge">should-have</span>
                </article>
                <article class="requirement" data-requirement="req-4" data-priority="nice-to-have">
                    <h4>Export to DOT</h4>
                    <span class="badge">nice-to-have</span>
                </article>
            </div>
        </section>

        <section data-section="plan" id="plan">
            <h2>Implementation Plan</h2>
            <div class="progress-container">
                <div class="progress-info">
                    <span class="progress-label">0% Complete</span>
                    <span class="progress-count">(0/5 tasks)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
            </div>
            <div class="phases-container">
                <details open data-phase="phase-1">
                    <summary>Phase 1: Foundation (0/2 tasks)</summary>
                    <div data-task="task-1-1" data-status="todo">
                        <input type="checkbox" disabled>
                        <div><strong>Add networkx dependency</strong></div>
                        <span class="estimate">(1.0h)</span>
                    </div>
                    <div data-task="task-1-2" data-status="todo">
                        <input type="checkbox" disabled>
                        <div><strong>Create nx adapter</strong></div>
                        <span class="estimate">(2.0h)</span>
                    </div>
                </details>
                <details data-phase="phase-2">
                    <summary>Phase 2: Algorithms (0/3 tasks)</summary>
                    <div data-task="task-2-1" data-status="todo">
                        <input type="checkbox" disabled>
                        <div><strong>Replace shortest_path</strong></div>
                        <span class="estimate">(1.0h)</span>
                    </div>
                    <div data-task="task-2-2" data-status="todo">
                        <input type="checkbox" disabled>
                        <div><strong>Replace topological_sort</strong></div>
                        <span class="estimate">(1.0h)</span>
                    </div>
                    <div data-task="task-2-3" data-status="todo">
                        <input type="checkbox" disabled>
                        <div><strong>Add neighbors method</strong></div>
                        <span class="estimate">(1.0h)</span>
                    </div>
                </details>
            </div>
        </section>
    </article>
</body>
</html>"""


@pytest.fixture
def doc() -> SubNodeDocument:
    return SubNodeDocument.from_string(TRACK_HTML)


@pytest.fixture
def doc_file(tmp_path: Path) -> SubNodeDocument:
    p = tmp_path / "track.html"
    p.write_text(TRACK_HTML, encoding="utf-8")
    return SubNodeDocument.from_file(p)


# -- Query tests --


class TestQuery:
    def test_query_all_tasks(self, doc: SubNodeDocument) -> None:
        tasks = doc.query("[data-task]")
        assert len(tasks) == 5

    def test_query_tasks_by_status(self, doc: SubNodeDocument) -> None:
        todo = doc.query('[data-task][data-status="todo"]')
        assert len(todo) == 5
        done = doc.query('[data-task][data-status="done"]')
        assert len(done) == 0

    def test_query_requirements_all(self, doc: SubNodeDocument) -> None:
        reqs = doc.query("[data-requirement]")
        assert len(reqs) == 4

    def test_query_requirements_by_priority(self, doc: SubNodeDocument) -> None:
        must = doc.query('[data-requirement][data-priority="must-have"]')
        assert len(must) == 2
        should = doc.query('[data-requirement][data-priority="should-have"]')
        assert len(should) == 1
        nice = doc.query('[data-requirement][data-priority="nice-to-have"]')
        assert len(nice) == 1

    def test_query_phases(self, doc: SubNodeDocument) -> None:
        phases = doc.query("[data-phase]")
        assert len(phases) == 2

    def test_query_sections(self, doc: SubNodeDocument) -> None:
        desc = doc.query('[data-section="description"]')
        assert len(desc) == 1
        plan = doc.query('[data-section="plan"]')
        assert len(plan) == 1

    def test_query_one_found(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["task"] == "task-1-1"

    def test_query_one_not_found(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="nonexistent"]')
        assert el is None

    def test_query_tasks_within_phase(self, doc: SubNodeDocument) -> None:
        p1_tasks = doc.query('[data-phase="phase-1"] [data-task]')
        assert len(p1_tasks) == 2
        p2_tasks = doc.query('[data-phase="phase-2"] [data-task]')
        assert len(p2_tasks) == 3


# -- Convenience method tests --


class TestConvenienceMethods:
    def test_tasks_all(self, doc: SubNodeDocument) -> None:
        assert len(doc.tasks()) == 5

    def test_tasks_by_status(self, doc: SubNodeDocument) -> None:
        assert len(doc.tasks(status="todo")) == 5
        assert len(doc.tasks(status="done")) == 0

    def test_tasks_by_phase(self, doc: SubNodeDocument) -> None:
        assert len(doc.tasks(phase="phase-1")) == 2
        assert len(doc.tasks(phase="phase-2")) == 3

    def test_tasks_by_phase_and_status(self, doc: SubNodeDocument) -> None:
        assert len(doc.tasks(phase="phase-1", status="todo")) == 2

    def test_requirements_all(self, doc: SubNodeDocument) -> None:
        assert len(doc.requirements()) == 4

    def test_requirements_by_priority(self, doc: SubNodeDocument) -> None:
        assert len(doc.requirements(priority="must-have")) == 2
        assert len(doc.requirements(priority="nice-to-have")) == 1

    def test_phases(self, doc: SubNodeDocument) -> None:
        assert len(doc.phases()) == 2

    def test_section(self, doc: SubNodeDocument) -> None:
        overview = doc.section("overview")
        assert overview is not None
        assert "overview text" in overview.text.lower()

    def test_section_not_found(self, doc: SubNodeDocument) -> None:
        assert doc.section("nonexistent") is None

    def test_progress_initial(self, doc: SubNodeDocument) -> None:
        p = doc.progress()
        assert p["total"] == 5
        assert p["done"] == 0
        assert p["todo"] == 5
        assert p["percent"] == 0


# -- Element wrapper tests --


class TestElement:
    def test_tag(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.tag == "div"

    def test_attrs(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.attrs["data-task"] == "task-1-1"
        assert el.attrs["data-status"] == "todo"

    def test_data(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["task"] == "task-1-1"
        assert el.data["status"] == "todo"
        assert "data-task" not in el.data  # prefix stripped

    def test_text(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert "Add networkx dependency" in el.text

    def test_html(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-requirement="req-1"]')
        assert el is not None
        assert "data-requirement" in el.html
        assert "must-have" in el.html

    def test_repr(self, doc: SubNodeDocument) -> None:
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        r = repr(el)
        assert "div" in r
        assert "task=task-1-1" in r


# -- Update tests --


class TestUpdate:
    def test_update_single(self, doc: SubNodeDocument) -> None:
        count = doc.update('[data-task="task-1-1"]', {"data-status": "done"})
        assert count == 1
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["status"] == "done"

    def test_update_multiple(self, doc: SubNodeDocument) -> None:
        count = doc.update("[data-task]", {"data-status": "done"})
        assert count == 5
        done = doc.query('[data-task][data-status="done"]')
        assert len(done) == 5

    def test_update_no_match(self, doc: SubNodeDocument) -> None:
        count = doc.update('[data-task="nonexistent"]', {"data-status": "done"})
        assert count == 0

    def test_update_sets_dirty(self, doc: SubNodeDocument) -> None:
        assert not doc.is_dirty
        doc.update('[data-task="task-1-1"]', {"data-status": "done"})
        assert doc.is_dirty

    def test_update_no_match_not_dirty(self, doc: SubNodeDocument) -> None:
        doc.update('[data-task="nonexistent"]', {"data-status": "done"})
        assert not doc.is_dirty

    def test_remove_attr(self, doc: SubNodeDocument) -> None:
        # First add a custom attr
        doc.update('[data-task="task-1-1"]', {"data-assigned": "alice"})
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data.get("assigned") == "alice"

        count = doc.remove_attr('[data-task="task-1-1"]', "data-assigned")
        assert count == 1
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert "assigned" not in el.data


# -- Task completion tests --


class TestTaskCompletion:
    def test_complete_task(self, doc: SubNodeDocument) -> None:
        assert doc.complete_task("task-1-1")
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["status"] == "done"

    def test_complete_task_not_found(self, doc: SubNodeDocument) -> None:
        assert not doc.complete_task("nonexistent")

    def test_complete_task_updates_dirty(self, doc: SubNodeDocument) -> None:
        doc.complete_task("task-1-1")
        assert doc.is_dirty

    def test_uncomplete_task(self, doc: SubNodeDocument) -> None:
        doc.complete_task("task-1-1")
        assert doc.uncomplete_task("task-1-1")
        el = doc.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["status"] == "todo"

    def test_uncomplete_task_not_found(self, doc: SubNodeDocument) -> None:
        assert not doc.uncomplete_task("nonexistent")

    def test_complete_updates_progress(self, doc: SubNodeDocument) -> None:
        doc.complete_task("task-1-1")
        doc.complete_task("task-1-2")
        p = doc.progress()
        assert p["done"] == 2
        assert p["todo"] == 3
        assert p["percent"] == 40

    def test_verify_requirement(self, doc: SubNodeDocument) -> None:
        assert doc.verify_requirement("req-1")
        el = doc.query_one('[data-requirement="req-1"]')
        assert el is not None
        assert el.data.get("verified") == "true"

    def test_verify_requirement_not_found(self, doc: SubNodeDocument) -> None:
        assert not doc.verify_requirement("nonexistent")


# -- Serialization tests --


class TestSerialization:
    def test_to_html_preserves_structure(self, doc: SubNodeDocument) -> None:
        html = doc.to_html()
        assert "<!DOCTYPE" in html or "<!doctype" in html
        assert "trk-test-001" in html
        assert "data-task" in html
        assert "data-requirement" in html

    def test_roundtrip_preserves_content(self, doc: SubNodeDocument) -> None:
        html = doc.to_html()
        doc2 = SubNodeDocument.from_string(html)
        assert len(doc2.tasks()) == 5
        assert len(doc2.requirements()) == 4
        assert len(doc2.phases()) == 2

    def test_modifications_persist_in_html(self, doc: SubNodeDocument) -> None:
        doc.complete_task("task-1-1")
        doc.complete_task("task-2-3")
        html = doc.to_html()

        doc2 = SubNodeDocument.from_string(html)
        assert len(doc2.tasks(status="done")) == 2
        assert len(doc2.tasks(status="todo")) == 3

    def test_save_to_file(self, doc_file: SubNodeDocument) -> None:
        doc_file.complete_task("task-1-1")
        path = doc_file.save()
        assert path.exists()

        # Reload and verify
        doc2 = SubNodeDocument.from_file(path)
        el = doc2.query_one('[data-task="task-1-1"]')
        assert el is not None
        assert el.data["status"] == "done"

    def test_save_clears_dirty(self, doc_file: SubNodeDocument) -> None:
        doc_file.complete_task("task-1-1")
        assert doc_file.is_dirty
        doc_file.save()
        assert not doc_file.is_dirty

    def test_save_to_new_path(self, doc: SubNodeDocument, tmp_path: Path) -> None:
        out = tmp_path / "output.html"
        doc.save(out)
        assert out.exists()
        doc2 = SubNodeDocument.from_file(out)
        assert len(doc2.tasks()) == 5

    def test_save_no_path_raises(self, doc: SubNodeDocument) -> None:
        with pytest.raises(ValueError, match="No file path"):
            doc.save()


# -- File loading tests --


class TestFileLoading:
    def test_from_file(self, tmp_path: Path) -> None:
        p = tmp_path / "test.html"
        p.write_text(TRACK_HTML, encoding="utf-8")
        doc = SubNodeDocument.from_file(p)
        assert len(doc.tasks()) == 5

    def test_from_real_track(self) -> None:
        """Test against actual track file if it exists."""
        track_path = Path(".htmlgraph/tracks/trk-0c23b03a.html")
        if not track_path.exists():
            pytest.skip("No real track file available")

        doc = SubNodeDocument.from_file(track_path)
        tasks = doc.tasks()
        assert len(tasks) > 0

        reqs = doc.requirements()
        assert len(reqs) > 0

        p = doc.progress()
        assert p["total"] > 0
