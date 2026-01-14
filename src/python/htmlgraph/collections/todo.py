from __future__ import annotations

"""
Todo collection for managing persistent todo items.

Unlike other collections, TodoCollection provides:
- Ephemeral-style API matching TodoWrite format
- Session-scoped todos that persist across context boundaries
- Automatic linking to current session and feature
- Bulk sync from TodoWrite format
"""


from datetime import datetime
from typing import TYPE_CHECKING, Any

from htmlgraph.ids import generate_id

if TYPE_CHECKING:
    from htmlgraph.models import Todo
    from htmlgraph.sdk import SDK


class TodoCollection:
    """
    Collection interface for persistent todos.

    Provides an API similar to TodoWrite but with persistence.
    Todos are stored as HTML files in `.htmlgraph/todos/`.

    Example:
        >>> sdk = SDK(agent="claude")
        >>>
        >>> # Create todos (mirrors TodoWrite API)
        >>> sdk.todos.add("Run tests", "Running tests")
        >>> sdk.todos.add("Fix errors", "Fixing errors")
        >>>
        >>> # Start a todo
        >>> sdk.todos.start("todo-abc123")
        >>>
        >>> # Complete a todo
        >>> sdk.todos.complete("todo-abc123")
        >>>
        >>> # List current todos
        >>> pending = sdk.todos.pending()
        >>> in_progress = sdk.todos.in_progress()
        >>>
        >>> # Sync from TodoWrite format
        >>> sdk.todos.sync_from_todowrite([
        ...     {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
        ...     {"content": "Task 2", "status": "completed", "activeForm": "Doing task 2"},
        ... ])
    """

    def __init__(self, sdk: SDK):
        """
        Initialize todo collection.

        Args:
            sdk: Parent SDK instance
        """
        self._sdk = sdk
        self._todos_dir = sdk._directory / "todos"
        self._todos_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded todos (lazy-loaded)
        self._todos: dict[str, Todo] | None = None
        self._ref_manager: Any = None  # Set by SDK during initialization

    def set_ref_manager(self, ref_manager: Any) -> None:
        """
        Set the ref manager for this collection.

        Called by SDK during initialization to enable short ref support.

        Args:
            ref_manager: RefManager instance from SDK
        """
        self._ref_manager = ref_manager

    def _ensure_loaded(self) -> dict[str, Todo]:
        """Load todos from disk if not cached."""
        if self._todos is None:
            self._todos = {}
            self._load_todos()
        return self._todos

    def _load_todos(self) -> None:
        """Load all todos from HTML files."""
        from htmlgraph.models import Todo
        from htmlgraph.parser import HtmlParser

        self._todos = {}

        for html_file in self._todos_dir.glob("*.html"):
            try:
                parser = HtmlParser(filepath=html_file)
                article = parser.get_article()
                if not article:
                    continue

                # Get type to verify this is a todo
                node_type = parser.get_data_attribute(article, "type")
                if node_type != "todo":
                    continue

                # Get all data attributes
                all_attrs = parser.get_all_data_attributes(article)

                # Parse timestamps
                created = datetime.now()
                if all_attrs.get("created"):
                    try:
                        created = datetime.fromisoformat(all_attrs["created"])
                    except ValueError:
                        pass

                updated = datetime.now()
                if all_attrs.get("updated"):
                    try:
                        updated = datetime.fromisoformat(all_attrs["updated"])
                    except ValueError:
                        pass

                started_at = None
                if all_attrs.get("started-at"):
                    try:
                        started_at = datetime.fromisoformat(all_attrs["started-at"])
                    except ValueError:
                        pass

                completed_at = None
                if all_attrs.get("completed-at"):
                    try:
                        completed_at = datetime.fromisoformat(all_attrs["completed-at"])
                    except ValueError:
                        pass

                # Get content from data attributes
                content = all_attrs.get("todo-content", "")
                active_form = all_attrs.get("todo-active-form", content)

                # Get status with default
                status = all_attrs.get("status", "pending")
                if status not in ("pending", "in_progress", "completed"):
                    status = "pending"

                todo = Todo(
                    id=article.attrs.get("id", html_file.stem),
                    content=content,
                    active_form=active_form,
                    status=status,  # type: ignore
                    created=created,
                    updated=updated,
                    started_at=started_at,
                    completed_at=completed_at,
                    session_id=all_attrs.get("session-id"),
                    feature_id=all_attrs.get("feature-id"),
                    agent=all_attrs.get("agent"),
                    completed_by=all_attrs.get("completed-by"),
                    priority=int(all_attrs.get("priority", 0)),
                    duration_seconds=float(all_attrs["duration"])
                    if all_attrs.get("duration")
                    else None,
                )
                self._todos[todo.id] = todo
            except Exception:
                # Skip malformed files
                pass

    def _save_todo(self, todo: Todo) -> None:
        """Save a todo to disk."""
        html_path = self._todos_dir / f"{todo.id}.html"
        html_path.write_text(todo.to_html())

    def _delete_todo_file(self, todo_id: str) -> bool:
        """Delete a todo file from disk."""
        html_path = self._todos_dir / f"{todo_id}.html"
        if html_path.exists():
            html_path.unlink()
            return True
        return False

    def add(
        self,
        content: str,
        active_form: str | None = None,
        feature_id: str | None = None,
        priority: int | None = None,
    ) -> Todo:
        """
        Add a new todo.

        Args:
            content: The imperative form (e.g., "Run tests")
            active_form: The present continuous form (e.g., "Running tests")
                        Defaults to content if not provided
            feature_id: Optional feature to link this todo to
            priority: Order in the list (auto-assigned if not provided)

        Returns:
            The created Todo

        Example:
            >>> todo = sdk.todos.add("Fix authentication bug", "Fixing authentication bug")
        """
        from htmlgraph.models import Todo

        todos = self._ensure_loaded()

        # Generate ID
        todo_id = generate_id(node_type="todo", title=content)

        # Get current session/feature context
        session_id = None
        if (
            hasattr(self._sdk, "session_manager")
            and self._sdk.session_manager._active_session
        ):
            session_id = self._sdk.session_manager._active_session.id

        # Use provided feature_id or try to get from active work
        if not feature_id and hasattr(self._sdk, "session_manager"):
            # Try to get primary feature from session
            active_session = self._sdk.session_manager._active_session
            if active_session and active_session.worked_on:
                feature_id = active_session.worked_on[0]

        # Auto-assign priority if not provided
        if priority is None:
            priority = len([t for t in todos.values() if t.status != "completed"])

        todo = Todo(
            id=todo_id,
            content=content,
            active_form=active_form or content,
            status="pending",
            session_id=session_id,
            feature_id=feature_id,
            agent=self._sdk.agent,
            priority=priority,
        )

        # Save to cache and disk
        todos[todo_id] = todo
        self._save_todo(todo)

        return todo

    def get(self, todo_id: str) -> Todo | None:
        """
        Get a todo by ID.

        Args:
            todo_id: Todo ID to retrieve

        Returns:
            Todo if found, None otherwise
        """
        return self._ensure_loaded().get(todo_id)

    def all(self) -> list[Todo]:
        """
        Get all todos.

        Returns:
            List of all todos, ordered by priority
        """
        todos = list(self._ensure_loaded().values())
        return sorted(todos, key=lambda t: t.priority)

    def pending(self) -> list[Todo]:
        """
        Get all pending todos.

        Returns:
            List of pending todos, ordered by priority
        """
        todos = [t for t in self._ensure_loaded().values() if t.status == "pending"]
        return sorted(todos, key=lambda t: t.priority)

    def in_progress(self) -> list[Todo]:
        """
        Get all in-progress todos.

        Returns:
            List of in-progress todos
        """
        return [t for t in self._ensure_loaded().values() if t.status == "in_progress"]

    def completed(self) -> list[Todo]:
        """
        Get all completed todos.

        Returns:
            List of completed todos
        """
        return [t for t in self._ensure_loaded().values() if t.status == "completed"]

    def start(self, todo_id: str) -> Todo | None:
        """
        Start working on a todo.

        Args:
            todo_id: Todo ID to start

        Returns:
            Updated Todo, or None if not found
        """
        todos = self._ensure_loaded()
        todo = todos.get(todo_id)
        if not todo:
            return None

        todo.start()
        self._save_todo(todo)
        return todo

    def complete(self, todo_id: str) -> Todo | None:
        """
        Complete a todo.

        Args:
            todo_id: Todo ID to complete

        Returns:
            Updated Todo, or None if not found
        """
        todos = self._ensure_loaded()
        todo = todos.get(todo_id)
        if not todo:
            return None

        todo.complete(agent=self._sdk.agent)
        self._save_todo(todo)
        return todo

    def delete(self, todo_id: str) -> bool:
        """
        Delete a todo.

        Args:
            todo_id: Todo ID to delete

        Returns:
            True if deleted, False if not found
        """
        todos = self._ensure_loaded()
        if todo_id in todos:
            del todos[todo_id]
            return self._delete_todo_file(todo_id)
        return False

    def clear_completed(self) -> int:
        """
        Remove all completed todos.

        Returns:
            Number of todos removed
        """
        todos = self._ensure_loaded()
        completed_ids = [t.id for t in todos.values() if t.status == "completed"]

        for todo_id in completed_ids:
            del todos[todo_id]
            self._delete_todo_file(todo_id)

        return len(completed_ids)

    def sync_from_todowrite(
        self,
        todowrite_list: list[dict[str, str]],
        feature_id: str | None = None,
        clear_existing: bool = False,
    ) -> list[Todo]:
        """
        Sync todos from TodoWrite format.

        This enables capturing ephemeral TodoWrite data into persistent storage.

        Args:
            todowrite_list: List of dicts with 'content', 'status', 'activeForm' keys
            feature_id: Optional feature to link all todos to
            clear_existing: If True, removes existing session todos first

        Returns:
            List of created/updated todos

        Example:
            >>> sdk.todos.sync_from_todowrite([
            ...     {"content": "Run tests", "status": "pending", "activeForm": "Running tests"},
            ...     {"content": "Fix errors", "status": "completed", "activeForm": "Fixing errors"},
            ... ])
        """
        from htmlgraph.models import Todo

        todos = self._ensure_loaded()

        # Get current session
        session_id = None
        if (
            hasattr(self._sdk, "session_manager")
            and self._sdk.session_manager._active_session
        ):
            session_id = self._sdk.session_manager._active_session.id

        # Clear existing session todos if requested
        if clear_existing and session_id:
            session_todo_ids = [
                t.id for t in todos.values() if t.session_id == session_id
            ]
            for todo_id in session_todo_ids:
                del todos[todo_id]
                self._delete_todo_file(todo_id)

        result = []
        for i, item in enumerate(todowrite_list):
            todo_id = generate_id(node_type="todo", title=item.get("content", ""))

            todo = Todo.from_todowrite(
                todo_dict=item,
                todo_id=todo_id,
                session_id=session_id,
                feature_id=feature_id,
                agent=self._sdk.agent,
                priority=i,
            )

            todos[todo_id] = todo
            self._save_todo(todo)
            result.append(todo)

        return result

    def to_todowrite_format(self) -> list[dict[str, str]]:
        """
        Export todos to TodoWrite format.

        Returns:
            List of dicts compatible with TodoWrite tool

        Example:
            >>> todowrite_list = sdk.todos.to_todowrite_format()
            >>> # Can be used with TodoWrite tool
        """
        todos = self.all()  # Already sorted by priority
        return [t.to_todowrite_format() for t in todos if t.status != "completed"]

    def for_feature(self, feature_id: str) -> list[Todo]:
        """
        Get all todos for a specific feature.

        Args:
            feature_id: Feature ID to filter by

        Returns:
            List of todos linked to this feature
        """
        todos = [
            t for t in self._ensure_loaded().values() if t.feature_id == feature_id
        ]
        return sorted(todos, key=lambda t: t.priority)

    def for_session(self, session_id: str) -> list[Todo]:
        """
        Get all todos for a specific session.

        Args:
            session_id: Session ID to filter by

        Returns:
            List of todos from this session
        """
        todos = [
            t for t in self._ensure_loaded().values() if t.session_id == session_id
        ]
        return sorted(todos, key=lambda t: t.priority)

    def summary(self) -> dict[str, Any]:
        """
        Get summary statistics for todos.

        Returns:
            Dict with counts by status and other stats
        """
        todos = list(self._ensure_loaded().values())

        pending_count = sum(1 for t in todos if t.status == "pending")
        in_progress_count = sum(1 for t in todos if t.status == "in_progress")
        completed_count = sum(1 for t in todos if t.status == "completed")

        # Calculate average completion time
        completed_durations = [
            t.duration_seconds
            for t in todos
            if t.status == "completed" and t.duration_seconds is not None
        ]
        avg_duration = (
            sum(completed_durations) / len(completed_durations)
            if completed_durations
            else None
        )

        return {
            "total": len(todos),
            "pending": pending_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "completion_rate": completed_count / len(todos) if todos else 0.0,
            "avg_duration_seconds": avg_duration,
        }
