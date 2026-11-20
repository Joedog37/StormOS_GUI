"""StormOS Settings Application.

Provides comprehensive configuration for user accounts, display & multi-monitor setup,
wallpaper personalization with real-time previews, mouse cursors, and security options.
"""

from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

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
    COLOR_SUCCESS,
    COLOR_WARNING,
    ORG_NAME,
)
from stormos.core.paths import ASSETS_DIR, get_asset_path
from stormos.services.audio_manager import (
    AMBIENT_PRESETS,
    CHANNEL_AMBIENT,
    CHANNEL_MASTER,
    CHANNEL_STARTUP,
    CHANNEL_UI,
    AudioManager,
)
from stormos.services.user_manager import UserManager, UserProfile
from stormos.ui.wallpaper_manager import WallpaperManager


class WallpaperCard(QFrame):
    """Clickable thumbnail card for wallpaper preset selection."""

    selected = Signal(str)  # Emits wallpaper id/path

    def __init__(
        self,
        wp_id: str,
        name: str,
        thumb_pixmap: QPixmap,
        is_active: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.wp_id = wp_id
        self._is_active = is_active
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(170, 140)
        self._setup_ui(name, thumb_pixmap)
        self.set_active(is_active)

    def _setup_ui(self, name: str, thumb_pixmap: QPixmap):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.img_label = QLabel()
        self.img_label.setFixedSize(156, 92)
        self.img_label.setPixmap(thumb_pixmap.scaled(156, 92, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("border-radius: 6px; background: transparent;")
        layout.addWidget(self.img_label)

        self.title_label = QLabel(name)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLOR_TEXT_MAIN}; background: transparent; border: none;")
        layout.addWidget(self.title_label)

    def set_active(self, active: bool):
        self._is_active = active
        border_col = COLOR_LIGHTNING if active else COLOR_PANEL_EDGE
        bg_col = "rgba(56, 201, 255, 0.12)" if active else COLOR_RAISED_PANEL
        self.setStyleSheet(
            f"""
            WallpaperCard {{
                background-color: {bg_col};
                border: 2px solid {border_col};
                border-radius: 8px;
            }}
            WallpaperCard:hover {{
                border-color: {COLOR_LIGHTNING};
                background-color: rgba(56, 201, 255, 0.18);
            }}
            """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.wp_id)
        super().mousePressEvent(event)


class SettingsApp(QWidget):
    """StormOS settings, display configuration, and personalization control panel."""

    settings_updated = Signal()
    wallpaper_changed = Signal(str)       # Emits new wallpaper path/id
    display_mode_changed = Signal(dict)   # Emits {mode, screen_index, width, height}

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.user_manager = UserManager()
        self.selected_wallpaper = self.current_user.wallpaper if self.current_user else "wallpaper.png"
        self._wp_cards: Dict[str, WallpaperCard] = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.setCursor(Qt.CursorShape.PointingHandCursor)
        tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_PANEL_EDGE};
                background-color: {COLOR_STORM_CLOUD};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 14px;
                margin-right: 2px;
                font-weight: bold;
                font-size: 11px;
            }}
            QTabBar::tab:hover {{
                background-color: #1c2b4d;
                color: {COLOR_TEXT_MAIN};
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_LIGHTNING};
                border-color: {COLOR_LIGHTNING};
            }}
            """
        )

        tabs.addTab(self._build_display_tab(), "🖥️ Display & Screens")
        tabs.addTab(self._build_personalization_tab(), "🎨 Personalization & Wallpaper")
        tabs.addTab(self._build_audio_tab(), "🔊 Audio & Sound")
        tabs.addTab(self._build_account_tab(), "👤 User Account")
        tabs.addTab(self._build_security_tab(), "🛡️ Security & Privacy")
        tabs.addTab(self._build_about_tab(), "⚡ About StormOS")

        main_layout.addWidget(tabs)

    # ----------------- 1. DISPLAY & SCREENS TAB -----------------

    def _build_display_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        title = QLabel("🖥️ Display & Multi-Monitor Configuration")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        desc = QLabel(
            "Manage connected monitors, screen resolutions, windowed/fullscreen display modes, "
            "and active display targeting for StormOS."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(desc)

        # Monitor detection card
        mon_card = QFrame()
        mon_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;")
        mc_layout = QVBoxLayout(mon_card)
        mc_layout.setSpacing(10)

        mc_header = QLabel("Connected Monitors Detected:")
        mc_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        mc_layout.addWidget(mc_header)

        self.monitor_combo = QComboBox()
        self.monitor_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.monitor_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        self._populate_monitors()
        mc_layout.addWidget(self.monitor_combo)

        # Refresh button
        btn_refresh_mon = QPushButton("🔄 Refresh Displays")
        btn_refresh_mon.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh_mon.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        btn_refresh_mon.clicked.connect(self._populate_monitors)
        mc_layout.addWidget(btn_refresh_mon)

        layout.addWidget(mon_card)

        # Display Mode & Resolution Card
        mode_card = QFrame()
        mode_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 12px;")
        m_layout = QVBoxLayout(mode_card)
        m_layout.setSpacing(12)

        m_header = QLabel("Display Mode & Resolution:")
        m_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        m_layout.addWidget(m_header)

        self.radio_fullscreen = QRadioButton("Fullscreen (Dedicated OS Experience) [F11]")
        self.radio_fullscreen.setChecked(True)
        self.radio_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_fullscreen.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-weight: bold;")
        m_layout.addWidget(self.radio_fullscreen)

        self.radio_maximized = QRadioButton("Maximized Windowed (With Desktop Bounds)")
        self.radio_maximized.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_maximized.setStyleSheet(f"color: {COLOR_TEXT_MAIN};")
        m_layout.addWidget(self.radio_maximized)

        self.radio_windowed = QRadioButton("Windowed Custom Resolution:")
        self.radio_windowed.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_windowed.setStyleSheet(f"color: {COLOR_TEXT_MAIN};")
        m_layout.addWidget(self.radio_windowed)

        # Resolution dropdown
        res_row = QHBoxLayout()
        res_row.setContentsMargins(20, 0, 0, 0)
        res_row.addWidget(QLabel("Preset:"))

        self.res_combo = QComboBox()
        self.res_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.res_combo.addItems([
            "1920 × 1080 (1080p FHD - 16:9)",
            "1600 × 900 (HD+ - 16:9)",
            "1366 × 768 (Laptop HD - 16:9)",
            "1280 × 800 (WXGA - 16:10)",
            "1024 × 768 (XGA - 4:3)",
            "Custom Resolution",
        ])
        self.res_combo.setCurrentIndex(3)  # 1280x800 default
        self.res_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        res_row.addWidget(self.res_combo, 1)
        m_layout.addLayout(res_row)

        # Custom resolution inputs
        self.custom_res_row = QHBoxLayout()
        self.custom_res_row.setContentsMargins(20, 0, 0, 0)
        self.custom_res_row.addWidget(QLabel("Width:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(800, 7680)
        self.spin_width.setValue(1280)
        self.spin_width.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 4px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px;")
        self.custom_res_row.addWidget(self.spin_width)

        self.custom_res_row.addWidget(QLabel("Height:"))
        self.spin_height = QSpinBox()
        self.spin_height.setRange(600, 4320)
        self.spin_height.setValue(800)
        self.spin_height.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 4px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 4px;")
        self.custom_res_row.addWidget(self.spin_height)
        m_layout.addLayout(self.custom_res_row)

        layout.addWidget(mode_card)

        # Apply Display Button
        btn_apply_disp = QPushButton("⚡ Apply Display Settings")
        btn_apply_disp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_disp.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                font-size: 13px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #A9EBFF;
            }}
            """
        )
        btn_apply_disp.clicked.connect(self._apply_display_settings)
        layout.addWidget(btn_apply_disp)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _populate_monitors(self):
        """Detect and populate all active monitors."""
        self.monitor_combo.clear()
        screens = QApplication.screens()
        primary = QApplication.primaryScreen()

        for idx, scr in enumerate(screens):
            geo = scr.geometry()
            rate = int(scr.refreshRate()) if hasattr(scr, "refreshRate") else 60
            is_pri = " [Primary]" if scr == primary else ""
            name = scr.name() if scr.name() else f"Monitor {idx+1}"
            text = f"Display {idx+1}: {name} — {geo.width()}×{geo.height()} @ {rate}Hz{is_pri}"
            self.monitor_combo.addItem(text, idx)

    def _apply_display_settings(self):
        """Gather display parameters and emit signal for main window."""
        screen_idx = self.monitor_combo.currentData()
        if screen_idx is None:
            screen_idx = 0

        mode = "fullscreen"
        if self.radio_maximized.isChecked():
            mode = "maximized"
        elif self.radio_windowed.isChecked():
            mode = "windowed"

        # Determine dimensions
        preset_idx = self.res_combo.currentIndex()
        if preset_idx == 0:
            w, h = 1920, 1080
        elif preset_idx == 1:
            w, h = 1600, 900
        elif preset_idx == 2:
            w, h = 1366, 768
        elif preset_idx == 3:
            w, h = 1280, 800
        elif preset_idx == 4:
            w, h = 1024, 768
        else:
            w = self.spin_width.value()
            h = self.spin_height.value()

        config = {
            "mode": mode,
            "screen_index": screen_idx,
            "width": w,
            "height": h,
        }
        self.display_mode_changed.emit(config)
        QMessageBox.information(
            self,
            "Display Settings Applied",
            f"Display mode set to '{mode.upper()}' on Display {screen_idx+1} ({w}×{h}).\nTip: Press F11 anytime to toggle fullscreen.",
        )

    # ----------------- 2. PERSONALIZATION & WALLPAPER TAB -----------------

    def _build_personalization_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        title = QLabel("🎨 Personalization, Wallpapers & Mouse Cursors")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        # Wallpaper Gallery Section
        wp_card = QFrame()
        wp_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        w_layout = QVBoxLayout(wp_card)
        w_layout.setSpacing(12)

        w_header = QLabel("Desktop Wallpaper Themes:")
        w_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        w_layout.addWidget(w_header)

        # Grid of wallpaper presets
        grid = QGridLayout()
        grid.setSpacing(10)

        presets = WallpaperManager.get_presets()
        for idx, preset in enumerate(presets):
            thumb = WallpaperManager.create_thumbnail(preset["id"], thumb_w=156, thumb_h=92)
            is_active = (self.selected_wallpaper == preset["id"] or self.selected_wallpaper == preset.get("path"))
            card = WallpaperCard(
                wp_id=preset["id"],
                name=preset["name"],
                thumb_pixmap=thumb,
                is_active=is_active,
            )
            card.selected.connect(self._on_wallpaper_card_selected)
            self._wp_cards[preset["id"]] = card
            row = idx // 3
            col = idx % 3
            grid.addWidget(card, row, col)

        w_layout.addLayout(grid)

        # Custom image selector
        custom_row = QHBoxLayout()
        self.custom_wp_path_label = QLabel(f"Selected: {self.selected_wallpaper}")
        self.custom_wp_path_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        custom_row.addWidget(self.custom_wp_path_label, 1)

        btn_browse = QPushButton("📁 Browse Custom Image...")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """
        )
        btn_browse.clicked.connect(self._browse_custom_wallpaper)
        custom_row.addWidget(btn_browse)

        btn_apply_wp = QPushButton("⚡ Apply Wallpaper Now")
        btn_apply_wp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_wp.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #A9EBFF;
            }}
            """
        )
        btn_apply_wp.clicked.connect(self._apply_current_wallpaper)
        custom_row.addWidget(btn_apply_wp)

        w_layout.addLayout(custom_row)
        layout.addWidget(wp_card)

        # Theme & Accents Card
        accent_card = QFrame()
        accent_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        a_layout = QVBoxLayout(accent_card)
        a_layout.setSpacing(10)

        a_header = QLabel("Accent Lighting & Color Schemes:")
        a_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        a_layout.addWidget(a_header)

        self.theme_combo = QComboBox()
        self.theme_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_combo.addItems([
            "Electric Cyan (#38C9FF) [Standard StormOS Baseline]",
            "Storm Amber (#FFB54A) [High-Alert Thunder]",
            "Thunder Red (#FF5C77) [Critical Ops Mode]",
            "Ice Blue (#A9EBFF) [Glacial Aurora]",
            "Neon Emerald (#00FFA3) [Cyber Velocity]",
            "Deep Violet (#9D4EDD) [Midnight Lightning]",
        ])
        self.theme_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        a_layout.addWidget(self.theme_combo)

        layout.addWidget(accent_card)

        # Mouse Cursors & System Pointer Card
        cursor_card = QFrame()
        cursor_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        c_layout = QVBoxLayout(cursor_card)
        c_layout.setSpacing(8)

        c_header = QLabel("🖱️ Mouse Cursors & Interactive Pointer Feedback:")
        c_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        c_layout.addWidget(c_header)

        c_info = QLabel(
            "• Pointer (Arrow): Default navigation cursor\n"
            "• Hand Pointer: Active on all buttons, dock items, clickable cards, and tabs\n"
            "• I-Beam Cursor: Active on text boxes, terminal console, and code editor\n"
            "• Resize Cursors: Active on all window borders (Horizontal, Vertical, Diagonal)\n"
            "• Splitter Cursors: Active on resizable sidebars and editor splitters"
        )
        c_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; line-height: 1.5;")
        c_layout.addWidget(c_info)

        layout.addWidget(cursor_card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _on_wallpaper_card_selected(self, wp_id: str):
        self.selected_wallpaper = wp_id
        self.custom_wp_path_label.setText(f"Selected: {wp_id}")
        for cid, card in self._wp_cards.items():
            card.set_active(cid == wp_id)

    def _browse_custom_wallpaper(self):
        """Open file dialog to pick custom image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Wallpaper Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if file_path:
            self.selected_wallpaper = file_path
            self.custom_wp_path_label.setText(f"Selected Custom: {Path(file_path).name}")
            for card in self._wp_cards.values():
                card.set_active(False)
            self._apply_current_wallpaper()

    def _apply_current_wallpaper(self):
        """Save wallpaper to user profile and update desktop view."""
        if not self.selected_wallpaper:
            return

        if self.current_user:
            self.current_user.wallpaper = self.selected_wallpaper
            self.user_manager.update_user(self.current_user)

        self.wallpaper_changed.emit(self.selected_wallpaper)
        self.settings_updated.emit()
        QMessageBox.information(self, "Wallpaper Updated", "Desktop wallpaper updated successfully!")

    # ----------------- 3. USER ACCOUNT TAB -----------------

    def _build_account_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        title = QLabel("👤 User Account Management")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        username = self.current_user.username if self.current_user else "guest"
        display_name = self.current_user.display_name if self.current_user else "Guest User"
        role = self.current_user.role if self.current_user else "guest"

        # ---- Profile Info Card ----
        profile_card = QFrame()
        profile_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        p_layout = QVBoxLayout(profile_card)
        p_layout.setSpacing(10)

        p_header = QLabel("Profile Information")
        p_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        p_layout.addWidget(p_header)

        p_layout.addWidget(QLabel(f"Username:  {username}"))
        p_layout.addWidget(QLabel(f"Account Role:  {role.upper()}"))

        p_layout.addWidget(QLabel("Display Name:"))
        self.disp_name_input = QLineEdit(display_name)
        self.disp_name_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.disp_name_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        p_layout.addWidget(self.disp_name_input)

        btn_save = QPushButton("💾 Save Display Name")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(self._primary_btn_style())
        btn_save.clicked.connect(self._save_display_name)
        p_layout.addWidget(btn_save)

        layout.addWidget(profile_card)

        # ---- Avatar Card ----
        avatar_card = QFrame()
        avatar_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        av_layout = QVBoxLayout(avatar_card)
        av_layout.setSpacing(10)

        av_header = QLabel("🖼️ Profile Avatar")
        av_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        av_layout.addWidget(av_header)

        av_info = QLabel(f"Current avatar: {self.current_user.avatar if self.current_user else 'stormos_logo.png'}")
        av_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        av_layout.addWidget(av_info)

        av_combo = QComboBox()
        av_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        av_combo.addItems(["stormos_logo.png", "avatar_default.png", "avatar_storm.png", "avatar_thunder.png", "Custom Image..."])
        av_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        av_layout.addWidget(av_combo)

        btn_avatar = QPushButton("📁 Choose Custom Avatar")
        btn_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_avatar.setStyleSheet(self._secondary_btn_style())
        btn_avatar.clicked.connect(self._choose_avatar)
        av_layout.addWidget(btn_avatar)

        btn_apply_avatar = QPushButton("⚡ Apply Avatar")
        btn_apply_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply_avatar.setStyleSheet(self._primary_btn_style())
        btn_apply_avatar.clicked.connect(lambda: self._apply_avatar(av_combo.currentText()))
        av_layout.addWidget(btn_apply_avatar)

        layout.addWidget(avatar_card)

        # ---- Password Change Card ----
        pw_card = QFrame()
        pw_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        pw_layout = QVBoxLayout(pw_card)
        pw_layout.setSpacing(10)

        pw_header = QLabel("🔒 Change Password")
        pw_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        pw_layout.addWidget(pw_header)

        pw_layout.addWidget(QLabel("Current Password:"))
        self.old_pw_input = QLineEdit()
        self.old_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pw_input.setPlaceholderText("Enter current password...")
        self.old_pw_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.old_pw_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        pw_layout.addWidget(self.old_pw_input)

        pw_layout.addWidget(QLabel("New Password:"))
        self.new_pw_input = QLineEdit()
        self.new_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw_input.setPlaceholderText("Enter new password...")
        self.new_pw_input.setCursor(Qt.CursorShape.IBeamCursor)
        self.new_pw_input.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
        pw_layout.addWidget(self.new_pw_input)

        pw_status = QLabel("")
        pw_status.setStyleSheet(f"font-size: 11px; min-height: 14px;")
        pw_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pw_status_label = pw_status
        pw_layout.addWidget(pw_status)

        btn_change_pw = QPushButton("🔑 Change Password")
        btn_change_pw.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change_pw.setStyleSheet(self._primary_btn_style())
        btn_change_pw.clicked.connect(self._change_password)
        pw_layout.addWidget(btn_change_pw)

        layout.addWidget(pw_card)

        # ---- Role & Permissions Card (Admin only) ----
        if self.current_user and self.current_user.role == "admin":
            role_card = QFrame()
            role_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
            r_layout = QVBoxLayout(role_card)
            r_layout.setSpacing(10)

            r_header = QLabel("🛡️ User Roles & Permissions")
            r_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
            r_layout.addWidget(r_header)

            r_info = QLabel("Manage roles for all registered accounts.")
            r_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
            r_layout.addWidget(r_info)

            # User list with role selector
            self.role_user_combo = QComboBox()
            self.role_user_combo.setCursor(Qt.CursorShape.PointingHandCursor)
            self._populate_role_users()
            self.role_user_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
            r_layout.addWidget(self.role_user_combo)

            role_row = QHBoxLayout()
            role_row.addWidget(QLabel("Set Role:"))
            self.role_combo = QComboBox()
            self.role_combo.setCursor(Qt.CursorShape.PointingHandCursor)
            self.role_combo.addItems(["admin", "user"])
            self.role_combo.setStyleSheet(f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;")
            role_row.addWidget(self.role_combo)
            r_layout.addLayout(role_row)

            btn_set_role = QPushButton("⚡ Update Role")
            btn_set_role.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_set_role.setStyleSheet(self._primary_btn_style())
            btn_set_role.clicked.connect(self._update_role)
            r_layout.addWidget(btn_set_role)

            layout.addWidget(role_card)

        # ---- Data Export / Backup Card ----
        backup_card = QFrame()
        backup_card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(backup_card)
        b_layout.setSpacing(10)

        b_header = QLabel("💾 Data Export & Backup")
        b_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        b_layout.addWidget(b_header)

        b_info = QLabel("Export your account data as a ZIP archive for safekeeping.")
        b_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        b_layout.addWidget(b_info)

        btn_export = QPushButton("📦 Export My Data")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet(self._primary_btn_style())
        btn_export.clicked.connect(self._export_data)
        b_layout.addWidget(btn_export)

        btn_import = QPushButton("📥 Import Data from Backup")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.setStyleSheet(self._secondary_btn_style())
        btn_import.clicked.connect(self._import_data)
        b_layout.addWidget(btn_import)

        layout.addWidget(backup_card)

        # ---- Danger Zone: Delete Account ----
        danger_card = QFrame()
        danger_card.setStyleSheet(f"background-color: rgba(255, 92, 119, 0.08); border: 1px solid {COLOR_ERROR}; border-radius: 8px; padding: 14px;")
        d_layout = QVBoxLayout(danger_card)
        d_layout.setSpacing(10)

        d_header = QLabel("⚠️ Danger Zone")
        d_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_ERROR};")
        d_layout.addWidget(d_header)

        d_info = QLabel("Permanently delete this account and all associated data. This action cannot be undone.")
        d_info.setWordWrap(True)
        d_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        d_layout.addWidget(d_info)

        btn_delete = QPushButton("🗑️ Delete My Account")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {COLOR_RAISED_PANEL};
                color: {COLOR_ERROR};
                border: 1px solid {COLOR_ERROR};
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLOR_ERROR};
                color: {COLOR_NIGHT_SKY};
            }}
            """
        )
        btn_delete.clicked.connect(self._delete_account)
        d_layout.addWidget(btn_delete)

        layout.addWidget(danger_card)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ---- Button style helpers ----

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLOR_LIGHTNING};
                color: {COLOR_NIGHT_SKY};
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: #A9EBFF;
            }}
            """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """

    # ---- Account tab handlers ----

    def _save_display_name(self):
        if not self.current_user:
            return
        new_name = self.disp_name_input.text().strip()
        if new_name:
            self.current_user.display_name = new_name
            self.user_manager.update_user(self.current_user)
            QMessageBox.information(self, "Success", "Display name updated successfully.")
            self.settings_updated.emit()

    def _choose_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Avatar Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)",
        )
        if file_path:
            self._apply_avatar(file_path)

    def _apply_avatar(self, avatar: str):
        if not self.current_user or avatar == "Custom Image...":
            return
        if self.user_manager.update_avatar(self.current_user.username, avatar):
            self.current_user.avatar = avatar
            QMessageBox.information(self, "Success", "Avatar updated successfully.")
            self.settings_updated.emit()

    def _change_password(self):
        if not self.current_user:
            return
        old_pw = self.old_pw_input.text()
        new_pw = self.new_pw_input.text()

        if not old_pw:
            self._set_pw_status("Please enter your current password.", is_error=True)
            return
        if not new_pw:
            self._set_pw_status("Please enter a new password.", is_error=True)
            return
        if len(new_pw) < 3:
            self._set_pw_status("New password must be at least 3 characters.", is_error=True)
            return

        success = self.user_manager.change_password(self.current_user.username, old_pw, new_pw)
        if success:
            self._set_pw_status("Password changed successfully!", is_error=False)
            self.old_pw_input.clear()
            self.new_pw_input.clear()
            QMessageBox.information(self, "Success", "Your password has been updated.")
        else:
            self._set_pw_status("Failed — check your current password.", is_error=True)

    def _set_pw_status(self, text: str, is_error: bool = False):
        color = COLOR_ERROR if is_error else COLOR_SUCCESS
        self.pw_status_label.setText(text)
        self.pw_status_label.setStyleSheet(f"font-size: 11px; color: {color}; min-height: 14px;")

    def _populate_role_users(self):
        """Fill the role management combo with all users."""
        self.role_user_combo.clear()
        users = self.user_manager.list_users()
        for u in users:
            self.role_user_combo.addItem(f"{u.display_name} ({u.username}) — {u.role}", u.username)

    def _update_role(self):
        if not self.current_user:
            return
        target_username = self.role_user_combo.currentData()
        new_role = self.role_combo.currentText()
        if not target_username:
            return

        success = self.user_manager.update_role(target_username, new_role, self.current_user)
        if success:
            QMessageBox.information(self, "Success", f"Role for '{target_username}' updated to '{new_role}'.")
            self._populate_role_users()
        else:
            QMessageBox.warning(self, "Error", "Could not update role. You may not have permission or this is the last admin.")

    def _export_data(self):
        if not self.current_user:
            return
        archive = self.user_manager.export_user_data(self.current_user.username)
        if archive:
            QMessageBox.information(self, "Export Complete", f"Data exported to:\n{archive}")
        else:
            QMessageBox.warning(self, "Export Failed", "Could not export user data.")

    def _import_data(self):
        archive_path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select Backup Archive",
            "",
            "ZIP Files (*.zip);;All Files (*.*)",
        )
        if not archive_path_str:
            return
        archive_path = Path(archive_path_str)
        if self.user_manager.import_user_data(archive_path):
            QMessageBox.information(self, "Import Complete", "User data restored successfully.")
        else:
            QMessageBox.warning(self, "Import Failed", "Could not restore data from the selected archive.")

    def _delete_account(self):
        if not self.current_user:
            return
        reply = QMessageBox.warning(
            self,
            "Delete Account",
            f"Are you sure you want to permanently delete '{self.current_user.username}'?\n\n"
            "All data will be lost. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success = self.user_manager.delete_user(self.current_user.username, self.current_user)
            if success:
                QMessageBox.information(self, "Account Deleted", "Your account has been deleted. Please log in again.")
                self.settings_updated.emit()
            else:
                QMessageBox.warning(self, "Delete Failed", "Could not delete account. You may be the last admin.")

    # ----------------- 4. AUDIO TAB -----------------

    def _build_audio_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        title = QLabel("🔊 Audio & Sound Settings")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        # Get audio manager instance
        self.audio_manager = AudioManager.get_instance()

        # ---- Master Volume Card ----
        master_card = QFrame()
        master_card.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;"
        )
        m_layout = QVBoxLayout(master_card)
        m_layout.setSpacing(10)

        m_header = QLabel("🎚️ Master Volume")
        m_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        m_layout.addWidget(m_header)

        self.master_slider = self._create_volume_slider()
        self.master_slider.setValue(int(self.audio_manager.get_volume(CHANNEL_MASTER) * 100))
        self.master_slider.valueChanged.connect(lambda v: self._on_volume_changed(CHANNEL_MASTER, v))
        m_layout.addWidget(self.master_slider)

        self.master_label = QLabel(f"{self.master_slider.value()}%")
        self.master_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; text-align: right;")
        self.master_slider.valueChanged.connect(lambda v: self.master_label.setText(f"{v}%"))
        m_layout.addWidget(self.master_label)

        layout.addWidget(master_card)

        # ---- Startup Sound Card ----
        startup_card = QFrame()
        startup_card.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;"
        )
        s_layout = QVBoxLayout(startup_card)
        s_layout.setSpacing(10)

        s_header = QLabel("🚀 Startup Sound")
        s_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        s_layout.addWidget(s_header)

        self.startup_toggle = QRadioButton("Play startup sound on boot")
        self.startup_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.startup_toggle.setChecked(self.audio_manager.startup_enabled)
        self.startup_toggle.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; spacing: 8px;")
        self.startup_toggle.toggled.connect(
            lambda checked: setattr(self.audio_manager, "startup_enabled", checked)
        )
        s_layout.addWidget(self.startup_toggle)

        s_layout.addWidget(QLabel("Volume:"))
        self.startup_slider = self._create_volume_slider()
        self.startup_slider.setValue(int(self.audio_manager.get_volume(CHANNEL_STARTUP) * 100))
        self.startup_slider.valueChanged.connect(lambda v: self._on_volume_changed(CHANNEL_STARTUP, v))
        s_layout.addWidget(self.startup_slider)

        btn_test_startup = QPushButton("🔊 Test Startup Sound")
        btn_test_startup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_startup.setStyleSheet(self._secondary_btn_style())
        btn_test_startup.clicked.connect(lambda: self.audio_manager.play_startup_sound())
        s_layout.addWidget(btn_test_startup)

        layout.addWidget(startup_card)

        # ---- Ambient Audio Card ----
        ambient_card = QFrame()
        ambient_card.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;"
        )
        a_layout = QVBoxLayout(ambient_card)
        a_layout.setSpacing(10)

        a_header = QLabel("🌧️ Ambient Background Audio")
        a_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        a_layout.addWidget(a_header)

        a_info = QLabel("Looping atmospheric sound that plays in the background.")
        a_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        a_layout.addWidget(a_info)

        self.ambient_combo = QComboBox()
        self.ambient_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for key, val in AMBIENT_PRESETS.items():
            self.ambient_combo.addItem(val["label"], key)
        self.ambient_combo.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; "
            f"border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;"
        )
        current_idx = max(0, self.ambient_combo.findData(self.audio_manager.get_ambient()))
        self.ambient_combo.setCurrentIndex(current_idx)
        self.ambient_combo.currentIndexChanged.connect(self._on_ambient_changed)
        a_layout.addWidget(self.ambient_combo)

        a_layout.addWidget(QLabel("Ambient Volume:"))
        self.ambient_slider = self._create_volume_slider()
        self.ambient_slider.setValue(int(self.audio_manager.get_volume(CHANNEL_AMBIENT) * 100))
        self.ambient_slider.valueChanged.connect(lambda v: self._on_volume_changed(CHANNEL_AMBIENT, v))
        a_layout.addWidget(self.ambient_slider)

        layout.addWidget(ambient_card)

        # ---- UI Sound Effects Card ----
        ui_card = QFrame()
        ui_card.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;"
        )
        u_layout = QVBoxLayout(ui_card)
        u_layout.setSpacing(10)

        u_header = QLabel("🖱️ UI Sound Effects")
        u_header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        u_layout.addWidget(u_header)

        self.ui_toggle = QRadioButton("Play sounds for clicks, window actions, and errors")
        self.ui_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ui_toggle.setChecked(self.audio_manager.ui_sounds_enabled)
        self.ui_toggle.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; spacing: 8px;")
        self.ui_toggle.toggled.connect(
            lambda checked: setattr(self.audio_manager, "ui_sounds_enabled", checked)
        )
        u_layout.addWidget(self.ui_toggle)

        u_layout.addWidget(QLabel("UI Volume:"))
        self.ui_slider = self._create_volume_slider()
        self.ui_slider.setValue(int(self.audio_manager.get_volume(CHANNEL_UI) * 100))
        self.ui_slider.valueChanged.connect(lambda v: self._on_volume_changed(CHANNEL_UI, v))
        u_layout.addWidget(self.ui_slider)

        # Test buttons row
        test_row = QHBoxLayout()
        for sound_name in ["click", "minimize", "maximize", "close", "error"]:
            btn = QPushButton(f"{sound_name.title()}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._secondary_btn_style())
            btn.clicked.connect(lambda _, s=sound_name: self.audio_manager.play_ui_sound(s))
            test_row.addWidget(btn)
        u_layout.addLayout(test_row)

        layout.addWidget(ui_card)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_volume_slider(self) -> "QSlider":
        from PySide6.QtWidgets import QSlider

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                background: {COLOR_STORM_CLOUD};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_LIGHTNING};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLOR_LIGHTNING_GLOW}, stop:1 {COLOR_LIGHTNING});
                border-radius: 3px;
            }}
            """
        )
        return slider

    def _on_volume_changed(self, channel: str, value: int) -> None:
        self.audio_manager.set_volume(channel, value / 100.0)

    def _on_ambient_changed(self, index: int) -> None:
        preset_key = self.ambient_combo.itemData(index)
        if preset_key is not None:
            self.audio_manager.set_ambient(str(preset_key))

    # ---- Button style helper (shared with account tab) ----

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background-color: {COLOR_STORM_CLOUD};
                color: {COLOR_TEXT_MAIN};
                border: 1px solid {COLOR_PANEL_EDGE};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {COLOR_LIGHTNING};
                color: {COLOR_LIGHTNING};
            }}
            """

    # ----------------- 5. SECURITY TAB -----------------

    def _build_security_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Cryptographic & Sandbox Security")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet(f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 8px; padding: 14px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        c_layout.addWidget(QLabel("• Password Hashing: PBKDF2-HMAC-SHA256 (120,000 rounds)"))
        c_layout.addWidget(QLabel("• Salt Entropy: 256-bit CSPRNG unique per user"))
        c_layout.addWidget(QLabel("• Timing-Safe Verification: hmac.compare_digest active"))
        c_layout.addWidget(QLabel("• Directory Traversal Protection: Enforced across all apps"))
        c_layout.addWidget(QLabel("• Untrusted Code Auto-Execution: Prohibited by baseline"))

        layout.addWidget(card)
        layout.addStretch()
        return widget

    # ----------------- 5. ABOUT TAB -----------------

    def _build_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        header = QLabel(f"⚡ {APP_NAME} Desktop")
        header.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {COLOR_LIGHTNING};")
        layout.addWidget(header)

        desc = QLabel(
            f"Version {APP_VERSION}\n"
            f"Crafted by {ORG_NAME}\n\n"
            "StormOS is a customized, high-performance fullscreen desktop environment\n"
            "built on Python 3.13 and PySide6 with cinematic storm-glass aesthetics,\n"
            "multi-monitor display control, and built-in Code & Utility ecosystems."
        )
        desc.setStyleSheet(f"color: {COLOR_TEXT_MAIN}; font-size: 12px; line-height: 1.5;")
        layout.addWidget(desc)

        layout.addStretch()
        return widget
