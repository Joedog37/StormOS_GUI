"""Tests for Phase 9 — Advanced Windowing & Multitasking.

Covers:
- WorkspaceManager: workspace creation, switching, window assignment, persistence
- Window snap grid: snap zone detection, snap geometry calculation
- Alt+Tab task switcher: population, navigation, selection
- Overview mode: population, thumbnail creation
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the project src directory is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication

# Workspace Manager tests
from stormos.services.workspace_manager import (
    WorkspaceManager,
    DEFAULT_WORKSPACE_COUNT,
    MIN_WORKSPACES,
    MAX_WORKSPACES,
)

# Window snap constants
from stormos.desktop.window import (
    SNAP_NONE,
    SNAP_LEFT,
    SNAP_RIGHT,
    SNAP_TOP_LEFT,
    SNAP_TOP_RIGHT,
    SNAP_BOTTOM_LEFT,
    SNAP_BOTTOM_RIGHT,
    SNAP_TOP,
    SNAP_THRESHOLD,
)


# Ensure QApplication exists for Qt object tests
app = QApplication.instance()
if app is None:
    app = QApplication([])


# =============================================================================
# WorkspaceManager Tests
# =============================================================================

class TestWorkspaceManagerConstants(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None

    def tearDown(self):
        WorkspaceManager._instance = None

    def test_default_workspace_count(self):
        self.assertEqual(DEFAULT_WORKSPACE_COUNT, 4)

    def test_min_workspaces(self):
        self.assertEqual(MIN_WORKSPACES, 1)

    def test_max_workspaces(self):
        self.assertEqual(MAX_WORKSPACES, 10)


class TestWorkspaceManagerCreation(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None
        self.wm = WorkspaceManager()

    def tearDown(self):
        WorkspaceManager._instance = None
        self.wm.deleteLater()

    def test_initial_workspace_count(self):
        self.assertEqual(self.wm.workspace_count, DEFAULT_WORKSPACE_COUNT)

    def test_initial_current_workspace(self):
        self.assertEqual(self.wm.current_workspace, 0)

    def test_initial_workspace_names(self):
        names = self.wm.get_all_workspace_names()
        self.assertEqual(len(names), 4)
        self.assertEqual(names[0], "Desktop 1")
        self.assertEqual(names[1], "Desktop 2")
        self.assertEqual(names[2], "Desktop 3")
        self.assertEqual(names[3], "Desktop 4")

    def test_singleton_pattern(self):
        wm1 = WorkspaceManager.get_instance()
        wm2 = WorkspaceManager.get_instance()
        self.assertIs(wm1, wm2)

    def test_current_workspace_name(self):
        self.assertEqual(self.wm.current_workspace_name, "Desktop 1")


class TestWorkspaceManagerCount(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None
        self.wm = WorkspaceManager()

    def tearDown(self):
        WorkspaceManager._instance = None
        self.wm.deleteLater()

    def test_increase_workspace_count(self):
        self.wm.workspace_count = 6
        self.assertEqual(self.wm.workspace_count, 6)
        names = self.wm.get_all_workspace_names()
        self.assertEqual(len(names), 6)

    def test_decrease_workspace_count(self):
        self.wm.workspace_count = 2
        self.assertEqual(self.wm.workspace_count, 2)

    def test_clamp_to_min(self):
        self.wm.workspace_count = 0
        self.assertEqual(self.wm.workspace_count, MIN_WORKSPACES)

    def test_clamp_to_max(self):
        self.wm.workspace_count = 100
        self.assertEqual(self.wm.workspace_count, MAX_WORKSPACES)

    def test_current_workspace_clamped_on_decrease(self):
        self.wm.set_current_workspace(3)
        self.assertEqual(self.wm.current_workspace, 3)
        self.wm.workspace_count = 2
        self.assertEqual(self.wm.current_workspace, 1)

    def test_windows_moved_on_workspace_removal(self):
        self.wm.assign_window_to_workspace("notes", 3)
        self.wm.workspace_count = 2
        self.assertEqual(self.wm.get_window_workspace("notes"), 1)


class TestWorkspaceManagerSwitching(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None
        self.wm = WorkspaceManager()

    def tearDown(self):
        WorkspaceManager._instance = None
        self.wm.deleteLater()

    def test_set_current_workspace(self):
        self.wm.set_current_workspace(2)
        self.assertEqual(self.wm.current_workspace, 2)

    def test_cannot_set_invalid_workspace(self):
        self.wm.set_current_workspace(10)
        self.assertEqual(self.wm.current_workspace, 0)

    def test_cannot_set_negative_workspace(self):
        self.wm.set_current_workspace(-1)
        self.assertEqual(self.wm.current_workspace, 0)

    def test_next_workspace(self):
        self.wm.next_workspace()
        self.assertEqual(self.wm.current_workspace, 1)

    def test_next_workspace_wraps_around(self):
        self.wm.set_current_workspace(3)
        self.wm.next_workspace()
        self.assertEqual(self.wm.current_workspace, 0)

    def test_previous_workspace(self):
        self.wm.previous_workspace()
        self.assertEqual(self.wm.current_workspace, 3)

    def test_previous_workspace_middle(self):
        self.wm.set_current_workspace(2)
        self.wm.previous_workspace()
        self.assertEqual(self.wm.current_workspace, 1)


class TestWorkspaceManagerWindowAssignment(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None
        self.wm = WorkspaceManager()

    def tearDown(self):
        WorkspaceManager._instance = None
        self.wm.deleteLater()

    def test_assign_window_to_workspace(self):
        self.wm.assign_window_to_workspace("notes", 1)
        self.assertEqual(self.wm.get_window_workspace("notes"), 1)
        self.assertIn("notes", self.wm.get_windows_in_workspace(1))

    def test_assign_window_invalid_workspace(self):
        self.wm.assign_window_to_workspace("notes", 100)
        self.assertIsNone(self.wm.get_window_workspace("notes"))

    def test_reassign_window(self):
        self.wm.assign_window_to_workspace("notes", 0)
        self.wm.assign_window_to_workspace("notes", 2)
        self.assertEqual(self.wm.get_window_workspace("notes"), 2)
        self.assertNotIn("notes", self.wm.get_windows_in_workspace(0))
        self.assertIn("notes", self.wm.get_windows_in_workspace(2))

    def test_get_windows_in_workspace(self):
        self.wm.assign_window_to_workspace("notes", 1)
        self.wm.assign_window_to_workspace("calculator", 1)
        windows = self.wm.get_windows_in_workspace(1)
        self.assertIn("notes", windows)
        self.assertIn("calculator", windows)

    def test_is_window_visible_assigned_to_current(self):
        self.wm.assign_window_to_workspace("notes", 0)
        self.assertTrue(self.wm.is_window_visible("notes"))

    def test_is_window_visible_assigned_to_other(self):
        self.wm.assign_window_to_workspace("notes", 1)
        self.assertFalse(self.wm.is_window_visible("notes"))

    def test_is_window_visible_unassigned(self):
        self.assertTrue(self.wm.is_window_visible("unknown_app"))

    def test_move_window_to_current_workspace(self):
        self.wm.assign_window_to_workspace("notes", 2)
        self.wm.move_window_to_current_workspace("notes")
        self.assertEqual(self.wm.get_window_workspace("notes"), 0)


class TestWorkspaceManagerNames(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None
        self.wm = WorkspaceManager()

    def tearDown(self):
        WorkspaceManager._instance = None
        self.wm.deleteLater()

    def test_set_workspace_name(self):
        self.wm.set_workspace_name(0, "Work")
        self.assertEqual(self.wm.get_workspace_name(0), "Work")

    def test_set_invalid_workspace_name(self):
        self.wm.set_workspace_name(100, "Invalid")
        self.assertEqual(self.wm.get_workspace_name(100), "Desktop 101")

    def test_get_all_workspace_names(self):
        self.wm.set_workspace_name(0, "Work")
        self.wm.set_workspace_name(1, "Personal")
        names = self.wm.get_all_workspace_names()
        self.assertEqual(names[0], "Work")
        self.assertEqual(names[1], "Personal")
        self.assertEqual(names[2], "Desktop 3")


class TestWorkspaceManagerPersistence(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None

    def tearDown(self):
        WorkspaceManager._instance = None

    def test_save_settings(self):
        wm = WorkspaceManager()
        wm.assign_window_to_workspace("notes", 1)
        wm.set_workspace_name(0, "Work")
        wm.set_current_workspace(2)

        settings = wm.save_settings()
        self.assertEqual(settings["workspace_count"], 4)
        self.assertEqual(settings["current_workspace"], 2)
        self.assertEqual(settings["window_assignments"]["notes"], 1)
        self.assertEqual(settings["names"][0], "Work")
        wm.deleteLater()

    def test_load_settings(self):
        wm1 = WorkspaceManager()
        wm1.assign_window_to_workspace("notes", 1)
        wm1.set_workspace_name(0, "Work")
        wm1.set_current_workspace(2)
        settings = wm1.save_settings()
        wm1.deleteLater()

        wm2 = WorkspaceManager()
        wm2.load_settings(settings)

        self.assertEqual(wm2.workspace_count, 4)
        self.assertEqual(wm2.current_workspace, 2)
        self.assertEqual(wm2.get_window_workspace("notes"), 1)
        self.assertEqual(wm2.get_workspace_name(0), "Work")
        wm2.deleteLater()

    def test_load_empty_settings(self):
        wm = WorkspaceManager()
        wm.load_settings({})
        self.assertEqual(wm.workspace_count, DEFAULT_WORKSPACE_COUNT)
        self.assertEqual(wm.current_workspace, 0)
        wm.deleteLater()


# =============================================================================
# Window Snap Grid Tests
# =============================================================================

class TestSnapConstants(unittest.TestCase):
    def test_snap_threshold(self):
        self.assertEqual(SNAP_THRESHOLD, 5)

    def test_snap_none(self):
        self.assertEqual(SNAP_NONE, "none")

    def test_snap_left(self):
        self.assertEqual(SNAP_LEFT, "left")

    def test_snap_right(self):
        self.assertEqual(SNAP_RIGHT, "right")

    def test_snap_top_left(self):
        self.assertEqual(SNAP_TOP_LEFT, "top_left")

    def test_snap_top_right(self):
        self.assertEqual(SNAP_TOP_RIGHT, "top_right")

    def test_snap_bottom_left(self):
        self.assertEqual(SNAP_BOTTOM_LEFT, "bottom_left")

    def test_snap_bottom_right(self):
        self.assertEqual(SNAP_BOTTOM_RIGHT, "bottom_right")

    def test_snap_top(self):
        self.assertEqual(SNAP_TOP, "top")


class TestWindowSnapDetection(unittest.TestCase):
    """Test snap zone detection logic using a mock parent widget."""

    def _make_parent(self):
        parent = MagicMock()
        parent.width.return_value = 1920
        parent.height.return_value = 1080
        return parent

    def _make_window(self, parent):
        from stormos.desktop.window import StormWindow
        win = StormWindow("test", parent=None)
        win.parentWidget = MagicMock(return_value=parent)
        return win

    def test_detect_snap_left(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(0, 100, 800, 600)
        self.assertEqual(zone, SNAP_LEFT)

    def test_detect_snap_right(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(1120, 100, 800, 600)
        self.assertEqual(zone, SNAP_RIGHT)

    def test_detect_snap_top_left(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(0, 0, 800, 600)
        self.assertEqual(zone, SNAP_TOP_LEFT)

    def test_detect_snap_top_right(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(1120, 0, 800, 600)
        self.assertEqual(zone, SNAP_TOP_RIGHT)

    def test_detect_snap_bottom_left(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(0, 480, 800, 600)
        self.assertEqual(zone, SNAP_BOTTOM_LEFT)

    def test_detect_snap_bottom_right(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(1120, 480, 800, 600)
        self.assertEqual(zone, SNAP_BOTTOM_RIGHT)

    def test_detect_snap_top(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(500, 0, 800, 600)
        self.assertEqual(zone, SNAP_TOP)

    def test_detect_no_snap_in_center(self):
        win = self._make_window(self._make_parent())
        zone = win._detect_snap_zone(500, 300, 800, 600)
        self.assertEqual(zone, SNAP_NONE)

    def test_detect_no_snap_without_parent(self):
        from stormos.desktop.window import StormWindow
        win = StormWindow("test", parent=None)
        zone = win._detect_snap_zone(0, 0, 800, 600)
        self.assertEqual(zone, SNAP_NONE)


class TestWindowSnapGeometry(unittest.TestCase):
    """Test snap geometry calculation."""

    def _make_parent(self):
        parent = MagicMock()
        parent.width.return_value = 1920
        parent.height.return_value = 1080
        return parent

    def _make_window(self, parent):
        from stormos.desktop.window import StormWindow
        win = StormWindow("test", parent=None)
        win.parentWidget = MagicMock(return_value=parent)
        return win

    def test_apply_snap_left_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_LEFT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 0)
        self.assertEqual(geom.y(), 0)
        self.assertEqual(geom.width(), 960)
        self.assertEqual(geom.height(), 1016)

    def test_apply_snap_right_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_RIGHT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 960)
        self.assertEqual(geom.width(), 960)

    def test_apply_snap_top_left_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_TOP_LEFT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 0)
        self.assertEqual(geom.y(), 0)
        self.assertEqual(geom.width(), 960)
        self.assertEqual(geom.height(), 508)

    def test_apply_snap_top_right_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_TOP_RIGHT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 960)
        self.assertEqual(geom.y(), 0)

    def test_apply_snap_bottom_left_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_BOTTOM_LEFT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 0)
        self.assertEqual(geom.y(), 508)

    def test_apply_snap_bottom_right_geometry(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_BOTTOM_RIGHT)
        geom = win.geometry()
        self.assertEqual(geom.x(), 960)
        self.assertEqual(geom.y(), 508)

    def test_apply_snap_top_maximizes(self):
        win = self._make_window(self._make_parent())
        win._apply_snap(SNAP_TOP)
        geom = win.geometry()
        self.assertEqual(geom.x(), 0)
        self.assertEqual(geom.width(), 1920)
        self.assertTrue(win._is_maximized)

    def test_apply_snap_none_does_nothing(self):
        win = self._make_window(self._make_parent())
        win.setGeometry(100, 100, 800, 600)
        win._apply_snap(SNAP_NONE)
        geom = win.geometry()
        self.assertEqual(geom.x(), 100)
        self.assertEqual(geom.y(), 100)


# =============================================================================
# Alt+Tab Task Switcher Tests
# =============================================================================

class TestAltTabSwitcher(unittest.TestCase):
    def test_switcher_creation(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()
        self.assertTrue(switcher.isHidden())
        switcher.deleteLater()

    def test_populate_with_no_windows(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()
        switcher.populate({})
        self.assertEqual(len(switcher._windows), 0)
        switcher.deleteLater()

    def test_populate_with_windows(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win1 = MagicMock()
        mock_win1._is_minimized = False
        mock_win1._title = "Notes"
        mock_win1._icon = "📝"

        mock_win2 = MagicMock()
        mock_win2._is_minimized = False
        mock_win2._title = "Calculator"
        mock_win2._icon = "⚡"

        windows = {"notes": mock_win1, "calculator": mock_win2}
        switcher.populate(windows)
        self.assertEqual(len(switcher._windows), 2)
        switcher.deleteLater()

    def test_populate_excludes_minimized(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win = MagicMock()
        mock_win._is_minimized = True
        mock_win._title = "Notes"
        mock_win._icon = "📝"

        windows = {"notes": mock_win}
        switcher.populate(windows)
        self.assertEqual(len(switcher._windows), 0)
        switcher.deleteLater()

    def test_navigate_next(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win1 = MagicMock()
        mock_win1._is_minimized = False
        mock_win1._title = "Notes"
        mock_win1._icon = "📝"

        mock_win2 = MagicMock()
        mock_win2._is_minimized = False
        mock_win2._title = "Calculator"
        mock_win2._icon = "⚡"

        windows = {"notes": mock_win1, "calculator": mock_win2}
        switcher.populate(windows)
        switcher._navigate_next()
        self.assertEqual(switcher._current_index, 1)
        switcher.deleteLater()

    def test_navigate_prev(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win1 = MagicMock()
        mock_win1._is_minimized = False
        mock_win1._title = "Notes"
        mock_win1._icon = "📝"

        mock_win2 = MagicMock()
        mock_win2._is_minimized = False
        mock_win2._title = "Calculator"
        mock_win2._icon = "⚡"

        windows = {"notes": mock_win1, "calculator": mock_win2}
        switcher.populate(windows)
        switcher._navigate_prev()
        self.assertEqual(switcher._current_index, 1)
        switcher.deleteLater()

    def test_navigate_wraps_forward(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win = MagicMock()
        mock_win._is_minimized = False
        mock_win._title = "Notes"
        mock_win._icon = "📝"

        windows = {"notes": mock_win}
        switcher.populate(windows)
        switcher._navigate_next()
        self.assertEqual(switcher._current_index, 0)
        switcher.deleteLater()

    def test_select_current(self):
        from stormos.desktop.task_switcher import AltTabSwitcher
        switcher = AltTabSwitcher()

        mock_win = MagicMock()
        mock_win._is_minimized = False
        mock_win._title = "Notes"
        mock_win._icon = "📝"

        windows = {"notes": mock_win}
        switcher.populate(windows)

        selected = []
        switcher.window_selected.connect(lambda aid: selected.append(aid))
        switcher._select_current()
        self.assertEqual(selected, ["notes"])
        switcher.deleteLater()


# =============================================================================
# Overview Mode Tests
# =============================================================================

class TestOverviewMode(unittest.TestCase):
    def test_overview_creation(self):
        from stormos.desktop.overview_mode import OverviewMode
        overview = OverviewMode()
        self.assertTrue(overview.isHidden())
        overview.deleteLater()

    def test_populate_with_no_windows(self):
        from stormos.desktop.overview_mode import OverviewMode
        overview = OverviewMode()
        overview.populate({}, workspace_count=4, current_workspace=0)
        self.assertEqual(len(overview._thumbnails), 0)
        overview.deleteLater()

    def test_populate_with_windows(self):
        from stormos.desktop.overview_mode import OverviewMode
        overview = OverviewMode()

        mock_win = MagicMock()
        mock_win._is_minimized = False
        mock_win._title = "Notes"
        mock_win._icon = "📝"

        windows = {"notes": mock_win}
        overview.populate(windows, workspace_count=4, current_workspace=0)
        self.assertEqual(len(overview._thumbnails), 1)
        overview.deleteLater()

    def test_populate_excludes_minimized(self):
        from stormos.desktop.overview_mode import OverviewMode
        overview = OverviewMode()

        mock_win = MagicMock()
        mock_win._is_minimized = True
        mock_win._title = "Notes"
        mock_win._icon = "📝"

        windows = {"notes": mock_win}
        overview.populate(windows, workspace_count=4, current_workspace=0)
        self.assertEqual(len(overview._thumbnails), 0)
        overview.deleteLater()

    def test_thumbnail_hover(self):
        from stormos.desktop.overview_mode import WindowThumbnail
        thumb = WindowThumbnail("notes", "Notes", "📝", workspace=0)
        thumb.set_hovered(True)
        self.assertTrue(thumb._is_hovered)
        thumb.set_hovered(False)
        self.assertFalse(thumb._is_hovered)
        thumb.deleteLater()

    def test_thumbnail_workspace(self):
        from stormos.desktop.overview_mode import WindowThumbnail
        thumb = WindowThumbnail("notes", "Notes", "📝", workspace=2)
        self.assertEqual(thumb._workspace, 2)
        thumb.set_workspace(3)
        self.assertEqual(thumb._workspace, 3)
        thumb.deleteLater()

    def test_thumbnail_click_signal(self):
        from stormos.desktop.overview_mode import WindowThumbnail
        thumb = WindowThumbnail("notes", "Notes", "📝", workspace=0)
        clicked = []
        thumb.clicked.connect(lambda aid: clicked.append(aid))
        thumb.clicked.emit("notes")
        self.assertEqual(clicked, ["notes"])
        thumb.deleteLater()


# =============================================================================
# Integration Tests
# =============================================================================

class TestPhase9Integration(unittest.TestCase):
    def setUp(self):
        WorkspaceManager._instance = None

    def tearDown(self):
        WorkspaceManager._instance = None

    def test_workspace_manager_with_desktop_view(self):
        """Test that DesktopView initializes workspace manager."""
        from stormos.desktop.desktop_view import DesktopView
        view = DesktopView()
        self.assertIsNotNone(view.workspace_manager)
        self.assertEqual(view.workspace_manager.workspace_count, DEFAULT_WORKSPACE_COUNT)
        view.deleteLater()

    def test_task_switcher_accessible(self):
        """Test that DesktopView has task switcher."""
        from stormos.desktop.desktop_view import DesktopView
        view = DesktopView()
        self.assertIsNotNone(view.task_switcher)
        view.deleteLater()

    def test_overview_accessible(self):
        """Test that DesktopView has overview mode."""
        from stormos.desktop.desktop_view import DesktopView
        view = DesktopView()
        self.assertIsNotNone(view.overview_mode)
        view.deleteLater()

    def test_workspace_switching_methods(self):
        """Test workspace switching methods on DesktopView."""
        from stormos.desktop.desktop_view import DesktopView
        view = DesktopView()

        view.next_workspace()
        self.assertEqual(view.workspace_manager.current_workspace, 1)

        view.previous_workspace()
        self.assertEqual(view.workspace_manager.current_workspace, 0)

        view.switch_workspace(3)
        self.assertEqual(view.workspace_manager.current_workspace, 3)
        view.deleteLater()


if __name__ == "__main__":
    unittest.main()
