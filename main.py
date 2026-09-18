"""Root launcher for StormOS desktop environment."""

import sys
from pathlib import Path

# Add src/ to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stormos.app import run_app

if __name__ == "__main__":
    sys.exit(run_app(fullscreen=True))
