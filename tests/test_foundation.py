"""Tests for Phase 1 - Clean Foundation."""

import os
import sys
from pathlib import Path
import pytest

# Ensure offscreen Qt rendering for automated testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from stormos import __version__
from stormos.core.constants import (
    APP_NAME,
    APP_VERSION,
    COLOR_NIGHT_SKY,
    COLOR_LIGHTNING,
    COLOR_STORM_CLOUD,
)
from stormos.core.paths import (
    PROJECT_ROOT as RESOLVED_ROOT,
    ASSETS_DIR,
    USERS_DIR,
    APPS_DIR,
    get_asset_path,
)
from stormos.app import create_application
from stormos.ui.main_window import StormMainWindow


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_version_and_metadata():
    """Verify system version and identity constants."""
    assert __version__ == "0.1.0"
    assert APP_VERSION == "0.1.0"
    assert APP_NAME == "StormOS"


def test_paths_resolution():
    """Verify path helper points to correct directories."""
    assert RESOLVED_ROOT.exists()
    assert (RESOLVED_ROOT / "src").exists()
    assert ASSETS_DIR.exists()
    assert USERS_DIR.exists()
    assert APPS_DIR.exists()

    logo_path = get_asset_path("stormos_logo.png")
    assert logo_path == ASSETS_DIR / "stormos_logo.png"
    assert logo_path.exists()


def test_color_constants():
    """Verify DESIGN.md compliant color palette hex strings."""
    assert COLOR_NIGHT_SKY == "#070B16"
    assert COLOR_LIGHTNING == "#38C9FF"
    assert COLOR_STORM_CLOUD == "#101A31"


def test_create_application(qapp):
    """Verify QApplication creation helper sets appropriate metadata."""
    app = create_application()
    assert app is not None
    assert app.applicationName() == APP_NAME


def test_main_window_init(qapp):
    """Verify StormMainWindow constructs and initializes cleanly."""
    window = StormMainWindow(fullscreen=False)
    assert window is not None
    assert APP_NAME in window.windowTitle()
    assert not window.isFullScreen()

    # Test fullscreen toggle
    window.toggle_fullscreen()
    assert window.isFullScreen()

    window.toggle_fullscreen()
    assert not window.isFullScreen()

    window.close()
