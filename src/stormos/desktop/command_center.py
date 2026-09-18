"""Command Center (Start Menu) for StormOS.

Provides a layered storm-glass panel with search, favorite applications,
system actions, and user session management.
"""

from typing import Callable, List, Dict, Any
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from stormos.apps.registry import AppRegistry
from stormos.core.constants import (
    APP_NAME,
    APP_VERSION,
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_MIST_BLUE,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    ORG_NAME,
)
from stormos.core.paths import get_asset_path
from stormos.services.user_manager import UserProfile


class AppItemWidget(QFrame):
    """Clickable app card inside the Command Center."""

    clicked = Signal(str)  # Emits app_id

    def __init__(
        self,
        app_id: str,
        name: str,
        description: str,
        icon_text: str = "⚡",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.app_id = app_id
        self.name = name
        self.description = description
        self.icon_text = icon_text
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(64)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(23, 35, 61, 0.7);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 10px;
                padding: 4px 8px;
            }}
            QFrame:hover {{
                background-color: rgba(30, 48, 80, 0.95);
                border: 1px solid {COLOR_LIGHTNING};
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        icon_label = QLabel(self.icon_text)
        icon_label.setStyleSheet(
            f"""
            font-size: 22px;
            color: {COLOR_LIGHTNING};
            background-color: {COLOR_STORM_CLOUD};
            border-radius: 8px;
            padding: 4px 8px;
            """
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        name_label = QLabel(self.name)
        name_label.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent; border: none;"
        )
        text_layout.addWidget(name_label)

        desc_label = QLabel(self.description)
        desc_label.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;"
        )
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.app_id)
        super().mousePressEvent(event)


class CommandCenter(QFrame):
    """Layered frosted storm-glass Command Center panel."""

    app_launched = Signal(str)      # Emits app_id
    lock_requested = Signal()
    reboot_requested = Signal()
    exit_requested = Signal()
    dismissed = Signal()

    DEFAULT_APPS = [
        {"id": "notes", "name": "Notes", "desc": "Lightweight storm scratchpad and memos", "icon": "📝"},
        {"id": "files", "name": "Files", "desc": "Explore user documents and storage", "icon": "📁"},
        {"id": "terminal", "name": "Storm Terminal", "desc": "Interactive system console and utilities", "icon": "⚡"},
        {"id": "monitor", "name": "System Activity", "desc": "Resource monitoring and hardware telemetry", "icon": "📊"},
        {"id": "settings", "name": "Settings", "desc": "User preferences, theme, and security", "icon": "⚙️"},
        {"id": "gallery", "name": "Media Gallery", "desc": "Browse wallpapers, artwork, and media", "icon": "🖼️"},
    ]

    def __init__(self, current_user: UserProfile | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_user = current_user
        self.setFixedSize(540, 580)
        self._app_items: List[AppItemWidget] = []
        self._setup_ui()

    def set_user(self, user: UserProfile):
        """Update user session details in Command Center."""
        self.current_user = user
        display_name = user.display_name or user.username
        self.user_name_label.setText(display_name)
        self.user_role_label.setText(f"@{user.username} • {user.role.upper()}")
        self.user_avatar_label.setText(user.username[:1].upper() if user.username else "U")

    def _setup_ui(self):
        self.setStyleSheet(
            f"""
            CommandCenter {{
                background-color: rgba(16, 26, 49, 0.95);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 16px;
            }}
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(14)

        # 1. Header with search bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        brand_icon = QLabel("⚡")
        brand_icon.setStyleSheet(f"font-size: 20px; color: {COLOR_LIGHTNING};")
        header_layout.addWidget(brand_icon)

        title_label = QLabel("COMMAND CENTER")
        title_label.setStyleSheet(
            f"""
            font-size: 14px;
            font-weight: 800;
            letter-spacing: 1.5px;
            color: {COLOR_LIGHTNING};
            """
        )
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {COLOR_TEXT_MAIN};
                background-color: {COLOR_STORM_CLOUD};
                border-color: {COLOR_LIGHTNING};
            }}
            """
        )
        close_btn.clicked.connect(self.dismissed.emit)
        header_layout.addWidget(close_btn)

        main_layout.addLayout(header_layout)

        # 2. Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search apps, utilities, or actions...")
        self.search_input.setStyleSheet(
            f"""
            QLineEdit {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLOR_LIGHTNING};
                background-color: rgba(23, 35, 61, 0.98);
            }}
            """
        )
        self.search_input.textChanged.connect(self._filter_apps)
        self.search_input.returnPressed.connect(self._launch_first_match)
        main_layout.addWidget(self.search_input)

        # 3. Section: Applications
        section_label = QLabel("APPLICATIONS & UTILITIES")
        section_label.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_SECONDARY}; letter-spacing: 1px;"
        )
        main_layout.addWidget(section_label)

        # Scrollable App Grid / List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.apps_layout = QVBoxLayout(scroll_content)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(8)

        self.refresh_apps()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # 4. User Profile & System Actions Footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 12px;
                padding: 6px 12px;
            }}
            """
        )
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(8, 6, 8, 6)
        footer_layout.setSpacing(10)

        # User Avatar
        initial = self.current_user.username[:1].upper() if (self.current_user and self.current_user.username) else "U"
        self.user_avatar_label = QLabel(initial)
        self.user_avatar_label.setFixedSize(32, 32)
        self.user_avatar_label.setStyleSheet(
            f"""
            background-color: {COLOR_LIGHTNING};
            color: {COLOR_NIGHT_SKY};
            font-size: 14px;
            font-weight: 800;
            border-radius: 16px;
            """
        )
        self.user_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(self.user_avatar_label)

        # User Text Details
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(1)
        user_info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        disp_name = self.current_user.display_name if self.current_user else "Storm User"
        self.user_name_label = QLabel(disp_name)
        self.user_name_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent; border: none;"
        )
        user_info_layout.addWidget(self.user_name_label)

        u_name = self.current_user.username if self.current_user else "user"
        role_str = self.current_user.role.upper() if self.current_user else "USER"
        self.user_role_label = QLabel(f"@{u_name} • {role_str}")
        self.user_role_label.setStyleSheet(
            f"font-size: 10px; color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;"
        )
        user_info_layout.addWidget(self.user_role_label)

        footer_layout.addLayout(user_info_layout)
        footer_layout.addStretch()

        # System Action Buttons
        lock_btn = QPushButton("🔒 Lock")
        lock_btn.setToolTip("Lock session / Switch user")
        self._style_footer_action_btn(lock_btn)
        lock_btn.clicked.connect(self._handle_lock)
        footer_layout.addWidget(lock_btn)

        reboot_btn = QPushButton("🔄 Reboot")
        reboot_btn.setToolTip("Restart StormOS environment")
        self._style_footer_action_btn(reboot_btn)
        reboot_btn.clicked.connect(self._handle_reboot)
        footer_layout.addWidget(reboot_btn)

        exit_btn = QPushButton("🛑 Exit")
        exit_btn.setToolTip("Safely exit StormOS back to Windows")
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(255, 92, 119, 0.15);
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_ERROR};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        exit_btn.clicked.connect(self._handle_exit)
        footer_layout.addWidget(exit_btn)

        main_layout.addWidget(footer_frame)

    def refresh_apps(self):
        """Reload registered applications from AppRegistry."""
        # Clear existing items
        for item in self._app_items:
            item.deleteLater()
        self._app_items.clear()

        # Clear layout items
        while self.apps_layout.count():
            child = self.apps_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        registered = AppRegistry.get_instance().list_apps()
        if registered:
            apps_to_display = [
                {"id": a.id, "name": a.name, "desc": a.description, "icon": a.icon}
                for a in registered
            ]
        else:
            apps_to_display = self.DEFAULT_APPS

        for app_data in apps_to_display:
            app_card = AppItemWidget(
                app_id=app_data["id"],
                name=app_data["name"],
                description=app_data["desc"],
                icon_text=app_data["icon"],
            )
            app_card.clicked.connect(self._handle_app_click)
            self._app_items.append(app_card)
            self.apps_layout.addWidget(app_card)

        self.apps_layout.addStretch()

    def _style_footer_action_btn(self, btn: QPushButton):
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )

    def _filter_apps(self, query: str):
        """Filter visible apps based on search query."""
        q = query.strip().lower()
        for item in self._app_items:
            match = (q in item.name.lower()) or (q in item.description.lower()) or (q in item.app_id.lower())
            item.setVisible(match)

    def _launch_first_match(self):
        """Launch the first visible app when Enter is pressed in search."""
        for item in self._app_items:
            if not item.isHidden():
                self._handle_app_click(item.app_id)
                break

    def _handle_app_click(self, app_id: str):
        self.app_launched.emit(app_id)
        self.dismissed.emit()

    def _handle_lock(self):
        self.lock_requested.emit()
        self.dismissed.emit()

    def _handle_reboot(self):
        self.reboot_requested.emit()
        self.dismissed.emit()

    def _handle_exit(self):
        self.exit_requested.emit()
        self.dismissed.emit()

    def showEvent(self, event):
        """Reset search and focus input upon display."""
        super().showEvent(event)
        self.search_input.clear()
        self.search_input.setFocus()
        for item in self._app_items:
            item.setVisible(True)

    def keyPressEvent(self, event: QKeyEvent):
        """Dismiss on Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self.dismissed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
