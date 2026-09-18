"""Safe Exit and Power Confirmation Dialog for StormOS.

Presents a frosted storm-glass confirmation dialog for cleanly exiting to Windows,
rebooting the desktop environment, or locking the user session.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
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
    COLOR_WARNING,
)


class SafeExitDialog(QDialog):
    """Frosted storm-glass dialog for confirming system power actions."""

    exit_confirmed = Signal()
    reboot_confirmed = Signal()
    lock_confirmed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Exit {APP_NAME}")
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 14px;
            }}
            """
        )
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Title
        header_layout = QHBoxLayout()
        icon_label = QLabel("⏻")
        icon_label.setStyleSheet(f"font-size: 24px; color: {COLOR_ERROR};")
        header_layout.addWidget(icon_label)

        title = QLabel(f"Exit or Power Down")
        title.setStyleSheet(
            f"""
            font-size: 18px;
            font-weight: 800;
            color: {COLOR_TEXT_MAIN};
            """
        )
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Message
        message = QLabel(
            f"Choose an action to proceed safely. Exiting will close {APP_NAME} and return to your Windows desktop."
        )
        message.setWordWrap(True)
        message.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT_SECONDARY}; line-height: 1.4;")
        layout.addWidget(message)

        # Action Buttons Vertical List
        btn_container = QVBoxLayout()
        btn_container.setSpacing(10)

        # 1. Exit to Windows
        self.exit_btn = QPushButton("🛑 Exit to Windows")
        self.exit_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(255, 92, 119, 0.2);
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_ERROR};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 700;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        self.exit_btn.clicked.connect(self._handle_exit)
        btn_container.addWidget(self.exit_btn)

        # 2. Reboot StormOS
        self.reboot_btn = QPushButton("🔄 Reboot StormOS (Restart Session)")
        self.reboot_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.reboot_btn.clicked.connect(self._handle_reboot)
        btn_container.addWidget(self.reboot_btn)

        # 3. Lock / Switch User
        self.lock_btn = QPushButton("🔒 Lock / Switch Account")
        self.lock_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        self.lock_btn.clicked.connect(self._handle_lock)
        btn_container.addWidget(self.lock_btn)

        layout.addLayout(btn_container)

        # Cancel button at bottom
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
            }}
            """
        )
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

    def _handle_exit(self):
        self.exit_confirmed.emit()
        self.accept()

    def _handle_reboot(self):
        self.reboot_confirmed.emit()
        self.accept()

    def _handle_lock(self):
        self.lock_confirmed.emit()
        self.accept()
