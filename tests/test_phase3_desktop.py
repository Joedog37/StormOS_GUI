"""Tests for Phase 3: Desktop Environment.

Covers wallpaper rendering, Storm Dock (Taskbar & Clock), Start button,
Command Center (Start Menu & App Filtering), and Safe Exit dialog workflows.
"""

import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from stormos.core.constants import APP_NAME
from stormos.desktop.command_center import CommandCenter, AppItemWidget
from stormos.desktop.desktop_view import DesktopCardWidget, DesktopView
from stormos.desktop.safe_exit_dialog import SafeExitDialog
from stormos.desktop.storm_dock import DockAppButton, StormDock
from stormos.services.user_manager import UserProfile


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_profile():
    return UserProfile(
        username="commander",
        display_name="Storm Commander",
        role="admin",
        wallpaper="wallpaper.png",
    )


# ==========================================
# 1. Storm Dock Tests
# ==========================================

def test_storm_dock_initialization(qapp, test_profile):
    """Verify StormDock renders Start button, app launchers, clock, and user badge."""
    dock = StormDock(current_user=test_profile)
    assert dock.start_btn.text() == "⚡ STORM"
    assert "Storm Commander" in dock.user_badge_btn.text()
    assert dock.time_label.text() != ""
    assert dock.date_label.text() != ""


def test_storm_dock_start_button_signal(qapp, test_profile):
    """Verify clicking the Start button emits command_center_toggled."""
    dock = StormDock(current_user=test_profile)
    toggled = []
    dock.command_center_toggled.connect(lambda: toggled.append(True))

    dock.start_btn.click()
    assert len(toggled) == 1


def test_storm_dock_app_launch(qapp, test_profile):
    """Verify clicking pinned app buttons emits app_launch_requested with correct app_id."""
    dock = StormDock(current_user=test_profile)
    launched = []
    dock.app_launch_requested.connect(lambda app_id: launched.append(app_id))

    # Find the Notes button
    buttons = dock.findChildren(DockAppButton)
    assert len(buttons) >= 4

    notes_btn = next((b for b in buttons if b.app_id == "notes"), None)
    assert notes_btn is not None
    notes_btn.click()

    assert len(launched) == 1
    assert launched[0] == "notes"


def test_storm_dock_user_update(qapp, test_profile):
    """Verify user badge updates when set_user is called."""
    dock = StormDock(current_user=test_profile)
    new_user = UserProfile(username="navigator", display_name="Chief Navigator")
    dock.set_user(new_user)
    assert "Chief Navigator" in dock.user_badge_btn.text()


# ==========================================
# 2. Command Center Tests
# ==========================================

def test_command_center_initialization(qapp, test_profile):
    """Verify CommandCenter displays title, user details, search input, and default apps."""
    cc = CommandCenter(current_user=test_profile)
    assert cc.search_input is not None
    assert cc.user_name_label.text() == "Storm Commander"
    assert "commander" in cc.user_role_label.text()
    assert len(cc._app_items) >= 5


def test_command_center_search_filtering(qapp, test_profile):
    """Verify real-time search filters the list of visible apps."""
    cc = CommandCenter(current_user=test_profile)

    # Search for 'notes'
    cc.search_input.setText("Notes")
    visible = [item for item in cc._app_items if not item.isHidden()]
    assert len(visible) == 1
    assert visible[0].app_id == "notes"

    # Search for something non-existent
    cc.search_input.setText("nonexistent_utility_123")
    visible = [item for item in cc._app_items if not item.isHidden()]
    assert len(visible) == 0

    # Clear search restores all
    cc.search_input.setText("")
    visible = [item for item in cc._app_items if not item.isHidden()]
    assert len(visible) == len(cc._app_items)


def test_command_center_launch_app_signal(qapp, test_profile):
    """Verify clicking an app card emits app_launched and dismissed."""
    cc = CommandCenter(current_user=test_profile)
    launched = []
    dismissed = []
    cc.app_launched.connect(lambda aid: launched.append(aid))
    cc.dismissed.connect(lambda: dismissed.append(True))

    notes_item = next((item for item in cc._app_items if item.app_id == "notes"), None)
    assert notes_item is not None
    notes_item.clicked.emit("notes")

    assert launched == ["notes"]
    assert len(dismissed) == 1


def test_command_center_enter_key_launch(qapp, test_profile):
    """Verify pressing return on search launches first matching app."""
    cc = CommandCenter(current_user=test_profile)
    launched = []
    cc.app_launched.connect(lambda aid: launched.append(aid))

    cc.search_input.setText("Terminal")
    cc._launch_first_match()

    assert launched == ["terminal"]


def test_command_center_system_actions(qapp, test_profile):
    """Verify system action triggers (Lock, Reboot, Exit)."""
    cc = CommandCenter(current_user=test_profile)
    locked, rebooted, exited = [], [], []
    cc.lock_requested.connect(lambda: locked.append(True))
    cc.reboot_requested.connect(lambda: rebooted.append(True))
    cc.exit_requested.connect(lambda: exited.append(True))

    cc._handle_lock()
    assert len(locked) == 1

    cc._handle_reboot()
    assert len(rebooted) == 1

    cc._handle_exit()
    assert len(exited) == 1


# ==========================================
# 3. Safe Exit Dialog Tests
# ==========================================

def test_safe_exit_dialog_signals(qapp):
    """Verify SafeExitDialog emits proper signals for each power choice."""
    dialog = SafeExitDialog()
    exited, rebooted, locked = [], [], []
    dialog.exit_confirmed.connect(lambda: exited.append(True))
    dialog.reboot_confirmed.connect(lambda: rebooted.append(True))
    dialog.lock_confirmed.connect(lambda: locked.append(True))

    dialog._handle_exit()
    assert len(exited) == 1

    dialog._handle_reboot()
    assert len(rebooted) == 1

    dialog._handle_lock()
    assert len(locked) == 1


# ==========================================
# 4. Desktop View Integration Tests
# ==========================================

def test_desktop_view_components(qapp, test_profile):
    """Verify DesktopView integrates wallpaper, dock, and command center."""
    view = DesktopView(current_user=test_profile)
    view.resize(1280, 800)

    assert view.dock is not None
    assert view.command_center is not None
    assert not view.command_center.isVisible()


def test_desktop_card_widget(qapp):
    """Verify DesktopCardWidget can be instantiated with custom title and icons."""
    card = DesktopCardWidget("Notes App", "Quick thoughts & memos", icon_text="📝")
    assert card is not None


def test_desktop_view_toggle_command_center(qapp, test_profile):
    """Verify toggling command center visibility."""
    view = DesktopView(current_user=test_profile)
    view.resize(1280, 800)

    assert view.command_center.isHidden()

    view.toggle_command_center()
    assert not view.command_center.isHidden()

    view.toggle_command_center()
    assert view.command_center.isHidden()


def test_desktop_view_app_launch_signal(qapp, test_profile):
    """Verify app launch requests propagate from desktop view and dock."""
    view = DesktopView(current_user=test_profile)
    view.resize(1280, 800)

    launched = []
    view.app_launch_requested.connect(lambda aid: launched.append(aid))

    view._handle_app_launch("notes")
    assert launched == ["notes"]
