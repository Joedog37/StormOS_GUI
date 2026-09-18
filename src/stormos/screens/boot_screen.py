"""Boot Screen for StormOS.

Displays a dark storm-sky atmosphere, centered Thunderhead logo,
a smooth electric cyan progress line, and cycles kernel boot diagnostics.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    APP_NAME,
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
    ORG_NAME,
)
from stormos.core.paths import get_asset_path


class BootScreen(QWidget):
    """Animated boot screen widget."""

    boot_finished = Signal()

    def __init__(self, parent: QWidget | None = None, auto_start: bool = True, step_interval_ms: int = 30):
        super().__init__(parent)
        self.step_interval_ms = step_interval_ms
        self.progress_val = 0

        self.status_messages = [
            "Initializing StormOS kernel...",
            "Loading display compositor...",
            "Mounting secure user subsystem...",
            "Validating cryptographic vault...",
            "Starting desktop environment...",
        ]
        self._current_msg_idx = 0

        self._setup_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

        if auto_start:
            self.start_boot()

    def _setup_ui(self):
        """Construct the boot UI layout."""
        self.setStyleSheet(f"background-color: {COLOR_NIGHT_SKY};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(40, 40, 40, 40)

        # Central Container
        container = QFrame()
        container.setStyleSheet(
            f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
            """
        )
        c_layout = QVBoxLayout(container)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setSpacing(20)

        # StormOS / Thunderhead Logo
        self.logo_label = QLabel()
        logo_path = get_asset_path("stormos_logo.png")
        if not logo_path.exists():
            logo_path = get_asset_path("storm_splash.png")

        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                self.logo_label.setPixmap(
                    pix.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self.logo_label)

        # Title
        title = QLabel(APP_NAME.upper())
        title.setStyleSheet(
            f"""
            font-size: 36px;
            font-weight: 800;
            color: {COLOR_TEXT_MAIN};
            letter-spacing: 6px;
            """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(title)

        org_label = QLabel(ORG_NAME.upper())
        org_label.setStyleSheet(
            f"""
            font-size: 13px;
            font-weight: 600;
            color: {COLOR_LIGHTNING};
            letter-spacing: 3px;
            """
        )
        org_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(org_label)

        # Electric Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setFixedWidth(320)
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {COLOR_RAISED_PANEL};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 {COLOR_LIGHTNING_GLOW},
                    stop: 1 {COLOR_LIGHTNING}
                );
                border-radius: 2px;
            }}
            """
        )
        c_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status text below progress bar
        self.status_label = QLabel(self.status_messages[0])
        self.status_label.setStyleSheet(
            f"""
            font-size: 13px;
            color: {COLOR_TEXT_SECONDARY};
            font-family: 'Segoe UI', Inter, sans-serif;
            """
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self.status_label)

        # Skip hint
        hint_label = QLabel("Click or press Space to skip")
        hint_label.setStyleSheet(
            f"""
            font-size: 11px;
            color: #4A628A;
            margin-top: 10px;
            """
        )
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(hint_label)

        layout.addWidget(container)

    def start_boot(self):
        """Begin the boot animation."""
        self.progress_val = 0
        self.progress_bar.setValue(0)
        self.timer.start(self.step_interval_ms)

    def _on_tick(self):
        """Update progress bar and status message."""
        self.progress_val += 2
        self.progress_bar.setValue(min(self.progress_val, 100))

        # Change message based on progress bracket
        bracket_size = 100 // len(self.status_messages)
        idx = min(self.progress_val // bracket_size, len(self.status_messages) - 1)
        if idx != self._current_msg_idx:
            self._current_msg_idx = idx
            self.status_label.setText(self.status_messages[idx])

        if self.progress_val >= 100:
            self.timer.stop()
            self.boot_finished.emit()

    def skip_boot(self):
        """Instantly skip boot sequence."""
        self.timer.stop()
        self.progress_bar.setValue(100)
        self.boot_finished.emit()

    def mousePressEvent(self, event):
        """Allow skipping on mouse click."""
        self.skip_boot()

    def keyPressEvent(self, event):
        """Allow skipping on Space or Enter."""
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.skip_boot()
        else:
            super().keyPressEvent(event)
