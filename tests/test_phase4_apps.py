"""Phase 4 Test Suite: Applications, Window System, and Package Management.

Covers:
1. AppRegistry and metadata management
2. StormWindow frame (dragging, minimize, maximize, close, focus)
3. Notes application (CRUD, auto-save, search, user storage)
4. Storm Power Calculator (natural math parser, calculation tape, converters, programmer base)
5. Files Explorer (sandbox enforcement, folder/file creation, navigation, previews)
6. Storm Terminal (cyber console, commands, math evaluation, history)
7. AppInstallerService (security baseline, manifest validation, path traversal blocking, install/uninstall)
8. DesktopView window manager integration (launching apps, multi-window stacking, focus management)
"""

import json
import zipfile
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from stormos.apps import register_builtin_apps
from stormos.apps.activity_monitor import ActivityMonitorApp
from stormos.apps.app_manager import AppManagerApp
from stormos.apps.calculator import CalculatorApp, evaluate_expression
from stormos.apps.files import FilesApp
from stormos.apps.notes import NotesApp
from stormos.apps.registry import AppMetadata, AppRegistry
from stormos.apps.settings import SettingsApp
from stormos.apps.terminal import TerminalApp
from stormos.desktop.desktop_view import DesktopView
from stormos.desktop.window import StormWindow, WindowTitleBar
from stormos.services.app_installer import AppInstallerService
from stormos.services.user_manager import UserProfile


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_profile(tmp_path):
    user_dir = tmp_path / "users" / "testuser"
    user_dir.mkdir(parents=True, exist_ok=True)
    return UserProfile(
        username="testuser",
        display_name="Test Operator",
        role="admin",
        password_hash="test_hash",
        salt="test_salt",
    )


# ==========================================
# 1. APP REGISTRY TESTS
# ==========================================

def test_app_registry_builtin_apps(qapp):
    """Verify standard built-in applications are registered."""
    register_builtin_apps()
    registry = AppRegistry.get_instance()

    app_ids = [a.id for a in registry.list_apps()]
    assert "notes" in app_ids
    assert "calculator" in app_ids
    assert "files" in app_ids
    assert "terminal" in app_ids
    assert "store" in app_ids
    assert "monitor" in app_ids
    assert "settings" in app_ids


def test_app_registry_custom_registration(qapp):
    """Verify custom app registration and unregistration."""
    registry = AppRegistry.get_instance()
    meta = AppMetadata(
        id="test_custom_app",
        name="Custom Test App",
        description="A test application",
        icon="🧪",
        category="Testing",
    )
    registry.register(meta)
    assert registry.get_app("test_custom_app") is not None

    filtered = registry.list_apps(category="Testing")
    assert any(a.id == "test_custom_app" for a in filtered)

    unregistered = registry.unregister("test_custom_app")
    assert unregistered is True
    assert registry.get_app("test_custom_app") is None


def test_app_registry_widget_factory(qapp, test_profile):
    """Verify registry can instantiate app widgets."""
    registry = AppRegistry.get_instance()
    calc_widget = registry.create_app_widget("calculator", test_profile)
    assert isinstance(calc_widget, CalculatorApp)

    notes_widget = registry.create_app_widget("notes", test_profile)
    assert isinstance(notes_widget, NotesApp)


# ==========================================
# 2. STORM WINDOW SYSTEM TESTS
# ==========================================

def test_storm_window_initialization(qapp):
    """Verify StormWindow creation and properties."""
    win = StormWindow(app_id="calc", title="Power Calculator", icon="⚡")
    assert win.app_id == "calc"
    assert win.title_bar._title == "Power Calculator"
    assert win._is_active is True
    assert not win._is_maximized
    assert not win._is_minimized


def test_storm_window_minimize_restore(qapp):
    """Verify minimizing and restoring window."""
    win = StormWindow(app_id="notes", title="Notes", icon="📝")
    minimized_events = []
    restored_events = []

    win.minimized.connect(lambda w: minimized_events.append(w))
    win.restored.connect(lambda w: restored_events.append(w))

    win.minimize_window()
    assert win._is_minimized is True
    assert win.isHidden()
    assert len(minimized_events) == 1

    win.restore_minimized()
    assert win._is_minimized is False
    assert win.isVisible()
    assert len(restored_events) == 1


def test_storm_window_maximize_restore(qapp):
    """Verify maximizing and restoring window bounds."""
    parent = DesktopView()
    parent.resize(1280, 800)

    win = StormWindow(app_id="files", title="Files", icon="📁", parent=parent)
    orig_geom = win.geometry()

    win.maximize_window()
    assert win._is_maximized is True
    assert win.geometry().width() == 1280

    win.restore_maximized()
    assert win._is_maximized is False
    assert win.geometry() == orig_geom


# ==========================================
# 3. NOTES APPLICATION TESTS
# ==========================================

def test_notes_app_lifecycle(qapp, test_profile, tmp_path, monkeypatch):
    """Verify Notes creation, saving, editing, and deletion."""
    monkeypatch.setattr("stormos.apps.notes.USERS_DIR", tmp_path / "users")
    notes = NotesApp(current_user=test_profile)

    # Initial sample note should exist
    assert notes.notes_list.count() >= 1

    # Create new note
    notes.create_new_note()
    notes.title_input.setText("Project Plan Alpha")
    notes.text_editor.setPlainText("Design high-voltage glass widgets.")
    notes.save_current_note()

    # Verify saved to disk
    note_file = notes.notes_dir / f"{notes.current_note_id}.json"
    assert note_file.exists()

    with open(note_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == "Project Plan Alpha"
    assert "high-voltage" in data["body"]

    # Delete note
    notes.delete_current_note()
    assert not note_file.exists()


# ==========================================
# 4. POWER CALCULATOR TESTS
# ==========================================

def test_calculator_math_evaluation(qapp):
    """Verify natural formula evaluation engine."""
    # Arithmetic
    valid, res = evaluate_expression("145 * 1.15")
    assert valid is True
    assert float(res) == pytest.approx(166.75)

    # Parentheses & Precedence
    valid, res = evaluate_expression("(10 + 20) * 3 / 2")
    assert valid is True
    assert float(res) == 45.0

    # Math functions
    valid, res = evaluate_expression("sqrt(144) + 8")
    assert valid is True
    assert float(res) == 20.0

    # Exponentiation
    valid, res = evaluate_expression("2^8")
    assert valid is True
    assert float(res) == 256.0

    # Percentage
    valid, res = evaluate_expression("200 * 15%")
    assert valid is True
    assert float(res) == 30.0

    # Invalid expressions
    valid, _ = evaluate_expression("invalid_command()")
    assert valid is False


def test_calculator_tape_history(qapp, test_profile):
    """Verify interactive calculation tape."""
    calc = CalculatorApp(current_user=test_profile)
    calc.expr_input.setText("50 + 25")
    calc._calculate_final()

    assert calc.tape_list.count() == 1
    assert "50 + 25" in calc.tape_list.item(0).text()
    assert "= 75" in calc.tape_list.item(0).text()


# ==========================================
# 5. FILES APPLICATION TESTS
# ==========================================

def test_files_app_navigation_and_sandbox(qapp, test_profile, tmp_path, monkeypatch):
    """Verify FilesApp explores user sandbox safely."""
    monkeypatch.setattr("stormos.apps.files.USERS_DIR", tmp_path / "users")
    files_app = FilesApp(current_user=test_profile)

    # Verify standard folders created
    assert (files_app.root_dir / "documents").exists()
    assert (files_app.root_dir / "downloads").exists()

    # Create file inside root
    doc_file = files_app.root_dir / "documents" / "test.txt"
    doc_file.write_text("Secret storm coordinates", encoding="utf-8")

    # Navigate into documents
    files_app.navigate_to(files_app.root_dir / "documents")
    assert files_app.current_dir == files_app.root_dir / "documents"
    assert files_app.table.rowCount() >= 1

    # Security: attempting to navigate outside sandbox stays in root
    files_app.navigate_to(Path("C:/Windows"))
    assert str(files_app.current_dir).startswith(str(files_app.root_dir))


# ==========================================
# 6. STORM TERMINAL TESTS
# ==========================================

def test_terminal_commands(qapp, test_profile, tmp_path, monkeypatch):
    """Verify terminal console commands."""
    monkeypatch.setattr("stormos.apps.terminal.USERS_DIR", tmp_path / "users")
    term = TerminalApp(current_user=test_profile)

    # calc command
    term.command_input.setText("calc 12 * 12")
    term._handle_command()
    assert "= 144" in term.output_view.toPlainText()

    # ver command
    term.command_input.setText("ver")
    term._handle_command()
    assert "StormOS" in term.output_view.toPlainText()

    # touch and ls
    term.command_input.setText("touch logfile.txt")
    term._handle_command()
    assert (term.current_dir / "logfile.txt").exists()


# ==========================================
# 7. APP INSTALLER & SECURITY TESTS
# ==========================================

def test_app_installer_manifest_validation(tmp_path):
    """Verify package manifest schema validation."""
    installer = AppInstallerService(apps_dir=tmp_path / "apps")

    # Valid manifest
    valid_m = {
        "id": "my_radar",
        "name": "My Radar",
        "version": "1.0.0",
        "description": "Radar app",
    }
    valid, msg = installer.validate_manifest(valid_m)
    assert valid is True

    # Invalid ID with uppercase / spaces
    invalid_m = {"id": "Invalid ID!", "name": "Test", "version": "1.0"}
    valid, msg = installer.validate_manifest(invalid_m)
    assert valid is False


def test_app_installer_security_path_traversal(tmp_path):
    """Verify app installer rejects packages containing path traversal attacks."""
    installer = AppInstallerService(apps_dir=tmp_path / "apps")
    malicious_zip = tmp_path / "malicious.stormapp"

    # Create zip with directory traversal
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"id": "evil", "name": "Evil", "version": "1.0"}))
        zf.writestr("../../system32/cmd.exe", "fake executable")

    valid, msg, _ = installer.validate_package_archive(malicious_zip)
    assert valid is False
    assert "Security violation" in msg or "not allowed" in msg


def test_app_installer_install_and_uninstall(tmp_path, test_profile):
    """Verify installation and uninstallation of safe app package."""
    installer = AppInstallerService(apps_dir=tmp_path / "apps")
    manifest = {
        "id": "mission_tool",
        "name": "Mission Planner",
        "version": "1.0.0",
        "description": "Tactical planner",
        "icon": "🎯",
        "category": "Productivity",
    }
    files = {"README.md": "Mission Planner details"}

    success, msg = installer.install_from_manifest_and_files(manifest, files, user=test_profile)
    assert success is True

    # App should be registered in AppRegistry
    app_meta = AppRegistry.get_instance().get_app("mission_tool")
    assert app_meta is not None
    assert app_meta.name == "Mission Planner"

    # Uninstall
    uninstalled, u_msg = installer.uninstall_app("mission_tool", user=test_profile)
    assert uninstalled is True
    assert AppRegistry.get_instance().get_app("mission_tool") is None


# ==========================================
# 8. DESKTOP VIEW MULTI-WINDOW INTEGRATION
# ==========================================

def test_desktop_view_multi_window_management(qapp, test_profile):
    """Verify DesktopView manages multiple concurrent application windows."""
    view = DesktopView(current_user=test_profile)
    view.resize(1280, 800)
    view.show()

    # Launch Calculator
    win_calc = view.launch_app("calculator")
    assert win_calc is not None
    assert "calculator" in view.open_windows
    assert not win_calc.isHidden()
    assert win_calc._is_active is True

    # Launch Notes
    win_notes = view.launch_app("notes")
    assert win_notes is not None
    assert "notes" in view.open_windows
    assert not win_notes.isHidden()
    assert win_notes._is_active is True
    assert win_calc._is_active is False  # Focused window deactivates others

    # Re-launching calculator brings it to focus
    view.launch_app("calculator")
    assert win_calc._is_active is True
    assert win_notes._is_active is False

    # Close window cleans up from open_windows
    win_calc.close_window()
    assert "calculator" not in view.open_windows
