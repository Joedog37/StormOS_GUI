"""Desktop environment view for StormOS.

Renders high-resolution storm wallpaper, interactive desktop widgets,
the floating Storm Dock (Taskbar), and the Command Center (Start Menu).
"""

from datetime import datetime
from PySide6.QtCore import QDateTime, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import stormos.apps  # Ensure built-in apps are registered
from stormos.apps.registry import AppRegistry
from stormos.core.constants import (
    APP_NAME,
    APP_VERSION,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    ORG_NAME,
)
from stormos.core.paths import get_asset_path
from stormos.desktop.command_center import CommandCenter
from stormos.desktop.safe_exit_dialog import SafeExitDialog
from stormos.desktop.storm_dock import StormDock
from stormos.desktop.window import StormWindow
from stormos.services.user_manager import UserManager, UserProfile
from stormos.ui.wallpaper_manager import WallpaperManager


class DesktopCardWidget(QFrame):
    """Interactive storm-glass card shortcut on the desktop surface."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str,
        icon_text: str = "⚡",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 100)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(16, 26, 49, 0.75);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 12px;
                padding: 10px;
            }}
            QFrame:hover {{
                background-color: rgba(23, 35, 61, 0.92);
                border: 1px solid {COLOR_LIGHTNING};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet(
            f"""
            font-size: 24px;
            color: {COLOR_LIGHTNING};
            background-color: {COLOR_STORM_CLOUD};
            border-radius: 10px;
            padding: 4px;
            """
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent; border: none;"
        )
        text_layout.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;"
        )
        text_layout.addWidget(sub_label)

        layout.addLayout(text_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class DesktopView(QWidget):
    """The root desktop workspace rendered once the user is authenticated."""

    logout_requested = Signal()
    reboot_requested = Signal()
    exit_requested = Signal()
    app_launch_requested = Signal(str)  # Emits app_id
    display_mode_changed = Signal(dict)  # Emits display configuration dictionary

    def __init__(self, current_user: UserProfile | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_user = current_user
        self._bg_pixmap: QPixmap | None = None
        self.open_windows: dict[str, StormWindow] = {}
        self._load_wallpaper()

        # Build UI layout & components
        self._setup_ui()

    def _load_wallpaper(self):
        """Load the default or user-configured wallpaper."""
        wp_name = self.current_user.wallpaper if self.current_user else "wallpaper.png"
        self._bg_pixmap = WallpaperManager.get_wallpaper_pixmap(wp_name, width=1920, height=1080)

    def set_wallpaper(self, wp_name_or_path: str, save_user_profile: bool = True):
        """Update active desktop wallpaper dynamically and persist to user profile."""
        if not wp_name_or_path:
            return
        self._bg_pixmap = WallpaperManager.get_wallpaper_pixmap(wp_name_or_path, width=1920, height=1080)
        if self.current_user:
            self.current_user.wallpaper = wp_name_or_path
            if save_user_profile:
                UserManager().update_user(self.current_user)
        self.update()

    def set_user(self, user: UserProfile):
        """Update current active user session across desktop widgets."""
        self.current_user = user
        self._load_wallpaper()
        self.dock.set_user(user)
        self.command_center.set_user(user)
        self.update()

    def _setup_ui(self):
        """Construct desktop layout, Storm Dock, and Command Center."""
        # Top-level layout for desktop surface
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 10)
        self.main_layout.setSpacing(10)

        # Clean desktop surface (pushes dock to bottom)
        self.main_layout.addStretch()

        # Floating Storm Dock (Taskbar at bottom)
        dock_container = QHBoxLayout()
        dock_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dock = StormDock(current_user=self.current_user, parent=self)
        self.dock.command_center_toggled.connect(self.toggle_command_center)
        self.dock.app_launch_requested.connect(self._handle_app_launch)
        self.dock.lock_requested.connect(self._confirm_lock)
        self.dock.reboot_requested.connect(self._confirm_reboot)
        self.dock.exit_requested.connect(self._open_safe_exit_dialog)

        dock_container.addWidget(self.dock)
        self.main_layout.addLayout(dock_container)

        # Compatibility aliases for status widgets
        self.greeting_label = self.dock.user_badge_btn
        self.clock_label = self.dock.time_label

        # Command Center (Start Menu overlay)
        self.command_center = CommandCenter(current_user=self.current_user, parent=self)
        self.command_center.app_launched.connect(self._handle_app_launch)
        self.command_center.lock_requested.connect(self._confirm_lock)
        self.command_center.reboot_requested.connect(self._confirm_reboot)
        self.command_center.exit_requested.connect(self._open_safe_exit_dialog)
        self.command_center.dismissed.connect(self.hide_command_center)
        self.command_center.hide()

    def toggle_command_center(self):
        """Toggle Command Center visibility."""
        if not self.command_center.isHidden():
            self.hide_command_center()
        else:
            self.show_command_center()

    def show_command_center(self):
        """Position and show Command Center above the dock."""
        self._position_command_center()
        self.command_center.show()
        self.command_center.raise_()
        self.command_center.setFocus()

    def hide_command_center(self):
        """Hide Command Center overlay."""
        self.command_center.hide()

    def _position_command_center(self):
        """Position Command Center centered horizontally above the bottom dock."""
        w = self.command_center.width()
        h = self.command_center.height()
        x = (self.width() - w) // 2
        # Position slightly above the dock with padding
        y = max(20, self.height() - self.dock.height() - h - 30)
        self.command_center.move(x, y)

    def _handle_app_launch(self, app_id: str):
        """Emit application launch request and open the application window."""
        self.hide_command_center()
        self.launch_app(app_id)

    def launch_app(self, app_id: str) -> Optional[StormWindow]:
        """Launch or focus an application window by app_id."""
        self.hide_command_center()
        app_id = app_id.lower()

        # If already running, restore/focus existing window
        if app_id in self.open_windows:
            window = self.open_windows[app_id]
            if window._is_minimized:
                window.restore_minimized()
            self._on_window_focused(window)
            self.app_launch_requested.emit(app_id)
            return window

        # Lookup application in AppRegistry
        meta = AppRegistry.get_instance().get_app(app_id)
        if not meta or not meta.factory:
            self.app_launch_requested.emit(app_id)
            return None

        # Instantiate application root widget
        app_widget = meta.factory(self.current_user, self)

        # Create Storm-glass window container
        window = StormWindow(
            app_id=meta.id,
            title=meta.name,
            icon=meta.icon,
            parent=self,
        )
        window.set_content_widget(app_widget)

        # Calculate cascade positioning
        w = min(meta.default_width, max(420, self.width() - 80))
        h = min(meta.default_height, max(300, self.height() - self.dock.height() - 80))
        offset = (len(self.open_windows) * 32) % 180
        x = max(20, min(60 + offset, max(20, self.width() - w - 40)))
        y = max(20, min(40 + offset, max(20, self.height() - self.dock.height() - h - 40)))

        window.setGeometry(x, y, w, h)

        # Connect window lifecycle events
        window.closed.connect(self._on_window_closed)
        window.focused.connect(self._on_window_focused)

        # Connect embedded app signals if present
        if hasattr(app_widget, "app_launched"):
            app_widget.app_launched.connect(self.launch_app)
        if hasattr(app_widget, "app_launch_requested"):
            app_widget.app_launch_requested.connect(self.launch_app)
        if hasattr(app_widget, "exit_requested"):
            app_widget.exit_requested.connect(window.close_window)
        if hasattr(app_widget, "wallpaper_changed"):
            app_widget.wallpaper_changed.connect(self.set_wallpaper)
        if hasattr(app_widget, "display_mode_changed"):
            app_widget.display_mode_changed.connect(self.display_mode_changed.emit)

        self.open_windows[meta.id] = window
        self._on_window_focused(window)
        window.show()
        window.raise_()

        self.app_launch_requested.emit(app_id)
        return window

    def _on_window_closed(self, window: StormWindow):
        """Clean up closed window from active registry."""
        if window.app_id in self.open_windows:
            del self.open_windows[window.app_id]

    def _on_window_focused(self, focused_win: StormWindow):
        """Bring focused window to front and update focus styles."""
        for w in self.open_windows.values():
            if w is not focused_win:
                w.set_active(False)
        focused_win.set_active(True)
        focused_win.raise_()

    def _open_safe_exit_dialog(self):
        """Open safe exit confirmation dialog."""
        self.hide_command_center()
        dialog = SafeExitDialog(parent=self)
        dialog.exit_confirmed.connect(self.exit_requested.emit)
        dialog.reboot_confirmed.connect(self.reboot_requested.emit)
        dialog.lock_confirmed.connect(self.logout_requested.emit)
        dialog.exec()

    def _confirm_lock(self):
        self.hide_command_center()
        self.logout_requested.emit()

    def _confirm_reboot(self):
        self.hide_command_center()
        self.reboot_requested.emit()

    def resizeEvent(self, event):
        """Reposition overlays and update maximized windows on resize."""
        super().resizeEvent(event)
        if self.command_center.isVisible():
            self._position_command_center()
        for window in self.open_windows.values():
            if window._is_maximized:
                window.setGeometry(0, 0, self.width(), max(300, self.height() - self.dock.height() - 20))

    def mousePressEvent(self, event: QMouseEvent):
        """Clicking on empty desktop dismisses Command Center."""
        if self.command_center.isVisible():
            # Check if click was outside command center and dock
            cc_rect = self.command_center.geometry()
            dock_rect = self.dock.geometry()
            pos = event.position().toPoint()
            if not cc_rect.contains(pos) and not dock_rect.contains(pos):
                self.hide_command_center()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        """Paint fullscreen wallpaper backdrop."""
        painter = QPainter(self)
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor(COLOR_NIGHT_SKY))
