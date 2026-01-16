"""
Tests for TodoCollection - persistent todo tracking.
"""

import pytest
from htmlgraph import SDK
from htmlgraph.models import Todo


@pytest.fixture
def sdk(tmp_path, isolated_db):
    """Create SDK with temporary directory."""
    graph_dir = tmp_path / ".htmlgraph"
    graph_dir.mkdir()
    (graph_dir / "features").mkdir()
    (graph_dir / "todos").mkdir()
    return SDK(agent="test-agent", directory=str(graph_dir), db_path=str(isolated_db))


class TestTodoModel:
    """Tests for Todo model."""

    def test_todo_creation(self, isolated_db):
        """Test basic todo creation."""
        todo = Todo(
            id="todo-123",
            content="Run tests",
            active_form="Running tests",
        )
        assert todo.id == "todo-123"
        assert todo.content == "Run tests"
        assert todo.active_form == "Running tests"
        assert todo.status == "pending"

    def test_todo_start(self, isolated_db):
        """Test starting a todo."""
        todo = Todo(
            id="todo-123",
            content="Run tests",
            active_form="Running tests",
        )
        todo.start()
        assert todo.status == "in_progress"
        assert todo.started_at is not None

    def test_todo_complete(self, isolated_db):
        """Test completing a todo."""
        todo = Todo(
            id="todo-123",
            content="Run tests",
            active_form="Running tests",
        )
        todo.start()
        todo.complete(agent="test-agent")
        assert todo.status == "completed"
        assert todo.completed_at is not None
        assert todo.completed_by == "test-agent"
        assert todo.duration_seconds is not None

    def test_todo_to_context(self, isolated_db):
        """Test context representation."""
        todo = Todo(id="todo-123", content="Run tests", active_form="Running tests")
        assert todo.to_context() == "[ ] Run tests"

        todo.start()
        assert todo.to_context() == "[~] Run tests"

        todo.complete()
        assert todo.to_context() == "[x] Run tests"

    def test_todo_to_html(self, isolated_db):
        """Test HTML serialization."""
        todo = Todo(
            id="todo-123",
            content="Run tests",
            active_form="Running tests",
            session_id="sess-456",
            feature_id="feat-789",
        )
        html = todo.to_html()
        assert 'id="todo-123"' in html
        assert 'data-type="todo"' in html
        assert 'data-status="pending"' in html
        assert "Run tests" in html
        assert 'data-session-id="sess-456"' in html
        assert 'data-feature-id="feat-789"' in html

    def test_todo_from_todowrite(self, isolated_db):
        """Test creating from TodoWrite format."""
        todowrite_dict = {
            "content": "Fix bug",
            "status": "in_progress",
            "activeForm": "Fixing bug",
        }
        todo = Todo.from_todowrite(
            todo_dict=todowrite_dict,
            todo_id="todo-abc",
            session_id="sess-123",
            feature_id="feat-456",
            agent="claude",
            priority=1,
        )
        assert todo.id == "todo-abc"
        assert todo.content == "Fix bug"
        assert todo.active_form == "Fixing bug"
        assert todo.status == "in_progress"
        assert todo.session_id == "sess-123"
        assert todo.feature_id == "feat-456"
        assert todo.agent == "claude"
        assert todo.priority == 1

    def test_todo_to_todowrite_format(self, isolated_db):
        """Test exporting to TodoWrite format."""
        todo = Todo(
            id="todo-123",
            content="Run tests",
            active_form="Running tests",
            status="pending",
        )
        result = todo.to_todowrite_format()
        assert result == {
            "content": "Run tests",
            "status": "pending",
            "activeForm": "Running tests",
        }


class TestTodoCollection:
    """Tests for TodoCollection."""

    def test_add_todo(self, sdk, isolated_db):
        """Test adding a todo."""
        todo = sdk.todos.add("Run tests", "Running tests")
        assert todo.content == "Run tests"
        assert todo.active_form == "Running tests"
        assert todo.status == "pending"
        assert todo.agent == "test-agent"

        # Verify persisted
        loaded = sdk.todos.get(todo.id)
        assert loaded is not None
        assert loaded.content == "Run tests"

    def test_list_todos(self, sdk, isolated_db):
        """Test listing todos."""
        sdk.todos.add("Task 1", "Doing task 1")
        sdk.todos.add("Task 2", "Doing task 2")
        sdk.todos.add("Task 3", "Doing task 3")

        all_todos = sdk.todos.all()
        assert len(all_todos) == 3

    def test_filter_by_status(self, sdk, isolated_db):
        """Test filtering by status."""
        t1 = sdk.todos.add("Task 1", "Doing task 1")
        t2 = sdk.todos.add("Task 2", "Doing task 2")
        t3 = sdk.todos.add("Task 3", "Doing task 3")

        sdk.todos.start(t1.id)
        sdk.todos.complete(t2.id)

        pending = sdk.todos.pending()
        assert len(pending) == 1
        assert pending[0].id == t3.id

        in_progress = sdk.todos.in_progress()
        assert len(in_progress) == 1
        assert in_progress[0].id == t1.id

        completed = sdk.todos.completed()
        assert len(completed) == 1
        assert completed[0].id == t2.id

    def test_start_todo(self, sdk, isolated_db):
        """Test starting a todo."""
        todo = sdk.todos.add("Run tests", "Running tests")
        started = sdk.todos.start(todo.id)

        assert started is not None
        assert started.status == "in_progress"
        assert started.started_at is not None

    def test_complete_todo(self, sdk, isolated_db):
        """Test completing a todo."""
        todo = sdk.todos.add("Run tests", "Running tests")
        sdk.todos.start(todo.id)
        completed = sdk.todos.complete(todo.id)

        assert completed is not None
        assert completed.status == "completed"
        assert completed.completed_at is not None

    def test_delete_todo(self, sdk, isolated_db):
        """Test deleting a todo."""
        todo = sdk.todos.add("Run tests", "Running tests")
        assert sdk.todos.get(todo.id) is not None

        result = sdk.todos.delete(todo.id)
        assert result is True
        assert sdk.todos.get(todo.id) is None

    def test_clear_completed(self, sdk, isolated_db):
        """Test clearing completed todos."""
        t1 = sdk.todos.add("Task 1", "Doing task 1")
        t2 = sdk.todos.add("Task 2", "Doing task 2")
        t3 = sdk.todos.add("Task 3", "Doing task 3")

        sdk.todos.complete(t1.id)
        sdk.todos.complete(t2.id)

        count = sdk.todos.clear_completed()
        assert count == 2

        all_todos = sdk.todos.all()
        assert len(all_todos) == 1
        assert all_todos[0].id == t3.id

    def test_sync_from_todowrite(self, sdk, isolated_db):
        """Test syncing from TodoWrite format."""
        todowrite_list = [
            {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
            {
                "content": "Task 2",
                "status": "in_progress",
                "activeForm": "Doing task 2",
            },
            {"content": "Task 3", "status": "completed", "activeForm": "Doing task 3"},
        ]

        todos = sdk.todos.sync_from_todowrite(todowrite_list)
        assert len(todos) == 3

        assert todos[0].content == "Task 1"
        assert todos[0].status == "pending"
        assert todos[0].priority == 0

        assert todos[1].content == "Task 2"
        assert todos[1].status == "in_progress"
        assert todos[1].priority == 1

        assert todos[2].content == "Task 3"
        assert todos[2].status == "completed"
        assert todos[2].priority == 2

    def test_to_todowrite_format(self, sdk, isolated_db):
        """Test exporting to TodoWrite format."""
        sdk.todos.add("Task 1", "Doing task 1")
        t2 = sdk.todos.add("Task 2", "Doing task 2")
        sdk.todos.add("Task 3", "Doing task 3")

        # Complete one
        sdk.todos.complete(t2.id)

        # Export should exclude completed
        result = sdk.todos.to_todowrite_format()
        assert len(result) == 2
        assert all(t["status"] != "completed" for t in result)

    def test_for_feature(self, sdk, isolated_db):
        """Test filtering by feature."""
        sdk.todos.add("Task 1", "Doing task 1", feature_id="feat-123")
        sdk.todos.add("Task 2", "Doing task 2", feature_id="feat-123")
        sdk.todos.add("Task 3", "Doing task 3", feature_id="feat-456")

        feature_todos = sdk.todos.for_feature("feat-123")
        assert len(feature_todos) == 2
        assert all(t.feature_id == "feat-123" for t in feature_todos)

    def test_summary(self, sdk, isolated_db):
        """Test summary statistics."""
        t1 = sdk.todos.add("Task 1", "Doing task 1")
        t2 = sdk.todos.add("Task 2", "Doing task 2")
        sdk.todos.add("Task 3", "Doing task 3")

        sdk.todos.start(t1.id)
        sdk.todos.complete(t2.id)

        summary = sdk.todos.summary()
        assert summary["total"] == 3
        assert summary["pending"] == 1
        assert summary["in_progress"] == 1
        assert summary["completed"] == 1
        assert summary["completion_rate"] == pytest.approx(1 / 3)

    def test_priority_ordering(self, sdk, isolated_db):
        """Test that todos are ordered by priority."""
        sdk.todos.add("Task 3", "Doing task 3")  # priority 0
        sdk.todos.add("Task 1", "Doing task 1")  # priority 1
        sdk.todos.add("Task 2", "Doing task 2")  # priority 2

        all_todos = sdk.todos.all()
        assert all_todos[0].priority == 0
        assert all_todos[1].priority == 1
        assert all_todos[2].priority == 2

    def test_persistence_across_reloads(self, sdk, tmp_path, isolated_db):
        """Test that todos persist across SDK reloads."""
        # Add todos
        todo1 = sdk.todos.add("Task 1", "Doing task 1")
        sdk.todos.start(todo1.id)

        # Create new SDK instance using same directory as first SDK
        graph_dir = tmp_path / ".htmlgraph"
        sdk2 = SDK(
            agent="test-agent", directory=str(graph_dir), db_path=str(isolated_db)
        )

        # Force reload by clearing cache
        sdk2.todos._todos = None

        # Check todos persist
        loaded = sdk2.todos.get(todo1.id)
        assert loaded is not None
        assert loaded.content == "Task 1"
        assert loaded.status == "in_progress"
