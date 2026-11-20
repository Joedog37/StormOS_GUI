"""Phase 8 — Audio System & Atmospheric Immersion Tests.

Tests the AudioManager service, volume mixer app, audio settings integration,
and UI sound effect generation without requiring a running Qt application.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the project src directory is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


class TestAudioManagerConstants(unittest.TestCase):
    """Test that audio manager constants and presets are correctly defined."""

    def test_ambient_presets_exist(self):
        from stormos.services.audio_manager import AMBIENT_PRESETS
        self.assertIn("none", AMBIENT_PRESETS)
        self.assertIn("rain", AMBIENT_PRESETS)
        self.assertIsNone(AMBIENT_PRESETS["none"]["file"])
        self.assertIsNotNone(AMBIENT_PRESETS["rain"]["file"])

    def test_ui_sound_effects_defined(self):
        from stormos.services.audio_manager import UI_SOUND_EFFECTS
        expected = {"click", "minimize", "maximize", "close", "error"}
        self.assertEqual(expected, set(UI_SOUND_EFFECTS.keys()))
        for name, params in UI_SOUND_EFFECTS.items():
            self.assertIn("freq", params)
            self.assertIn("duration", params)
            self.assertIn("amp", params)
            self.assertGreater(params["freq"], 0)
            self.assertGreater(params["duration"], 0)
            self.assertGreater(params["amp"], 0)

    def test_channel_constants(self):
        from stormos.services.audio_manager import (
            CHANNEL_MASTER,
            CHANNEL_STARTUP,
            CHANNEL_AMBIENT,
            CHANNEL_UI,
        )
        self.assertEqual(CHANNEL_MASTER, "master")
        self.assertEqual(CHANNEL_STARTUP, "startup")
        self.assertEqual(CHANNEL_AMBIENT, "ambient")
        self.assertEqual(CHANNEL_UI, "ui")

    def test_default_volumes(self):
        from stormos.services.audio_manager import (
            DEFAULT_MASTER_VOLUME,
            DEFAULT_STARTUP_VOLUME,
            DEFAULT_AMBIENT_VOLUME,
            DEFAULT_UI_VOLUME,
        )
        self.assertEqual(DEFAULT_MASTER_VOLUME, 0.7)
        self.assertEqual(DEFAULT_STARTUP_VOLUME, 0.5)
        self.assertEqual(DEFAULT_AMBIENT_VOLUME, 0.3)
        self.assertEqual(DEFAULT_UI_VOLUME, 0.6)


class TestAudioManagerVolume(unittest.TestCase):
    """Test volume control logic without Qt audio backend."""

    def setUp(self):
        # Reset singleton before each test
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def _create_manager(self):
        """Create a manager with mocked Qt objects."""
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                return AudioManager()

    def test_set_and_get_volume(self):
        mgr = self._create_manager()
        mgr.set_volume("master", 0.5)
        self.assertAlmostEqual(mgr.get_volume("master"), 0.5)

    def test_volume_clamped_to_zero(self):
        mgr = self._create_manager()
        mgr.set_volume("master", -10.0)
        self.assertEqual(mgr.get_volume("master"), 0.0)

    def test_volume_clamped_to_one(self):
        mgr = self._create_manager()
        mgr.set_volume("master", 5.0)
        self.assertEqual(mgr.get_volume("master"), 1.0)

    def test_mute_channel(self):
        mgr = self._create_manager()
        mgr.set_volume("ui", 0.8)
        mgr.mute_channel("ui")
        self.assertEqual(mgr.get_volume("ui"), 0.0)

    def test_unmute_channel_restores_default(self):
        mgr = self._create_manager()
        mgr.mute_channel("ui")
        mgr.unmute_channel("ui")
        from stormos.services.audio_manager import DEFAULT_UI_VOLUME
        self.assertAlmostEqual(mgr.get_volume("ui"), DEFAULT_UI_VOLUME)

    def test_unmute_channel_with_custom_volume(self):
        mgr = self._create_manager()
        mgr.mute_channel("ui")
        mgr.unmute_channel("ui", 0.9)
        self.assertAlmostEqual(mgr.get_volume("ui"), 0.9)

    def test_effective_volume_considers_master(self):
        mgr = self._create_manager()
        mgr.set_volume("master", 0.5)
        mgr.set_volume("ui", 0.8)
        effective = mgr.get_effective_volume("ui")
        self.assertAlmostEqual(effective, 0.4)  # 0.5 * 0.8

    def test_effective_volume_master_returns_master(self):
        mgr = self._create_manager()
        mgr.set_volume("master", 0.6)
        self.assertAlmostEqual(mgr.get_effective_volume("master"), 0.6)

    def test_default_volumes_on_init(self):
        mgr = self._create_manager()
        from stormos.services.audio_manager import (
            DEFAULT_MASTER_VOLUME,
            DEFAULT_STARTUP_VOLUME,
            DEFAULT_AMBIENT_VOLUME,
            DEFAULT_UI_VOLUME,
        )
        self.assertAlmostEqual(mgr.get_volume("master"), DEFAULT_MASTER_VOLUME)
        self.assertAlmostEqual(mgr.get_volume("startup"), DEFAULT_STARTUP_VOLUME)
        self.assertAlmostEqual(mgr.get_volume("ambient"), DEFAULT_AMBIENT_VOLUME)
        self.assertAlmostEqual(mgr.get_volume("ui"), DEFAULT_UI_VOLUME)


class TestAudioManagerStartupSound(unittest.TestCase):
    """Test startup sound enable/disable and playback logic."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def _create_manager(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                return AudioManager()

    def test_startup_enabled_by_default(self):
        mgr = self._create_manager()
        self.assertTrue(mgr.startup_enabled)

    def test_disable_startup_sound(self):
        mgr = self._create_manager()
        mgr.startup_enabled = False
        self.assertFalse(mgr.startup_enabled)

    def test_play_startup_sound_skips_when_disabled(self):
        mgr = self._create_manager()
        mgr.startup_enabled = False
        # Should not raise and should return early
        mgr.play_startup_sound()

    def test_play_startup_sound_skips_when_file_missing(self):
        mgr = self._create_manager()
        mgr.startup_enabled = True
        # With a missing file, it should gracefully skip
        mgr.play_startup_sound()


class TestAudioManagerAmbient(unittest.TestCase):
    """Test ambient audio preset switching."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def _create_manager(self):
        mock_player_class = MagicMock()
        mock_player_instance = MagicMock()
        mock_player_class.return_value = mock_player_instance
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", mock_player_class):
                from stormos.services.audio_manager import AudioManager
                return AudioManager()

    def test_ambient_defaults_to_none(self):
        mgr = self._create_manager()
        self.assertEqual(mgr.get_ambient(), "none")

    def test_set_ambient_to_rain(self):
        mgr = self._create_manager()
        with patch.object(mgr, "_start_ambient", MagicMock):
            mgr.set_ambient("rain")
        self.assertEqual(mgr.get_ambient(), "rain")

    def test_set_ambient_to_none(self):
        mgr = self._create_manager()
        with patch.object(mgr, "_start_ambient", MagicMock):
            mgr.set_ambient("rain")
            mgr.set_ambient("none")
        self.assertEqual(mgr.get_ambient(), "none")

    def test_set_unknown_ambient_ignored(self):
        mgr = self._create_manager()
        mgr.set_ambient("unknown_preset")
        self.assertEqual(mgr.get_ambient(), "none")

    def test_pause_ambient(self):
        mgr = self._create_manager()
        mgr._ambient_player = MagicMock()
        mgr.pause_ambient()
        mgr._ambient_player.pause.assert_called_once()

    def test_resume_ambient(self):
        mgr = self._create_manager()
        mgr._ambient_player = MagicMock()
        mgr.resume_ambient()
        mgr._ambient_player.play.assert_called_once()


class TestAudioManagerUISounds(unittest.TestCase):
    """Test UI sound effect enable/disable."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def _create_manager(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                return AudioManager()

    def test_ui_sounds_enabled_by_default(self):
        mgr = self._create_manager()
        self.assertTrue(mgr.ui_sounds_enabled)

    def test_disable_ui_sounds(self):
        mgr = self._create_manager()
        mgr.ui_sounds_enabled = False
        self.assertFalse(mgr.ui_sounds_enabled)

    def test_play_ui_sound_skips_when_disabled(self):
        mgr = self._create_manager()
        mgr.ui_sounds_enabled = False
        # Should not raise
        mgr.play_ui_sound("click")


class TestAudioManagerSettingsPersistence(unittest.TestCase):
    """Test save/load settings serialization."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def _create_manager(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                return AudioManager()

    def test_save_settings_returns_dict(self):
        mgr = self._create_manager()
        settings = mgr.save_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn("volumes", settings)
        self.assertIn("startup_enabled", settings)
        self.assertIn("ui_sounds_enabled", settings)
        self.assertIn("ambient_preset", settings)

    def test_save_and_load_preserves_volumes(self):
        mgr = self._create_manager()
        mgr.set_volume("master", 0.3)
        mgr.set_volume("ui", 0.9)
        settings = mgr.save_settings()

        # Create new manager and load
        mgr2 = self._create_manager()
        mgr2.load_settings(settings)
        self.assertAlmostEqual(mgr2.get_volume("master"), 0.3)
        self.assertAlmostEqual(mgr2.get_volume("ui"), 0.9)

    def test_save_and_load_preserves_flags(self):
        mgr = self._create_manager()
        mgr.startup_enabled = False
        mgr.ui_sounds_enabled = False
        settings = mgr.save_settings()

        mgr2 = self._create_manager()
        mgr2.load_settings(settings)
        self.assertFalse(mgr2.startup_enabled)
        self.assertFalse(mgr2.ui_sounds_enabled)

    def test_save_and_load_preserves_ambient(self):
        mgr = self._create_manager()
        with patch.object(mgr, "_start_ambient", MagicMock):
            mgr.set_ambient("rain")
        settings = mgr.save_settings()

        mgr2 = self._create_manager()
        mgr2.load_settings(settings)
        self.assertEqual(mgr2.get_ambient(), "rain")

    def test_load_empty_settings_uses_defaults(self):
        mgr = self._create_manager()
        mgr.load_settings({})
        self.assertTrue(mgr.startup_enabled)
        self.assertTrue(mgr.ui_sounds_enabled)
        self.assertEqual(mgr.get_ambient(), "none")


class TestAudioManagerWavGeneration(unittest.TestCase):
    """Test WAV file generation for UI sound effects."""

    def test_generate_wav_creates_file(self):
        import tempfile
        import wave
        from stormos.services.audio_manager import AudioManager

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_sound.wav"
            params = {"freq": 440, "duration": 0.1, "amp": 0.5}
            AudioManager._generate_wav(path, params)

            self.assertTrue(path.exists())
            # Verify it's a valid WAV
            with wave.open(str(path), "r") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), 44100)
                frames = wf.getnframes()
                self.assertGreater(frames, 0)

    def test_generate_wav_file_size_reasonable(self):
        import tempfile
        from stormos.services.audio_manager import AudioManager

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_sound.wav"
            params = {"freq": 880, "duration": 0.05, "amp": 0.3}
            AudioManager._generate_wav(path, params)

            size = path.stat().st_size
            # WAV header (44 bytes) + samples
            # 0.05s * 44100 Hz * 2 bytes = ~4410 bytes
            self.assertGreater(size, 44)
            self.assertLess(size, 10000)

    def test_generate_wav_handles_os_error(self):
        import logging
        from stormos.services.audio_manager import AudioManager

        # Try to write to a read-only path — should log error but not crash
        AudioManager._generate_wav(Path("/nonexistent/dir/sound.wav"), {"freq": 440, "duration": 0.1, "amp": 0.5})


class TestAudioManagerSingleton(unittest.TestCase):
    """Test singleton pattern for AudioManager."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def test_singleton_returns_same_instance(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                inst1 = AudioManager.get_instance()
                inst2 = AudioManager.get_instance()
                self.assertIs(inst1, inst2)


class TestAudioManagerShutdown(unittest.TestCase):
    """Test cleanup and shutdown."""

    def setUp(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def tearDown(self):
        from stormos.services.audio_manager import AudioManager
        AudioManager._instance = None

    def test_shutdown_clears_effects(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.services.audio_manager import AudioManager
                mgr = AudioManager()
                mgr.shutdown()
                self.assertEqual(len(mgr._ui_effects), 0)


class TestMixerAppRegistration(unittest.TestCase):
    """Test that the Volume Mixer app is registered in the app registry."""

    def test_mixer_registered(self):
        from stormos.apps.registry import AppRegistry
        registry = AppRegistry.get_instance()
        mixer = registry.get_app("mixer")
        self.assertIsNotNone(mixer)
        self.assertEqual(mixer.name, "Volume Mixer")
        self.assertEqual(mixer.category, "System")
        self.assertTrue(mixer.is_builtin)
        self.assertIsNotNone(mixer.factory)

    def test_mixer_default_size(self):
        from stormos.apps.registry import AppRegistry
        registry = AppRegistry.get_instance()
        mixer = registry.get_app("mixer")
        self.assertEqual(mixer.default_width, 480)
        self.assertEqual(mixer.default_height, 560)


class TestMixerAppCreation(unittest.TestCase):
    """Test that the MixerApp can be instantiated."""

    def test_mixer_app_instantiable(self):
        with patch("stormos.services.audio_manager.QSoundEffect", MagicMock):
            with patch("stormos.services.audio_manager.QMediaPlayer", MagicMock):
                from stormos.apps.mixer import MixerApp
                app = MixerApp()
                self.assertIsNotNone(app)
                self.assertEqual(app.windowTitle(), "Volume Mixer")


class TestAudioIntegration(unittest.TestCase):
    """Test that audio constants are importable from settings and main_window."""

    def test_settings_imports_audio_manager(self):
        # Verify settings.py can import audio manager components
        from stormos.services.audio_manager import (
            AMBIENT_PRESETS,
            CHANNEL_AMBIENT,
            CHANNEL_MASTER,
            CHANNEL_STARTUP,
            CHANNEL_UI,
            AudioManager,
        )
        self.assertIsNotNone(AudioManager)
        self.assertIsNotNone(AMBIENT_PRESETS)

    def test_audio_manager_importable_from_main_window_context(self):
        from stormos.services.audio_manager import AudioManager
        self.assertTrue(hasattr(AudioManager, "get_instance"))
        self.assertTrue(hasattr(AudioManager, "play_startup_sound"))
        self.assertTrue(hasattr(AudioManager, "play_ui_sound"))
        self.assertTrue(hasattr(AudioManager, "set_ambient"))
        self.assertTrue(hasattr(AudioManager, "set_volume"))


if __name__ == "__main__":
    unittest.main()
