"""StormOS Portable Package Build Script.

Creates a self-contained portable ZIP distribution of StormOS that can be
extracted and run without installation on Windows, Linux, or macOS.

Usage:
    python scripts/build_portable.py
    python scripts/build_portable.py --platform windows
    python scripts/build_portable.py --platform linux
    python scripts/build_portable.py --platform macos
"""

import os
import sys
import shutil
import zipfile
import subprocess
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
ASSETS_DIR = PROJECT_ROOT / "assets"
SRC_DIR = PROJECT_ROOT / "src"
MAIN_PY = PROJECT_ROOT / "main.py"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
README = PROJECT_ROOT / "README.md"

# Files and directories to include in the portable package
PORTABLE_INCLUDES = [
    "main.py",
    "requirements.txt",
    "README.md",
    "PLAN.md",
    "DESIGN.md",
    "src/",
    "assets/",
    "scripts/",
]

# Files to exclude from the portable package
PORTABLE_EXCLUDES = {
    "__pycache__",
    ".git",
    ".idea",
    ".venv",
    "venv",
    ".pytest_cache",
    ".refact",
    ".junie",
    "backups",
    "users",
    "store",
    "build",
    "dist",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
}


def should_exclude(path: Path, name: str) -> bool:
    """Check if a path should be excluded from the portable package."""
    for pattern in PORTABLE_EXCLUDES:
        if pattern.startswith("*"):
            # Glob pattern
            if name.endswith(pattern[1:]):
                return True
        elif pattern in path.parts or name == pattern:
            return True
    return False


def create_portable_source_zip() -> Path:
    """Create a portable ZIP containing the source code and assets."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_filename = f"StormOS-portable-source-{timestamp}.zip"
    zip_path = DIST_DIR / zip_filename
    
    DIST_DIR.mkdir(exist_ok=True)
    
    print(f"[*] Creating portable source package: {zip_filename}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in PORTABLE_INCLUDES:
            item_path = PROJECT_ROOT / item
            if item_path.is_file():
                zf.write(item_path, item)
                print(f"  + {item}")
            elif item_path.is_dir():
                for root, dirs, files in os.walk(item_path):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d, d)]
                    
                    for file in files:
                        file_path = Path(root) / file
                        arcname = str(file_path.relative_to(PROJECT_ROOT)).replace(os.sep, "/")
                        
                        if not should_exclude(file_path, file):
                            zf.write(file_path, arcname)
                            print(f"  + {arcname}")
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[+] Portable source package created: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def create_portable_exe_zip() -> Path:
    """Create a portable ZIP containing the compiled executable."""
    exe_dir = DIST_DIR / "StormOS"
    
    if not exe_dir.exists():
        print("[!] Compiled executable not found. Run 'python scripts/build_exe.py' first.")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_filename = f"StormOS-portable-windows-{timestamp}.zip"
    zip_path = DIST_DIR / zip_filename
    
    print(f"[*] Creating portable executable package: {zip_filename}")
    
    # Prepare extra files to add
    launcher_content = """@echo off
REM StormOS Portable Launcher
REM Run StormOS from this directory without installation
echo Starting StormOS...
start "" "StormOS\\StormOS.exe"
"""
    
    portable_readme = """# StormOS Portable

This is the portable version of StormOS - no installation required.

## How to Run

### Windows
Double-click `StormOS-Portable.bat` or run `StormOS\\StormOS.exe` directly.

### Running from Command Line
```
cd StormOS
StormOS.exe
```

## Features
- No installation required
- User data is stored in the `users/` directory relative to the executable
- Can be run from a USB drive or network location
- All settings are preserved between runs

## System Requirements
- Windows 10 or later
- 4GB RAM minimum
- Python 3.13+ (only for development, not for running the portable version)

## Notes
- First run may take a moment as StormOS initializes
- User data is stored locally and persists across runs
- For best performance, run from an SSD
"""
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for item in exe_dir.rglob("*"):
            if item.is_file():
                arcname = str(item.relative_to(exe_dir.parent)).replace(os.sep, "/")
                zf.write(item, arcname)
        
        # Add launcher script inside the context manager
        zf.writestr("StormOS-Portable.bat", launcher_content)
        zf.writestr("README.txt", portable_readme)
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[+] Portable executable package created: {zip_path} ({size_mb:.1f} MB)")
    return zip_path


def create_run_script() -> Path:
    """Create a cross-platform run script for the source-based portable package."""
    run_script = PROJECT_ROOT / "run_stormos.py"
    
    content = '''#!/usr/bin/env python3
"""StormOS Portable Run Script.

This script launches StormOS from a portable source directory.
Works on Windows, Linux, and macOS.
"""

import sys
import os
from pathlib import Path

# Add the source directory to the Python path
script_dir = Path(__file__).resolve().parent
src_dir = script_dir / "src"

if src_dir.exists():
    sys.path.insert(0, str(src_dir))
    
    # Set the project root for StormOS to find assets
    os.environ["STORMOS_PROJECT_ROOT"] = str(script_dir)

try:
    from stormos.core.paths import setup_paths
    setup_paths(script_dir)
except ImportError:
    pass

# Import and run StormOS
try:
    import main
    main.main()
except KeyboardInterrupt:
    print("\\nStormOS shutting down...")
    sys.exit(0)
'''
    
    with open(run_script, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"[+] Created run script: {run_script}")
    return run_script


def create_launch_script() -> Path:
    """Create a shell script for Linux/macOS."""
    launch_script = PROJECT_ROOT / "launch_stormos.sh"
    
    content = '''#!/bin/bash
# StormOS Launcher Script for Linux/macOS
# This script checks dependencies and launches StormOS

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "⚡ Starting StormOS..."

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "Error: Python 3.13+ is required but not found."
    echo "Please install Python from https://www.python.org/downloads/"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
REQUIRED="3.13"

echo "Detected Python version: $PYTHON_VERSION"

# Check if virtual environment exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
fi

# Check if requirements are installed
$PYTHON -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing dependencies..."
    $PYTHON -m pip install -r requirements.txt
fi

# Launch StormOS
$PYTHON main.py

# Handle exit
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "StormOS exited cleanly."
else
    echo "StormOS exited with code $exit_code"
fi

exit $exit_code
'''
    
    with open(launch_script, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Make it executable on Unix systems
    os.chmod(launch_script, 0o755)
    
    print(f"[+] Created launch script: {launch_script}")
    return launch_script


def build_all() -> list:
    """Build all portable packages."""
    packages = []
    
    print("=" * 60)
    print("StormOS Portable Package Builder")
    print("=" * 60)
    print()
    
    # Create run scripts
    create_run_script()
    create_launch_script()
    print()
    
    # Create source-based portable package
    source_zip = create_portable_source_zip()
    if source_zip:
        packages.append(source_zip)
    print()
    
    # Create executable-based portable package (if available)
    exe_zip = create_portable_exe_zip()
    if exe_zip:
        packages.append(exe_zip)
    print()
    
    print("=" * 60)
    print(f"Build complete! {len(packages)} package(s) created in {DIST_DIR}")
    print("=" * 60)
    
    return packages


if __name__ == "__main__":
    platform = "all"
    if "--platform" in sys.argv:
        idx = sys.argv.index("--platform")
        if idx + 1 < len(sys.argv):
            platform = sys.argv[idx + 1].lower()
    
    if platform == "all":
        packages = build_all()
    elif platform == "windows":
        packages = [create_portable_exe_zip()]
    elif platform in ("linux", "macos"):
        packages = [create_portable_source_zip()]
        create_launch_script()
    else:
        print(f"Unknown platform: {platform}")
        print("Supported platforms: windows, linux, macos, all")
        sys.exit(1)
    
    sys.exit(0 if packages else 1)
