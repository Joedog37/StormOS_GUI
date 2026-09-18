"""StormOS Application Registry and Base Metadata."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Type
from PySide6.QtWidgets import QWidget
from stormos.services.user_manager import UserProfile


@dataclass
class AppMetadata:
    """Metadata describing a StormOS application."""
    id: str
    name: str
    description: str
    icon: str = "⚡"
    category: str = "Utilities"
    is_builtin: bool = True
    factory: Optional[Callable[[Optional[UserProfile], Optional[QWidget]], QWidget]] = None
    default_width: int = 800
    default_height: int = 560
    min_width: int = 400
    min_height: int = 300


class AppRegistry:
    """Central registry of available applications in StormOS."""

    _instance: Optional["AppRegistry"] = None

    def __init__(self):
        self._apps: Dict[str, AppMetadata] = {}

    @classmethod
    def get_instance(cls) -> "AppRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, metadata: AppMetadata):
        """Register an application in the system."""
        self._apps[metadata.id] = metadata

    def unregister(self, app_id: str) -> bool:
        """Unregister an application by id."""
        if app_id in self._apps:
            del self._apps[app_id]
            return True
        return False

    def get_app(self, app_id: str) -> Optional[AppMetadata]:
        """Get metadata for an application by id."""
        return self._apps.get(app_id)

    def list_apps(self, category: Optional[str] = None) -> List[AppMetadata]:
        """List registered applications, optionally filtered by category."""
        apps = list(self._apps.values())
        if category:
            apps = [a for a in apps if a.category.lower() == category.lower()]
        return apps

    def create_app_widget(
        self, app_id: str, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None
    ) -> Optional[QWidget]:
        """Instantiate the root widget for an application."""
        app = self.get_app(app_id)
        if app and app.factory:
            return app.factory(current_user, parent)
        return None
