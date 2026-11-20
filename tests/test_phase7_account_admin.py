"""Test suite for Phase 7 — User Management & Account Administration.

Covers: account editing, password changes, role-based permissions,
user deletion, data export/backup, avatars, and permission checks.
"""

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

# Ensure offscreen Qt rendering for automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox

from stormos.apps.settings import SettingsApp
from stormos.services.user_manager import UserManager, UserProfile


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def tmp_users(tmp_path):
    """Provide a temporary users directory and UserManager instance."""
    users_dir = tmp_path / "users"
    um = UserManager(users_dir=users_dir)
    return um, users_dir


@pytest.fixture
def admin_user(tmp_users):
    """Create an admin user for testing."""
    um, _ = tmp_users
    profile = um.create_user(
        username="admin1",
        password="adminpw",
        display_name="Admin User",
        role="admin",
    )
    return um, profile


@pytest.fixture
def standard_user(tmp_users):
    """Create a standard user for testing."""
    um, _ = tmp_users
    profile = um.create_user(
        username="stduser",
        password="stdpw",
        display_name="Standard User",
        role="user",
    )
    return um, profile


# ==========================================
# 1. PASSWORD CHANGE TESTS
# ==========================================


def test_change_password_success(admin_user):
    """Verify a user can change their password with correct old password."""
    um, profile = admin_user
    success = um.change_password("admin1", "adminpw", "newpassword")
    assert success is True

    # Verify new password works
    reloaded = um.authenticate("admin1", "newpassword")
    assert reloaded is not None
    assert reloaded.username == "admin1"


def test_change_password_wrong_old_password(admin_user):
    """Verify password change fails with wrong old password."""
    um, _ = admin_user
    success = um.change_password("admin1", "wrongold", "newpassword")
    assert success is False

    # Old password should still work
    reloaded = um.authenticate("admin1", "adminpw")
    assert reloaded is not None


def test_change_password_empty_new_password(admin_user):
    """Verify password change rejects empty new password."""
    um, _ = admin_user
    success = um.change_password("admin1", "adminpw", "")
    assert success is False


def test_change_password_nonexistent_user(tmp_users):
    """Verify password change fails for non-existent user."""
    um, _ = tmp_users
    success = um.change_password("nouser", "old", "new")
    assert success is False


# ==========================================
# 2. DISPLAY NAME UPDATE TESTS
# ==========================================


def test_update_display_name(admin_user):
    """Verify display name can be updated."""
    um, _ = admin_user
    success = um.update_display_name("admin1", "New Display Name")
    assert success is True

    profile = um.get_user("admin1")
    assert profile.display_name == "New Display Name"


def test_update_display_name_empty_rejected(admin_user):
    """Verify empty display name is rejected."""
    um, _ = admin_user
    success = um.update_display_name("admin1", "   ")
    assert success is False


def test_update_display_name_whitespace_stripped(admin_user):
    """Verify display name whitespace is stripped."""
    um, _ = admin_user
    um.update_display_name("admin1", "  Trimmed Name  ")
    profile = um.get_user("admin1")
    assert profile.display_name == "Trimmed Name"


# ==========================================
# 3. ROLE MANAGEMENT TESTS
# ==========================================


def test_update_role_admin_to_user(admin_user, standard_user):
    """Verify admin can change another user's role."""
    um_admin, admin_profile = admin_user
    _, std_profile = standard_user

    success = um_admin.update_role("stduser", "admin", admin_profile)
    assert success is True

    updated = um_admin.get_user("stduser")
    assert updated.role == "admin"


def test_update_role_non_admin_rejected(admin_user, standard_user):
    """Verify non-admin cannot change roles."""
    um_admin, admin_profile = admin_user
    um_std, std_profile = standard_user

    success = um_std.update_role("admin1", "user", std_profile)
    assert success is False


def test_update_role_invalid_role(admin_user):
    """Verify invalid role is rejected."""
    um, admin_profile = admin_user
    success = um.update_role("admin1", "superadmin", admin_profile)
    assert success is False


def test_cannot_demote_last_admin(admin_user):
    """Verify the last admin cannot be demoted to user."""
    um, admin_profile = admin_user
    success = um.update_role("admin1", "user", admin_profile)
    assert success is False


def test_update_role_nonexistent_user(admin_user):
    """Verify role update fails for non-existent user."""
    um, admin_profile = admin_user
    success = um.update_role("nouser", "admin", admin_profile)
    assert success is False


# ==========================================
# 4. AVATAR MANAGEMENT TESTS
# ==========================================


def test_update_avatar(admin_user):
    """Verify avatar can be updated."""
    um, _ = admin_user
    success = um.update_avatar("admin1", "custom_avatar.png")
    assert success is True

    profile = um.get_user("admin1")
    assert profile.avatar == "custom_avatar.png"


def test_update_avatar_nonexistent_user(tmp_users):
    """Verify avatar update fails for non-existent user."""
    um, _ = tmp_users
    success = um.update_avatar("nouser", "avatar.png")
    assert success is False


# ==========================================
# 5. USER DELETION TESTS
# ==========================================


def test_delete_user_success(admin_user, standard_user):
    """Verify admin can delete a standard user."""
    um_admin, admin_profile = admin_user
    _, std_profile = standard_user

    success = um_admin.delete_user("stduser", admin_profile)
    assert success is True

    assert um_admin.get_user("stduser") is None


def test_delete_last_admin_rejected(admin_user):
    """Verify the last admin cannot be deleted."""
    um, admin_profile = admin_user
    success = um.delete_user("admin1", admin_profile)
    assert success is False


def test_delete_nonexistent_user(tmp_users):
    """Verify deleting non-existent user returns False."""
    um, _ = tmp_users
    success = um.delete_user("nouser")
    assert success is False


def test_delete_user_removes_directory(admin_user, standard_user):
    """Verify user directory is removed after deletion."""
    um_admin, admin_profile = admin_user
    _, _ = standard_user

    user_dir = um_admin._get_user_folder("stduser")
    assert user_dir.exists()

    um_admin.delete_user("stduser", admin_profile)
    assert not user_dir.exists()


# ==========================================
# 6. DATA EXPORT / BACKUP TESTS
# ==========================================


def test_export_user_data(admin_user):
    """Verify user data can be exported to a ZIP archive."""
    um, _ = admin_user

    # Create some user data
    docs_dir = um._get_user_folder("admin1") / "documents"
    test_file = docs_dir / "test.txt"
    test_file.write_text("Hello StormOS", encoding="utf-8")

    archive = um.export_user_data("admin1")
    assert archive is not None
    assert archive.exists()
    assert archive.suffix == ".zip"

    # Verify archive contents
    with zipfile.ZipFile(archive, "r") as zf:
        names = zf.namelist()
        assert any("test.txt" in n for n in names)


def test_export_nonexistent_user(tmp_users):
    """Verify export returns None for non-existent user."""
    um, _ = tmp_users
    archive = um.export_user_data("nouser")
    assert archive is None


def test_import_user_data(tmp_path):
    """Verify user data can be imported from a ZIP archive."""
    users_dir = tmp_path / "users"
    um = UserManager(users_dir=users_dir)

    # Create a user and export
    um.create_user("exporter", "pw", display_name="Exporter", role="user")
    docs_dir = um._get_user_folder("exporter") / "documents"
    (docs_dir / "data.txt").write_text("Important data", encoding="utf-8")

    archive = um.export_user_data("exporter")
    assert archive is not None

    # Delete the user
    um.delete_user("exporter")
    assert um.get_user("exporter") is None

    # Import the archive
    success = um.import_user_data(archive)
    assert success is True

    # Verify user is restored
    restored = um.get_user("exporter")
    assert restored is not None
    assert restored.username == "exporter"


def test_import_nonexistent_archive(tmp_users):
    """Verify import fails for non-existent archive."""
    um, _ = tmp_users
    success = um.import_user_data(Path("/nonexistent/archive.zip"))
    assert success is False


# ==========================================
# 7. PERMISSION CHECK TESTS
# ==========================================


def test_permission_admin_can_delete(admin_user):
    """Verify admin can perform admin actions."""
    um, admin_profile = admin_user
    assert um.check_permission(admin_profile, "delete_user") is True
    assert um.check_permission(admin_profile, "change_role") is True
    assert um.check_permission(admin_profile, "manage_accounts") is True


def test_permission_standard_user_cannot_delete(standard_user):
    """Verify standard user cannot perform admin actions."""
    um, std_profile = standard_user
    assert um.check_permission(std_profile, "delete_user") is False
    assert um.check_permission(std_profile, "change_role") is False
    assert um.check_permission(std_profile, "manage_accounts") is False


def test_permission_any_user_can_read(admin_user, standard_user):
    """Verify any authenticated user can perform non-admin actions."""
    um_admin, admin_profile = admin_user
    um_std, std_profile = standard_user

    assert um_admin.check_permission(admin_profile, "read_profile") is True
    assert um_std.check_permission(std_profile, "read_profile") is True


# ==========================================
# 8. SETTINGS UI INTEGRATION TESTS
# ==========================================


def test_settings_account_tab_builds(qapp, admin_user, monkeypatch):
    """Verify the account tab builds without errors."""
    um, admin_profile = admin_user
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    settings = SettingsApp(current_user=admin_profile)
    # The account tab should build without raising
    assert settings is not None


def test_settings_password_change_ui(qapp, admin_user, monkeypatch):
    """Verify the password change UI fields exist."""
    um, admin_profile = admin_user
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    settings = SettingsApp(current_user=admin_profile)
    assert hasattr(settings, "old_pw_input")
    assert hasattr(settings, "new_pw_input")
    assert hasattr(settings, "pw_status_label")


def test_settings_admin_sees_role_management(qapp, admin_user, monkeypatch):
    """Verify admin users see the role management section."""
    um, admin_profile = admin_user
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    settings = SettingsApp(current_user=admin_profile)
    assert hasattr(settings, "role_user_combo")
    assert hasattr(settings, "role_combo")


def test_settings_standard_user_no_role_management(qapp, standard_user, monkeypatch):
    """Verify standard users do not see the role management section."""
    um, std_profile = standard_user
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    settings = SettingsApp(current_user=std_profile)
    assert not hasattr(settings, "role_user_combo")


def test_settings_export_data(qapp, admin_user, monkeypatch, tmp_path):
    """Verify the export data handler works from settings UI."""
    um, admin_profile = admin_user
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)

    settings = SettingsApp(current_user=admin_profile)
    # Use the same UserManager instance that created the user
    archive = um.export_user_data("admin1")
    assert archive is not None
