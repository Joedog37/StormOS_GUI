"""Main entry point for StormOS inside src/."""

import sys
from pathlib import Path

# Ensure src/ directory is on sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from stormos.app import run_app


def main() -> int:
    """Run the StormOS desktop environment."""
    return run_app(fullscreen=True)


if __name__ == "__main__":
    sys.exit(main())
