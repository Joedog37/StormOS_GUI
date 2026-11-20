"""Workspace manager for StormOS virtual desktops.

Manages multiple virtual workspaces (desktops), window-to-workspace assignment,
workspace switching, and persistence of workspace state.
"""

import logging
from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# Default number of workspaces
DEFAULT_WORKSPACE_COUNT = 4
MIN_WORKSPACES = 1
MAX_WORKSPACES = 10


class WorkspaceManager(QObject):
    """Manages virtual workspaces for StormOS.

    Each workspace holds a set of window app_ids. Switching workspaces
    shows/hides windows accordingly. Singleton pattern via get_instance().
    """

    workspace_changed = Signal(int)  # new workspace index
    workspace_count_changed = Signal(int)  # new count
    windows_moved = Signal(int, int, list)  # from_ws, to_ws, app_ids

    _instance: Optional["WorkspaceManager"] = None

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._workspace_count = DEFAULT_WORKSPACE_COUNT
        self._current_workspace = 0
        # workspace_index -> set of app_ids
        self._workspace_windows: Dict[int, set] = {i: set() for i in range(self._workspace_count)}
        # app_id -> workspace_index (for windows not on any workspace, they appear on all)
        self._window_workspace: Dict[str, int] = {}
        self._names: Dict[int, str] = {i: f"Desktop {i + 1}" for i in range(self._workspace_count)}

    @classmethod
    def get_instance(cls) -> "WorkspaceManager":
        """Return the singleton WorkspaceManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---- Workspace Count ----

    @property
    def workspace_count(self) -> int:
        return self._workspace_count

    @workspace_count.setter
    def workspace_count(self, count: int) -> None:
        count = max(MIN_WORKSPACES, min(MAX_WORKSPACES, count))
        old_count = self._workspace_count

        if count > old_count:
            # Add new workspaces
            for i in range(old_count, count):
                self._workspace_windows[i] = set()
                self._names[i] = f"Desktop {i + 1}"
        elif count < old_count:
            # Move windows from removed workspaces to the last remaining one
            target = count - 1
            for i in range(count, old_count):
                for app_id in self._workspace_windows[i]:
                    self.assign_window_to_workspace(app_id, target)
                del self._workspace_windows[i]
                del self._names[i]
                # Reassign any window pointing to removed workspace
                new_list = dict(self._window_workspace)
                for app_id, ws in new_list.items():
                    if ws >= count:
                        self._window_workspace[app_id] = target

        self._workspace_count = count
        # Clamp current workspace
        if self._current_workspace >= count:
            self._current_workspace = count - 1
        self.workspace_count_changed.emit(count)
        logger.info("Workspace count changed: %d -> %d", old_count, count)

    # ---- Current Workspace ----

    @property
    def current_workspace(self) -> int:
        return self._current_workspace

    @property
    def current_workspace_name(self) -> str:
        return self._names.get(self._current_workspace, "Desktop")

    def set_current_workspace(self, index: int) -> None:
        """Switch to the workspace at the given index."""
        if 0 <= index < self._workspace_count and index != self._current_workspace:
            old = self._current_workspace
            self._current_workspace = index
            self.workspace_changed.emit(index)
            logger.info("Workspace switched: %d -> %d", old, index)

    def next_workspace(self) -> None:
        """Cycle to the next workspace."""
        next_idx = (self._current_workspace + 1) % self._workspace_count
        self.set_current_workspace(next_idx)

    def previous_workspace(self) -> None:
        """Cycle to the previous workspace."""
        prev_idx = (self._current_workspace - 1) % self._workspace_count
        self.set_current_workspace(prev_idx)

    # ---- Window Assignment ----

    def assign_window_to_workspace(self, app_id: str, workspace_index: int) -> None:
        """Assign a window to a specific workspace."""
        if workspace_index < 0 or workspace_index >= self._workspace_count:
            return

        # Remove from old workspace
        old_ws = self._window_workspace.get(app_id)
        if old_ws is not None and old_ws in self._workspace_windows:
            self._workspace_windows[old_ws].discard(app_id)

        # Assign to new workspace
        self._window_workspace[app_id] = workspace_index
        self._workspace_windows[workspace_index].add(app_id)
        logger.debug("Window %s assigned to workspace %d", app_id, workspace_index)

    def get_window_workspace(self, app_id: str) -> Optional[int]:
        """Get the workspace index for a window, or None if unassigned."""
        return self._window_workspace.get(app_id)

    def get_windows_in_workspace(self, workspace_index: int) -> set:
        """Get all app_ids in a workspace."""
        return self._workspace_windows.get(workspace_index, set()).copy()

    def get_visible_windows(self) -> set:
        """Get all windows visible on the current workspace.

        Returns windows assigned to the current workspace plus any unassigned windows
        (which appear on all workspaces).
        """
        current = self._workspace_windows.get(self._current_workspace, set())
        # Unassigned windows appear everywhere
        all_assigned = set()
        for ws_windows in self._workspace_windows.values():
            all_assigned.update(ws_windows)
        unassigned = set()
        # We don't track all windows here; caller must filter
        return current

    def is_window_visible(self, app_id: str) -> bool:
        """Check if a window should be visible on the current workspace."""
        ws = self._window_workspace.get(app_id)
        if ws is None:
            # Unassigned windows appear on all workspaces
            return True
        return ws == self._current_workspace

    def move_window_to_current_workspace(self, app_id: str) -> None:
        """Move a window to the current workspace."""
        self.assign_window_to_workspace(app_id, self._current_workspace)

    # ---- Workspace Names ----

    def set_workspace_name(self, index: int, name: str) -> None:
        """Set a custom name for a workspace."""
        if 0 <= index < self._workspace_count:
            self._names[index] = name
            logger.info("Workspace %d renamed to '%s'", index, name)

    def get_workspace_name(self, index: int) -> str:
        """Get the name of a workspace."""
        return self._names.get(index, f"Desktop {index + 1}")

    def get_all_workspace_names(self) -> List[str]:
        """Get names of all workspaces."""
        return [self._names.get(i, f"Desktop {i + 1}") for i in range(self._workspace_count)]

    # ---- Persistence ----

    def save_settings(self) -> Dict:
        """Serialize workspace settings."""
        return {
            "workspace_count": self._workspace_count,
            "current_workspace": self._current_workspace,
            "window_assignments": {
                app_id: ws for app_id, ws in self._window_workspace.items()
                if ws is not None
            },
            "names": dict(self._names),
        }

    def load_settings(self, settings: Dict) -> None:
        """Restore workspace settings."""
        count = settings.get("workspace_count", DEFAULT_WORKSPACE_COUNT)
        self.workspace_count = count

        names = settings.get("names", {})
        for i, name in names.items():
            idx = int(i)
            if 0 <= idx < self._workspace_count:
                self._names[idx] = name

        assignments = settings.get("window_assignments", {})
        for app_id, ws in assignments.items():
            ws_int = int(ws)
            if 0 <= ws_int < self._workspace_count:
                self._window_workspace[app_id] = ws_int
                self._workspace_windows[ws_int].add(app_id)

        current = settings.get("current_workspace", 0)
        if 0 <= current < self._workspace_count:
            self._current_workspace = current
