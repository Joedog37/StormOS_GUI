"""StormOS Window Framework.

Provides draggable, resizable, custom storm-glass window containers
with minimize, maximize, restore, and close controls.
"""

from typing import Optional
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
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
)


class WindowTitleBar(QFrame):
    """Custom storm-glass titlebar with icon, title, and window control buttons."""

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    double_clicked = Signal()

    def __init__(self, title: str = "Application", icon: str = "⚡", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._title = title
        self._icon = icon
        self._is_maximized = False
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            f"""
            WindowTitleBar {{
                background-color: rgba(16, 26, 49, 0.95);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid {COLOR_PANEL_EDGE};
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(8)

        # App Icon & Title
        self.icon_label = QLabel(self._icon)
        self.icon_label.setStyleSheet(f"font-size: 15px; color: {COLOR_LIGHTNING}; background: transparent;")
        layout.addWidget(self.icon_label)

        self.title_label = QLabel(self._title)
        self.title_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Window Control Buttons: Minimize, Maximize, Close
        btn_style_common = f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_MAIN};
                border-color: {COLOR_PANEL_EDGE};
            }}
        """

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(28, 24)
        self.min_btn.setToolTip("Minimize")
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.setStyleSheet(btn_style_common)
        self.min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(28, 24)
        self.max_btn.setToolTip("Maximize / Restore")
        self.max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.max_btn.setStyleSheet(btn_style_common)
        self.max_btn.clicked.connect(self.maximize_clicked.emit)
        layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(28, 24)
        self.close_btn.setToolTip("Close")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 92, 119, 0.25);
                color: {COLOR_ERROR};
                border-color: {COLOR_ERROR};
            }}
            """
        )
        self.close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.close_btn)

    def set_title(self, title: str):
        self._title = title
        self.title_label.setText(title)

    def set_icon(self, icon: str):
        self._icon = icon
        self.icon_label.setText(icon)

    def set_maximized_state(self, is_maximized: bool):
        self._is_maximized = is_maximized
        self.max_btn.setText("❐" if is_maximized else "□")

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class StormWindow(QFrame):
    """A floating, draggable, resizable application window in StormOS."""

    closed = Signal(object)      # Emits self
    minimized = Signal(object)   # Emits self
    maximized = Signal(object)   # Emits self
    restored = Signal(object)    # Emits self
    focused = Signal(object)     # Emits self

    RESIZE_BORDER_SIZE = 8

    def __init__(
        self,
        app_id: str,
        title: str = "Application",
        icon: str = "⚡",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.app_id = app_id
        self._title = title
        self._icon = icon

        self._is_active = False
        self._is_maximized = False
        self._is_minimized = False
        self._normal_geometry = QRect(100, 80, 800, 560)

        # Dragging & Resizing tracking
        self._drag_pos: Optional[QPoint] = None
        self._resize_drag: Optional[str] = None
        self._resize_start_geom: Optional[QRect] = None
        self._resize_start_pos: Optional[QPoint] = None

        self.setMouseTracking(True)
        self._setup_ui()
        self.setGeometry(self._normal_geometry)
        self.set_active(True)

    def _setup_ui(self):
        self.setObjectName("StormWindow")
        self._update_window_style()

        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(1, 1, 1, 1)
        self.window_layout.setSpacing(0)

        # Title bar
        self.title_bar = WindowTitleBar(title=self._title, icon=self._icon, parent=self)
        self.title_bar.minimize_clicked.connect(self.toggle_minimize)
        self.title_bar.maximize_clicked.connect(self.toggle_maximize)
        self.title_bar.close_clicked.connect(self.close_window)
        self.title_bar.double_clicked.connect(self.toggle_maximize)
        self.window_layout.addWidget(self.title_bar)

        # Content container
        self.content_container = QWidget(self)
        self.content_container.setStyleSheet(
            f"""
            QWidget {{
                background-color: rgba(16, 26, 49, 0.94);
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            """
        )
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.window_layout.addWidget(self.content_container, 1)

    def set_content_widget(self, widget: QWidget):
        """Set the main application widget inside the window."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.content_layout.addWidget(widget)

    def set_active(self, active: bool):
        """Set focus highlight status."""
        if self._is_active != active:
            self._is_active = active
            self._update_window_style()
            if active:
                self.focused.emit(self)

    def _update_window_style(self):
        border_color = COLOR_LIGHTNING if self._is_active else COLOR_PANEL_EDGE
        border_width = "1.5px" if self._is_active else "1px"
        glow_shadow = "0 0 12px rgba(56, 201, 255, 0.25)" if self._is_active else "none"

        self.setStyleSheet(
            f"""
            QFrame#StormWindow {{
                background-color: rgba(16, 26, 49, 0.96);
                border: {border_width} solid {border_color};
                border-radius: 12px;
            }}
            """
        )

    def toggle_minimize(self):
        """Minimize or restore window."""
        if self._is_minimized:
            self.restore_minimized()
        else:
            self.minimize_window()

    def minimize_window(self):
        """Hide window and signal minimization."""
        self._is_minimized = True
        self.hide()
        self.minimized.emit(self)

    def restore_minimized(self):
        """Restore a minimized window to desktop."""
        self._is_minimized = False
        self.show()
        self.raise_()
        self.set_active(True)
        self.restored.emit(self)

    def toggle_maximize(self):
        """Toggle maximized and normal geometry."""
        if self._is_maximized:
            self.restore_maximized()
        else:
            self.maximize_window()

    def maximize_window(self):
        """Maximize window to fit available desktop space."""
        if not self._is_maximized:
            self._normal_geometry = self.geometry()
            self._is_maximized = True
            self.title_bar.set_maximized_state(True)
            if self.parentWidget():
                # Fit within parent bounds leaving margin for dock at bottom
                parent_rect = self.parentWidget().rect()
                # Leave 64px for bottom dock
                self.setGeometry(0, 0, parent_rect.width(), max(300, parent_rect.height() - 64))
            self.maximized.emit(self)

    def restore_maximized(self):
        """Restore window from maximized state back to normal bounds."""
        if self._is_maximized:
            self._is_maximized = False
            self.title_bar.set_maximized_state(False)
            self.setGeometry(self._normal_geometry)
            self.restored.emit(self)

    def close_window(self):
        """Close window and notify subscribers."""
        self.closed.emit(self)
        self.deleteLater()

    # --- Mouse Dragging & Resizing Logic ---

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_active(True)
            self.raise_()

            # Check if clicked on title bar area for dragging
            title_rect = self.title_bar.rect()
            title_pos = self.title_bar.mapFromParent(event.position().toPoint())
            if title_rect.contains(title_pos) and not self._is_maximized:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return

            # Check if clicking near borders/corners for resizing
            resize_direction = self._get_resize_direction(event.position().toPoint())
            if resize_direction and not self._is_maximized:
                self._resize_drag = resize_direction
                self._resize_start_geom = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Handle dragging
        if self._drag_pos is not None and not self._is_maximized:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if self.parentWidget():
                # Constrain within parent boundary
                max_x = max(0, self.parentWidget().width() - 80)
                max_y = max(0, self.parentWidget().height() - 80)
                new_x = max(-self.width() + 80, min(new_pos.x(), max_x))
                new_y = max(0, min(new_pos.y(), max_y))
                self.move(new_x, new_y)
            else:
                self.move(new_pos)
            event.accept()
            return

        # Handle resizing
        if self._resize_drag and self._resize_start_geom and self._resize_start_pos and not self._is_maximized:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            g = QRect(self._resize_start_geom)

            if "r" in self._resize_drag:
                g.setWidth(max(380, g.width() + delta.x()))
            if "b" in self._resize_drag:
                g.setHeight(max(260, g.height() + delta.y()))
            if "l" in self._resize_drag:
                new_w = max(380, g.width() - delta.x())
                g.setLeft(g.right() - new_w)
            if "t" in self._resize_drag:
                new_h = max(260, g.height() - delta.y())
                g.setTop(g.bottom() - new_h)

            self.setGeometry(g)
            event.accept()
            return

        # Update cursor on hover over borders
        if not self._is_maximized:
            direction = self._get_resize_direction(event.position().toPoint())
            self._update_cursor_for_direction(direction)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        self._resize_drag = None
        self._resize_start_geom = None
        self._resize_start_pos = None
        super().mouseReleaseEvent(event)

    def _get_resize_direction(self, pos: QPoint) -> Optional[str]:
        """Detect if cursor is on window resize borders."""
        b = self.RESIZE_BORDER_SIZE
        w = self.width()
        h = self.height()

        left = pos.x() <= b
        right = pos.x() >= w - b
        top = pos.y() <= b
        bottom = pos.y() >= h - b

        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return None

    def _update_cursor_for_direction(self, direction: Optional[str]):
        if direction in ("tl", "br"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif direction in ("tr", "bl"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif direction in ("l", "r"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif direction in ("t", "b"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
