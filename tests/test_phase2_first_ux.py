"""Tests for Phase 2 - First User Experience (Boot, Login, Auth, Desktop Transition)."""

import os
import sys
from pathlib import Path
import pytest

# Ensure offscreen Qt rendering for automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from stormos.core.security import (
    hash_password,
    verify_password,
    validate_username,
    sanitize_filename,
)
from stormos.services.user_manager import UserManager, UserProfile
from stormos.screens.boot_screen import BootScreen
from stormos.screens.login_screen import LoginScreen
from stormos.screens.signup_dialog import SignUpDialog
from stormos.desktop.desktop_view import DesktopView
from stormos.ui.main_window import StormMainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ==========================================
# 1. Security & Cryptography Tests
# ==========================================

def test_password_hashing_and_verification():
    """Verify PBKDF2 salted hashing and timing-safe verification."""
    password = "SuperSecretPassword123!"
    pw_hash, salt = hash_password(password)

    assert pw_hash is not None
    assert salt is not None
    assert len(pw_hash) == 64  # SHA256 hex digest length
    assert len(salt) == 64     # 32 bytes hex length

    # Verification success
    assert verify_password(password, pw_hash, salt) is True

    # Verification failure
    assert verify_password("WrongPassword", pw_hash, salt) is False
    assert verify_password("", pw_hash, salt) is False
    assert verify_password(password, "invalid_hash", salt) is False


def test_unique_salts():
    """Verify that hashing the same password twice yields different salts and hashes."""
    pwd = "common_password"
    hash1, salt1 = hash_password(pwd)
    hash2, salt2 = hash_password(pwd)

    assert salt1 != salt2
    assert hash1 != hash2


def test_username_validation():
    """Verify username policy and path traversal protection."""
    assert validate_username("storm") is True
    assert validate_username("operator_01") is True
    assert validate_username("admin-user") is True

    # Invalid usernames
    assert validate_username("ab") is False            # Too short
    assert validate_username("a" * 33) is False        # Too long
    assert validate_username("user/../admin") is False # Path traversal
    assert validate_username("user\\test") is False    # Backslash
    assert validate_username("user;rm") is False       # Special characters
    assert validate_username("") is False


def test_sanitize_filename():
    """Verify filename sanitization against dangerous characters."""
    assert sanitize_filename("safe_file.png") == "safe_file.png"
    assert sanitize_filename("../evil/file.png") == "file.png"
    assert sanitize_filename("bad:name?.jpg") == "bad_name_.jpg"
    assert sanitize_filename("con.txt") == "con.txt"


# ==========================================
# 2. User Manager Tests
# ==========================================

def test_user_manager_crud(tmp_path):
    """Verify user creation, persistence, and authentication."""
    manager = UserManager(users_dir=tmp_path)

    # Initial state should be empty
    assert len(manager.list_users()) == 0

    # Create user
    created = manager.create_user(
        username="alice",
        password="secretpassword",
        display_name="Alice Explorer",
        role="admin",
    )
    assert created is not None
    assert created.username == "alice"
    assert created.display_name == "Alice Explorer"
    assert created.role == "admin"
    assert (tmp_path / "alice" / "profile.json").exists()

    # Disallow duplicate username
    dup = manager.create_user(username="alice", password="other")
    assert dup is None

    # Load user
    loaded = manager.get_user("alice")
    assert loaded is not None
    assert loaded.display_name == "Alice Explorer"

    # Authenticate
    auth_success = manager.authenticate("alice", "secretpassword")
    assert auth_success is not None
    assert auth_success.username == "alice"

    auth_fail = manager.authenticate("alice", "wrongpass")
    assert auth_fail is None


def test_ensure_default_account(tmp_path):
    """Verify automated provisioning of local test account if no users exist."""
    manager = UserManager(users_dir=tmp_path)
    default_user = manager.ensure_default_account()

    assert default_user is not None
    assert default_user.username == "storm"
    assert manager.authenticate("storm", "storm") is not None


# ==========================================
# 3. Boot Screen Tests
# ==========================================

def test_boot_screen_lifecycle(qapp):
    """Verify BootScreen initialization, progress, and skip action."""
    boot = BootScreen(auto_start=False)
    assert boot.progress_bar.value() == 0

    signal_received = []
    boot.boot_finished.connect(lambda: signal_received.append(True))

    # Skip boot triggers completion signal
    boot.skip_boot()
    assert boot.progress_bar.value() == 100
    assert len(signal_received) == 1


# ==========================================
# 4. Login Screen Tests
# ==========================================

def test_login_screen_auth(qapp, tmp_path):
    """Verify LoginScreen user loading, invalid input handling, and successful login."""
    manager = UserManager(users_dir=tmp_path)
    manager.ensure_default_account()

    login_screen = LoginScreen(user_manager=manager)
    assert login_screen.user_combo.count() >= 1

    logged_user = []
    login_screen.login_successful.connect(lambda u: logged_user.append(u))

    # Test invalid password
    login_screen.password_input.setText("wrong")
    login_screen._handle_login()
    assert len(logged_user) == 0
    assert "Invalid password" in login_screen.status_label.text()

    # Test quick login as storm
    login_screen._quick_login_storm()
    assert len(logged_user) == 1
    assert logged_user[0].username == "storm"


def test_signup_dialog_validation(qapp, tmp_path):
    """Verify SignUpDialog input validation and error handling."""
    manager = UserManager(users_dir=tmp_path)
    manager.ensure_default_account()

    dialog = SignUpDialog(user_manager=manager)

    # 1. Empty username
    dialog.username_input.setText("")
    dialog.password_input.setText("validpassword")
    dialog.confirm_password_input.setText("validpassword")
    dialog._handle_signup()
    assert "Username cannot be empty" in dialog.status_label.text()

    # 2. Invalid username format
    dialog.username_input.setText("bad/user")
    dialog._handle_signup()
    assert "3-32 characters" in dialog.status_label.text()

    # 3. Existing username
    dialog.username_input.setText("storm")
    dialog._handle_signup()
    assert "already exists" in dialog.status_label.text()

    # 4. Empty password
    dialog.username_input.setText("newpilot")
    dialog.password_input.setText("")
    dialog.confirm_password_input.setText("")
    dialog._handle_signup()
    assert "Password cannot be empty" in dialog.status_label.text()

    # 5. Password mismatch
    dialog.password_input.setText("password123")
    dialog.confirm_password_input.setText("password456")
    dialog._handle_signup()
    assert "Passwords do not match" in dialog.status_label.text()


def test_signup_dialog_success(qapp, tmp_path):
    """Verify successful account creation via SignUpDialog."""
    manager = UserManager(users_dir=tmp_path)
    dialog = SignUpDialog(user_manager=manager)

    created_events = []
    dialog.user_created.connect(lambda u: created_events.append(u))

    dialog.username_input.setText("sky_pilot")
    dialog.display_name_input.setText("Sky Pilot")
    dialog.password_input.setText("securepass123")
    dialog.confirm_password_input.setText("securepass123")

    dialog._handle_signup()

    assert len(created_events) == 1
    assert created_events[0].username == "sky_pilot"
    assert created_events[0].display_name == "Sky Pilot"
    assert manager.user_exists("sky_pilot")
    assert manager.authenticate("sky_pilot", "securepass123") is not None


# ==========================================
# 5. Desktop View Tests
# ==========================================

def test_desktop_view_rendering(qapp):
    """Verify DesktopView displays active user session and triggers signals."""
    user = UserProfile(
        username="storm",
        display_name="Storm Commander",
        password_hash="hash",
        salt="salt",
        role="admin",
    )
    desktop = DesktopView(current_user=user)
    assert "Storm Commander" in desktop.greeting_label.text()
    assert "ADMIN" in desktop.greeting_label.text()

    logout_fired = []
    desktop.logout_requested.connect(lambda: logout_fired.append(True))
    desktop.logout_requested.emit()
    assert len(logout_fired) == 1


# ==========================================
# 6. Window Screen Navigation Integration
# ==========================================

def test_main_window_screen_flow(qapp):
    """Verify screen transitions: Boot -> Login -> Desktop -> Logout -> Reboot."""
    window = StormMainWindow(fullscreen=False, skip_boot=False)

    # Initial state is Boot Screen
    assert window.stack.currentWidget() == window.boot_screen

    # Complete Boot -> Login Screen
    window.boot_screen.skip_boot()
    assert window.stack.currentWidget() == window.login_screen

    # Successful Login -> Desktop View
    user = window.user_manager.ensure_default_account()
    window.login_screen.login_successful.emit(user)
    assert window.stack.currentWidget() == window.desktop_view
    assert "Storm Operator" in window.desktop_view.greeting_label.text()

    # Logout -> Login Screen
    window.desktop_view.logout_requested.emit()
    assert window.stack.currentWidget() == window.login_screen

    # Reboot -> Boot Screen
    window.desktop_view.reboot_requested.emit()
    assert window.stack.currentWidget() == window.boot_screen
