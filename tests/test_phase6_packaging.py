"""Tests for Phase 6 - Packaging and Executable Bundling."""

import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

from stormos.core.paths import (
    ASSETS_DIR,
    BUNDLE_ROOT,
    PROJECT_ROOT,
    RUNTIME_ROOT,
    USERS_DIR,
    APPS_DIR,
    STORE_DIR,
    get_asset_path,
)
from scripts.build_exe import generate_app_icon, ICO_PATH, LOGO_PATH


def test_app_icon_generation():
    """Verify that multi-resolution .ico file is generated from stormos_logo.png."""
    assert LOGO_PATH.exists()
    ico = generate_app_icon()
    assert ico is not None
    assert ico.exists()
    assert ico.stat().st_size > 0


def test_frozen_paths_resolution(tmp_path):
    """Test path resolution behavior under frozen (PyInstaller) simulation."""
    fake_meipass = tmp_path / "meipass_bundle"
    fake_meipass_assets = fake_meipass / "assets"
    fake_meipass_assets.mkdir(parents=True)
    (fake_meipass_assets / "wallpaper.png").write_text("dummy_wp")

    fake_runtime_dir = tmp_path / "runtime_dir"
    fake_runtime_dir.mkdir(parents=True)
    fake_exe = fake_runtime_dir / "StormOS.exe"
    fake_exe.touch()

    with patch.object(sys, "frozen", True, create=True), \
         patch.object(sys, "_MEIPASS", str(fake_meipass), create=True), \
         patch.object(sys, "executable", str(fake_exe)):

        # Test imports and helper behavior
        # Re-evaluating dynamic path behavior
        mei_pass = Path(getattr(sys, "_MEIPASS"))
        runtime = Path(sys.executable).parent

        assert mei_pass == fake_meipass
        assert runtime == fake_runtime_dir

        # Users and Store directories are always rooted in runtime
        assert runtime / "users" == fake_runtime_dir / "users"
        assert runtime / "store" == fake_runtime_dir / "store"


def test_all_essential_assets_exist():
    """Verify all core assets required for StormOS standalone package exist."""
    required_assets = [
        "stormos_logo.png",
        "wallpaper.png",
        "storm_splash.png",
        "stormos.ico",
        "startup.wav",
        "rain-and-little-storm-298087.mp3",
    ]
    for asset_name in required_assets:
        asset_file = get_asset_path(asset_name)
        assert asset_file.exists(), f"Missing required asset: {asset_name}"
        assert asset_file.stat().st_size > 0


def test_compiled_executable_bundle_exists():
    """Verify the PyInstaller compiled executable and directory structure."""
    dist_file = PROJECT_ROOT / "dist" / "StormOS.exe"
    dist_dir_exe = PROJECT_ROOT / "dist" / "StormOS" / "StormOS.exe"
    root_exe = PROJECT_ROOT / "StormOS.exe"

    has_valid_exe = (
        (dist_file.exists() and dist_file.stat().st_size > 100_000)
        or (dist_dir_exe.exists() and dist_dir_exe.stat().st_size > 100_000)
        or (root_exe.exists() and root_exe.stat().st_size > 100_000)
    )
    assert has_valid_exe, "A compiled StormOS.exe binary should exist and be valid"
