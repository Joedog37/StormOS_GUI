"""User profile and account management service for StormOS.

Handles account CRUD, authentication, role-based permissions,
data export/backup, and avatar management.
"""

import json
import logging
import shutil
import tarfile
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from stormos.core.paths import USERS_DIR
from stormos.core.security import (
    hash_password,
    validate_username,
    verify_password,
)

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """Represents a StormOS user profile."""

    username: str
    display_name: str
    password_hash: str = ""
    salt: str = ""
    role: str = "user"  # "admin" or "user"
    avatar: str = "stormos_logo.png"
    wallpaper: str = "wallpaper.png"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    theme: str = "dark_storm"


class UserManager:
    """Manages creation, loading, and authentication of user accounts."""

    def __init__(self, users_dir: Optional[Path] = None):
        self.users_dir = users_dir or USERS_DIR
        self.users_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_folder(self, username: str) -> Path:
        """Return the directory path for a specific user."""
        return self.users_dir / username

    def _get_profile_path(self, username: str) -> Path:
        """Return the profile.json file path for a specific user."""
        return self._get_user_folder(username) / "profile.json"

    def user_exists(self, username: str) -> bool:
        """Check if a user account already exists."""
        if not validate_username(username):
            return False
        return self._get_profile_path(username).exists()

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str | None = None,
        role: str = "user",
        avatar: str = "stormos_logo.png",
        wallpaper: str = "wallpaper.png",
    ) -> Optional[UserProfile]:
        """Create a new user profile with salted hash password storage."""
        if not validate_username(username):
            logger.error("Invalid username format: %s", username)
            return None

        if self.user_exists(username):
            logger.warning("User %s already exists", username)
            return None

        if not password:
            logger.error("Password cannot be empty")
            return None

        pw_hash, salt = hash_password(password)
        profile = UserProfile(
            username=username,
            display_name=display_name or username.capitalize(),
            password_hash=pw_hash,
            salt=salt,
            role=role,
            avatar=avatar,
            wallpaper=wallpaper,
        )

        user_dir = self._get_user_folder(username)
        user_dir.mkdir(parents=True, exist_ok=True)
        # Create user data subfolders
        (user_dir / "documents").mkdir(exist_ok=True)
        (user_dir / "pictures").mkdir(exist_ok=True)
        (user_dir / "settings").mkdir(exist_ok=True)

        profile_path = self._get_profile_path(username)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(asdict(profile), f, indent=2)

        return profile

    def get_user(self, username: str) -> Optional[UserProfile]:
        """Load a user profile by username."""
        if not self.user_exists(username):
            return None

        profile_path = self._get_profile_path(username)
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserProfile(**data)
        except Exception as e:
            logger.error("Failed to load user profile for %s: %s", username, e)
            return None

    def list_users(self) -> List[UserProfile]:
        """List all registered users on the system."""
        users: List[UserProfile] = []
        if not self.users_dir.exists():
            return users

        for item in self.users_dir.iterdir():
            if item.is_dir():
                profile = self.get_user(item.name)
                if profile:
                    users.append(profile)
        return users

    def authenticate(self, username: str, password: str) -> Optional[UserProfile]:
        """Authenticate user credentials safely."""
        profile = self.get_user(username)
        if not profile:
            return None

        if verify_password(password, profile.password_hash, profile.salt):
            return profile
        return None

    def update_user(self, profile: UserProfile) -> bool:
        """Update and persist an existing user profile."""
        if not self.user_exists(profile.username):
            logger.error("Cannot update non-existent user: %s", profile.username)
            return False

        profile_path = self._get_profile_path(profile.username)
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(asdict(profile), f, indent=2)
            return True
        except Exception as e:
            logger.error("Failed to update user profile for %s: %s", profile.username, e)
            return False

    # ---- Phase 7: Account Administration ----

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change a user's password after verifying the old one.

        Returns True on success, False if old password is wrong or new password is empty.
        """
        if not new_password:
            logger.error("New password cannot be empty")
            return False

        profile = self.get_user(username)
        if not profile:
            logger.error("User not found for password change: %s", username)
            return False

        if not verify_password(old_password, profile.password_hash, profile.salt):
            logger.warning("Old password verification failed for %s", username)
            return False

        pw_hash, salt = hash_password(new_password)
        profile.password_hash = pw_hash
        profile.salt = salt
        return self.update_user(profile)

    def update_display_name(self, username: str, display_name: str) -> bool:
        """Update the display name for an existing user."""
        if not display_name or not display_name.strip():
            logger.error("Display name cannot be empty")
            return False

        profile = self.get_user(username)
        if not profile:
            return False

        profile.display_name = display_name.strip()
        return self.update_user(profile)

    def update_role(self, username: str, new_role: str, requesting_user: Optional[UserProfile] = None) -> bool:
        """Update a user's role (admin/user).

        Only administrators can change roles. An admin cannot demote themselves
        if they are the last admin.
        """
        if new_role not in ("admin", "user"):
            logger.error("Invalid role: %s", new_role)
            return False

        # Permission check — only admins can change roles
        if requesting_user and requesting_user.role != "admin":
            logger.warning("Non-admin user %s attempted to change role", requesting_user.username)
            return False

        profile = self.get_user(username)
        if not profile:
            return False

        # Prevent removing the last admin
        if new_role == "user" and profile.role == "admin":
            admins = [u for u in self.list_users() if u.role == "admin"]
            if len(admins) <= 1:
                logger.warning("Cannot demote last admin: %s", username)
                return False

        profile.role = new_role
        return self.update_user(profile)

    def update_avatar(self, username: str, avatar: str) -> bool:
        """Update a user's avatar reference (filename or path)."""
        profile = self.get_user(username)
        if not profile:
            return False

        profile.avatar = avatar
        return self.update_user(profile)

    def delete_user(self, username: str, requesting_user: Optional[UserProfile] = None) -> bool:
        """Delete a user account and all associated data.

        Only admins can delete users. A user cannot delete themselves if they
        are the last admin.
        """
        profile = self.get_user(username)
        if not profile:
            return False

        # Permission check
        if requesting_user and requesting_user.role != "admin" and requesting_user.username != username:
            logger.warning("Non-admin %s attempted to delete %s", requesting_user.username, username)
            return False

        # Prevent deleting the last admin
        if profile.role == "admin":
            admins = [u for u in self.list_users() if u.role == "admin"]
            if len(admins) <= 1:
                logger.warning("Cannot delete last admin: %s", username)
                return False

        user_dir = self._get_user_folder(username)
        try:
            if user_dir.exists():
                shutil.rmtree(user_dir)
            logger.info("Deleted user account: %s", username)
            return True
        except Exception as e:
            logger.error("Failed to delete user %s: %s", username, e)
            return False

    def export_user_data(self, username: str, dest_dir: Optional[Path] = None) -> Optional[Path]:
        """Export a user's data folder as a ZIP archive for backup.

        Returns the path to the created archive, or None on failure.
        """
        profile = self.get_user(username)
        if not profile:
            return None

        user_dir = self._get_user_folder(username)
        if not user_dir.exists():
            return None

        if dest_dir is None:
            dest_dir = self.users_dir.parent / "backups"
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"{username}_export_{timestamp}.zip"
        archive_path = dest_dir / archive_name

        try:
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in user_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.users_dir.parent)
                        zf.write(file_path, arcname)
            logger.info("Exported user data for %s to %s", username, archive_path)
            return archive_path
        except Exception as e:
            logger.error("Failed to export user data for %s: %s", username, e)
            return None

    def import_user_data(self, archive_path: Path) -> bool:
        """Restore a user's data from a ZIP export archive.

        Returns True on success, False on failure.
        """
        if not archive_path.exists():
            logger.error("Archive not found: %s", archive_path)
            return False

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(self.users_dir.parent)
            logger.info("Imported user data from %s", archive_path)
            return True
        except Exception as e:
            logger.error("Failed to import user data from %s: %s", archive_path, e)
            return False

    def check_permission(self, user: UserProfile, action: str) -> bool:
        """Check if a user has permission to perform a given action.

        Actions requiring admin role:
        - delete_user, change_role, manage_accounts, system_settings
        All other actions are allowed for any authenticated user.
        """
        admin_actions = {"delete_user", "change_role", "manage_accounts", "system_settings"}
        if action in admin_actions and user.role != "admin":
            return False
        return True

    def ensure_default_account(self) -> UserProfile:
        """Ensure at least one local administrator/operator account exists for testing."""
        users = self.list_users()
        if users:
            return users[0]

        # Create standard test account
        created = self.create_user(
            username="storm",
            password="storm",
            display_name="Storm Operator",
            role="admin",
            avatar="stormos_logo.png",
            wallpaper="wallpaper.png",
        )
        if created:
            return created

        # Fallback if creation had issues
        return self.get_user("storm")  # type: ignore
