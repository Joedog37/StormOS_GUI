"""Floating Storm Dock for StormOS.

Provides a low floating horizontal glass dock featuring the Storm crest (Start button),
quick app launchers, active user status, live system clock, and power actions.
"""

from datetime import datetime
from typing import List, Dict
from PySide6.QtCore import QDateTime, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    APP_NAME,
    COLOR_ERROR,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
)
from stormos.services.user_manager import UserProfile


class DockAppButton(QPushButton):
    """Button for quick app launch in Storm Dock."""

    def __init__(self, app_id: str, name: str, icon_text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.app_id = app_id
        self.name = name
        self.icon_text = icon_text
        self.setText(f"{icon_text} {name}")
        self.setToolTip(f"Launch {name}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MAIN};
                font-size: 11px;
                font-weight: 600;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(56, 201, 255, 0.12);
                border: 1px solid {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            QPushButton:pressed {{
                background-color: rgba(56, 201, 255, 0.25);
            }}
            """
        )


class StormDock(QFrame):
    """Low floating horizontal Storm Dock."""

    command_center_toggled = Signal()
    app_launch_requested = Signal(str)  # Emits app_id
    lock_requested = Signal()
    reboot_requested = Signal()
    exit_requested = Signal()

    PINNED_APPS = [
        {"id": "notes", "name": "Notes", "icon": "📝"},
        {"id": "calculator", "name": "Calc", "icon": "⚡"},
        {"id": "files", "name": "Files", "icon": "📁"},
        {"id": "terminal", "name": "Terminal", "icon": "💻"},
        {"id": "store", "name": "Store", "icon": "🛍️"},
        {"id": "settings", "name": "Settings", "icon": "⚙️"},
    ]

    def __init__(self, current_user: UserProfile | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_user = current_user
        self.setFixedHeight(54)
        self._setup_ui()

        # Clock timer (updates every second)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    def set_user(self, user: UserProfile):
        """Update active user in dock status."""
        self.current_user = user
        display_name = user.display_name or user.username
        role_str = user.role.upper() if user.role else "USER"
        self.user_badge_btn.setText(f"👤 {display_name} ({role_str})")

    def _setup_ui(self):
        self.setStyleSheet(
            f"""
            StormDock {{
                background-color: rgba(16, 26, 49, 0.92);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 16px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 8, 4)
        layout.setSpacing(6)

        # 1. Left: Storm Crest / Start Button
        self.start_btn = QPushButton("⚡ STORM")
        self.start_btn.setToolTip("Open Command Center (Start Menu)")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.5px;
                border: none;
                border-radius: 8px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_LIGHTNING_GLOW};
            }}
            QPushButton:pressed {{
                background-color: rgba(56, 201, 255, 0.8);
            }}
            """
        )
        self.start_btn.clicked.connect(self.command_center_toggled.emit)
        layout.addWidget(self.start_btn)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet(f"color: {COLOR_PANEL_EDGE}; max-height: 20px;")
        layout.addWidget(div1)

        # 2. Center: Quick Pinned App Launchers
        self.app_buttons_layout = QHBoxLayout()
        self.app_buttons_layout.setSpacing(4)

        for app_info in self.PINNED_APPS:
            btn = DockAppButton(
                app_id=app_info["id"],
                name=app_info["name"],
                icon_text=app_info["icon"],
            )
            btn.clicked.connect(lambda checked=False, aid=app_info["id"]: self.app_launch_requested.emit(aid))
            self.app_buttons_layout.addWidget(btn)

        layout.addLayout(self.app_buttons_layout)
        layout.addStretch()

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet(f"color: {COLOR_PANEL_EDGE}; max-height: 24px;")
        layout.addWidget(div2)

        # 3. Right: User Badge, Clock, and Safe Power/Exit Button
        user_name = self.current_user.display_name if self.current_user else "Operator"
        role_str = self.current_user.role.upper() if (self.current_user and self.current_user.role) else "USER"
        self.user_badge_btn = QPushButton(f"👤 {user_name} ({role_str})")
        self.user_badge_btn.setToolTip(f"Active User Session: {user_name} ({role_str})")
        self.user_badge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.user_badge_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_MAIN};
                font-size: 11px;
                font-weight: 600;
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                background-color: {COLOR_STORM_CLOUD};
            }}
            """
        )
        self.user_badge_btn.clicked.connect(self.command_center_toggled.emit)
        layout.addWidget(self.user_badge_btn)

        # Live Clock & Date
        self.clock_widget = QWidget()
        clock_layout = QVBoxLayout(self.clock_widget)
        clock_layout.setContentsMargins(4, 0, 4, 0)
        clock_layout.setSpacing(0)
        clock_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent;"
        )
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.time_label)

        self.date_label = QLabel("Jan 01, 2026")
        self.date_label.setStyleSheet(
            f"font-size: 9px; color: {COLOR_TEXT_SECONDARY}; background: transparent;"
        )
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.date_label)

        layout.addWidget(self.clock_widget)

        # Safe Exit / Power Button
        self.power_btn = QPushButton("⏻")
        self.power_btn.setToolTip("System Power / Exit Options")
        self.power_btn.setFixedSize(30, 30)
        self.power_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.power_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(255, 92, 119, 0.15);
                color: {COLOR_ERROR};
                font-size: 13px;
                font-weight: bold;
                border: 1px solid {COLOR_ERROR};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        self.power_btn.clicked.connect(self.exit_requested.emit)
        layout.addWidget(self.power_btn)

    def _update_clock(self):
        """Update live time and date formatting."""
        now = datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%b %d, %Y"))
