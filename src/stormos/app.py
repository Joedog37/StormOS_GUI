"""Application initialization and runner for StormOS."""

import sys
from PySide6.QtWidgets import QApplication
from stormos.core.constants import APP_NAME, ORG_NAME
from stormos.ui.main_window import StormMainWindow


def create_application() -> QApplication:
    """Create or retrieve the QApplication instance with proper metadata."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    return app


def run_app(fullscreen: bool = True) -> int:
    """Run the StormOS application lifecycle."""
    app = create_application()
    window = StormMainWindow(fullscreen=fullscreen)
    window.show()
    return app.exec()
