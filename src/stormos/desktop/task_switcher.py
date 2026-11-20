"""Alt+Tab task switcher overlay for StormOS.

Provides a full-screen overlay showing all open application windows
in a grid, allowing the user to cycle through and select a window.
"""

import logging
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, QRect, QSize, Property, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QKeySequence, QShortcut
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


class SwitcherCard(QFrame):
    """A single application card in the task switcher."""

    selected = Signal()

    def __init__(self, app_id: str, title: str, icon: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.app_id = app_id
        self._title = title
        self._icon = icon
        self._is_selected = False
        self.setFixedSize(200, 140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._update_style()

        # Icon
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self._title)
        title_label.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {COLOR_TEXT_MAIN}; background: transparent;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # App ID
        id_label = QLabel(self.app_id)
        id_label.setStyleSheet(
            f"font-size: 10px; color: {COLOR_TEXT_SECONDARY}; background: transparent;"
        )
        id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(id_label)

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._update_style()

    def _update_style(self):
        border_color = COLOR_LIGHTNING if self._is_selected else COLOR_PANEL_EDGE
        bg_color = "rgba(23, 35, 61, 0.95)" if self._is_selected else "rgba(16, 26, 49, 0.85)"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 12px;
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit()
        super().mousePressEvent(event)


class AltTabSwitcher(QWidget):
    """Full-screen overlay for Alt+Tab task switching.

    Shows all open windows as cards in a grid layout.
    Arrow keys or Alt+Right/Left cycle through windows.
    Enter or click selects the highlighted window.
    Escape dismisses the switcher.
    """

    window_selected = Signal(str)  # Emits app_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._windows: List[Dict] = []  # [{"app_id": str, "title": str, "icon": str}]
        self._current_index = 0
        self._cards: List[SwitcherCard] = []
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(f"background-color: rgba(7, 11, 22, 0.85);")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(60, 80, 60, 60)
        self.main_layout.setSpacing(0)

        # Title
        title = QLabel("⚡ Switch Application")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {COLOR_LIGHTNING}; "
            f"background: transparent; letter-spacing: 1px;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Use ← → to navigate, Enter to select, Esc to cancel")
        subtitle.setStyleSheet(
            f"font-size: 11px; color: {COLOR_TEXT_SECONDARY}; background: transparent;"
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(subtitle)

        self.main_layout.addSpacing(30)

        # Cards container
        cards_container = QWidget()
        self.cards_layout = QHBoxLayout(cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(20)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(cards_container, 1)

        # Setup keyboard shortcuts
        shortcut_right = QShortcut(QKeySequence("Right"), self)
        shortcut_right.activated.connect(self._navigate_next)
        shortcut_left = QShortcut(QKeySequence("Left"), self)
        shortcut_left.activated.connect(self._navigate_prev)
        shortcut_enter = QShortcut(QKeySequence("Return"), self)
        shortcut_enter.activated.connect(self._select_current)
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self.hide)
        shortcut_tab = QShortcut(QKeySequence("Tab"), self)
        shortcut_tab.activated.connect(self._navigate_next)
        shortcut_shift_tab = QShortcut(QKeySequence("Shift+Tab"), self)
        shortcut_shift_tab.activated.connect(self._navigate_prev)

    def populate(self, windows: Dict[str, StormWindow]) -> None:
        """Populate the switcher with open windows."""
        self._windows = []
        for app_id, win in windows.items():
            if not win._is_minimized:
                self._windows.append({
                    "app_id": app_id,
                    "title": win._title,
                    "icon": win._icon,
                })

        self._current_index = 0
        self._build_cards()

    def _build_cards(self):
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        if not self._windows:
            label = QLabel("No open applications")
            label.setStyleSheet(f"font-size: 14px; color: {COLOR_TEXT_SECONDARY}; background: transparent;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(label)
            return

        for i, win_info in enumerate(self._windows):
            card = SwitcherCard(
                app_id=win_info["app_id"],
                title=win_info["title"],
                icon=win_info["icon"],
            )
            card.set_selected(i == self._current_index)
            card.selected.connect(lambda aid=win_info["app_id"]: self._on_card_selected(aid))
            self._cards.append(card)
            self.cards_layout.addWidget(card)

    def show_switcher(self, windows: Dict[str, StormWindow]) -> None:
        """Show the switcher overlay."""
        self.populate(windows)
        self.show()
        self.raise_()
        self.activateWindow()
        logger.debug("Alt+Tab switcher shown with %d windows", len(self._windows))

    def _navigate_next(self):
        if not self._windows:
            return
        old = self._current_index
        self._current_index = (self._current_index + 1) % len(self._windows)
        self._update_selection(old)

    def _navigate_prev(self):
        if not self._windows:
            return
        old = self._current_index
        self._current_index = (self._current_index - 1) % len(self._windows)
        self._update_selection(old)

    def _update_selection(self, old_index: int):
        if old_index < len(self._cards):
            self._cards[old_index].set_selected(False)
        if self._current_index < len(self._cards):
            self._cards[self._current_index].set_selected(True)

    def _select_current(self):
        if self._windows and 0 <= self._current_index < len(self._windows):
            app_id = self._windows[self._current_index]["app_id"]
            self.hide()
            self.window_selected.emit(app_id)

    def _on_card_selected(self, app_id: str):
        self.hide()
        self.window_selected.emit(app_id)

    def hideEvent(self, event):
        """Clear selection on hide."""
        for card in self._cards:
            card.set_selected(False)
        super().hideEvent(event)
