"""StormOS Volume Mixer Application.

Provides a quick-access mixing panel for all audio channels with
real-time volume control and mute toggles.
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from stormos.core.constants import (
    COLOR_LIGHTNING,
    COLOR_LIGHTNING_GLOW,
    COLOR_NIGHT_SKY,
    COLOR_PANEL_EDGE,
    COLOR_RAISED_PANEL,
    COLOR_STORM_CLOUD,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_SECONDARY,
)
from stormos.services.audio_manager import (
    AMBIENT_PRESETS,
    CHANNEL_AMBIENT,
    CHANNEL_MASTER,
    CHANNEL_STARTUP,
    CHANNEL_UI,
    AudioManager,
)
from stormos.services.user_manager import UserProfile


class MixerApp(QWidget):
    """Volume mixer application for real-time audio channel control."""

    def __init__(self, current_user: Optional[UserProfile] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_user = current_user
        self.audio_manager = AudioManager.get_instance()
        self.setWindowTitle("Volume Mixer")
        self.setStyleSheet(f"background-color: {COLOR_NIGHT_SKY};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("🎚️ Volume Mixer")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLOR_LIGHTNING};")
        layout.addWidget(title)

        # Channel definitions: (key, label, icon)
        self.channels = [
            (CHANNEL_MASTER, "Master Volume", "🔊"),
            (CHANNEL_STARTUP, "Startup Sound", "🚀"),
            (CHANNEL_AMBIENT, "Ambient Audio", "🌧️"),
            (CHANNEL_UI, "UI Sound Effects", "🖱️"),
        ]

        self.sliders = {}
        self.mute_checks = {}
        self.labels = {}

        for ch_key, ch_label, ch_icon in self.channels:
            card = self._create_channel_card(ch_key, ch_label, ch_icon)
            layout.addWidget(card)

        # Ambient preset selector
        ambient_frame = self._create_ambient_section()
        layout.addWidget(ambient_frame)

        layout.addStretch()

    def _create_channel_card(self, channel: str, label: str, icon: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; "
            f"border-radius: 8px; padding: 12px;"
        )
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        # Header row: icon + label + mute checkbox
        header_row = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 16px;")
        header_row.addWidget(icon_label)

        name_label = QLabel(label)
        name_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        header_row.addWidget(name_label)

        header_row.addStretch()

        mute_check = QCheckBox("Mute")
        mute_check.setCursor(Qt.CursorShape.PointingHandCursor)
        mute_check.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; spacing: 4px;")
        mute_check.toggled.connect(lambda checked, ch=channel: self._on_mute(ch, checked))
        header_row.addWidget(mute_check)
        self.mute_checks[channel] = mute_check

        c_layout.addLayout(header_row)

        # Volume slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        vol = int(self.audio_manager.get_volume(channel) * 100)
        slider.setValue(vol)
        slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                background: {COLOR_STORM_CLOUD};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLOR_LIGHTNING};
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLOR_LIGHTNING_GLOW}, stop:1 {COLOR_LIGHTNING});
                border-radius: 3px;
            }}
            """
        )
        slider.valueChanged.connect(lambda v, ch=channel: self._on_slider_changed(ch, v))
        c_layout.addWidget(slider)
        self.sliders[channel] = slider

        # Volume percentage label
        vol_label = QLabel(f"{vol}%")
        vol_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; text-align: right;")
        vol_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        slider.valueChanged.connect(lambda v: vol_label.setText(f"{v}%"))
        c_layout.addWidget(vol_label)
        self.labels[channel] = vol_label

        return card

    def _create_ambient_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"background-color: {COLOR_RAISED_PANEL}; border: 1px solid {COLOR_PANEL_EDGE}; "
            f"border-radius: 8px; padding: 12px;"
        )
        f_layout = QVBoxLayout(frame)
        f_layout.setSpacing(8)

        header = QLabel("🌧️ Ambient Preset")
        header.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {COLOR_TEXT_MAIN};")
        f_layout.addWidget(header)

        from PySide6.QtWidgets import QComboBox

        combo = QComboBox()
        combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for key, val in AMBIENT_PRESETS.items():
            combo.addItem(val["label"], key)
        combo.setStyleSheet(
            f"background-color: {COLOR_STORM_CLOUD}; color: {COLOR_TEXT_MAIN}; padding: 6px; "
            f"border: 1px solid {COLOR_PANEL_EDGE}; border-radius: 6px;"
        )
        current_idx = max(0, combo.findData(self.audio_manager.get_ambient()))
        combo.setCurrentIndex(current_idx)
        combo.currentIndexChanged.connect(self._on_ambient_changed)
        f_layout.addWidget(combo)
        self.ambient_combo = combo

        return frame

    def _on_slider_changed(self, channel: str, value: int) -> None:
        self.audio_manager.set_volume(channel, value / 100.0)

    def _on_mute(self, channel: str, checked: bool) -> None:
        if checked:
            # Store current value before muting
            current = self.audio_manager.get_volume(channel)
            self.sliders[channel].setProperty("pre_mute_volume", current)
            self.audio_manager.mute_channel(channel)
            self.sliders[channel].setValue(0)
        else:
            # Restore previous volume
            pre_mute = self.sliders[channel].property("pre_mute_volume")
            if pre_mute is not None and pre_mute > 0:
                self.audio_manager.unmute_channel(channel, pre_mute)
                self.sliders[channel].setValue(int(pre_mute * 100))
            else:
                self.audio_manager.unmute_channel(channel)
                self.sliders[channel].setValue(50)

    def _on_ambient_changed(self, index: int) -> None:
        preset_key = self.ambient_combo.itemData(index)
        if preset_key is not None:
            self.audio_manager.set_ambient(str(preset_key))
