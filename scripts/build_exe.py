"""StormOS Executable Build Script.

Builds a standalone Windows executable (.exe) for StormOS using PyInstaller.
Bundles all assets, modules, and styles while preserving persistent user data directories.
"""

import os
import sys
import shutil
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
LOGO_PATH = ASSETS_DIR / "stormos_logo.png"
ICO_PATH = ASSETS_DIR / "stormos.ico"


def generate_app_icon() -> Path:
    """Generate a multi-resolution Windows .ico from stormos_logo.png."""
    if not LOGO_PATH.exists():
        print(f"[!] Logo not found at {LOGO_PATH}, skipping icon generation.")
        return None

    print(f"[*] Generating Windows icon {ICO_PATH} from {LOGO_PATH.name}...")
    img = Image.open(LOGO_PATH)
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ICO_PATH, format="ICO", sizes=icon_sizes)
    print(f"[+] Successfully generated {ICO_PATH}")
    return ICO_PATH


def build_executable(onefile: bool = False) -> bool:
    """Run PyInstaller with optimal flags for StormOS."""
    generate_app_icon()

    import PyInstaller.__main__

    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"

    # PyInstaller arguments
    args = [
        str(PROJECT_ROOT / "main.py"),
        f"--name=StormOS",
        "--noconfirm",
        "--clean",
        "--windowed",  # Suppress background cmd console window for seamless OS feel
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--add-data={ASSETS_DIR}{os.pathsep}assets",
        f"--paths={PROJECT_ROOT / 'src'}",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=stormos",
        "--hidden-import=stormos.core",
        "--hidden-import=stormos.core.constants",
        "--hidden-import=stormos.core.paths",
        "--hidden-import=stormos.core.security",
        "--hidden-import=stormos.ui",
        "--hidden-import=stormos.ui.main_window",
        "--hidden-import=stormos.ui.theme",
        "--hidden-import=stormos.ui.wallpaper_manager",
        "--hidden-import=stormos.screens",
        "--hidden-import=stormos.screens.boot_screen",
        "--hidden-import=stormos.screens.login_screen",
        "--hidden-import=stormos.screens.signup_dialog",
        "--hidden-import=stormos.desktop",
        "--hidden-import=stormos.desktop.desktop_view",
        "--hidden-import=stormos.desktop.storm_dock",
        "--hidden-import=stormos.desktop.command_center",
        "--hidden-import=stormos.desktop.window",
        "--hidden-import=stormos.desktop.safe_exit_dialog",
        "--hidden-import=stormos.apps",
        "--hidden-import=stormos.apps.registry",
        "--hidden-import=stormos.apps.calculator",
        "--hidden-import=stormos.apps.notes",
        "--hidden-import=stormos.apps.files",
        "--hidden-import=stormos.apps.terminal",
        "--hidden-import=stormos.apps.activity_monitor",
        "--hidden-import=stormos.apps.settings",
        "--hidden-import=stormos.apps.app_manager",
        "--hidden-import=stormos.services",
        "--hidden-import=stormos.services.user_manager",
        "--hidden-import=stormos.services.app_installer",
    ]

    if ICO_PATH.exists():
        args.append(f"--icon={ICO_PATH}")

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    print(f"[*] Starting PyInstaller build for StormOS...")
    try:
        PyInstaller.__main__.run(args)
        print(f"[+] Build complete! Output located at: {dist_dir}")
        return True
    except Exception as e:
        print(f"[!] PyInstaller build failed: {e}")
        return False


if __name__ == "__main__":
    is_onefile = "--onefile" in sys.argv
    success = build_executable(onefile=is_onefile)
    sys.exit(0 if success else 1)
