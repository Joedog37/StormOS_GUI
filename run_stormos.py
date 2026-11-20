#!/usr/bin/env python3
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
    print("\nStormOS shutting down...")
    sys.exit(0)
