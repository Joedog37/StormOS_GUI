"""User profile and account management service for StormOS."""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

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
