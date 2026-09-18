"""StormOS Applications Package.

Provides built-in applications and central registration.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from stormos.apps.registry import AppMetadata, AppRegistry
from stormos.services.user_manager import UserProfile


def register_builtin_apps():
    """Register all default built-in applications into the global AppRegistry."""
    registry = AppRegistry.get_instance()

    # 1. Notes
    def _create_notes(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.notes import NotesApp
        return NotesApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="notes",
            name="Notes",
            description="Lightweight storm scratchpad, memos, and persistence.",
            icon="📝",
            category="Productivity",
            is_builtin=True,
            factory=_create_notes,
            default_width=840,
            default_height=580,
        )
    )

    # 2. Storm Power Calculator
    def _create_calculator(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.calculator import CalculatorApp
        return CalculatorApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="calculator",
            name="Power Calculator",
            description="Natural math expression engine, live calculation tape, multi-unit converters, and programmer base tools.",
            icon="⚡",
            category="Utilities",
            is_builtin=True,
            factory=_create_calculator,
            default_width=860,
            default_height=590,
        )
    )

    # 3. Files Explorer
    def _create_files(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.files import FilesApp
        return FilesApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="files",
            name="Files & Storage",
            description="Explore, preview, organize, and manage user profile storage.",
            icon="📁",
            category="System",
            is_builtin=True,
            factory=_create_files,
            default_width=880,
            default_height=580,
        )
    )

    # 4. Storm Terminal
    def _create_terminal(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.terminal import TerminalApp
        return TerminalApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="terminal",
            name="Storm Terminal",
            description="Interactive cyber console, math evaluator, and shell utilities.",
            icon="💻",
            category="System",
            is_builtin=True,
            factory=_create_terminal,
            default_width=820,
            default_height=520,
        )
    )

    # 5. App Store & Package Manager
    def _create_store(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.app_manager import AppManagerApp
        return AppManagerApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="store",
            name="App Store",
            description="Discover, inspect, install, and manage StormOS app packages.",
            icon="🛍️",
            category="System",
            is_builtin=True,
            factory=_create_store,
            default_width=880,
            default_height=600,
        )
    )

    # 6. System Activity Monitor
    def _create_monitor(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.activity_monitor import ActivityMonitorApp
        return ActivityMonitorApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="monitor",
            name="Activity Monitor",
            description="Real-time system telemetry, memory stats, CPU indicators, and tasks.",
            icon="📊",
            category="System",
            is_builtin=True,
            factory=_create_monitor,
            default_width=800,
            default_height=520,
        )
    )

    # 7. Settings
    def _create_settings(user: Optional[UserProfile], parent: Optional[QWidget]) -> QWidget:
        from stormos.apps.settings import SettingsApp
        return SettingsApp(current_user=user, parent=parent)

    registry.register(
        AppMetadata(
            id="settings",
            name="Settings",
            description="Personalization, display preferences, themes, and security settings.",
            icon="⚙️",
            category="Preferences",
            is_builtin=True,
            factory=_create_settings,
            default_width=760,
            default_height=540,
        )
    )


# Automatically register on import
register_builtin_apps()
