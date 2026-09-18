"""Desktop environment components (Storm Dock, Command Center, Wallpaper, Dialogs)."""

from stormos.desktop.command_center import CommandCenter
from stormos.desktop.desktop_view import DesktopCardWidget, DesktopView
from stormos.desktop.safe_exit_dialog import SafeExitDialog
from stormos.desktop.storm_dock import StormDock

__all__ = [
    "CommandCenter",
    "DesktopCardWidget",
    "DesktopView",
    "SafeExitDialog",
    "StormDock",
]
