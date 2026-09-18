"""Path resolution helpers for StormOS."""

import sys
from pathlib import Path

# Base project root directory (or executable directory when frozen)
if getattr(sys, "frozen", False):
    # PyInstaller temporary extraction directory for bundled static assets and code
    mei_pass = getattr(sys, "_MEIPASS", None)
    if mei_pass:
        BUNDLE_ROOT = Path(mei_pass)
    else:
        BUNDLE_ROOT = Path(sys.executable).resolve().parent
    # Persistent runtime directory where user profiles, installed apps, and store packages reside
    RUNTIME_ROOT = Path(sys.executable).resolve().parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    RUNTIME_ROOT = BUNDLE_ROOT

PROJECT_ROOT = RUNTIME_ROOT

# Core subdirectories
SRC_DIR = BUNDLE_ROOT / "src"

# Asset directory: check bundle assets first, then _internal/assets, fallback to runtime assets
if (BUNDLE_ROOT / "assets").exists():
    ASSETS_DIR = BUNDLE_ROOT / "assets"
elif (RUNTIME_ROOT / "_internal" / "assets").exists():
    ASSETS_DIR = RUNTIME_ROOT / "_internal" / "assets"
else:
    ASSETS_DIR = RUNTIME_ROOT / "assets"

# Persistent user and app data directories reside in RUNTIME_ROOT
USERS_DIR = RUNTIME_ROOT / "users"
APPS_DIR = RUNTIME_ROOT / "apps"
STORE_DIR = RUNTIME_ROOT / "store"


def get_asset_path(filename: str) -> Path:
    """Return the absolute path to an asset file in the assets/ directory."""
    if (ASSETS_DIR / filename).exists():
        return ASSETS_DIR / filename
    if (BUNDLE_ROOT / "assets" / filename).exists():
        return BUNDLE_ROOT / "assets" / filename
    if (RUNTIME_ROOT / "_internal" / "assets" / filename).exists():
        return RUNTIME_ROOT / "_internal" / "assets" / filename
    if (RUNTIME_ROOT / "assets" / filename).exists():
        return RUNTIME_ROOT / "assets" / filename
    return ASSETS_DIR / filename
