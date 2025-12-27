"""
File watcher for automatic graph reloading.

Monitors .htmlgraph/**/*.html files and reloads collections when changes are detected.
"""

import fnmatch
import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


# Collection-specific file patterns for smart filtering
COLLECTION_PATTERNS = {
    "features": ["feat-*.html", "feature-*.html"],
    "bugs": ["bug-*.html"],
    "spikes": ["spk-*.html", "spike-*.html"],
    "sessions": ["sess-*.html", "session-*.html"],
    "tracks": ["trk-*.html", "track-*.html"],
    "chores": ["chore-*.html"],
    "insights": ["insi-*.html", "insight-*.html"],
    "patterns": ["patt-*.html", "pattern-*.html"],
    "metrics": ["metr-*.html", "metric-*.html"],
}


class GraphFileHandler(FileSystemEventHandler):
    """Handler for filesystem events on graph HTML files."""

    def __init__(self, collection: str, reload_callback: Callable[[], None]):
        """
        Initialize handler.

        Args:
            collection: Name of the collection (e.g., 'features', 'sessions')
            reload_callback: Function to call when reload is needed
        """
        self.collection = collection
        self.reload_callback = reload_callback
        self.debounce_timer: threading.Timer | None = None
        self.debounce_delay = 0.5  # 500ms debounce

    def _is_relevant_file(self, filepath: str) -> bool:
        """
        Check if changed file is relevant to this watcher's collection.

        Args:
            filepath: Path to the file that changed

        Returns:
            True if the file matches this collection's patterns
        """
        filename = Path(filepath).name

        # Skip non-HTML files
        if not filename.endswith(".html"):
            return False

        # Get patterns for this collection (default to all HTML if not found)
        patterns = COLLECTION_PATTERNS.get(self.collection, ["*.html"])

        # Check if filename matches any pattern
        return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)

    def _trigger_reload(self):
        """Trigger a reload after debounce delay."""
        print(f"[FileWatcher] Reloading collection: {self.collection}")
        self.reload_callback()

    def _debounced_reload(self):
        """Debounce rapid file changes to avoid excessive reloads."""
        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = threading.Timer(self.debounce_delay, self._trigger_reload)
        self.debounce_timer.start()

    def on_created(self, event: FileSystemEvent):
        """Handle file creation."""
        if event.is_directory:
            return

        # Skip if not relevant to our collection
        if not self._is_relevant_file(event.src_path):
            return

        print(
            f"[FileWatcher] {self.collection}: File created - {Path(event.src_path).name}"
        )
        self._debounced_reload()

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        if event.is_directory:
            return

        # Skip if not relevant to our collection
        if not self._is_relevant_file(event.src_path):
            return

        print(
            f"[FileWatcher] {self.collection}: File modified - {Path(event.src_path).name}"
        )
        self._debounced_reload()

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if event.is_directory:
            return

        # Skip if not relevant to our collection
        if not self._is_relevant_file(event.src_path):
            return

        print(
            f"[FileWatcher] {self.collection}: File deleted - {Path(event.src_path).name}"
        )
        self._debounced_reload()


class GraphWatcher:
    """Watches graph directories and triggers reloads on changes."""

    def __init__(
        self,
        graph_dir: Path,
        collections: list[str],
        get_graph_callback: Callable[[str], any],
    ):
        """
        Initialize watcher.

        Args:
            graph_dir: Root .htmlgraph directory
            collections: List of collection names to watch
            get_graph_callback: Function to get graph instance for a collection
        """
        self.graph_dir = graph_dir
        self.collections = collections
        self.get_graph_callback = get_graph_callback
        self.observer = Observer()
        self.handlers: dict[str, GraphFileHandler] = {}

    def start(self):
        """Start watching for file changes."""
        print(
            f"[FileWatcher] Starting file watcher for {len(self.collections)} collections..."
        )

        for collection in self.collections:
            collection_dir = self.graph_dir / collection
            if not collection_dir.exists():
                continue

            # Create handler with reload callback
            def make_reload_callback(coll):
                def reload():
                    graph = self.get_graph_callback(coll)
                    count = graph.reload()
                    print(f"[FileWatcher] Reloaded {count} nodes in {coll}")

                return reload

            handler = GraphFileHandler(collection, make_reload_callback(collection))
            self.handlers[collection] = handler

            # Watch the collection directory
            # Use recursive=True for tracks since they're stored in subdirectories
            recursive = collection == "tracks"
            self.observer.schedule(handler, str(collection_dir), recursive=recursive)

        self.observer.start()
        print(f"[FileWatcher] Watching {self.graph_dir} for changes...")

    def stop(self):
        """Stop watching for file changes."""
        print("[FileWatcher] Stopping file watcher...")
        self.observer.stop()
        self.observer.join()

        # Cancel any pending debounce timers
        for handler in self.handlers.values():
            if handler.debounce_timer:
                handler.debounce_timer.cancel()
