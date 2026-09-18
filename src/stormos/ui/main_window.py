"""Main application window for StormOS.

Coordinates the screen transitions: Boot -> Login -> Desktop,
with keyboard shortcuts and window state management.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import APP_NAME, APP_VERSION, ORG_NAME
from stormos.core.paths import get_asset_path
from stormos.desktop.desktop_view import DesktopView
from stormos.screens.boot_screen import BootScreen
from stormos.screens.login_screen import LoginScreen
from stormos.services.user_manager import UserManager, UserProfile
from stormos.ui.theme import get_base_stylesheet


class StormMainWindow(QMainWindow):
    """The root fullscreen desktop window managing OS screens and transitions."""

    def __init__(self, fullscreen: bool = True, skip_boot: bool = False):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {ORG_NAME}")
        self.setStyleSheet(get_base_stylesheet())

        # Set window icon if available
        logo_path = get_asset_path("stormos_logo.png")
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        self.user_manager = UserManager()
        self.user_manager.ensure_default_account()

        self._setup_screens(skip_boot=skip_boot)
        self._setup_shortcuts()
        self.setMinimumSize(800, 500)

        if fullscreen:
            self.showFullScreen()
        else:
            self.resize(1280, 800)
            self.show()

    def _setup_screens(self, skip_boot: bool = False):
        """Initialize the stacked screens and connect signals."""
        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        # 0: Boot Screen
        self.boot_screen = BootScreen(auto_start=not skip_boot)
        self.boot_screen.boot_finished.connect(self._on_boot_finished)
        self.stack.addWidget(self.boot_screen)

        # 1: Login Screen
        self.login_screen = LoginScreen(user_manager=self.user_manager)
        self.login_screen.login_successful.connect(self._on_login_successful)
        self.login_screen.exit_requested.connect(self.close)
        self.stack.addWidget(self.login_screen)

        # 2: Desktop View
        self.desktop_view = DesktopView()
        self.desktop_view.logout_requested.connect(self._on_logout)
        self.desktop_view.reboot_requested.connect(self._on_reboot)
        self.desktop_view.exit_requested.connect(self.close)
        self.desktop_view.display_mode_changed.connect(self.apply_display_settings)
        self.stack.addWidget(self.desktop_view)

        if skip_boot:
            self.stack.setCurrentWidget(self.login_screen)
        else:
            self.stack.setCurrentWidget(self.boot_screen)

    def _setup_shortcuts(self):
        """Keyboard shortcuts for window control."""
        # Toggle fullscreen on F11
        shortcut_f11 = QShortcut(QKeySequence("F11"), self)
        shortcut_f11.activated.connect(self.toggle_fullscreen)

        # Escape shortcut for emergency exit
        shortcut_esc = QShortcut(QKeySequence("Esc"), self)
        shortcut_esc.activated.connect(self._on_esc_pressed)

    def _on_boot_finished(self):
        """Transition from Boot Screen to Login Screen."""
        self.login_screen.refresh_users()
        self.stack.setCurrentWidget(self.login_screen)

    def _on_login_successful(self, profile: UserProfile):
        """Transition from Login Screen to Desktop Workspace."""
        self.desktop_view.set_user(profile)
        self.stack.setCurrentWidget(self.desktop_view)

    def _on_logout(self):
        """Return to Login Screen from Desktop."""
        self.login_screen.refresh_users()
        self.stack.setCurrentWidget(self.login_screen)

    def _on_reboot(self):
        """Trigger a clean reboot sequence back to Boot Screen."""
        self.stack.setCurrentWidget(self.boot_screen)
        self.boot_screen.start_boot()

    def _on_esc_pressed(self):
        """Handle Escape key."""
        # If in fullscreen, exit fullscreen; otherwise close
        if self.isFullScreen():
            self.toggle_fullscreen()
        else:
            self.close()

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        if self.isFullScreen():
            self.showNormal()
            self.resize(1280, 800)
        else:
            self.showFullScreen()

    def apply_display_settings(self, settings: dict):
        """Apply display configuration (monitor target, resolution preset, fullscreen/windowed)."""
        mode = settings.get("mode", "fullscreen").lower()
        screen_idx = settings.get("screen_index", 0)
        width = settings.get("width", 1280)
        height = settings.get("height", 800)

        screens = QApplication.screens()
        target_screen = screens[screen_idx] if 0 <= screen_idx < len(screens) else QApplication.primaryScreen()
        screen_geo = target_screen.geometry() if target_screen else self.screen().geometry()

        if mode == "fullscreen":
            self.showNormal()
            if self.windowHandle() and target_screen:
                self.windowHandle().setScreen(target_screen)
            self.setGeometry(screen_geo)
            self.showFullScreen()
        elif mode == "maximized":
            self.showNormal()
            if self.windowHandle() and target_screen:
                self.windowHandle().setScreen(target_screen)
            avail = target_screen.availableGeometry() if target_screen else screen_geo
            self.setGeometry(avail)
            self.showMaximized()
        else:  # windowed
            self.showNormal()
            self.resize(width, height)
            x = screen_geo.x() + max(0, (screen_geo.width() - width) // 2)
            y = screen_geo.y() + max(0, (screen_geo.height() - height) // 2)
            self.move(x, y)
