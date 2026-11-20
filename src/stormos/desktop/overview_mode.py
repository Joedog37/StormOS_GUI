"""Overview mode (Minimap) for StormOS.

Shows all open windows as scaled-down thumbnails in a bird's-eye view.
Users can click a thumbnail to focus that window or press Escape to exit.
"""

import logging
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, QRect, QSize, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QKeySequence, QShortcut, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    COLOR_LIGHTNING,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
)
from stormos.desktop.window import StormWindow

logger = logging.getLogger(__name__)


class WindowThumbnail(QFrame):
    """A thumbnail representation of an open window in overview mode."""

    clicked = Signal(str)  # Emits app_id

    def __init__(self, app_id: str, title: str, icon: str, workspace: int = 0,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.app_id = app_id
        self._title = title
        self._icon = icon
        self._workspace = workspace
        self._is_hovered = False
        self.setFixedSize(180, 130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self._update_style()

        # Header with icon and title
        header = QHBoxLayout()
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        header.addWidget(icon_label)

        title_label = QLabel(self._title)
        title_label.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent;"
        )
        title_label.setWordWrap(True)
        header.addWidget(title_label, 1)
        layout.addLayout(header)

        # Workspace indicator
        ws_label = QLabel(f"Desktop {self._workspace + 1}")
        ws_label.setStyleSheet(
            f"font-size: 9px; color: {COLOR_TEXT_SECONDARY}; background: transparent;"
        )
        layout.addWidget(ws_label)

        # Preview area (simulated window content)
        preview = QFrame()
        preview.setFixedHeight(50)
        preview.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(16, 26, 49, 0.6);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 4px;
            }}
            """
        )
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        # Title bar simulation
        title_bar = QFrame()
        title_bar.setFixedHeight(12)
        title_bar.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(23, 35, 61, 0.9);
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }}
            """
        )
        preview_layout.addWidget(title_bar)
        layout.addWidget(preview)

    def set_workspace(self, workspace: int):
        self._workspace = workspace
        self.update()

    def set_hovered(self, hovered: bool):
        self._is_hovered = hovered
        self._update_style()

    def _update_style(self):
        border_color = COLOR_LIGHTNING if self._is_hovered else COLOR_PANEL_EDGE
        bg_color = "rgba(23, 35, 61, 0.95)" if self._is_hovered else "rgba(16, 26, 49, 0.85)"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.app_id)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_hovered(False)
        super().leaveEvent(event)


class OverviewMode(QWidget):
    """Full-screen overview showing all open windows as thumbnails.

    Activated by a keyboard shortcut (e.g., Ctrl+Overview).
    Shows windows grouped by workspace.
    Click a thumbnail to focus that window.
    Escape to exit overview mode.
    """

    window_selected = Signal(str)  # Emits app_id
    workspace_selected = Signal(int)  # Emits workspace index

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._thumbnails: List[WindowThumbnail] = []
        self._workspace_labels: Dict[int, QLabel] = {}
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(f"background-color: rgba(7, 11, 22, 0.9);")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(20)

        # Title
        title = QLabel("⚡ Overview")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {COLOR_LIGHTNING}; "
            f"background: transparent; letter-spacing: 1px;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Click a window to focus it, Esc to exit")
        subtitle.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; background: transparent;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(subtitle)

        # Scrollable content area
        scroll = QFrame()
        scroll.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(16, 26, 49, 0.5);
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 12px;
            }}
            """
        )
        scroll_layout = QVBoxLayout(scroll)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(16)

        # Workspace sections
        self.workspace_sections = QVBoxLayout()
        self.workspace_sections.setSpacing(20)
        scroll_layout.addLayout(self.workspace_sections)
        scroll_layout.addStretch()

        self.main_layout.addWidget(scroll, 1)

        # Keyboard shortcuts
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self.hide)

    def populate(self, windows: Dict[str, StormWindow], workspace_count: int = 4,
                 current_workspace: int = 0) -> None:
        """Populate overview with open windows grouped by workspace."""
        # Clear existing
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails = []
        self._workspace_labels.clear()

        # Clear workspace sections
        while self.workspace_sections.count():
            item = self.workspace_sections.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Group windows by workspace
        workspaces: Dict[int, List] = {i: [] for i in range(workspace_count)}

        for app_id, win in windows.items():
            ws = current_workspace  # Default to current workspace
            workspaces.setdefault(ws, [])
            workspaces[ws].append({
                "app_id": app_id,
                "title": win._title,
                "icon": win._icon,
                "minimized": win._is_minimized,
            })

        # Build workspace sections
        for ws_idx in range(workspace_count):
            ws_windows = workspaces.get(ws_idx, [])
            if not ws_windows:
                continue

            # Workspace label
            ws_label = QLabel(f"🖥️ Desktop {ws_idx + 1}" + (" (Current)" if ws_idx == current_workspace else ""))
            ws_label.setStyleSheet(
                f"font-size: 13px; font-weight: 700; color: {COLOR_LIGHTNING if ws_idx == current_workspace else COLOR_TEXT_MAIN}; "
                f"background: transparent;"
            )
            self.workspace_sections.addWidget(ws_label)
            self._workspace_labels[ws_idx] = ws_label

            # Thumbnail grid
            grid = QHBoxLayout()
            grid.setSpacing(12)
            grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

            for win_info in ws_windows:
                if win_info["minimized"]:
                    continue
                thumb = WindowThumbnail(
                    app_id=win_info["app_id"],
                    title=win_info["title"],
                    icon=win_info["icon"],
                    workspace=ws_idx,
                )
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self._thumbnails.append(thumb)
                grid.addWidget(thumb)

            self.workspace_sections.addLayout(grid)

        if not self._thumbnails:
            label = QLabel("No open windows")
            label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.workspace_sections.addWidget(label)

    def show_overview(self, windows: Dict[str, StormWindow], workspace_count: int = 4,
                      current_workspace: int = 0) -> None:
        """Show the overview mode."""
        self.populate(windows, workspace_count, current_workspace)
        self.show()
        self.raise_()
        self.activateWindow()
        logger.debug("Overview mode shown with %d windows", len(self._thumbnails))

    def _on_thumbnail_clicked(self, app_id: str):
        self.hide()
        self.window_selected.emit(app_id)

    def hideEvent(self, event):
        """Clear hover state on hide."""
        for thumb in self._thumbnails:
            thumb.set_hovered(False)
        super().hideEvent(event)
