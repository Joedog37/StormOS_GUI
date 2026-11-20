"""Audio management service for StormOS.

Handles startup sounds, ambient background audio, UI sound effects,
and per-channel volume control. Uses PySide6's QSoundEffect for WAV
files and QMediaPlayer for MP3 ambient tracks.
"""

import logging
import wave
import struct
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtMultimedia import QAudioDevice, QMediaDevices, QMediaPlayer, QSoundEffect
from PySide6.QtCore import QObject, QUrl, Property, Signal

from stormos.core.paths import get_asset_path

logger = logging.getLogger(__name__)

# Volume ranges: 0.0 (mute) to 1.0 (full)
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0
DEFAULT_MASTER_VOLUME = 0.7
DEFAULT_STARTUP_VOLUME = 0.5
DEFAULT_AMBIENT_VOLUME = 0.3
DEFAULT_UI_VOLUME = 0.6

# Audio channel names
CHANNEL_MASTER = "master"
CHANNEL_STARTUP = "startup"
CHANNEL_AMBIENT = "ambient"
CHANNEL_UI = "ui"

# Ambient track presets
AMBIENT_PRESETS = {
    "none": {"label": "None (Silent)", "file": None},
    "rain": {"label": "Rain & Storm", "file": "rain-and-little-storm-298087.mp3"},
}

# Startup sound file
STARTUP_SOUND_FILE = "startup.wav"

# UI sound effect names and their generated wave parameters
UI_SOUND_EFFECTS = {
    "click": {"freq": 880, "duration": 0.05, "amp": 0.3},
    "minimize": {"freq": 660, "duration": 0.08, "amp": 0.25},
    "maximize": {"freq": 440, "duration": 0.08, "amp": 0.25},
    "close": {"freq": 330, "duration": 0.1, "amp": 0.2},
    "error": {"freq": 220, "duration": 0.2, "amp": 0.35},
}


class AudioManager(QObject):
    """Central audio manager for StormOS.

    Manages startup sound, ambient background loops, UI sound effects,
    and per-channel volume mixing. Singleton pattern via get_instance().
    """

    volume_changed = Signal(str, float)  # channel_name, new_volume
    ambient_changed = Signal(str)  # new preset name

    _instance: Optional["AudioManager"] = None

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._volumes: Dict[str, float] = {
            CHANNEL_MASTER: DEFAULT_MASTER_VOLUME,
            CHANNEL_STARTUP: DEFAULT_STARTUP_VOLUME,
            CHANNEL_AMBIENT: DEFAULT_AMBIENT_VOLUME,
            CHANNEL_UI: DEFAULT_UI_VOLUME,
        }
        self._startup_enabled = True
        self._ui_sounds_enabled = True
        self._current_ambient = "none"

        # Ambient player for MP3 looping
        self._ambient_player: Optional[QMediaPlayer] = None

        # UI sound effects cache
        self._ui_effects: Dict[str, QSoundEffect] = {}

        # Generate UI sound effect WAV files on first access
        self._ensure_ui_sound_files()

    @classmethod
    def get_instance(cls) -> "AudioManager":
        """Return the singleton AudioManager instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ---- Volume Control ----

    def set_volume(self, channel: str, volume: float) -> None:
        """Set volume for a specific channel (0.0–1.0)."""
        clamped = max(MIN_VOLUME, min(MAX_VOLUME, volume))
        self._volumes[channel] = clamped

        # If master volume changes, propagate to all active players
        if channel == CHANNEL_MASTER:
            self._apply_master_volume()

        self.volume_changed.emit(channel, clamped)
        logger.debug("Volume set: %s = %.2f", channel, clamped)

    def get_volume(self, channel: str) -> float:
        """Get current volume for a channel."""
        return self._volumes.get(channel, 0.0)

    def get_effective_volume(self, channel: str) -> float:
        """Get effective volume considering master mix."""
        if channel == CHANNEL_MASTER:
            return self._volumes[CHANNEL_MASTER]
        return self._volumes.get(channel, 0.0) * self._volumes[CHANNEL_MASTER]

    def mute_channel(self, channel: str) -> None:
        """Mute a specific channel."""
        self.set_volume(channel, 0.0)

    def unmute_channel(self, channel: str, volume: Optional[float] = None) -> None:
        """Unmute a channel, restoring or setting a volume."""
        if volume is None:
            volume = {
                CHANNEL_STARTUP: DEFAULT_STARTUP_VOLUME,
                CHANNEL_AMBIENT: DEFAULT_AMBIENT_VOLUME,
                CHANNEL_UI: DEFAULT_UI_VOLUME,
            }.get(channel, 0.5)
        self.set_volume(channel, volume)

    def _apply_master_volume(self) -> None:
        """Apply master volume to all active players."""
        master = self._volumes[CHANNEL_MASTER]

        # Apply to ambient player
        if self._ambient_player:
            self._ambient_player.setVolume(master * self._volumes[CHANNEL_AMBIENT])

        # Apply to UI sound effects
        for effect in self._ui_effects.values():
            effect.setVolume(master * self._volumes[CHANNEL_UI])

    # ---- Startup Sound ----

    def play_startup_sound(self) -> None:
        """Play the startup boot sound."""
        if not self._startup_enabled:
            return

        sound_path = get_asset_path(STARTUP_SOUND_FILE)
        if not sound_path.exists():
            logger.warning("Startup sound file not found: %s", sound_path)
            return

        vol = self.get_effective_volume(CHANNEL_STARTUP)
        effect = QSoundEffect()
        effect.setSource(QUrl.fromLocalFile(str(sound_path)))
        effect.setVolume(vol)
        effect.play()
        logger.info("Startup sound played at volume %.2f", vol)

    @property
    def startup_enabled(self) -> bool:
        return self._startup_enabled

    @startup_enabled.setter
    def startup_enabled(self, value: bool) -> None:
        self._startup_enabled = value
        logger.info("Startup sound %s", "enabled" if value else "disabled")

    # ---- Ambient Background Audio ----

    def set_ambient(self, preset_name: str) -> None:
        """Set or change the ambient background audio preset."""
        preset = AMBIENT_PRESETS.get(preset_name)
        if not preset:
            logger.error("Unknown ambient preset: %s", preset_name)
            return

        # Stop current ambient
        self._stop_ambient()
        self._current_ambient = preset_name
        self.ambient_changed.emit(preset_name)

        if preset["file"]:
            self._start_ambient(preset["file"])
        else:
            logger.info("Ambient audio disabled (preset: none)")

    def get_ambient(self) -> str:
        """Return the current ambient preset name."""
        return self._current_ambient

    def _start_ambient(self, filename: str) -> None:
        """Start looping ambient audio from the given file."""
        sound_path = get_asset_path(filename)
        if not sound_path.exists():
            logger.warning("Ambient file not found: %s", sound_path)
            return

        self._ambient_player = QMediaPlayer()
        self._ambient_player.setSource(QUrl.fromLocalFile(str(sound_path)))
        vol = self.get_effective_volume(CHANNEL_AMBIENT)
        self._ambient_player.setVolume(vol)
        self._ambient_player.setLoops(QMediaPlayer.Infinite)
        self._ambient_player.play()
        logger.info("Ambient audio started: %s at volume %.2f", filename, vol)

    def _stop_ambient(self) -> None:
        """Stop the current ambient audio."""
        if self._ambient_player:
            self._ambient_player.stop()
            self._ambient_player.deleteLater()
            self._ambient_player = None

    def pause_ambient(self) -> None:
        """Pause the ambient audio."""
        if self._ambient_player:
            self._ambient_player.pause()

    def resume_ambient(self) -> None:
        """Resume paused ambient audio."""
        if self._ambient_player:
            self._ambient_player.play()

    # ---- UI Sound Effects ----

    def play_ui_sound(self, sound_name: str) -> None:
        """Play a named UI sound effect (click, minimize, maximize, close, error)."""
        if not self._ui_sounds_enabled:
            return

        effect = self._ui_effects.get(sound_name)
        if effect:
            effect.play()
        else:
            logger.warning("UI sound effect not found: %s", sound_name)

    @property
    def ui_sounds_enabled(self) -> bool:
        return self._ui_sounds_enabled

    @ui_sounds_enabled.setter
    def ui_sounds_enabled(self, value: bool) -> None:
        self._ui_sounds_enabled = value
        logger.info("UI sounds %s", "enabled" if value else "disabled")

    def _ensure_ui_sound_files(self) -> None:
        """Generate short WAV files for UI sound effects and load them."""
        assets = get_asset_path("")  # Get assets directory

        for name, params in UI_SOUND_EFFECTS.items():
            wav_path = assets / f"ui_{name}.wav"
            if not wav_path.exists():
                self._generate_wav(wav_path, params)

            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(wav_path)))
            vol = self.get_effective_volume(CHANNEL_UI)
            effect.setVolume(vol)
            self._ui_effects[name] = effect

    @staticmethod
    def _generate_wav(path: Path, params: Dict) -> None:
        """Generate a simple sine-wave WAV file for a UI sound effect."""
        freq = params["freq"]
        duration = params["duration"]
        amp = params["amp"]
        sample_rate = 44100
        num_samples = int(sample_rate * duration)

        try:
            with wave.open(str(path), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)

                for i in range(num_samples):
                    t = i / sample_rate
                    # Envelope: quick attack, slow decay
                    envelope = min(1.0, (i / (sample_rate * 0.01))) * max(0.0, 1.0 - (i / num_samples))
                    sample = int(amp * 32767.0 * envelope * __import__("math").sin(2 * __import__("math").pi * freq * t))
                    wf.writeframes(struct.pack("<h", sample))

            logger.debug("Generated UI sound WAV: %s", path.name)
        except OSError as e:
            logger.error("Failed to generate WAV file %s: %s", path, e)

    # ---- Settings Persistence ----

    def save_settings(self) -> Dict:
        """Serialize audio settings to a dictionary for persistence."""
        return {
            "volumes": dict(self._volumes),
            "startup_enabled": self._startup_enabled,
            "ui_sounds_enabled": self._ui_sounds_enabled,
            "ambient_preset": self._current_ambient,
        }

    def load_settings(self, settings: Dict) -> None:
        """Restore audio settings from a dictionary."""
        if "volumes" in settings:
            for ch, vol in settings["volumes"].items():
                self._volumes[ch] = max(MIN_VOLUME, min(MAX_VOLUME, float(vol)))
        self._startup_enabled = settings.get("startup_enabled", True)
        self._ui_sounds_enabled = settings.get("ui_sounds_enabled", True)
        preset = settings.get("ambient_preset", "none")
        if preset in AMBIENT_PRESETS:
            self._current_ambient = preset
        self._apply_master_volume()

    # ---- Cleanup ----

    def shutdown(self) -> None:
        """Stop all audio and release resources."""
        self._stop_ambient()
        for effect in self._ui_effects.values():
            effect.stop()
            effect.deleteLater()
        self._ui_effects.clear()
