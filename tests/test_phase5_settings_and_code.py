"""Comprehensive test suite for Display Settings, Wallpapers, Mouse Cursors, and Notepad++ Code Studio."""

import json
import os
import sys
from pathlib import Path
import pytest

# Ensure offscreen Qt rendering for automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont, QPixmap, QTextCursor
from PySide6.QtWidgets import QApplication, QMessageBox

from stormos.apps.notes import NotesApp, StormCodeEditor, StormSyntaxHighlighter
from stormos.apps.settings import SettingsApp, WallpaperCard
from stormos.core.constants import COLOR_LIGHTNING, COLOR_NIGHT_SKY
from stormos.desktop.desktop_view import DesktopView
from stormos.desktop.storm_dock import StormDock
from stormos.desktop.window import StormWindow
from stormos.services.user_manager import UserManager, UserProfile
from stormos.ui.main_window import StormMainWindow
from stormos.ui.wallpaper_manager import WallpaperManager, WALLPAPER_PRESETS


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_profile():
    return UserProfile(
        username="storm_coder",
        display_name="Storm Coder",
        role="admin",
        avatar="stormos_logo.png",
        wallpaper="wallpaper.png",
    )


# ==========================================
# 1. DISPLAY & MULTI-MONITOR TESTS
# ==========================================

def test_display_settings_tab_and_monitors(qapp, test_profile, monkeypatch):
    """Verify monitor detection and display mode configurations."""
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    settings = SettingsApp(current_user=test_profile)
    assert settings.monitor_combo.count() >= 1

    # Verify resolution combo has standard presets
    assert settings.res_combo.count() >= 5
    assert "1920" in settings.res_combo.itemText(0)

    # Test display settings emission
    emitted_config = {}

    def on_disp_changed(cfg):
        nonlocal emitted_config
        emitted_config = cfg

    settings.display_mode_changed.connect(on_disp_changed)
    settings.radio_windowed.setChecked(True)
    settings.res_combo.setCurrentIndex(3)  # 1280x800
    settings._apply_display_settings()

    assert emitted_config.get("mode") == "windowed"
    assert emitted_config.get("width") == 1280
    assert emitted_config.get("height") == 800


def test_main_window_apply_display_settings(qapp):
    """Verify StormMainWindow applies display resolution and windowed modes."""
    main_win = StormMainWindow(fullscreen=False, skip_boot=True)
    main_win.apply_display_settings({
        "mode": "windowed",
        "screen_index": 0,
        "width": 1024,
        "height": 768,
    })
    assert main_win.width() == 1024
    assert main_win.height() == 768
    main_win.close()


# ==========================================
# 2. WALLPAPER & PERSONALIZATION TESTS
# ==========================================

def test_wallpaper_manager_procedural_rendering(qapp):
    """Verify procedural wallpapers render valid high-resolution pixmaps."""
    presets = WallpaperManager.get_presets()
    assert len(presets) >= 4

    # Test procedural renders
    pix_night = WallpaperManager.render_procedural_wallpaper("deep_night", 800, 600)
    assert not pix_night.isNull()
    assert pix_night.width() == 800
    assert pix_night.height() == 600

    pix_lightning = WallpaperManager.render_procedural_wallpaper("lightning_surge", 800, 600)
    assert not pix_lightning.isNull()

    pix_nebula = WallpaperManager.render_procedural_wallpaper("midnight_nebula", 800, 600)
    assert not pix_nebula.isNull()

    # Test thumbnail generation
    thumb = WallpaperManager.create_thumbnail("deep_night", 160, 100)
    assert not thumb.isNull()
    assert thumb.width() == 160
    assert thumb.height() == 100


def test_desktop_view_dynamic_wallpaper_update(qapp, test_profile, tmp_path, monkeypatch):
    """Verify DesktopView updates wallpaper in real-time and persists to user profile."""
    monkeypatch.setattr("stormos.services.user_manager.USERS_DIR", tmp_path / "users")
    um = UserManager(users_dir=tmp_path / "users")
    user = um.create_user("coder", "password", display_name="Coder")

    desktop = DesktopView(current_user=user)
    assert desktop._bg_pixmap is not None

    # Change to procedural wallpaper
    desktop.set_wallpaper("lightning_surge")
    assert user.wallpaper == "lightning_surge"

    # Verify persisted to disk
    loaded_user = um.get_user("coder")
    assert loaded_user.wallpaper == "lightning_surge"


# ==========================================
# 3. MOUSE CURSORS TESTS
# ==========================================

def test_interactive_mouse_cursors(qapp, test_profile):
    """Verify pointing hand and text cursors across critical UI components."""
    # Dock buttons
    dock = StormDock(current_user=test_profile)
    assert dock.start_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert dock.user_badge_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert dock.power_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor

    # Window buttons
    win = StormWindow(app_id="test", title="Test App")
    assert win.title_bar.min_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert win.title_bar.max_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert win.title_bar.close_btn.cursor().shape() == Qt.CursorShape.PointingHandCursor

    # Editor text cursor
    editor = StormCodeEditor()
    assert editor.cursor().shape() == Qt.CursorShape.IBeamCursor


# ==========================================
# 4. NOTEPAD++ CODE STUDIO TESTS
# ==========================================

def test_code_editor_line_numbers_and_gutter(qapp):
    """Verify line numbers gutter and auto-indent in StormCodeEditor."""
    editor = StormCodeEditor()
    editor.setPlainText("def add(a, b):\n    return a + b\n")

    assert editor.blockCount() == 3
    assert editor.line_number_area_width() > 10

    # Test telemetry emission
    telemetry_data = None

    def on_telemetry(line, col, total_lines, total_chars):
        nonlocal telemetry_data
        telemetry_data = (line, col, total_lines, total_chars)

    editor.cursor_telemetry_changed.connect(on_telemetry)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    editor.setTextCursor(cursor)

    assert telemetry_data is not None
    assert telemetry_data[0] == 1  # line 1
    assert telemetry_data[2] == 3  # 3 lines


def test_syntax_highlighter_multilanguage(qapp):
    """Verify syntax highlighter rules across Python, JSON, Markdown, and HTML."""
    editor = StormCodeEditor()
    highlighter = StormSyntaxHighlighter(editor.document(), language="python")

    # Verify python rules loaded
    assert len(highlighter._rules) > 10

    # Switch to JSON
    highlighter.set_language("json")
    assert len(highlighter._rules) > 5

    # Switch to Markdown
    highlighter.set_language("markdown")
    assert len(highlighter._rules) >= 5

    # Switch to HTML
    highlighter.set_language("html")
    assert len(highlighter._rules) >= 4


def test_notepad_multi_tab_operations(qapp, test_profile, tmp_path, monkeypatch):
    """Verify Notepad++ multi-tab document creation, file saving, find & replace."""
    monkeypatch.setattr("stormos.apps.notes.USERS_DIR", tmp_path / "users")
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Discard)
    notes_app = NotesApp(current_user=test_profile)

    # Initial tab
    assert len(notes_app.tabs_data) == 1
    assert notes_app.tab_widget.count() == 1

    # Add new tab
    notes_app.new_file()
    assert len(notes_app.tabs_data) == 2
    assert notes_app.tab_widget.count() == 2

    # Write code into current tab
    current_doc = notes_app.get_current_document()
    assert current_doc is not None
    current_doc.editor.setPlainText('print("StormOS Cyber Engine")\n')

    # Find & Replace
    notes_app.find_input.setText("Cyber")
    notes_app.replace_input.setText("Quantum")
    notes_app._replace_all_matches()
    assert "Quantum" in current_doc.editor.toPlainText()

    # Close tab
    notes_app.close_tab(1)
    assert len(notes_app.tabs_data) == 1
